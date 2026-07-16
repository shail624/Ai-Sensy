"""Contact import tests (Doc 04 §14.1, Doc 06 imports queue, FR-CON-03/05/06)."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.crm.csv_io import error_report_csv, map_and_validate, read_csv
from app.models.job_records import STATUS_COMPLETED
from app.repositories.contact import ContactRepository
from app.services.import_service import ImportService
from app.storage.base import get_provider

PASSWORD = "Sup3r-Secret-Pass1"
CSV = (
    "Phone,Name,Plan\n"
    "+14155550001,Alice,gold\n"
    "+14155550002,Bob,silver\n"
    "not-a-phone,Broken,bronze\n"
)
MAPPING = {"Phone": "phone_e164", "Name": "full_name"}


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _upload_csv(client, h, body: str = CSV) -> str:
    resp = await client.post(
        "/api/v1/media/upload",
        headers=h,
        files={"file": ("contacts.csv", body.encode(), "text/csv")},
        data={"media_type": "document"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- CSV parser / validation (pure) -----------------------------------------
def test_map_and_validate_separates_good_and_bad_rows() -> None:
    result = map_and_validate(read_csv(CSV.encode()), {**MAPPING, "Plan": "attr.plan"})
    assert result.total == 3
    assert [r.fields["full_name"] for r in result.rows] == ["Alice", "Bob"]
    assert result.rows[0].attributes == {"plan": "gold"}
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 4 and "E.164" in result.errors[0].error


def test_map_and_validate_requires_phone_and_rejects_bad_targets() -> None:
    missing = map_and_validate([{"Name": "X"}], {"Name": "full_name"})
    assert "phone_e164 is required" in missing.errors[0].error
    bad = map_and_validate([{"A": "1"}], {"A": "nonsense"})
    assert "unknown mapping target" in bad.errors[0].error


def test_error_report_csv_has_header_and_rows() -> None:
    result = map_and_validate(read_csv(CSV.encode()), MAPPING)
    report = error_report_csv(result.errors).decode()
    assert report.splitlines()[0] == "row_number,error,data"
    assert "not-a-phone" in report


# --- API: 202 only ----------------------------------------------------------
async def test_import_returns_202_with_job_and_poll_url(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    upload_id = await _upload_csv(client, h)

    dispatched: list = []
    import app.crm.tasks as tasks

    tasks.run_contact_import.apply_async = lambda args, task_id: dispatched.append((args, task_id))

    resp = await client.post(
        "/api/v1/contacts/import",
        headers=h,
        json={"upload_id": upload_id, "format": "csv", "mapping": MAPPING},
    )
    assert resp.status_code == 202
    job = resp.json()["job"]
    assert job["type"] == "import" and job["status"] == "queued"
    assert job["poll_url"] == f"/api/v1/contacts/import/{job['id']}"
    # Work was handed to the queue, not done inline.
    assert dispatched and dispatched[0][0] == [job["id"]]
    assert (await client.get(job["poll_url"], headers=h)).json()["status"] == "pending"


async def test_import_validation_422_and_unknown_upload_404(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    upload_id = await _upload_csv(client, h)
    for body in (
        {"upload_id": upload_id, "mapping": {"Name": "full_name"}},  # no phone target
        {"upload_id": upload_id, "mapping": {"P": "bogus"}},  # unknown target
        {"upload_id": upload_id, "mapping": MAPPING, "dedup_strategy": "nope"},
        {"upload_id": upload_id, "mapping": MAPPING, "format": "xlsx"},  # csv only, this step
    ):
        assert (await client.post("/api/v1/contacts/import", headers=h, json=body)).status_code == 422
    missing = await client.post(
        "/api/v1/contacts/import", headers=h, json={"upload_id": str(uuid.uuid4()), "mapping": MAPPING}
    )
    assert missing.status_code == 404


async def test_import_permission_enforcement(client, make_user) -> None:
    # agent lacks contacts:import
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    h = await _headers(client, "agent@vi.co")
    assert (
        await client.post(
            "/api/v1/contacts/import",
            headers=h,
            json={"upload_id": str(uuid.uuid4()), "mapping": MAPPING},
        )
    ).status_code == 403
    assert (await client.get(f"/api/v1/contacts/import/{uuid.uuid4()}")).status_code == 401


# --- Worker path: the task body --------------------------------------------
async def _start(client, session_factory, h, body=CSV, **overrides):
    upload_id = await _upload_csv(client, h, body)
    import app.crm.tasks as tasks

    tasks.run_contact_import.apply_async = lambda args, task_id: None
    payload = {"upload_id": upload_id, "format": "csv", "mapping": {**MAPPING, "Plan": "attr.plan"}}
    payload.update(overrides)
    resp = await client.post("/api/v1/contacts/import", headers=h, json=payload)
    assert resp.status_code == 202
    return resp.json()["job"]["id"]


async def test_run_import_creates_contacts_and_error_report(client, make_user, session_factory) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    import_id = await _start(client, session_factory, h)

    async with session_factory() as session:
        job = await ImportService(session).run(import_id)

    assert job.status == STATUS_COMPLETED
    assert job.total_rows == 3 and job.success_rows == 2 and job.error_rows == 1
    assert job.processed_rows == 3

    listing = await client.get("/api/v1/contacts", headers=h)
    assert {c["full_name"] for c in listing.json()["data"]} == {"Alice", "Bob"}
    assert all(c["source"] == "import" for c in listing.json()["data"])

    # The error report is stored and exposed as a signed URL (FR-CON-05/09).
    assert job.error_report_key
    report = await get_provider("local").get(job.error_report_key)
    assert b"not-a-phone" in report
    progress = (await client.get(f"/api/v1/contacts/import/{import_id}", headers=h)).json()
    assert progress["status"] == "completed" and progress["error_rows"] == 1
    assert "signature=" in progress["error_report_url"]


async def test_import_dedup_skip_leaves_existing_untouched(client, make_user, session_factory) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post(
        "/api/v1/contacts", headers=h, json={"phone_e164": "+14155550001", "full_name": "Original"}
    )
    import_id = await _start(client, session_factory, h, dedup_strategy="skip")
    async with session_factory() as session:
        job = await ImportService(session).run(import_id)
    assert job.success_rows == 1  # only Bob was new; Alice skipped

    async with session_factory() as session:
        existing = await ContactRepository(session).get_active_by_wa_id(1, "14155550001")
        assert existing.full_name == "Original"


async def test_import_dedup_overwrite_replaces_fields(client, make_user, session_factory) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post(
        "/api/v1/contacts", headers=h, json={"phone_e164": "+14155550001", "full_name": "Original"}
    )
    import_id = await _start(client, session_factory, h, dedup_strategy="overwrite")
    async with session_factory() as session:
        await ImportService(session).run(import_id)
        existing = await ContactRepository(session).get_active_by_wa_id(1, "14155550001")
        assert existing.full_name == "Alice"


async def test_import_is_retry_safe(client, make_user, session_factory) -> None:
    """Re-running a completed import must converge, not duplicate (Doc 06 §8)."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    import_id = await _start(client, session_factory, h, dedup_strategy="skip")
    async with session_factory() as session:
        await ImportService(session).run(import_id)
    async with session_factory() as session:
        again = await ImportService(session).run(import_id)
    assert again.status == STATUS_COMPLETED
    assert (await client.get("/api/v1/contacts", headers=h)).json()["page"]["total"] == 2
