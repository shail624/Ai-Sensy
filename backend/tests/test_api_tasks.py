"""Task API tests (Doc 14 §6, §7) — the CRM Follow-up Engine over HTTP.

Covers the transport contract the service tests do not: the ``tasks:read``/``write``/``assign``
permission split, the RFC 7807 problem envelope on every failure mode, cursor pagination through
the wire format, the bulk envelope, and the timeline projection as the customer profile sees it.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.db.mixins import utcnow
from app.models.conversation import Conversation
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount

PASSWORD = "Sup3r-Secret-Pass1"
TASKS_URL = "/api/v1/tasks"
PROBLEM = "application/problem+json"


# --- Helpers ------------------------------------------------------------------------------------
async def _headers(client, make_user, *, email: str, **kw) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _owner(client, make_user, email: str = "owner@vi.co") -> dict[str, str]:
    """A superuser — the only role in these tests that may also create contacts."""
    return await _headers(client, make_user, email=email, is_superuser=True)


async def _contact(client, headers, phone: str = "+919990000001") -> str:
    resp = await client.post("/api/v1/contacts", headers=headers, json={"phone_e164": phone})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _payload(contact_id: str, **overrides) -> dict:
    body = {
        "contact_id": contact_id,
        "title": "Collect Aadhaar",
        "task_type": "collect_documents",
        "priority": "high",
        "due_at": (utcnow() + timedelta(days=1)).isoformat() + "Z",
        "has_time": True,
    }
    body.update(overrides)
    return body


async def _create(client, headers, contact_id: str, **overrides):
    return await client.post(TASKS_URL, headers=headers, json=_payload(contact_id, **overrides))


def _assert_problem(resp, status: int, code: str | None = None) -> dict:
    """Every failure is an RFC 7807 problem+json document (Doc 04 §5)."""
    assert resp.status_code == status, resp.text
    assert resp.headers["content-type"].startswith(PROBLEM)
    body = resp.json()
    assert {"type", "title", "status", "detail", "instance", "code"} <= set(body)
    assert body["status"] == status
    assert body["type"].startswith("https://api.internal/errors/")
    if code is not None:
        assert body["code"] == code
    return body


async def _seed_conversation(session_factory, organization, contact_public_id: str) -> str:
    """A conversation for the optional lead link — seeded directly, no webhook round-trip."""
    from sqlalchemy import select

    from app.models.contact import Contact

    async with session_factory() as session:
        contact = (
            await session.scalars(
                select(Contact).where(Contact.uuid == uuid.UUID(contact_public_id).bytes)
            )
        ).first()
        waba = WhatsAppBusinessAccount(
            organization_id=organization.id,
            waba_id="WABA-1",
            business_name="Vi",
            access_token_enc=b"ciphertext",
        )
        session.add(waba)
        await session.flush()
        number = PhoneNumber(
            organization_id=organization.id,
            waba_id=waba.id,
            phone_number_id="PN-1",
            display_number="+911111111111",
        )
        session.add(number)
        await session.flush()
        conversation = Conversation(
            organization_id=organization.id,
            phone_number_id=number.id,
            contact_id=contact.id,
        )
        session.add(conversation)
        await session.commit()
        return conversation.public_id


# --- Create -------------------------------------------------------------------------------------
async def test_create_returns_201_with_display_fields(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)

    resp = await _create(client, owner, contact_id)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["contact_id"] == contact_id
    assert body["assigned_agent_id"] == body["created_by"]  # self-assigned by default
    assert body["assigned_agent_name"] == "Test User"
    assert body["row_version"] == 0
    uuid.UUID(body["id"])  # public ids are uuid strings on the wire


async def test_create_accepts_optional_conversation_link(
    client, make_user, session_factory, organization
):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    conversation_id = await _seed_conversation(session_factory, organization, contact_id)

    resp = await _create(client, owner, contact_id, conversation_id=conversation_id)

    assert resp.status_code == 201, resp.text
    assert resp.json()["conversation_id"] == conversation_id


async def test_create_with_unknown_contact_is_404_problem(client, make_user):
    owner = await _owner(client, make_user)
    resp = await _create(client, owner, str(uuid.uuid4()))
    _assert_problem(resp, 404, "not_found")


async def test_create_with_unknown_conversation_is_404(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    resp = await _create(client, owner, contact_id, conversation_id=str(uuid.uuid4()))
    _assert_problem(resp, 404)


# --- Validation (422 problems) ------------------------------------------------------------------
@pytest.mark.parametrize(
    "override",
    [
        {"title": ""},
        {"task_type": "teleport"},
        {"priority": "urgent"},
        {"due_at": "not-a-date"},
        {"title": "x" * 161},
    ],
    ids=["empty-title", "bad-type", "bad-priority", "bad-due", "long-title"],
)
async def test_invalid_create_bodies_are_422_problems(client, make_user, override):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)

    resp = await _create(client, owner, contact_id, **override)

    body = _assert_problem(resp, 422, "validation_error")
    assert body["errors"] and "field" in body["errors"][0]


async def test_missing_required_field_is_422(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    body = _payload(contact_id)
    del body["due_at"]

    resp = await client.post(TASKS_URL, headers=owner, json=body)

    _assert_problem(resp, 422, "validation_error")


async def test_limit_above_max_is_422(client, make_user):
    owner = await _owner(client, make_user)
    resp = await client.get(f"{TASKS_URL}?limit=500", headers=owner)
    _assert_problem(resp, 422)


async def test_bulk_update_without_any_change_is_422(client, make_user):
    owner = await _owner(client, make_user)
    resp = await client.post(
        f"{TASKS_URL}/bulk-update", headers=owner, json={"task_ids": [str(uuid.uuid4())]}
    )
    _assert_problem(resp, 422)


# --- Read ---------------------------------------------------------------------------------------
async def test_get_and_list_round_trip(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    one = await client.get(f"{TASKS_URL}/{task_id}", headers=owner)
    listed = await client.get(TASKS_URL, headers=owner)

    assert one.status_code == 200 and one.json()["id"] == task_id
    body = listed.json()
    assert [t["id"] for t in body["data"]] == [task_id]
    assert body["page"]["limit"] == 50 and body["page"]["has_more"] is False


async def test_get_unknown_task_is_404_problem(client, make_user):
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{TASKS_URL}/{uuid.uuid4()}", headers=owner), 404)


async def test_stats_endpoint_returns_four_buckets(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    await _create(client, owner, contact_id)  # due tomorrow → upcoming

    resp = await client.get(f"{TASKS_URL}/stats", headers=owner)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"overdue": 0, "due_today": 0, "upcoming": 1, "completed_today": 0}


async def test_stats_route_is_not_shadowed_by_the_id_route(client, make_user):
    """``/tasks/stats`` must resolve before ``/tasks/{task_id}`` — a uuid parse would 422."""
    owner = await _owner(client, make_user)
    assert (await client.get(f"{TASKS_URL}/stats", headers=owner)).status_code == 200


# --- Actions & state machine (Doc 14 §4.4 → 409) ------------------------------------------------
async def test_complete_then_second_complete_is_409_problem(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    first = await client.post(
        f"{TASKS_URL}/{task_id}/complete", headers=owner, json={"completion_notes": "done"}
    )
    second = await client.post(f"{TASKS_URL}/{task_id}/complete", headers=owner, json={})

    assert first.status_code == 200 and first.json()["status"] == "completed"
    _assert_problem(second, 409, "task_state")


async def test_cancel_then_complete_is_409(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    await client.post(f"{TASKS_URL}/{task_id}/cancel", headers=owner, json={"reason": "withdrew"})
    resp = await client.post(f"{TASKS_URL}/{task_id}/complete", headers=owner, json={})

    _assert_problem(resp, 409, "task_state")


async def test_reopen_an_open_task_is_409(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    resp = await client.post(f"{TASKS_URL}/{task_id}/reopen", headers=owner, json={})

    _assert_problem(resp, 409, "task_state")


async def test_reopen_clears_completion_over_the_wire(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    await client.post(
        f"{TASKS_URL}/{task_id}/complete", headers=owner, json={"completion_notes": "done"}
    )

    resp = await client.post(f"{TASKS_URL}/{task_id}/reopen", headers=owner, json={})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["completed_at"] is None and body["completion_notes"] is None


def test_reopen_body_takes_no_reason() -> None:
    """Doc 14 §4.4 — reopening carries no outcome, so the schema exposes no ``reason``."""
    from app.schemas.task import TaskReasonRequest, TaskReopenRequest

    assert set(TaskReopenRequest.model_fields) == {"expected_row_version"}
    assert "reason" in TaskReasonRequest.model_fields  # skip/cancel keep theirs


async def test_skip_and_reschedule(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    new_due = (utcnow() + timedelta(days=5)).isoformat() + "Z"

    moved = await client.post(
        f"{TASKS_URL}/{task_id}/reschedule", headers=owner, json={"due_at": new_due}
    )
    skipped = await client.post(
        f"{TASKS_URL}/{task_id}/skip", headers=owner, json={"reason": "no answer"}
    )

    assert moved.status_code == 200 and moved.json()["row_version"] == 1
    assert skipped.status_code == 200 and skipped.json()["status"] == "skipped"


async def test_patch_edits_fields(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    resp = await client.patch(
        f"{TASKS_URL}/{task_id}", headers=owner, json={"title": "Renamed", "priority": "low"}
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Renamed" and resp.json()["priority"] == "low"


async def test_delete_is_soft_and_hides_the_task(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]

    assert (await client.delete(f"{TASKS_URL}/{task_id}", headers=owner)).status_code == 204
    _assert_problem(await client.get(f"{TASKS_URL}/{task_id}", headers=owner), 404)


# --- Optimistic concurrency (TA-INV 7 → 409) ----------------------------------------------------
async def test_stale_row_version_is_409_problem(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    await client.patch(f"{TASKS_URL}/{task_id}", headers=owner, json={"title": "First"})

    resp = await client.patch(
        f"{TASKS_URL}/{task_id}", headers=owner,
        json={"title": "Second", "expected_row_version": 0},
    )

    _assert_problem(resp, 409, "version_conflict")


async def test_current_row_version_is_accepted(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    created = (await _create(client, owner, contact_id)).json()

    resp = await client.post(
        f"{TASKS_URL}/{created['id']}/complete", headers=owner,
        json={"expected_row_version": created["row_version"]},
    )

    assert resp.status_code == 200, resp.text


# --- Permissions (Doc 14 §6) --------------------------------------------------------------------
async def test_analyst_can_read_but_not_write(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))

    assert (await client.get(TASKS_URL, headers=analyst)).status_code == 200
    _assert_problem(await _create(client, analyst, contact_id), 403, "forbidden")


async def test_agent_can_write_but_not_reassign(client, make_user):
    """Agents hold ``tasks:read``/``tasks:write``; reassignment stays with managers (§6)."""
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    peer = await make_user(email="peer@vi.co", password=PASSWORD, roles=("agent",))
    task_id = (await _create(client, agent, contact_id)).json()["id"]

    resp = await client.post(
        f"{TASKS_URL}/{task_id}/reassign", headers=agent,
        json={"assigned_agent_id": peer.user.public_id},
    )

    _assert_problem(resp, 403, "forbidden")


async def test_manager_can_reassign(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))
    peer = await make_user(email="peer@vi.co", password=PASSWORD, roles=("agent",))
    task_id = (await _create(client, manager, contact_id)).json()["id"]

    resp = await client.post(
        f"{TASKS_URL}/{task_id}/reassign", headers=manager,
        json={"assigned_agent_id": peer.user.public_id},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["assigned_agent_id"] == peer.user.public_id
    assert resp.json()["assigned_agent_name"] == "Test User"


async def test_bulk_reassign_requires_tasks_assign(client, make_user):
    """The conditional gate of §7.1: bulk is ``tasks:write`` unless it reassigns."""
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    peer = await make_user(email="peer@vi.co", password=PASSWORD, roles=("agent",))
    task_id = (await _create(client, agent, contact_id)).json()["id"]

    allowed = await client.post(
        f"{TASKS_URL}/bulk-update", headers=agent,
        json={"task_ids": [task_id], "priority": "low"},
    )
    refused = await client.post(
        f"{TASKS_URL}/bulk-update", headers=agent,
        json={"task_ids": [task_id], "assigned_agent_id": peer.user.public_id},
    )

    assert allowed.status_code == 200, allowed.text
    _assert_problem(refused, 403, "forbidden")


async def test_unauthenticated_request_is_401_problem(client):
    _assert_problem(await client.get(TASKS_URL), 401)


# --- Filters, sorting & cursor pagination (Doc 14 §7.2) -----------------------------------------
async def test_cursor_pagination_walks_every_task_once(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    base = utcnow() + timedelta(days=1)
    for i in range(5):
        await _create(
            client, owner, contact_id,
            title=f"t{i}", due_at=(base + timedelta(hours=i)).isoformat() + "Z",
        )

    seen: list[str] = []
    url = f"{TASKS_URL}?limit=2"
    for _ in range(10):
        body = (await client.get(url, headers=owner)).json()
        seen.extend(t["id"] for t in body["data"])
        if not body["page"]["has_more"]:
            break
        url = f"{TASKS_URL}?limit=2&cursor={body['page']['next_cursor']}"

    assert len(seen) == 5 and len(set(seen)) == 5


async def test_completed_at_sort_is_accepted(client, make_user):
    """Doc 14 §10 maps the Completed view to ``status=completed&sort=-completed_at``."""
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    await client.post(f"{TASKS_URL}/{task_id}/complete", headers=owner, json={})

    resp = await client.get(
        f"{TASKS_URL}?status=completed&sort=-completed_at", headers=owner
    )

    assert resp.status_code == 200, resp.text
    assert [t["id"] for t in resp.json()["data"]] == [task_id]


async def test_unknown_sort_is_422(client, make_user):
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{TASKS_URL}?sort=colour", headers=owner), 422)


async def test_view_and_repeatable_filters(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    await _create(client, owner, contact_id, title="calling", task_type="call")
    await _create(client, owner, contact_id, title="meeting", task_type="meeting")

    filtered = await client.get(f"{TASKS_URL}?type=call&type=meeting", headers=owner)
    single = await client.get(f"{TASKS_URL}?type=call", headers=owner)

    assert len(filtered.json()["data"]) == 2
    assert [t["title"] for t in single.json()["data"]] == ["calling"]


async def test_search_and_contact_scope(client, make_user):
    owner = await _owner(client, make_user)
    first = await _contact(client, owner)
    second = await _contact(client, owner, phone="+919990000002")
    await _create(client, owner, first, title="Aadhaar chase")
    await _create(client, owner, second, title="Renewal call")

    searched = await client.get(f"{TASKS_URL}?q=aadhaar", headers=owner)
    scoped = await client.get(f"{TASKS_URL}?contact_id={second}", headers=owner)

    assert [t["title"] for t in searched.json()["data"]] == ["Aadhaar chase"]
    assert [t["title"] for t in scoped.json()["data"]] == ["Renewal call"]


async def test_bad_view_is_422(client, make_user):
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{TASKS_URL}?view=yesterday", headers=owner), 422)


# --- Bulk operations (Doc 14 §7.1) --------------------------------------------------------------
async def test_bulk_update_returns_partial_success_summary(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    ids = [(await _create(client, owner, contact_id, title=f"b{i}")).json()["id"] for i in range(2)]

    resp = await client.post(
        f"{TASKS_URL}/bulk-update", headers=owner,
        json={"task_ids": [*ids, str(uuid.uuid4())], "status": "completed"},
    )

    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]
    assert summary["total"] == 3 and summary["succeeded"] == 2 and summary["skipped"] == 1


async def test_bulk_update_counts_illegal_transitions_as_failed(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    ok = (await _create(client, owner, contact_id, title="ok")).json()["id"]
    blocked = (await _create(client, owner, contact_id, title="blocked")).json()["id"]
    await client.post(f"{TASKS_URL}/{blocked}/cancel", headers=owner, json={})

    resp = await client.post(
        f"{TASKS_URL}/bulk-update", headers=owner,
        json={"task_ids": [ok, blocked], "status": "completed"},
    )

    summary = resp.json()["summary"]
    assert summary["succeeded"] == 1 and summary["failed"] == 1


async def test_bulk_delete_hides_every_task(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    ids = [(await _create(client, owner, contact_id, title=f"d{i}")).json()["id"] for i in range(3)]

    resp = await client.post(
        f"{TASKS_URL}/bulk-delete", headers=owner, json={"task_ids": ids}
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["summary"]["succeeded"] == 3
    assert (await client.get(TASKS_URL, headers=owner)).json()["data"] == []


async def test_bulk_delete_requires_ids(client, make_user):
    owner = await _owner(client, make_user)
    _assert_problem(
        await client.post(f"{TASKS_URL}/bulk-delete", headers=owner, json={"task_ids": []}), 422
    )


# --- History & timeline (Doc 14 §5.2/§5.3) ------------------------------------------------------
async def test_history_endpoint_returns_ordered_events(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    await client.post(
        f"{TASKS_URL}/{task_id}/complete", headers=owner, json={"completion_notes": "done"}
    )

    resp = await client.get(f"{TASKS_URL}/{task_id}/history", headers=owner)

    assert resp.status_code == 200, resp.text
    events = resp.json()["data"]
    assert [e["event_type"] for e in events] == ["created", "completed"]
    assert events[1]["note"] == "done"
    assert events[0]["actor_name"] == "Test User"
    uuid.UUID(events[0]["actor_user_id"])  # public id, never the internal integer


async def test_task_lifecycle_appears_on_the_contact_timeline(client, make_user):
    """FR-TASK-09 — the profile timeline picks task events up with no new UI surface."""
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    await client.post(
        f"{TASKS_URL}/{task_id}/reschedule", headers=owner,
        json={"due_at": (utcnow() + timedelta(days=4)).isoformat() + "Z"},
    )
    await client.post(f"{TASKS_URL}/{task_id}/complete", headers=owner, json={})

    timeline = await client.get(f"/api/v1/contacts/{contact_id}/timeline", headers=owner)

    assert timeline.status_code == 200, timeline.text
    events = timeline.json()["data"]
    types = {e["event_type"] for e in events}
    assert {"task_created", "task_rescheduled", "task_completed"} <= types
    task_event = next(e for e in events if e["event_type"] == "task_created")
    assert task_event["ref_type"] == "task"
    assert task_event["payload"]["title"] == "Collect Aadhaar"


async def test_history_requires_tasks_read(client, make_user):
    owner = await _owner(client, make_user)
    contact_id = await _contact(client, owner)
    task_id = (await _create(client, owner, contact_id)).json()["id"]
    outsider = await _headers(client, make_user, email="nobody@vi.co")

    _assert_problem(
        await client.get(f"{TASKS_URL}/{task_id}/history", headers=outsider), 403, "forbidden"
    )


# --- Build --------------------------------------------------------------------------------------
def test_every_documented_task_route_is_mounted() -> None:
    """The fifteen operations of Doc 14 §7.1, verified against the generated schema."""
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/tasks": {"get", "post"},
        "/api/v1/tasks/stats": {"get"},
        "/api/v1/tasks/{task_id}": {"get", "patch", "delete"},
        "/api/v1/tasks/{task_id}/complete": {"post"},
        "/api/v1/tasks/{task_id}/skip": {"post"},
        "/api/v1/tasks/{task_id}/cancel": {"post"},
        "/api/v1/tasks/{task_id}/reopen": {"post"},
        "/api/v1/tasks/{task_id}/reschedule": {"post"},
        "/api/v1/tasks/{task_id}/reassign": {"post"},
        "/api/v1/tasks/{task_id}/history": {"get"},
        "/api/v1/tasks/bulk-update": {"post"},
        "/api/v1/tasks/bulk-delete": {"post"},
    }
    for path, methods in expected.items():
        assert methods <= set(paths[path]), path
    assert sum(len(m) for m in expected.values()) == 15
