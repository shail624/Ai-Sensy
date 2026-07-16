"""Bulk contact operation tests (Doc 04 §29/§30, FR-CON-06/07/08) — Module 2 Step 5C."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.models.job_records import STATUS_COMPLETED
from app.services.bulk_service import BulkService
from app.storage.base import get_provider

PASSWORD = "Sup3r-Secret-Pass1"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


@pytest.fixture(autouse=True)
def _stub_queue():
    """Bulk endpoints must hand off to the queue, never run inline."""
    import app.crm.tasks as tasks

    for task in (
        tasks.run_contact_bulk_update,
        tasks.run_contact_bulk_delete,
        tasks.run_contact_deduplicate,
    ):
        task.apply_async = lambda args, task_id: None


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _owner(client, make_user) -> dict[str, str]:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    return await _headers(client, "owner@vi.co")


async def _contact(client, h, phone: str, **fields) -> str:
    body = {"phone_e164": phone}
    body.update(fields)
    resp = await client.post("/api/v1/contacts", headers=h, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _tag(client, h, name: str) -> str:
    resp = await client.post("/api/v1/tags", headers=h, json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _run(session_factory, job_id: str):
    async with session_factory() as session:
        return await BulkService(session).run(job_id)


# --- API contract: 202 + job, never inline ----------------------------------
async def test_bulk_update_returns_202_with_job_and_poll_url(client, make_user) -> None:
    h = await _owner(client, make_user)
    contact_id = await _contact(client, h, "+14155550001")
    tag_id = await _tag(client, h, "vip")

    dispatched: list = []
    import app.crm.tasks as tasks

    tasks.run_contact_bulk_update.apply_async = (
        lambda args, task_id: dispatched.append((args, task_id))
    )

    resp = await client.post(
        "/api/v1/contacts/bulk-update",
        headers=h,
        json={"ids": [contact_id], "action": "add_tags", "payload": {"tags": [tag_id]}},
    )
    assert resp.status_code == 202, resp.text
    job = resp.json()["job"]
    assert job["type"] == "bulk_update" and job["status"] == "queued"
    assert job["poll_url"] == f"/api/v1/contacts/bulk/{job['id']}"
    # Handed to the queue, not applied inline.
    assert dispatched and dispatched[0][0] == [job["id"]]

    progress = (await client.get(job["poll_url"], headers=h)).json()
    assert progress["job_status"] == "pending"
    assert progress["summary"] == {
        "total": 1,
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
    }
    # The contact is untouched until a worker runs it.
    assert (await client.get(f"/api/v1/contacts/{contact_id}", headers=h)).json()["tags"] == []


async def test_bulk_addressing_and_payload_validation(client, make_user) -> None:
    h = await _owner(client, make_user)
    contact_id = await _contact(client, h, "+14155550001")
    tag_id = await _tag(client, h, "vip")

    for body in (
        # Neither addressing mode, and both at once (§30 — mutually exclusive).
        {"action": "add_tags", "payload": {"tags": [tag_id]}},
        {
            "ids": [contact_id],
            "filter": {"match_type": "all", "rules": []},
            "action": "add_tags",
            "payload": {"tags": [tag_id]},
        },
        {"ids": [], "action": "add_tags", "payload": {"tags": [tag_id]}},
        {"ids": [contact_id], "action": "nonsense", "payload": {}},
        {"ids": [contact_id], "action": "add_tags", "payload": {}},
        {"ids": [contact_id], "action": "add_tags", "payload": {"tags": [str(uuid.uuid4())]}},
        {"ids": [contact_id], "action": "set_attributes", "payload": {"attributes": {}}},
        {
            "ids": [contact_id],
            "action": "set_attributes",
            "payload": {"attributes": {"nope": "x"}},
        },
        {
            "filter": {
                "match_type": "all",
                "rules": [
                    {"field_source": "contact", "field_key": "bogus", "operator": "eq", "value": "x"}
                ],
            },
            "action": "add_tags",
            "payload": {"tags": [tag_id]},
        },
    ):
        resp = await client.post("/api/v1/contacts/bulk-update", headers=h, json=body)
        assert resp.status_code == 422, f"{body} -> {resp.status_code} {resp.text}"


async def test_bulk_permission_enforcement(client, make_user) -> None:
    await make_user(email="viewer@vi.co", password=PASSWORD, roles=("viewer",))
    h = await _headers(client, "viewer@vi.co")
    for path, body in (
        ("/api/v1/contacts/bulk-update", {"ids": [str(uuid.uuid4())], "action": "add_tags"}),
        ("/api/v1/contacts/bulk-delete", {"ids": [str(uuid.uuid4())]}),
        ("/api/v1/contacts/deduplicate", {"keys": ["email"]}),
    ):
        assert (await client.post(path, headers=h, json=body)).status_code == 403
    assert (await client.get(f"/api/v1/contacts/bulk/{uuid.uuid4()}")).status_code == 401


async def test_unknown_bulk_job_is_404(client, make_user) -> None:
    h = await _owner(client, make_user)
    assert (
        await client.get(f"/api/v1/contacts/bulk/{uuid.uuid4()}", headers=h)
    ).status_code == 404


async def test_expected_count_guard_returns_409(client, make_user) -> None:
    """A filter that shifted underneath the caller acts on nothing (Doc 04 §30)."""
    h = await _owner(client, make_user)
    await _contact(client, h, "+14155550001")
    await _contact(client, h, "+14155550002")

    resp = await client.post(
        "/api/v1/contacts/bulk-delete",
        headers=h,
        json={"filter": {"match_type": "all", "rules": []}, "expected_count": 5},
    )
    assert resp.status_code == 409, resp.text
    # The correct count is accepted.
    ok = await client.post(
        "/api/v1/contacts/bulk-delete",
        headers=h,
        json={"filter": {"match_type": "all", "rules": []}, "expected_count": 2},
    )
    assert ok.status_code == 202, ok.text


# --- Worker path: bulk update ------------------------------------------------
async def test_bulk_update_add_tags_over_filter(client, make_user, session_factory) -> None:
    h = await _owner(client, make_user)
    await _contact(client, h, "+14155550001", full_name="Alice", opt_in_status="opted_in")
    await _contact(client, h, "+14155550002", full_name="Bob", opt_in_status="opted_in")
    await _contact(client, h, "+14155550003", full_name="Carol", opt_in_status="opted_out")
    tag_id = await _tag(client, h, "vip")

    resp = await client.post(
        "/api/v1/contacts/bulk-update",
        headers=h,
        json={
            "filter": {
                "match_type": "all",
                "rules": [
                    {
                        "field_source": "contact",
                        "field_key": "opt_in_status",
                        "operator": "eq",
                        "value": "opted_in",
                    }
                ],
            },
            "action": "add_tags",
            "payload": {"tags": [tag_id]},
        },
    )
    job_id = resp.json()["job"]["id"]
    job = await _run(session_factory, job_id)

    assert job.status == STATUS_COMPLETED
    assert (job.total_items, job.succeeded_items, job.failed_items) == (2, 2, 0)

    progress = (await client.get(f"/api/v1/contacts/bulk/{job_id}", headers=h)).json()
    assert progress["status"] == "success"
    assert progress["summary"]["succeeded"] == 2

    # Only the filtered contacts were tagged.
    listing = (await client.get("/api/v1/contacts", headers=h)).json()["data"]
    tagged = {c["full_name"] for c in listing if c["tags"]}
    assert tagged == {"Alice", "Bob"}


async def test_bulk_update_is_idempotent_and_counts_skips(
    client, make_user, session_factory
) -> None:
    """Re-running converges: an already-applied tag is a skip, not a duplicate (Doc 06 §8)."""
    h = await _owner(client, make_user)
    contact_id = await _contact(client, h, "+14155550001")
    tag_id = await _tag(client, h, "vip")
    body = {"ids": [contact_id], "action": "add_tags", "payload": {"tags": [tag_id]}}

    first = (await client.post("/api/v1/contacts/bulk-update", headers=h, json=body)).json()
    job = await _run(session_factory, first["job"]["id"])
    assert (job.succeeded_items, job.skipped_items) == (1, 0)

    again = await _run(session_factory, first["job"]["id"])
    assert (again.succeeded_items, again.skipped_items) == (0, 1)

    contact = (await client.get(f"/api/v1/contacts/{contact_id}", headers=h)).json()
    assert [t["name"] for t in contact["tags"]] == ["vip"]


async def test_bulk_update_set_attributes(client, make_user, session_factory) -> None:
    h = await _owner(client, make_user)
    contact_id = await _contact(client, h, "+14155550001")
    created = await client.post(
        "/api/v1/custom-attributes",
        headers=h,
        json={"key_name": "plan", "label": "Plan", "data_type": "string"},
    )
    assert created.status_code == 201, created.text

    resp = await client.post(
        "/api/v1/contacts/bulk-update",
        headers=h,
        json={
            "ids": [contact_id],
            "action": "set_attributes",
            "payload": {"attributes": {"plan": "gold"}},
        },
    )
    job = await _run(session_factory, resp.json()["job"]["id"])
    assert job.succeeded_items == 1

    contact = (await client.get(f"/api/v1/contacts/{contact_id}", headers=h)).json()
    assert contact["attributes"]["plan"] == "gold"


async def test_bulk_update_reports_bad_item_without_failing_the_rest(
    client, make_user, session_factory
) -> None:
    """One bad id is reported in errors[]; valid items still commit (Doc 04 §29)."""
    h = await _owner(client, make_user)
    good = await _contact(client, h, "+14155550001")
    missing = str(uuid.uuid4())
    tag_id = await _tag(client, h, "vip")

    resp = await client.post(
        "/api/v1/contacts/bulk-update",
        headers=h,
        json={
            "ids": [good, missing],
            "action": "add_tags",
            "payload": {"tags": [tag_id]},
        },
    )
    job_id = resp.json()["job"]["id"]
    job = await _run(session_factory, job_id)

    assert (job.succeeded_items, job.failed_items) == (1, 1)
    progress = (await client.get(f"/api/v1/contacts/bulk/{job_id}", headers=h)).json()
    assert progress["status"] == "partial_success"
    assert progress["errors"][0]["id"] == missing
    assert progress["errors"][0]["code"] == "not_found"
    # The full report is downloadable and signed.
    assert "signature=" in progress["error_report_url"]
    report = (await get_provider("local").get(job.error_report_key)).decode()
    assert missing in report and "contact_id,code,message" in report

    # The good contact was still tagged.
    contact = (await client.get(f"/api/v1/contacts/{good}", headers=h)).json()
    assert [t["name"] for t in contact["tags"]] == ["vip"]


# --- Worker path: bulk delete ------------------------------------------------
async def test_bulk_delete_soft_deletes_and_is_retry_safe(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    await _contact(client, h, "+14155550001", full_name="Alice")
    await _contact(client, h, "+14155550002", full_name="Bob")
    keep = await _contact(client, h, "+14155550003", full_name="Carol")

    resp = await client.post(
        "/api/v1/contacts/bulk-delete",
        headers=h,
        json={
            "filter": {
                "match_type": "any",
                "rules": [
                    {
                        "field_source": "contact",
                        "field_key": "full_name",
                        "operator": "in",
                        "value": ["Alice", "Bob"],
                    }
                ],
            }
        },
    )
    job_id = resp.json()["job"]["id"]
    job = await _run(session_factory, job_id)
    assert (job.total_items, job.succeeded_items, job.failed_items) == (2, 2, 0)

    remaining = (await client.get("/api/v1/contacts", headers=h)).json()["data"]
    assert [c["id"] for c in remaining] == [keep]

    # Re-running finds nothing left to delete rather than erroring.
    again = await _run(session_factory, job_id)
    assert again.status == STATUS_COMPLETED and again.failed_items == 0
    assert len((await client.get("/api/v1/contacts", headers=h)).json()["data"]) == 1


async def test_bulk_ids_selection_is_chunked(
    client, make_user, session_factory, monkeypatch
) -> None:
    """An explicit selection is resolved in windows, never one unbounded IN clause."""
    h = await _owner(client, make_user)
    ids = [await _contact(client, h, f"+1415555000{i}") for i in range(1, 6)]
    monkeypatch.setattr("app.services.bulk_service._BATCH", 2)

    resp = await client.post("/api/v1/contacts/bulk-delete", headers=h, json={"ids": ids})
    job_id = resp.json()["job"]["id"]

    async with session_factory() as session:
        service = BulkService(session)
        windows: list[int] = []
        original = service._contacts.get_active_by_uuids

        async def _counted(organization_id, public_ids):
            windows.append(len(public_ids))
            return await original(organization_id, public_ids)

        service._contacts.get_active_by_uuids = _counted
        job = await service.run(job_id)

    assert job.succeeded_items == 5
    assert windows == [2, 2, 1]
    assert (await client.get("/api/v1/contacts", headers=h)).json()["data"] == []


async def test_bulk_delete_streams_in_bounded_batches(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The audience is walked in keyset batches, not one giant query (Doc 06 §2.3)."""
    h = await _owner(client, make_user)
    for i in range(1, 4):
        await _contact(client, h, f"+1415555000{i}")
    monkeypatch.setattr("app.services.bulk_service._BATCH", 2)

    resp = await client.post(
        "/api/v1/contacts/bulk-delete",
        headers=h,
        json={"filter": {"match_type": "all", "rules": []}},
    )
    job_id = resp.json()["job"]["id"]

    async with session_factory() as session:
        service = BulkService(session)
        calls: list = []
        original = service._evaluator.paginate_matching

        async def _counted(*args, **kwargs):
            calls.append(kwargs.get("cursor"))
            return await original(*args, **kwargs)

        service._evaluator.paginate_matching = _counted
        job = await service.run(job_id)

    assert job.succeeded_items == 3
    assert len(calls) > 1 and calls[0] is None


# --- Worker path: deduplicate ------------------------------------------------
async def test_deduplicate_report_lists_groups_without_merging(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    first = await _contact(client, h, "+14155550001", full_name="Alice", email="a@x.com")
    second = await _contact(client, h, "+14155550002", full_name="Alicia", email="A@X.com ")
    await _contact(client, h, "+14155550003", full_name="Bob", email="b@x.com")

    resp = await client.post(
        "/api/v1/contacts/deduplicate", headers=h, json={"keys": ["email"], "mode": "report"}
    )
    job_id = resp.json()["job"]["id"]
    job = await _run(session_factory, job_id)

    assert job.status == STATUS_COMPLETED
    assert job.total_items == 1  # one duplicate group, matched case-insensitively

    report = (await get_provider("local").get(job.error_report_key)).decode()
    assert "a@x.com" in report and first in report and second in report
    assert "b@x.com" not in report

    # Nothing was merged — a report is read-only.
    assert len((await client.get("/api/v1/contacts", headers=h)).json()["data"]) == 3


async def test_deduplicate_merge_folds_duplicates_into_the_oldest(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    primary = await _contact(client, h, "+14155550001", email="a@x.com")
    duplicate = await _contact(
        client, h, "+14155550002", email="a@x.com", full_name="Alice", locale="en"
    )
    vip = await _tag(client, h, "vip")
    assert (
        await client.post(
            f"/api/v1/contacts/{duplicate}/tags", headers=h, json={"tags": [vip]}
        )
    ).status_code == 200

    resp = await client.post(
        "/api/v1/contacts/deduplicate", headers=h, json={"keys": ["email"], "mode": "merge"}
    )
    job = await _run(session_factory, resp.json()["job"]["id"])
    assert job.status == STATUS_COMPLETED and job.succeeded_items == 1

    # The duplicate is gone; the oldest contact survives.
    remaining = (await client.get("/api/v1/contacts", headers=h)).json()["data"]
    assert [c["id"] for c in remaining] == [primary]

    survivor = (await client.get(f"/api/v1/contacts/{primary}", headers=h)).json()
    # Blanks filled from the duplicate; its identity (phone) is untouched.
    assert survivor["full_name"] == "Alice" and survivor["locale"] == "en"
    assert survivor["phone_e164"] == "+14155550001"
    # Tags moved across.
    assert [t["name"] for t in survivor["tags"]] == ["vip"]

    # The merge is on the survivor's timeline (FR-CON-14).
    timeline = (await client.get(f"/api/v1/contacts/{primary}/timeline", headers=h)).json()
    merged = [e for e in timeline["data"] if e["event_type"] == "contact_merged"]
    assert merged and merged[0]["payload"]["merged_from"] == duplicate


async def test_deduplicate_merge_keeps_primary_values_and_is_retry_safe(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    primary = await _contact(client, h, "+14155550001", email="a@x.com", full_name="Original")
    await _contact(client, h, "+14155550002", email="a@x.com", full_name="Duplicate")

    resp = await client.post(
        "/api/v1/contacts/deduplicate", headers=h, json={"keys": ["email"], "mode": "merge"}
    )
    job_id = resp.json()["job"]["id"]
    await _run(session_factory, job_id)

    survivor = (await client.get(f"/api/v1/contacts/{primary}", headers=h)).json()
    assert survivor["full_name"] == "Original"  # a set primary field is never overwritten

    # Re-running finds no duplicates left.
    again = await _run(session_factory, job_id)
    assert again.status == STATUS_COMPLETED and again.total_items == 0
    assert len((await client.get("/api/v1/contacts", headers=h)).json()["data"]) == 1


async def test_deduplicate_rejects_unsupported_key(client, make_user) -> None:
    h = await _owner(client, make_user)
    resp = await client.post(
        "/api/v1/contacts/deduplicate", headers=h, json={"keys": ["locale"], "mode": "report"}
    )
    assert resp.status_code == 422, resp.text


async def test_deduplicate_by_wa_id_finds_nothing(client, make_user, session_factory) -> None:
    """wa_id is unique per org, so the phone key can never report a duplicate (Doc 03 §6.1)."""
    h = await _owner(client, make_user)
    await _contact(client, h, "+14155550001")
    await _contact(client, h, "+14155550002")

    resp = await client.post(
        "/api/v1/contacts/deduplicate", headers=h, json={"keys": ["wa_id"], "mode": "report"}
    )
    job = await _run(session_factory, resp.json()["job"]["id"])
    assert job.status == STATUS_COMPLETED and job.total_items == 0
