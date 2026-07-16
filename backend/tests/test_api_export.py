"""Contact export tests (Doc 04 §14.1, Doc 06 ``exports`` queue, FR-CON-15)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.config import settings
from app.crm.csv_io import EXPORT_COLUMNS
from app.db.mixins import utcnow
from app.models.job_records import STATUS_READY
from app.services.export_service import ExportService
from app.storage.base import get_provider

PASSWORD = "Sup3r-Secret-Pass1"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed_contacts(client, h) -> None:
    for phone, name in (
        ("+14155550001", "Alice"),
        ("+14155550002", "Bob"),
        ("+14155550003", "Carol"),
    ):
        resp = await client.post(
            "/api/v1/contacts", headers=h, json={"phone_e164": phone, "full_name": name}
        )
        assert resp.status_code == 201, resp.text


async def _start(client, h, **overrides) -> str:
    """Start an export with the queue stubbed out, returning the job id."""
    import app.crm.tasks as tasks

    tasks.run_contact_export.apply_async = lambda args, task_id: None
    payload = {"format": "csv", "match_type": "all", "rules": []}
    payload.update(overrides)
    resp = await client.post("/api/v1/contacts/export", headers=h, json=payload)
    assert resp.status_code == 202, resp.text
    return resp.json()["job"]["id"]


# --- API: 202 only ----------------------------------------------------------
async def test_export_returns_202_with_job_and_poll_url(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)

    dispatched: list = []
    import app.crm.tasks as tasks

    tasks.run_contact_export.apply_async = lambda args, task_id: dispatched.append((args, task_id))

    resp = await client.post(
        "/api/v1/contacts/export", headers=h, json={"format": "csv", "match_type": "all"}
    )
    assert resp.status_code == 202
    job = resp.json()["job"]
    assert job["type"] == "export" and job["status"] == "queued"
    assert job["poll_url"] == f"/api/v1/contacts/export/{job['id']}"
    # Handed to the queue, not generated inline.
    assert dispatched and dispatched[0][0] == [job["id"]]

    progress = (await client.get(job["poll_url"], headers=h)).json()
    assert progress["status"] == "pending"
    assert progress["download_url"] is None


async def test_export_validation_422_and_unknown_job_404(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    for body in (
        {"format": "pdf"},  # csv/xlsx/json only
        {"format": "csv", "match_type": "nonsense"},
        {
            "format": "csv",
            "rules": [
                {"field_source": "contact", "field_key": "bogus", "operator": "eq", "value": "x"}
            ],
        },
    ):
        resp = await client.post("/api/v1/contacts/export", headers=h, json=body)
        assert resp.status_code == 422, resp.text
    missing = await client.get(f"/api/v1/contacts/export/{uuid.uuid4()}", headers=h)
    assert missing.status_code == 404


async def test_export_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    h = await _headers(client, "agent@vi.co")
    assert (
        await client.post("/api/v1/contacts/export", headers=h, json={"format": "csv"})
    ).status_code == 403
    assert (await client.get(f"/api/v1/contacts/export/{uuid.uuid4()}")).status_code == 401


# --- Worker path: the task body --------------------------------------------
async def test_run_export_generates_csv_with_signed_download_url(
    client, make_user, session_factory
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)
    export_id = await _start(client, h)

    async with session_factory() as session:
        job = await ExportService(session).run(export_id)

    assert job.status == STATUS_READY
    assert job.row_count == 3
    assert job.storage_key and job.expires_at > utcnow()

    body = (await get_provider("local").get(job.storage_key)).decode()
    lines = body.splitlines()
    assert lines[0].split(",") == list(EXPORT_COLUMNS)
    assert len(lines) == 4
    assert {"Alice", "Bob", "Carol"} <= set(body.replace(",", " ").split())

    progress = (await client.get(f"/api/v1/contacts/export/{export_id}", headers=h)).json()
    assert progress["status"] == "ready" and progress["row_count"] == 3
    assert "signature=" in progress["download_url"]


async def test_export_filters_restrict_rows(client, make_user, session_factory) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)
    export_id = await _start(
        client,
        h,
        rules=[
            {"field_source": "contact", "field_key": "full_name", "operator": "eq", "value": "Bob"}
        ],
    )

    async with session_factory() as session:
        job = await ExportService(session).run(export_id)

    assert job.row_count == 1
    body = (await get_provider("local").get(job.storage_key)).decode()
    assert "Bob" in body and "Alice" not in body


async def test_export_streams_in_batches_without_materialising(
    client, make_user, session_factory, monkeypatch
) -> None:
    """Rows are pulled in bounded keyset batches, not one giant query (Doc 06 §2.3)."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)
    monkeypatch.setattr("app.services.export_service._BATCH", 2)
    export_id = await _start(client, h)

    async with session_factory() as session:
        service = ExportService(session)
        calls: list = []
        original = service._evaluator.paginate_matching

        async def _counted(*args, **kwargs):
            calls.append(kwargs.get("cursor"))
            return await original(*args, **kwargs)

        service._evaluator.paginate_matching = _counted
        job = await service.run(export_id)

    assert job.row_count == 3
    assert len(calls) == 2 and calls[0] is None and calls[1] is not None


async def test_expired_export_hides_download_url(client, make_user, session_factory) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)
    export_id = await _start(client, h)

    async with session_factory() as session:
        service = ExportService(session)
        job = await service.run(export_id)
        assert await service.download_url(job) is not None
        job.expires_at = utcnow() - timedelta(seconds=1)
        assert await service.download_url(job) is None


async def test_export_is_retry_safe(client, make_user, session_factory) -> None:
    """Re-running regenerates the artifact rather than duplicating rows (Doc 06 §8)."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed_contacts(client, h)
    export_id = await _start(client, h)

    async with session_factory() as session:
        await ExportService(session).run(export_id)
    async with session_factory() as session:
        again = await ExportService(session).run(export_id)

    assert again.status == STATUS_READY and again.row_count == 3
    body = (await get_provider("local").get(again.storage_key)).decode()
    assert len(body.splitlines()) == 4
