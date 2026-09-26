"""Governed personal and team-shared Campaign saved-view contracts."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.reactivation_view import WorkspaceView

PASSWORD = "Sup3r-Secret-Pass!"
VIEWS = "/api/v1/campaigns/views"
CONTACT_VIEWS = "/api/v1/contacts/views"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_reader_saves_portable_private_view_without_page(client, make_user):
    analyst = await make_user(email="campaign-view-analyst@vi.co", roles=("analyst",))
    manager = await make_user(email="campaign-view-manager@vi.co", roles=("manager",))
    analyst_headers = await _headers(client, analyst.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "My active campaigns",
        "visibility": "private",
        "filters": {
            "q": "August",
            "status": "running",
            "sort": "-total_recipients",
            "page": 9,
        },
    }

    created = await client.post(VIEWS, headers=analyst_headers, json=payload)
    own = await client.get(VIEWS, headers=analyst_headers)
    other = await client.get(VIEWS, headers=manager_headers)

    assert created.status_code == 201, created.text
    assert created.json()["display"] == "list"
    assert created.json()["is_owner"] is True
    assert created.json()["can_delete"] is True
    assert created.json()["filters"] == {
        "q": "August",
        "status": "running",
        "sort": "-total_recipients",
    }
    assert own.json()["data"] == [created.json()]
    assert other.json()["data"] == []


@pytest.mark.anyio
async def test_team_views_require_campaign_manager_permission_and_are_visible(client, make_user):
    analyst = await make_user(email="campaign-shared-analyst@vi.co", roles=("analyst",))
    manager = await make_user(email="campaign-shared-manager@vi.co", roles=("manager",))
    analyst_headers = await _headers(client, analyst.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "Team broadcasts",
        "visibility": "shared",
        "filters": {"status": "scheduled", "sort": "created_at"},
    }

    forbidden = await client.post(VIEWS, headers=analyst_headers, json=payload)
    created = await client.post(VIEWS, headers=manager_headers, json=payload)
    listed = await client.get(VIEWS, headers=analyst_headers)

    assert forbidden.status_code == 403
    assert created.status_code == 201, created.text
    assert listed.json()["data"][0]["name"] == "Team broadcasts"
    assert listed.json()["data"][0]["can_delete"] is False
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=analyst_headers)
    ).status_code == 403
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=manager_headers)
    ).status_code == 204


@pytest.mark.anyio
async def test_campaign_workspace_names_and_rows_are_isolated(client, make_user, session_factory):
    manager = await make_user(email="campaign-workspace-manager@vi.co", roles=("manager",))
    headers = await _headers(client, manager.user.email)
    name = "Priority queue"

    campaign = await client.post(
        VIEWS,
        headers=headers,
        json={"name": name, "visibility": "shared", "filters": {}},
    )
    contact = await client.post(
        CONTACT_VIEWS,
        headers=headers,
        json={"name": name, "visibility": "shared", "filters": {}},
    )

    assert campaign.status_code == 201, campaign.text
    assert contact.status_code == 201, contact.text
    assert [row["name"] for row in (await client.get(VIEWS, headers=headers)).json()["data"]] == [
        name
    ]
    async with session_factory() as session:
        workspaces = set((await session.scalars(select(WorkspaceView.workspace))).all())
    assert {"campaigns", "contacts"} <= workspaces


@pytest.mark.anyio
async def test_campaign_view_validation_and_audit(client, make_user, session_factory):
    manager = await make_user(email="campaign-view-audit@vi.co", roles=("manager",))
    headers = await _headers(client, manager.user.email)

    invalid = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": "Invalid",
            "visibility": "shared",
            "filters": {"status": "not-a-status"},
        },
    )
    created = await client.post(
        VIEWS,
        headers=headers,
        json={"name": "Audited campaigns", "visibility": "shared", "filters": {}},
    )
    assert invalid.status_code == 422
    assert created.status_code == 201, created.text
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=headers)
    ).status_code == 204

    async with session_factory() as session:
        actions = set((await session.scalars(select(AuditLog.action))).all())
    assert {"campaign_view.created", "campaign_view.deleted"} <= actions


def test_openapi_declares_campaign_saved_view_operations() -> None:
    from app.main import create_app

    schema = create_app().openapi()
    assert {"get", "post"} <= set(schema["paths"][VIEWS])
    assert "delete" in schema["paths"][f"{VIEWS}/{{view_id}}"]
    create_schema = schema["components"]["schemas"]["CampaignViewCreate"]
    assert {"name", "filters"} <= set(create_schema["required"])
