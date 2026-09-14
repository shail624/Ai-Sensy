"""Unified Download Center contract: ownership, RBAC, status and keyset history."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.config import settings
from app.db.mixins import utcnow
from app.models.job_records import (
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_READY,
    ExportJob,
)

PASSWORD = "Sup3r-Secret-Pass1"
BASE = "/api/v1/downloads"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _job(
    session_factory,
    *,
    organization_id: int,
    requested_by: int,
    entity: str,
    status: str = STATUS_PENDING,
    created_delta: timedelta = timedelta(),
    expired: bool = False,
    filters: dict | None = None,
) -> ExportJob:
    now = utcnow()
    async with session_factory() as session:
        job = ExportJob(
            organization_id=organization_id,
            requested_by=requested_by,
            entity=entity,
            format="csv",
            status=status,
            row_count=42 if status == STATUS_READY else None,
            storage_key=f"exports/{requested_by}/{entity.replace(':', '-')}.csv"
            if status == STATUS_READY
            else None,
            expires_at=now - timedelta(minutes=1)
            if expired
            else (now + timedelta(hours=1) if status == STATUS_READY else None),
            created_at=now + created_delta,
            completed_at=now if status in (STATUS_READY, STATUS_FAILED) else None,
            filters_json=filters,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def test_download_center_lists_only_the_requesting_users_allowed_exports(
    client, make_user, session_factory, organization
) -> None:
    manager = await make_user(
        email="manager@vi.co", password=PASSWORD, roles=("manager",)
    )
    other = await make_user(email="other@vi.co", password=PASSWORD, roles=("manager",))
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="contacts",
        status=STATUS_READY,
    )
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="report:campaigns",
        status=STATUS_PROCESSING,
        created_delta=timedelta(seconds=1),
    )
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="conversation_transcript",
        created_delta=timedelta(seconds=2),
    )
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="campaign_results",
        created_delta=timedelta(seconds=3),
        filters={"campaign_name": "August recovery"},
    )
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=other.user.id,
        entity="contacts",
    )

    response = await client.get(BASE, headers=await _headers(client, "manager@vi.co"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["page"]["total"] == 4
    assert [row["category"] for row in body["data"]] == [
        "campaigns",
        "chat_history",
        "analytics",
        "contacts",
    ]
    assert body["data"][0]["name"] == "August recovery results"
    assert body["data"][1]["name"] == "Chat transcript"
    assert body["data"][2]["name"] == "Campaigns report"
    assert body["data"][2]["download_url"] is None
    assert "signature=" in body["data"][3]["download_url"]


async def test_download_center_applies_current_family_permissions(
    client, make_user, session_factory, organization
) -> None:
    analyst = await make_user(
        email="analyst@vi.co", password=PASSWORD, roles=("analyst",)
    )
    for entity in ("contacts", "report:messages"):
        await _job(
            session_factory,
            organization_id=organization.id,
            requested_by=analyst.user.id,
            entity=entity,
        )
    headers = await _headers(client, "analyst@vi.co")

    all_rows = (await client.get(BASE, headers=headers)).json()
    blocked_family = await client.get(BASE, headers=headers, params={"category": "contacts"})

    assert all_rows["page"]["total"] == 1
    assert all_rows["data"][0]["category"] == "analytics"
    assert blocked_family.status_code == 200
    assert blocked_family.json()["data"] == []


async def test_download_center_normalizes_expiry_and_filters_status(
    client, make_user, session_factory, organization
) -> None:
    manager = await make_user(
        email="manager@vi.co", password=PASSWORD, roles=("manager",)
    )
    expired = await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="contacts",
        status=STATUS_READY,
        expired=True,
    )
    await _job(
        session_factory,
        organization_id=organization.id,
        requested_by=manager.user.id,
        entity="report:failures",
        status=STATUS_FAILED,
    )
    headers = await _headers(client, "manager@vi.co")

    response = await client.get(BASE, headers=headers, params={"status": "expired"})

    assert response.status_code == 200, response.text
    assert response.json()["page"]["total"] == 1
    row = response.json()["data"][0]
    assert row["id"] == expired.public_id
    assert row["status"] == "expired"
    assert row["download_url"] is None
    ready = await client.get(BASE, headers=headers, params={"status": "ready"})
    assert ready.json()["page"]["total"] == 0


async def test_download_center_uses_stable_keyset_pagination(
    client, make_user, session_factory, organization
) -> None:
    manager = await make_user(
        email="manager@vi.co", password=PASSWORD, roles=("manager",)
    )
    for index in range(3):
        await _job(
            session_factory,
            organization_id=organization.id,
            requested_by=manager.user.id,
            entity="contacts",
            created_delta=timedelta(seconds=index),
        )
    headers = await _headers(client, "manager@vi.co")

    first = (await client.get(BASE, headers=headers, params={"limit": 2})).json()
    second = (
        await client.get(
            BASE,
            headers=headers,
            params={"limit": 2, "cursor": first["page"]["next_cursor"]},
        )
    ).json()

    assert first["page"]["total"] == 3
    assert first["page"]["has_more"] is True
    assert len(first["data"]) == 2
    assert second["page"]["has_more"] is False
    assert len(second["data"]) == 1
    assert {row["id"] for row in first["data"]}.isdisjoint(
        {row["id"] for row in second["data"]}
    )


async def test_download_center_rejects_unauthorized_roles_and_invalid_filters(
    client, make_user
) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")

    assert (await client.get(BASE)).status_code == 401
    assert (await client.get(BASE, headers=headers)).status_code == 403
    assert (
        await client.get(BASE, headers=headers, params={"status": "unknown"})
    ).status_code == 422
