"""Governed personal and team-shared Report saved-view contracts."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.reactivation_view import WorkspaceView

PASSWORD = "Sup3r-Secret-Pass!"
VIEWS = "/api/v1/analytics/views"
KYC_VIEWS = "/api/v1/kyc/views"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_reader_saves_portable_private_report_view_without_export_state(client, make_user):
    analyst = await make_user(email="report-view-analyst@vi.co", roles=("analyst",))
    manager = await make_user(email="report-view-manager@vi.co", roles=("manager",))
    analyst_headers = await _headers(client, analyst.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "My comparison",
        "visibility": "private",
        "filters": {
            "from": "2026-07-01T00:00:00Z",
            "to": "2026-08-01T00:00:00Z",
            "granularity": "week",
            "compare": "previous_period",
            "report": "kyc",
            "format": "pdf",
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
        "from": "2026-07-01T00:00:00",
        "to": "2026-08-01T00:00:00",
        "preset": None,
        "granularity": "week",
        "compare": "previous_period",
    }
    assert own.json()["data"] == [created.json()]
    assert other.json()["data"] == []


@pytest.mark.anyio
async def test_team_views_require_reports_manager_permission_and_are_visible(client, make_user):
    analyst = await make_user(email="report-shared-analyst@vi.co", roles=("analyst",))
    manager = await make_user(email="report-shared-manager@vi.co", roles=("manager",))
    analyst_headers = await _headers(client, analyst.user.email)
    manager_headers = await _headers(client, manager.user.email)
    payload = {
        "name": "Monthly leadership",
        "visibility": "shared",
        "filters": {
            "preset": "this_month",
            "granularity": "day",
            "compare": "previous_period",
        },
    }

    forbidden = await client.post(VIEWS, headers=analyst_headers, json=payload)
    created = await client.post(VIEWS, headers=manager_headers, json=payload)
    listed = await client.get(VIEWS, headers=analyst_headers)

    assert forbidden.status_code == 403
    assert created.status_code == 201, created.text
    assert listed.json()["data"][0]["name"] == "Monthly leadership"
    assert listed.json()["data"][0]["can_delete"] is False
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=analyst_headers)
    ).status_code == 403
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=manager_headers)
    ).status_code == 204


@pytest.mark.anyio
async def test_report_workspace_names_and_rows_are_isolated(client, make_user, session_factory):
    manager = await make_user(email="report-workspace-manager@vi.co", roles=("manager",))
    headers = await _headers(client, manager.user.email)
    name = "Priority view"

    report = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": name,
            "visibility": "shared",
            "filters": {"preset": "last_30d"},
        },
    )
    kyc = await client.post(
        KYC_VIEWS,
        headers=headers,
        json={"name": name, "visibility": "shared", "filters": {}},
    )

    assert report.status_code == 201, report.text
    assert kyc.status_code == 201, kyc.text
    assert [row["name"] for row in (await client.get(VIEWS, headers=headers)).json()["data"]] == [
        name
    ]
    async with session_factory() as session:
        workspaces = set((await session.scalars(select(WorkspaceView.workspace))).all())
    assert {"reports", "kyc"} <= workspaces


@pytest.mark.anyio
async def test_report_view_range_validation_and_audit(client, make_user, session_factory):
    manager = await make_user(email="report-view-audit@vi.co", roles=("manager",))
    headers = await _headers(client, manager.user.email)

    invalid = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": "Ambiguous",
            "visibility": "shared",
            "filters": {
                "preset": "last_30d",
                "from": "2026-07-01T00:00:00Z",
                "to": "2026-08-01T00:00:00Z",
            },
        },
    )
    created = await client.post(
        VIEWS,
        headers=headers,
        json={
            "name": "Audited reports",
            "visibility": "shared",
            "filters": {"preset": "last_7d"},
        },
    )
    assert invalid.status_code == 422
    assert created.status_code == 201, created.text
    assert (
        await client.delete(f"{VIEWS}/{created.json()['id']}", headers=headers)
    ).status_code == 204

    async with session_factory() as session:
        actions = set((await session.scalars(select(AuditLog.action))).all())
    assert {"report_view.created", "report_view.deleted"} <= actions


def test_openapi_declares_report_saved_view_operations() -> None:
    from app.main import create_app

    schema = create_app().openapi()
    assert {"get", "post"} <= set(schema["paths"][VIEWS])
    assert "delete" in schema["paths"][f"{VIEWS}/{{view_id}}"]
    create_schema = schema["components"]["schemas"]["ReportViewCreate"]
    assert {"name", "filters"} <= set(create_schema["required"])
