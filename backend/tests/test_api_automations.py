"""HTTP contract tests for versioned automation definitions (Design Book 22)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.automation import AutomationFlowVersion
from app.models.organization import Organization
from app.models.user import User

PASSWORD = "Sup3r-Secret-Pass1"
AUTOMATIONS = "/api/v1/automations"


async def _headers(client, make_user, *, email: str, **kwargs) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kwargs)
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _login(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _simple_graph(message: str = "Notify the owner") -> dict:
    return {
        "nodes": [
            {
                "id": "trigger-1",
                "kind": "trigger",
                "label": "New contact",
                "config": {"event": "contact.created"},
            },
            {
                "id": "notify-1",
                "kind": "notification",
                "label": "Notify owner",
                "config": {"message": message},
            },
        ],
        "edges": [{"id": "edge-1", "source": "trigger-1", "target": "notify-1"}],
    }


def _campaign_graph(*, approval: bool) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "lead.stage_changed"},
        },
        {
            "id": "campaign-1",
            "kind": "campaign",
            "config": {"campaign_id": str(uuid.uuid4())},
        },
    ]
    edges = [{"id": "edge-1", "source": "trigger-1", "target": "campaign-1"}]
    if approval:
        nodes.append(
            {
                "id": "approval-1",
                "kind": "approval",
                "config": {"permission": "campaigns:send"},
            }
        )
        edges.append({"id": "edge-2", "source": "campaign-1", "target": "approval-1"})
    return {"nodes": nodes, "edges": edges}


async def _create(client, headers, *, graph: dict | None = None, name: str = "Lead welcome"):
    body = {"name": name, "description": "A governed workflow draft"}
    if graph is not None:
        body["graph"] = graph
    return await client.post(AUTOMATIONS, headers=headers, json=body)


def _assert_problem(response, status: int, code: str | None = None) -> None:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status
    if code is not None:
        assert body["code"] == code


async def test_create_list_get_and_validate_incomplete_draft(client, make_user) -> None:
    owner = await _headers(client, make_user, email="owner@automation.co", is_superuser=True)

    response = await _create(client, owner)

    assert response.status_code == 201, response.text
    flow = response.json()
    uuid.UUID(flow["id"])
    assert flow["status"] == "draft"
    assert flow["graph"] == {"nodes": [], "edges": []}
    assert flow["has_unpublished_changes"] is True
    assert (await client.get(AUTOMATIONS, headers=owner)).json()["total"] == 1
    assert (await client.get(f"{AUTOMATIONS}/{flow['id']}", headers=owner)).json()["id"] == flow["id"]

    validation = await client.post(f"{AUTOMATIONS}/{flow['id']}/validate", headers=owner)
    assert validation.status_code == 200
    assert validation.json() == {
        "valid": False,
        "issues": [
            {
                "code": "nodes_required",
                "message": "Add at least one node before publishing.",
                "node_id": None,
            }
        ],
    }


async def test_publish_versions_restore_and_active_snapshot_immutability(
    client, make_user, session_factory
) -> None:
    owner = await _headers(client, make_user, email="versions@automation.co", is_superuser=True)
    flow = (await _create(client, owner, graph=_simple_graph())).json()

    first = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/publish",
        headers=owner,
        json={"expected_row_version": flow["row_version"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["active_version_no"] == 1
    assert first.json()["has_unpublished_changes"] is False

    updated = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}",
        headers=owner,
        json={
            "graph": _simple_graph("Notify the manager"),
            "expected_row_version": first.json()["row_version"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["active_version_no"] == 1
    assert updated.json()["has_unpublished_changes"] is True

    second = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/publish",
        headers=owner,
        json={"expected_row_version": updated.json()["row_version"]},
    )
    assert second.json()["active_version_no"] == 2
    versions = (await client.get(f"{AUTOMATIONS}/{flow['id']}/versions", headers=owner)).json()[
        "data"
    ]
    assert [item["version_no"] for item in versions] == [2, 1]
    assert versions[0]["content_hash"] != versions[1]["content_hash"]
    assert versions[1]["graph"]["nodes"][1]["config"]["message"] == "Notify the owner"

    restored = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/versions/1/restore",
        headers=owner,
        json={"expected_row_version": second.json()["row_version"]},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["active_version_no"] == 2
    assert restored.json()["has_unpublished_changes"] is True
    assert restored.json()["graph"] == versions[1]["graph"]
    async with session_factory() as session:
        rows = list((await session.scalars(select(AutomationFlowVersion))).all())
        assert len(rows) == 2


async def test_publication_is_fail_closed_for_invalid_graphs(client, make_user) -> None:
    owner = await _headers(client, make_user, email="invalid@automation.co", is_superuser=True)
    flow = (await _create(client, owner, graph=_campaign_graph(approval=False))).json()

    response = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/publish", headers=owner, json={}
    )

    _assert_problem(response, 422, "automation_definition_invalid")
    errors = response.json()["errors"]
    assert {error["code"] for error in errors} == {"campaign_approval_required"}
    assert {error["field"] for error in errors} == {"graph.nodes.campaign-1"}

    cycle = _simple_graph()
    cycle["edges"].append(
        {"id": "edge-2", "source": "notify-1", "target": "trigger-1"}
    )
    changed = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}", headers=owner, json={"graph": cycle}
    )
    validation = await client.post(f"{AUTOMATIONS}/{flow['id']}/validate", headers=owner)
    assert changed.status_code == 200
    assert {issue["code"] for issue in validation.json()["issues"]} >= {
        "cycle_detected",
        "trigger_has_input",
    }


async def test_campaign_definition_publishes_only_with_downstream_approval(client, make_user) -> None:
    owner = await _headers(client, make_user, email="approval@automation.co", is_superuser=True)
    flow = (await _create(client, owner, graph=_campaign_graph(approval=True))).json()

    validation = await client.post(f"{AUTOMATIONS}/{flow['id']}/validate", headers=owner)
    published = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/publish", headers=owner, json={}
    )

    assert validation.json() == {"valid": True, "issues": []}
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"


async def test_disable_enable_and_optimistic_concurrency(client, make_user) -> None:
    owner = await _headers(client, make_user, email="state@automation.co", is_superuser=True)
    flow = (await _create(client, owner, graph=_simple_graph())).json()
    draft_disable = await client.post(f"{AUTOMATIONS}/{flow['id']}/disable", headers=owner, json={})
    _assert_problem(draft_disable, 409, "automation_state")

    published = (
        await client.post(f"{AUTOMATIONS}/{flow['id']}/publish", headers=owner, json={})
    ).json()
    stale = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}",
        headers=owner,
        json={"name": "Stale write", "expected_row_version": flow["row_version"]},
    )
    _assert_problem(stale, 409, "version_conflict")

    disabled = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/disable",
        headers=owner,
        json={"expected_row_version": published["row_version"]},
    )
    enabled = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/enable",
        headers=owner,
        json={"expected_row_version": disabled.json()["row_version"]},
    )
    assert disabled.json()["status"] == "disabled"
    assert enabled.json()["status"] == "published"


async def test_typed_node_configs_reject_unknown_or_incomplete_payloads(client, make_user) -> None:
    owner = await _headers(client, make_user, email="typed@automation.co", is_superuser=True)
    invalid = _simple_graph()
    invalid["nodes"][0]["config"]["unexpected"] = True
    _assert_problem(await _create(client, owner, graph=invalid), 422, "validation_error")

    schedule = _simple_graph()
    schedule["nodes"][0]["config"] = {"event": "schedule"}
    _assert_problem(await _create(client, owner, graph=schedule), 422, "validation_error")

    unresolved = _campaign_graph(approval=True)
    unresolved["nodes"][1]["config"]["campaign_id"] = "00000000-0000-0000-0000-000000000000"
    flow = (await _create(client, owner, graph=unresolved, name="Unresolved reference")).json()
    validation = await client.post(f"{AUTOMATIONS}/{flow['id']}/validate", headers=owner)
    assert {issue["code"] for issue in validation.json()["issues"]} == {"reference_required"}


async def test_permissions_allow_manager_authoring_and_analyst_read_only(client, make_user) -> None:
    manager = await _headers(client, make_user, email="manager@automation.co", roles=("manager",))
    analyst = await _headers(client, make_user, email="analyst@automation.co", roles=("analyst",))
    agent = await _headers(client, make_user, email="agent@automation.co", roles=("agent",))

    created = await _create(client, manager, graph=_simple_graph())
    assert created.status_code == 201, created.text
    flow_id = created.json()["id"]
    assert (await client.get(f"{AUTOMATIONS}/{flow_id}", headers=analyst)).status_code == 200
    _assert_problem(
        await client.patch(f"{AUTOMATIONS}/{flow_id}", headers=analyst, json={"name": "No"}),
        403,
        "forbidden",
    )
    _assert_problem(await client.get(f"{AUTOMATIONS}/{flow_id}", headers=agent), 403, "forbidden")
    assert (
        await client.post(f"{AUTOMATIONS}/{flow_id}/publish", headers=manager, json={})
    ).status_code == 200


async def test_foreign_tenant_ids_are_hidden_and_mutations_are_audited(
    client, make_user, session_factory, organization
) -> None:
    owner = await _headers(client, make_user, email="tenant-one@automation.co", is_superuser=True)
    flow = (await _create(client, owner, graph=_simple_graph())).json()
    await client.post(f"{AUTOMATIONS}/{flow['id']}/publish", headers=owner, json={})

    async with session_factory() as session:
        other_org = Organization(name="Other", slug="other-automation")
        session.add(other_org)
        await session.flush()
        session.add(
            User(
                organization_id=other_org.id,
                email="tenant-two@automation.co",
                password_hash=hash_password(PASSWORD),
                full_name="Other Owner",
                is_active=True,
                is_superuser=True,
            )
        )
        await session.commit()
    other = await _login(client, "tenant-two@automation.co")
    _assert_problem(await client.get(f"{AUTOMATIONS}/{flow['id']}", headers=other), 404)
    _assert_problem(
        await client.post(f"{AUTOMATIONS}/{flow['id']}/disable", headers=other, json={}), 404
    )

    async with session_factory() as session:
        actions = list(
            (
                await session.scalars(
                    select(AuditLog.action).where(AuditLog.entity_type == "automation_flow")
                )
            ).all()
        )
        assert actions == ["automation.created", "automation.published"]


def test_openapi_mounts_every_automation_operation() -> None:
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/automations",
        "/api/v1/automations/{automation_id}",
        "/api/v1/automations/{automation_id}/validate",
        "/api/v1/automations/{automation_id}/publish",
        "/api/v1/automations/{automation_id}/versions",
        "/api/v1/automations/{automation_id}/versions/{version_no}/restore",
        "/api/v1/automations/{automation_id}/disable",
        "/api/v1/automations/{automation_id}/enable",
    }
    assert expected <= set(paths)
