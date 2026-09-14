"""Governed personal and team-shared Reactivation saved-view contracts."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.reactivation_view import ReactivationView
from app.models.user import User

PASSWORD = "Sup3r-Secret-Pass!"
VIEWS = "/api/v1/reactivation/views"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_reader_saves_private_view_and_other_users_cannot_see_it(client, make_user):
    agent = await make_user(email="view-agent@vi.co", roles=("agent",))
    manager = await make_user(email="view-manager@vi.co", roles=("manager",))
    agent_headers = await _headers(client, agent.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "My priority follow-ups",
        "visibility": "private",
        "display": "list",
        "filters": {
            "q": "Asha",
            "stage": "lead_confirmed",
            "label": "priority",
            "owner_user_id": agent.user.public_id,
            "reminder_view": "overdue",
            "reminder_date": "2026-08-24",
        },
    }

    created = await client.post(VIEWS, headers=agent_headers, json=payload)
    own = await client.get(VIEWS, headers=agent_headers)
    other = await client.get(VIEWS, headers=manager_headers)

    assert created.status_code == 201, created.text
    assert created.json()["is_owner"] is True
    assert created.json()["can_delete"] is True
    assert created.json()["filters"] | payload["filters"] == created.json()["filters"]
    assert own.json()["data"] == [created.json()]
    assert other.json()["data"] == []


@pytest.mark.anyio
async def test_team_views_require_manager_permission_and_are_visible_to_readers(client, make_user):
    agent = await make_user(email="shared-agent@vi.co", roles=("agent",))
    manager = await make_user(email="shared-manager@vi.co", roles=("manager",))
    agent_headers = await _headers(client, agent.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "Overdue team queue",
        "visibility": "shared",
        "display": "board",
        "filters": {"reminder_view": "overdue"},
    }

    forbidden = await client.post(VIEWS, headers=agent_headers, json=payload)
    created = await client.post(VIEWS, headers=manager_headers, json=payload)
    listed = await client.get(VIEWS, headers=agent_headers)

    assert forbidden.status_code == 403
    assert created.status_code == 201, created.text
    assert created.json()["can_delete"] is True
    assert listed.status_code == 200
    assert listed.json()["data"][0]["name"] == "Overdue team queue"
    assert listed.json()["data"][0]["can_delete"] is False

    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=agent_headers)
    ).status_code == 403
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=manager_headers)
    ).status_code == 204


@pytest.mark.anyio
async def test_view_names_are_case_insensitively_unique_within_each_scope(client, make_user):
    first = await make_user(email="scope-one@vi.co", roles=("manager",))
    second = await make_user(email="scope-two@vi.co", roles=("manager",))
    first_headers = await _headers(client, first.user.email)
    second_headers = await _headers(client, second.user.email)

    private = {"name": "My Queue", "visibility": "private", "filters": {}}
    assert (await client.post(VIEWS, headers=first_headers, json=private)).status_code == 201
    assert (
        await client.post(
            VIEWS,
            headers=first_headers,
            json={**private, "name": "my QUEUE"},
        )
    ).status_code == 409
    assert (await client.post(VIEWS, headers=second_headers, json=private)).status_code == 201

    shared = {"name": "Team Queue", "visibility": "shared", "filters": {}}
    assert (await client.post(VIEWS, headers=first_headers, json=shared)).status_code == 201
    assert (
        await client.post(
            VIEWS,
            headers=second_headers,
            json={**shared, "name": "team QUEUE"},
        )
    ).status_code == 409


@pytest.mark.anyio
async def test_private_and_cross_tenant_view_ids_are_hidden(client, make_user, session_factory):
    agent = await make_user(email="hidden-agent@vi.co", roles=("agent",))
    manager = await make_user(email="hidden-manager@vi.co", roles=("manager",))
    agent_headers = await _headers(client, agent.user.email)
    manager_headers = await _headers(client, manager.user.email)
    own = await client.post(
        VIEWS,
        headers=agent_headers,
        json={"name": "Hidden private", "visibility": "private", "filters": {}},
    )

    async with session_factory() as session:
        foreign_org = Organization(name="Foreign views", slug="foreign-reactivation-views")
        session.add(foreign_org)
        await session.flush()
        foreign_user = User(
            organization_id=foreign_org.id,
            email="foreign-view-owner@vi.co",
            password_hash=hash_password(PASSWORD),
            full_name="Foreign owner",
            is_superuser=True,
        )
        session.add(foreign_user)
        await session.flush()
        foreign = ReactivationView(
            organization_id=foreign_org.id,
            created_by_user_id=foreign_user.id,
            name="Foreign shared",
            visibility="shared",
            display="board",
            filters_json={},
        )
        session.add(foreign)
        await session.commit()
        foreign_id = foreign.public_id

    assert own.status_code == 201
    assert (
        await client.delete(f"{VIEWS}/{own.json()['id']}", headers=manager_headers)
    ).status_code == 404
    assert (
        await client.delete(f"{VIEWS}/{foreign_id}", headers=manager_headers)
    ).status_code == 404


@pytest.mark.anyio
async def test_saved_view_mutations_are_audited_and_filters_are_validated(
    client, make_user, session_factory
):
    manager = await make_user(email="audit-view-manager@vi.co", roles=("manager",))
    headers = await _headers(client, manager.user.email)

    invalid = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": "Invalid stage",
            "visibility": "shared",
            "filters": {"stage": "invented", "reminder_view": "someday"},
        },
    )
    created = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": "Audited view",
            "visibility": "shared",
            "filters": {"stage": "documents_pending"},
        },
    )
    assert invalid.status_code == 422
    assert created.status_code == 201, created.text
    deleted = await client.delete(f"{VIEWS}/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    async with session_factory() as session:
        actions = set((await session.scalars(select(AuditLog.action))).all())
    assert {"reactivation_view.created", "reactivation_view.deleted"} <= actions


def test_openapi_declares_reactivation_saved_view_operations() -> None:
    from app.main import create_app

    schema = create_app().openapi()
    assert {"get", "post"} <= set(schema["paths"][VIEWS])
    assert "delete" in schema["paths"][f"{VIEWS}/{{view_id}}"]
    create_schema = schema["components"]["schemas"]["ReactivationViewCreate"]
    assert {"name", "filters"} <= set(create_schema["required"])
