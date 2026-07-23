"""Task service tests (Doc 14 §4.4/§4.5, §5.3, §7.3) — the CRM Follow-up Engine's rules.

Drives ``TaskService`` directly so the state machine (TA-INV 1–7), the timeline projection, the
bucket boundary math and the bulk partial-success envelope are asserted at the layer that owns
them — the API tests cover the transport of the same behaviour.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_event import (
    EVENT_TASK_ASSIGNED,
    EVENT_TASK_CANCELLED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_CREATED,
    EVENT_TASK_RESCHEDULED,
    REF_TYPE_TASK,
    ContactEvent,
)
from app.models.task import (
    TASK_PRIORITY_CRITICAL,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_LOW,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_OPEN,
    TASK_STATUS_SKIPPED,
    TASK_TYPE_CALL,
    TASK_TYPE_COLLECT_DOCUMENTS,
    Task,
)
from app.models.task_event import (
    TASK_EVENT_ASSIGNED,
    TASK_EVENT_COMPLETED,
    TASK_EVENT_CREATED,
    TASK_EVENT_PRIORITY_CHANGED,
    TASK_EVENT_REASSIGNED,
    TASK_EVENT_REOPENED,
    TASK_EVENT_SKIPPED,
    TaskEvent,
)
from app.services.task_service import TaskService, TaskStateError


# --- Fixtures & helpers -------------------------------------------------------------------------
@pytest.fixture
async def actor(make_user):
    """The acting agent — creator and default assignee of every task built here."""
    return (await make_user(email="agent@vi.test", roles=("agent",))).user


@pytest.fixture
async def contact(db_session, organization) -> Contact:
    row = Contact(
        organization_id=organization.id,
        wa_id="919990000001",
        phone_e164="+919990000001",
        full_name="Ramesh K.",
    )
    db_session.add(row)
    await db_session.commit()
    return row


def _svc(db_session) -> TaskService:
    return TaskService(db_session)


async def _create(
    db_session,
    organization,
    actor,
    contact,
    *,
    title: str = "Collect Aadhaar",
    task_type: str = TASK_TYPE_COLLECT_DOCUMENTS,
    priority: str = "medium",
    due_at: datetime | None = None,
    assigned_agent_id: uuidlib.UUID | None = None,
):
    return await _svc(db_session).create(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuidlib.UUID(contact.public_id),
        conversation_id=None,
        title=title,
        task_type=task_type,
        priority=priority,
        due_at=due_at or (utcnow() + timedelta(days=1)),
        has_time=True,
        reminder_at=None,
        description=None,
        assigned_agent_id=assigned_agent_id,
    )


async def _events_of(db_session, task_public_id: str) -> list[TaskEvent]:
    task = (
        await db_session.scalars(
            select(Task).where(Task.uuid == uuidlib.UUID(task_public_id).bytes)
        )
    ).first()
    return list(
        (
            await db_session.scalars(
                select(TaskEvent).where(TaskEvent.task_id == task.id).order_by(TaskEvent.id)
            )
        ).all()
    )


async def _timeline_types(db_session, contact: Contact) -> list[str]:
    rows = (
        await db_session.scalars(
            select(ContactEvent)
            .where(ContactEvent.contact_id == contact.id)
            .order_by(ContactEvent.id)
        )
    ).all()
    return [r.event_type for r in rows]


# --- Creation (TA-INV 1) ------------------------------------------------------------------------
async def test_create_starts_open_and_self_assigns(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)

    assert view.status == TASK_STATUS_OPEN
    assert view.assigned_agent_id == actor.public_id  # defaults to the caller (Doc 14 §7.4)
    assert view.created_by == actor.public_id
    assert view.row_version == 0
    assert view.completed_at is None and view.completion_notes is None


async def test_create_writes_history_and_timeline(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)

    assert [e.event_type for e in await _events_of(db_session, view.public_id)] == [
        TASK_EVENT_CREATED
    ]
    assert await _timeline_types(db_session, contact) == [EVENT_TASK_CREATED]


async def test_create_for_another_agent_emits_assignment(
    db_session, organization, actor, contact, make_user
):
    other = (await make_user(email="other@vi.test", roles=("agent",))).user

    view = await _create(
        db_session, organization, actor, contact,
        assigned_agent_id=uuidlib.UUID(other.public_id),
    )

    assert view.assigned_agent_id == other.public_id
    assert view.created_by == actor.public_id  # "assigned by" stays the creator (FR-TASK-06)
    types = [e.event_type for e in await _events_of(db_session, view.public_id)]
    assert types == [TASK_EVENT_CREATED, TASK_EVENT_ASSIGNED]
    assert await _timeline_types(db_session, contact) == [EVENT_TASK_CREATED, EVENT_TASK_ASSIGNED]


async def test_create_rejects_unknown_contact(db_session, organization, actor):
    with pytest.raises(NotFoundError):
        await _svc(db_session).create(
            organization_id=organization.id, actor=actor, contact_id=uuidlib.uuid4(),
            conversation_id=None, title="x", task_type=TASK_TYPE_CALL, priority="medium",
            due_at=utcnow(), has_time=True, reminder_at=None, description=None,
            assigned_agent_id=None,
        )


async def test_create_rejects_unknown_task_type(db_session, organization, actor, contact):
    with pytest.raises(BadRequestError):
        await _create(db_session, organization, actor, contact, task_type="teleport")


# --- State machine (Doc 14 §4.4, TA-INV 1–4) ----------------------------------------------------
async def test_complete_sets_completion_fields(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)

    done = await _svc(db_session).complete(
        organization_id=organization.id, actor=actor,
        public_id=uuidlib.UUID(view.public_id), expected_row_version=None,
        completion_notes="Documents received.", create_timeline_note=False,
    )

    assert done.status == TASK_STATUS_COMPLETED
    assert done.completed_at is not None
    assert done.completion_notes == "Documents received."


@pytest.mark.parametrize(
    "terminal,method",
    [
        (TASK_STATUS_COMPLETED, "complete"),
        (TASK_STATUS_SKIPPED, "skip"),
        (TASK_STATUS_CANCELLED, "cancel"),
    ],
)
async def test_terminal_transitions_only_from_open(
    db_session, organization, actor, contact, terminal, method
):
    """A task may leave ``open`` once; a second terminal transition is a 409 (TA-INV 1–3)."""
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    kwargs = {"organization_id": organization.id, "actor": actor, "public_id": task_id,
              "expected_row_version": None}
    first = getattr(_svc(db_session), method)
    moved = await (
        first(**kwargs, completion_notes=None, create_timeline_note=False)
        if method == "complete"
        else first(**kwargs, reason=None)
    )
    assert moved.status == terminal

    with pytest.raises(TaskStateError) as exc:
        await (
            first(**kwargs, completion_notes=None, create_timeline_note=False)
            if method == "complete"
            else first(**kwargs, reason=None)
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "task_state"


async def test_cancelled_task_cannot_be_completed(db_session, organization, actor, contact):
    """The cross-transition the old code allowed: cancelled → completed is not in §4.4."""
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    await _svc(db_session).cancel(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, reason="Customer withdrew.",
    )

    with pytest.raises(TaskStateError):
        await _svc(db_session).complete(
            organization_id=organization.id, actor=actor, public_id=task_id,
            expected_row_version=None, completion_notes=None, create_timeline_note=False,
        )


async def test_open_task_cannot_be_reopened(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)

    with pytest.raises(TaskStateError):
        await _svc(db_session).reopen(
            organization_id=organization.id, actor=actor,
            public_id=uuidlib.UUID(view.public_id), expected_row_version=None,
        )


@pytest.mark.parametrize("method", ["skip", "cancel"])
async def test_reopen_returns_terminal_to_open(db_session, organization, actor, contact, method):
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    await getattr(_svc(db_session), method)(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, reason="later",
    )

    reopened = await _svc(db_session).reopen(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None,
    )

    assert reopened.status == TASK_STATUS_OPEN


async def test_reopen_clears_every_completion_field(db_session, organization, actor, contact):
    """TA-INV 4 — ``completion_notes`` must not survive a reopen (the audited defect)."""
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, completion_notes="Done and dusted.",
        create_timeline_note=False,
    )

    reopened = await _svc(db_session).reopen(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None,
    )

    assert reopened.status == TASK_STATUS_OPEN
    assert reopened.completed_at is None
    assert reopened.completion_notes is None
    row = (await db_session.scalars(select(Task).where(Task.uuid == task_id.bytes))).first()
    await db_session.refresh(row)
    assert row.completed_by is None
    # The cleared values survive in history — reopen is logged, not erased (TA-INV 6).
    reopen_event = [
        e for e in await _events_of(db_session, view.public_id)
        if e.event_type == TASK_EVENT_REOPENED
    ][0]
    assert reopen_event.from_json["completion_notes"] == "Done and dusted."


async def test_skip_and_cancel_are_retained_not_deleted(db_session, organization, actor, contact):
    """TA-INV 3 — business outcomes stay fully auditable."""
    view = await _create(db_session, organization, actor, contact)
    await _svc(db_session).skip(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(view.public_id),
        expected_row_version=None, reason="No answer.",
    )

    row = (
        await db_session.scalars(
            select(Task).where(Task.uuid == uuidlib.UUID(view.public_id).bytes)
        )
    ).first()
    await db_session.refresh(row)
    assert row.deleted_at is None and row.status == TASK_STATUS_SKIPPED
    skip_event = [
        e for e in await _events_of(db_session, view.public_id)
        if e.event_type == TASK_EVENT_SKIPPED
    ][0]
    assert skip_event.note == "No answer."
    assert skip_event.from_json == {"status": TASK_STATUS_OPEN}


async def test_soft_delete_is_not_cancel(db_session, organization, actor, contact):
    """TA-INV 5 — delete is cleanup: the row keeps its status and drops out of reads."""
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)

    await _svc(db_session).delete(
        organization_id=organization.id, actor=actor, public_id=task_id
    )

    row = (await db_session.scalars(select(Task).where(Task.uuid == task_id.bytes))).first()
    await db_session.refresh(row)
    assert row.deleted_at is not None
    assert row.status == TASK_STATUS_OPEN  # not cancelled
    with pytest.raises(NotFoundError):
        await _svc(db_session).get(organization_id=organization.id, public_id=task_id)


# --- Timeline projection (Doc 14 §5.3, TA-INV 6) ------------------------------------------------
async def test_lifecycle_projects_onto_contact_timeline(
    db_session, organization, actor, contact, make_user
):
    other = (await make_user(email="peer@vi.test", roles=("agent",))).user
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    svc = _svc(db_session)
    await svc.reschedule(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, due_at=utcnow() + timedelta(days=3),
        has_time=True, reminder_at=None,
    )
    await svc.reassign(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, assigned_agent_id=uuidlib.UUID(other.public_id),
    )
    await svc.complete(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, completion_notes=None, create_timeline_note=False,
    )

    assert await _timeline_types(db_session, contact) == [
        EVENT_TASK_CREATED, EVENT_TASK_RESCHEDULED, EVENT_TASK_ASSIGNED, EVENT_TASK_COMPLETED,
    ]


async def test_projection_payload_and_ref(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact, priority=TASK_PRIORITY_HIGH)

    event = (
        await db_session.scalars(
            select(ContactEvent).where(ContactEvent.contact_id == contact.id)
        )
    ).first()
    task = (
        await db_session.scalars(
            select(Task).where(Task.uuid == uuidlib.UUID(view.public_id).bytes)
        )
    ).first()
    assert event.ref_type == REF_TYPE_TASK and event.ref_id == task.id
    assert event.payload_json["title"] == "Collect Aadhaar"
    assert event.payload_json["priority"] == TASK_PRIORITY_HIGH
    assert event.payload_json["status"] == TASK_STATUS_OPEN


async def test_cancel_projects_but_skip_does_not(db_session, organization, actor, contact):
    """§5.3 defines five constants — ``skipped`` has none, so it stays history-only."""
    skipped = await _create(db_session, organization, actor, contact, title="Skip me")
    cancelled = await _create(db_session, organization, actor, contact, title="Cancel me")
    svc = _svc(db_session)
    await svc.skip(
        organization_id=organization.id, actor=actor,
        public_id=uuidlib.UUID(skipped.public_id), expected_row_version=None, reason=None,
    )
    await svc.cancel(
        organization_id=organization.id, actor=actor,
        public_id=uuidlib.UUID(cancelled.public_id), expected_row_version=None, reason=None,
    )

    types = await _timeline_types(db_session, contact)
    assert types.count(EVENT_TASK_CANCELLED) == 1
    assert EVENT_TASK_COMPLETED not in types


async def test_completion_note_surfaces_only_when_requested(
    db_session, organization, actor, contact
):
    """FR-TASK-07 — the projection always fires; the flag decides whether the note is surfaced."""
    quiet = await _create(db_session, organization, actor, contact, title="Quiet")
    loud = await _create(db_session, organization, actor, contact, title="Loud")
    svc = _svc(db_session)
    await svc.complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(quiet.public_id),
        expected_row_version=None, completion_notes="private", create_timeline_note=False,
    )
    await svc.complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(loud.public_id),
        expected_row_version=None, completion_notes="shared", create_timeline_note=True,
    )

    rows = (
        await db_session.scalars(
            select(ContactEvent)
            .where(ContactEvent.contact_id == contact.id,
                   ContactEvent.event_type == EVENT_TASK_COMPLETED)
            .order_by(ContactEvent.id)
        )
    ).all()
    assert "note" not in rows[0].payload_json
    assert rows[1].payload_json["note"] == "shared"


# --- Optimistic concurrency (TA-INV 7) ----------------------------------------------------------
async def test_stale_row_version_conflicts(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    await _svc(db_session).reschedule(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=view.row_version, due_at=utcnow() + timedelta(days=2),
        has_time=True, reminder_at=None,
    )

    with pytest.raises(VersionConflictError) as exc:
        await _svc(db_session).complete(
            organization_id=organization.id, actor=actor, public_id=task_id,
            expected_row_version=view.row_version,  # now stale
            completion_notes=None, create_timeline_note=False,
        )
    assert exc.value.status_code == 409


async def test_row_version_increments_on_each_write(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)

    bumped = await _svc(db_session).update(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=0, title="Renamed", description=None, task_type=None,
        priority=None, due_at=None, has_time=None, reminder_at=None,
    )

    assert bumped.row_version == 1
    assert bumped.title == "Renamed"


async def test_omitted_row_version_skips_the_guard(db_session, organization, actor, contact):
    """The guard is opt-in: a client that does not send a version is not blocked."""
    view = await _create(db_session, organization, actor, contact)
    done = await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(view.public_id),
        expected_row_version=None, completion_notes=None, create_timeline_note=False,
    )
    assert done.status == TASK_STATUS_COMPLETED


# --- Buckets (Doc 14 §7.3) ----------------------------------------------------------------------
async def _seeded_buckets(db_session, organization, actor, contact) -> dict[str, str]:
    """One task in each bucket, keyed by name (times are UTC — the actor's default timezone)."""
    now = utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    made = {
        "overdue": start - timedelta(hours=2),
        "today": start + timedelta(hours=12),
        "upcoming": start + timedelta(days=2),
    }
    out = {}
    for name, due in made.items():
        view = await _create(db_session, organization, actor, contact, title=name, due_at=due)
        out[name] = view.public_id
    return out


@pytest.mark.parametrize("view_name", ["overdue", "today", "upcoming"])
async def test_bucket_selects_only_its_window(
    db_session, organization, actor, contact, view_name
):
    seeded = await _seeded_buckets(db_session, organization, actor, contact)

    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, view=view_name, limit=50
    )

    assert [t.public_id for t in result.tasks] == [seeded[view_name]]


async def test_completed_bucket_excludes_open_tasks(db_session, organization, actor, contact):
    await _seeded_buckets(db_session, organization, actor, contact)
    done = await _create(db_session, organization, actor, contact, title="finished")
    await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(done.public_id),
        expected_row_version=None, completion_notes=None, create_timeline_note=False,
    )

    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, view="completed", limit=50
    )

    assert [t.public_id for t in result.tasks] == [done.public_id]


async def test_stats_counts_each_bucket(db_session, organization, actor, contact):
    await _seeded_buckets(db_session, organization, actor, contact)
    done = await _create(db_session, organization, actor, contact, title="finished")
    await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(done.public_id),
        expected_row_version=None, completion_notes=None, create_timeline_note=False,
    )

    stats = await _svc(db_session).stats(
        organization_id=organization.id, actor=actor, assignee_id=None
    )

    assert (stats.overdue, stats.due_today, stats.upcoming, stats.completed_today) == (1, 1, 1, 1)


async def test_stats_rejects_unknown_assignee(db_session, organization, actor):
    with pytest.raises(NotFoundError):
        await _svc(db_session).stats(
            organization_id=organization.id, actor=actor, assignee_id=uuidlib.uuid4()
        )


async def test_invalid_view_is_rejected(db_session, organization, actor):
    with pytest.raises(BadRequestError):
        await _svc(db_session).list(
            organization_id=organization.id, actor=actor, view="yesterday", limit=50
        )


async def test_invalid_sort_is_rejected(db_session, organization, actor):
    with pytest.raises(BadRequestError):
        await _svc(db_session).list(
            organization_id=organization.id, actor=actor, sort="colour", limit=50
        )


# --- Cursor pagination (Doc 14 §7.2) ------------------------------------------------------------
async def _page_all(db_session, organization, actor, *, sort: str, limit: int) -> list[str]:
    """Walk every page, asserting the walk terminates and never repeats a row."""
    seen: list[str] = []
    cursor = None
    for _ in range(20):
        result = await _svc(db_session).list(
            organization_id=organization.id, actor=actor, sort=sort, cursor=cursor, limit=limit
        )
        seen.extend(t.public_id for t in result.tasks)
        if not result.has_more:
            return seen
        cursor = result.next_cursor
    raise AssertionError("pagination did not terminate")


async def test_due_at_pagination_is_stable_and_complete(
    db_session, organization, actor, contact
):
    base = utcnow() + timedelta(days=1)
    for i in range(7):
        await _create(
            db_session, organization, actor, contact,
            title=f"t{i}", due_at=base + timedelta(hours=i),
        )

    walked = await _page_all(db_session, organization, actor, sort="due_at", limit=3)

    assert len(walked) == 7
    assert len(set(walked)) == 7  # no row seen twice across page boundaries


async def test_priority_sort_pagination_walks_composite_key(
    db_session, organization, actor, contact
):
    """The ``(rank, due_at)`` keyset needs this module's own cursor — walk it end to end."""
    order = [TASK_PRIORITY_LOW, TASK_PRIORITY_CRITICAL, TASK_PRIORITY_HIGH, "medium"] * 2
    base = utcnow() + timedelta(days=1)
    for i, prio in enumerate(order):
        await _create(
            db_session, organization, actor, contact,
            title=f"p{i}", priority=prio, due_at=base + timedelta(minutes=i),
        )

    walked = await _page_all(db_session, organization, actor, sort="-priority", limit=3)

    assert len(walked) == len(order) and len(set(walked)) == len(order)
    first_page = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, sort="-priority", limit=2
    )
    assert [t.priority for t in first_page.tasks] == [TASK_PRIORITY_CRITICAL] * 2


async def test_completed_at_sort_excludes_unfinished_tasks(
    db_session, organization, actor, contact
):
    """A task that was never completed has no position on a completion-ordered list."""
    await _create(db_session, organization, actor, contact, title="still open")
    done = await _create(db_session, organization, actor, contact, title="done")
    await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(done.public_id),
        expected_row_version=None, completion_notes=None, create_timeline_note=False,
    )

    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, sort="-completed_at", limit=50
    )

    assert [t.public_id for t in result.tasks] == [done.public_id]


async def test_malformed_cursor_is_rejected(db_session, organization, actor):
    with pytest.raises(BadRequestError):
        await _svc(db_session).list(
            organization_id=organization.id, actor=actor, sort="priority",
            cursor="not-a-cursor", limit=10,
        )


# --- Filters (Doc 14 §7.2) ----------------------------------------------------------------------
async def test_assignee_and_creator_filters(db_session, organization, actor, contact, make_user):
    other = (await make_user(email="peer@vi.test", roles=("agent",))).user
    mine = await _create(db_session, organization, actor, contact, title="mine")
    theirs = await _create(
        db_session, organization, actor, contact, title="theirs",
        assigned_agent_id=uuidlib.UUID(other.public_id),
    )

    to_me = await _svc(db_session).list(
        organization_id=organization.id, actor=actor,
        assignee_id=uuidlib.UUID(actor.public_id), limit=50,
    )
    by_me = await _svc(db_session).list(
        organization_id=organization.id, actor=actor,
        assigned_by_id=uuidlib.UUID(actor.public_id), limit=50,
    )

    assert [t.public_id for t in to_me.tasks] == [mine.public_id]
    assert {t.public_id for t in by_me.tasks} == {mine.public_id, theirs.public_id}


async def test_search_matches_title_and_description(db_session, organization, actor, contact):
    await _create(db_session, organization, actor, contact, title="Collect Aadhaar")
    await _create(db_session, organization, actor, contact, title="Call about renewal")

    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, q="aadhaar", limit=50
    )

    assert [t.title for t in result.tasks] == ["Collect Aadhaar"]


async def test_deleted_tasks_are_excluded_from_lists(db_session, organization, actor, contact):
    kept = await _create(db_session, organization, actor, contact, title="kept")
    gone = await _create(db_session, organization, actor, contact, title="gone")
    await _svc(db_session).delete(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(gone.public_id)
    )

    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, limit=50
    )

    assert [t.public_id for t in result.tasks] == [kept.public_id]


# --- Bulk operations (Doc 14 §7.1, Doc 04 §29) --------------------------------------------------
async def test_bulk_update_applies_and_writes_typed_history(
    db_session, organization, actor, contact
):
    ids = [
        uuidlib.UUID((await _create(db_session, organization, actor, contact, title=f"b{i}")).public_id)
        for i in range(3)
    ]

    outcome = await _svc(db_session).bulk_update(
        organization_id=organization.id, actor=actor, public_ids=ids,
        status=None, priority=TASK_PRIORITY_CRITICAL, due_at=None, assigned_agent_id=None,
    )

    assert (outcome.succeeded, outcome.failed, outcome.skipped) == (3, 0, 0)
    types = [e.event_type for e in await _events_of(db_session, str(ids[0]))]
    assert TASK_EVENT_PRIORITY_CHANGED in types


async def test_bulk_update_reports_illegal_transitions_as_failures(
    db_session, organization, actor, contact
):
    """A cancelled task cannot be completed in bulk either — and it fails alone."""
    ok = await _create(db_session, organization, actor, contact, title="ok")
    blocked = await _create(db_session, organization, actor, contact, title="blocked")
    await _svc(db_session).cancel(
        organization_id=organization.id, actor=actor,
        public_id=uuidlib.UUID(blocked.public_id), expected_row_version=None, reason=None,
    )

    outcome = await _svc(db_session).bulk_update(
        organization_id=organization.id, actor=actor,
        public_ids=[uuidlib.UUID(ok.public_id), uuidlib.UUID(blocked.public_id)],
        status=TASK_STATUS_COMPLETED, priority=None, due_at=None, assigned_agent_id=None,
    )

    assert (outcome.succeeded, outcome.failed) == (1, 1)
    rows = {
        r.title: r
        for r in (await db_session.scalars(select(Task))).all()
    }
    await db_session.refresh(rows["ok"])
    await db_session.refresh(rows["blocked"])
    assert rows["ok"].status == TASK_STATUS_COMPLETED
    assert rows["blocked"].status == TASK_STATUS_CANCELLED  # untouched


async def test_bulk_rejected_item_is_not_partially_applied(
    db_session, organization, actor, contact
):
    """Priority must not stick on an item whose status change is refused."""
    blocked = await _create(
        db_session, organization, actor, contact, title="blocked", priority=TASK_PRIORITY_LOW
    )
    await _svc(db_session).cancel(
        organization_id=organization.id, actor=actor,
        public_id=uuidlib.UUID(blocked.public_id), expected_row_version=None, reason=None,
    )

    outcome = await _svc(db_session).bulk_update(
        organization_id=organization.id, actor=actor,
        public_ids=[uuidlib.UUID(blocked.public_id)],
        status=TASK_STATUS_COMPLETED, priority=TASK_PRIORITY_CRITICAL,
        due_at=None, assigned_agent_id=None,
    )

    assert outcome.failed == 1 and outcome.succeeded == 0
    row = (
        await db_session.scalars(
            select(Task).where(Task.uuid == uuidlib.UUID(blocked.public_id).bytes)
        )
    ).first()
    await db_session.refresh(row)
    assert row.priority == TASK_PRIORITY_LOW  # rolled forward untouched


async def test_bulk_update_counts_unknown_ids_as_skipped(
    db_session, organization, actor, contact
):
    known = await _create(db_session, organization, actor, contact)

    outcome = await _svc(db_session).bulk_update(
        organization_id=organization.id, actor=actor,
        public_ids=[uuidlib.UUID(known.public_id), uuidlib.uuid4()],
        status=None, priority=TASK_PRIORITY_HIGH, due_at=None, assigned_agent_id=None,
    )

    assert (outcome.total, outcome.succeeded, outcome.skipped) == (2, 1, 1)


async def test_bulk_reassign_projects_timeline(db_session, organization, actor, contact, make_user):
    other = (await make_user(email="peer@vi.test", roles=("agent",))).user
    task = await _create(db_session, organization, actor, contact)

    await _svc(db_session).bulk_update(
        organization_id=organization.id, actor=actor,
        public_ids=[uuidlib.UUID(task.public_id)], status=None, priority=None, due_at=None,
        assigned_agent_id=uuidlib.UUID(other.public_id),
    )

    assert EVENT_TASK_ASSIGNED in await _timeline_types(db_session, contact)
    types = [e.event_type for e in await _events_of(db_session, task.public_id)]
    assert TASK_EVENT_REASSIGNED in types


async def test_bulk_delete_soft_deletes(db_session, organization, actor, contact):
    ids = [
        uuidlib.UUID((await _create(db_session, organization, actor, contact, title=f"d{i}")).public_id)
        for i in range(2)
    ]

    outcome = await _svc(db_session).bulk_delete(
        organization_id=organization.id, actor=actor, public_ids=[*ids, uuidlib.uuid4()]
    )

    assert (outcome.total, outcome.succeeded, outcome.skipped) == (3, 2, 1)
    result = await _svc(db_session).list(
        organization_id=organization.id, actor=actor, limit=50
    )
    assert result.tasks == []


# --- History (Doc 14 §5.2) ----------------------------------------------------------------------
async def test_history_is_ordered_and_attributed(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)
    task_id = uuidlib.UUID(view.public_id)
    await _svc(db_session).complete(
        organization_id=organization.id, actor=actor, public_id=task_id,
        expected_row_version=None, completion_notes="ok", create_timeline_note=False,
    )

    history = await _svc(db_session).history(organization_id=organization.id, public_id=task_id)

    assert [e.event_type for e in history] == [TASK_EVENT_CREATED, TASK_EVENT_COMPLETED]
    assert history[0].actor_user_id == actor.public_id
    assert history[0].actor_name == actor.full_name
    assert history[1].note == "ok"


async def test_history_of_unknown_task_is_404(db_session, organization, actor):
    with pytest.raises(NotFoundError):
        await _svc(db_session).history(
            organization_id=organization.id, public_id=uuidlib.uuid4()
        )


async def test_reassign_history_never_leaks_internal_ids(
    db_session, organization, actor, contact, make_user
):
    other = (await make_user(email="peer@vi.test", roles=("agent",))).user
    view = await _create(db_session, organization, actor, contact)

    await _svc(db_session).reassign(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(view.public_id),
        expected_row_version=None, assigned_agent_id=uuidlib.UUID(other.public_id),
    )

    event = [
        e for e in await _events_of(db_session, view.public_id)
        if e.event_type == TASK_EVENT_REASSIGNED
    ][0]
    assert event.from_json == {"assigned_agent": actor.public_id}
    assert event.to_json == {"assigned_agent": other.public_id}


# --- Org scoping --------------------------------------------------------------------------------
async def test_task_from_another_org_is_not_found(db_session, organization, actor, contact):
    view = await _create(db_session, organization, actor, contact)

    with pytest.raises(NotFoundError):
        await _svc(db_session).get(
            organization_id=organization.id + 999, public_id=uuidlib.UUID(view.public_id)
        )
