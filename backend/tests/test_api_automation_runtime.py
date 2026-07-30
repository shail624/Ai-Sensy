"""Runtime and HTTP contract tests for deterministic automation test runs (Design Book 23)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.automation import (
    AUTOMATION_ATTEMPT_INTERRUPTED,
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SUCCEEDED,
    AUTOMATION_RUN_RUNNING,
    AutomationRun,
    AutomationStepAttempt,
)
from app.models.job import JobMetadata
from app.models.organization import Organization
from app.models.user import User
from app.services.automation_runtime_service import AutomationRuntimeService

PASSWORD = "Sup3r-Secret-Pass1"
AUTOMATIONS = "/api/v1/automations"


async def _headers(client, make_user, *, email: str, **kwargs) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kwargs)
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _login(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _graph() -> dict:
    return {
        "nodes": [
            {
                "id": "trigger-1",
                "kind": "trigger",
                "config": {"event": "contact.created"},
            },
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {"field": "contact.tier", "operator": "eq", "value": "gold"},
            },
            {
                "id": "notify-1",
                "kind": "notification",
                "config": {"message": "Notify the owner"},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "condition-1"},
            {"id": "edge-2", "source": "condition-1", "target": "notify-1"},
        ],
    }


async def _published(client, headers) -> dict:
    created = await client.post(
        AUTOMATIONS,
        headers=headers,
        json={"name": "Lead qualification", "graph": _graph()},
    )
    assert created.status_code == 201, created.text
    response = await client.post(
        f"{AUTOMATIONS}/{created.json()['id']}/publish", headers=headers, json={}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _key() -> str:
    return str(uuid.uuid4())


async def test_test_run_is_durable_and_idempotent(
    client, make_user, session_factory, monkeypatch
) -> None:
    owner = await _headers(
        client, make_user, email="runtime-owner@example.com", is_superuser=True
    )
    flow = await _published(client, owner)
    dispatched: list[tuple[list[int], str]] = []

    def _dispatch(*, args, task_id):
        dispatched.append((args, task_id))

    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async", _dispatch
    )
    key = _key()
    first = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**owner, "Idempotency-Key": key},
        json={"input": {"contact": {"tier": "gold"}}},
    )
    replay = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**owner, "Idempotency-Key": key},
        json={"input": {"contact": {"tier": "gold"}}},
    )

    assert first.status_code == 202, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert len(dispatched) == 1
    assert dispatched[0][1] == first.json()["correlation_id"]
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AutomationRun)) == 1
        job = (await session.scalars(select(JobMetadata))).one()
        assert job.queue == "automation.run"
        assert job.ref_type == "automation_run"


async def test_idempotency_key_cannot_be_reused_for_different_input(
    client, make_user, monkeypatch
) -> None:
    owner = await _headers(
        client, make_user, email="runtime-conflict@example.com", is_superuser=True
    )
    flow = await _published(client, owner)
    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async",
        lambda **_: None,
    )
    key = _key()
    headers = {**owner, "Idempotency-Key": key}
    assert (
        await client.post(
            f"{AUTOMATIONS}/{flow['id']}/test-runs",
            headers=headers,
            json={"input": {"contact": {"tier": "gold"}}},
        )
    ).status_code == 202
    conflict = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers=headers,
        json={"input": {"contact": {"tier": "silver"}}},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "automation_run_conflict"


async def test_worker_executes_pinned_graph_in_order_without_effects(
    client, make_user, session_factory, monkeypatch
) -> None:
    owner = await _headers(
        client, make_user, email="runtime-worker@example.com", is_superuser=True
    )
    flow = await _published(client, owner)
    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async",
        lambda **_: None,
    )
    created = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**owner, "Idempotency-Key": _key()},
        json={"input": {"contact": {"tier": "gold"}}},
    )
    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        assert await AutomationRuntimeService(session).execute_test_run(run.id) == "succeeded"

    detail = await client.get(
        f"/api/v1/automation-runs/{created.json()['id']}", headers=owner
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "succeeded"
    assert body["completed_steps"] == body["total_steps"] == 3
    assert [attempt["node_id"] for attempt in body["attempts"]] == [
        "trigger-1",
        "condition-1",
        "notify-1",
    ]
    assert body["attempts"][1]["output"]["matched"] is True
    assert body["attempts"][2]["output"]["simulated"] is True


async def test_redelivery_resumes_successful_checkpoints(
    client, make_user, session_factory, monkeypatch
) -> None:
    owner = await _headers(
        client, make_user, email="runtime-resume@example.com", is_superuser=True
    )
    flow = await _published(client, owner)
    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async",
        lambda **_: None,
    )
    await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**owner, "Idempotency-Key": _key()},
        json={"input": {"contact": {"tier": "gold"}}},
    )
    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        run.status = AUTOMATION_RUN_RUNNING
        session.add_all(
            [
                AutomationStepAttempt(
                    organization_id=run.organization_id,
                    run_id=run.id,
                    node_id="trigger-1",
                    node_kind="trigger",
                    attempt_no=1,
                    status=AUTOMATION_ATTEMPT_SUCCEEDED,
                ),
                AutomationStepAttempt(
                    organization_id=run.organization_id,
                    run_id=run.id,
                    node_id="condition-1",
                    node_kind="condition",
                    attempt_no=1,
                    status=AUTOMATION_ATTEMPT_RUNNING,
                ),
            ]
        )
        await session.commit()
        await AutomationRuntimeService(session).execute_test_run(run.id)
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        assert [a.status for a in attempts] == [
            AUTOMATION_ATTEMPT_SUCCEEDED,
            AUTOMATION_ATTEMPT_INTERRUPTED,
            AUTOMATION_ATTEMPT_SUCCEEDED,
            AUTOMATION_ATTEMPT_SUCCEEDED,
        ]
        assert [a.node_id for a in attempts].count("trigger-1") == 1


async def test_dirty_draft_is_not_implicitly_executed(
    client, make_user, monkeypatch
) -> None:
    owner = await _headers(
        client, make_user, email="runtime-dirty@example.com", is_superuser=True
    )
    flow = await _published(client, owner)
    updated = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}", headers=owner, json={"name": "Unpublished name"}
    )
    assert updated.status_code == 200
    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async",
        lambda **_: None,
    )
    response = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**owner, "Idempotency-Key": _key()},
        json={"input": {}},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "automation_run_conflict"


async def test_runtime_permissions_tenant_isolation_and_audit(
    client, make_user, session_factory, monkeypatch
) -> None:
    manager = await _headers(
        client, make_user, email="runtime-manager@example.com", roles=("manager",)
    )
    analyst = await _headers(
        client, make_user, email="runtime-analyst@example.com", roles=("analyst",)
    )
    flow = await _published(client, manager)
    monkeypatch.setattr(
        "app.api.v1.endpoints.automations.execute_automation_test_run.apply_async",
        lambda **_: None,
    )
    created = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/test-runs",
        headers={**manager, "Idempotency-Key": _key()},
        json={"input": {}},
    )
    assert created.status_code == 202
    assert (
        await client.get(f"{AUTOMATIONS}/{flow['id']}/runs", headers=analyst)
    ).status_code == 200
    assert (
        await client.post(
            f"{AUTOMATIONS}/{flow['id']}/test-runs",
            headers={**analyst, "Idempotency-Key": _key()},
            json={"input": {}},
        )
    ).status_code == 403

    async with session_factory() as session:
        other_org = Organization(name="Other runtime", slug="other-runtime")
        session.add(other_org)
        await session.flush()
        session.add(
            User(
                organization_id=other_org.id,
                email="runtime-other@example.com",
                password_hash=hash_password(PASSWORD),
                full_name="Other Owner",
                is_active=True,
                is_superuser=True,
            )
        )
        await session.commit()
    other = await _login(client, "runtime-other@example.com")
    assert (
        await client.get(f"/api/v1/automation-runs/{created.json()['id']}", headers=other)
    ).status_code == 404
    async with session_factory() as session:
        actions = list(
            (
                await session.scalars(
                    select(AuditLog.action).where(
                        AuditLog.entity_type == "automation_run"
                    )
                )
            ).all()
        )
        assert actions == ["automation.test_run_created"]


def test_openapi_mounts_automation_runtime_operations() -> None:
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert {
        "/api/v1/automations/{automation_id}/test-runs",
        "/api/v1/automations/{automation_id}/runs",
        "/api/v1/automation-runs/{run_id}",
    } <= set(paths)
