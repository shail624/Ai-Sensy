"""Task service (Doc 14 §4.5) — the CRM Follow-up Engine's business rules.

Every mutation writes the same transaction: the task change, an immutable ``task_events`` row
(history, Doc 14 §5.2), and — for create/assign/reschedule/complete/cancel — a ``contact_events``
projection onto the frozen activity timeline (``ref_type="task"``, Doc 14 §5.3). Public UUIDs in
and out; internal integer ids never leave the service. Optimistic concurrency is enforced with the
``row_version`` counter (``409`` on mismatch, Doc 14 §14).
"""

from __future__ import annotations

import base64
import builtins
import json
import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, encode_cursor
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    VersionConflictError,
)
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_event import (
    EVENT_TASK_ASSIGNED,
    EVENT_TASK_CANCELLED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_CREATED,
    EVENT_TASK_DUE_NOTIFIED,
    EVENT_TASK_RESCHEDULED,
    EVENT_TASK_SNOOZED,
    REF_TYPE_TASK,
)
from app.models.conversation import Conversation
from app.models.task import (
    TASK_PRIORITIES,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_OPEN,
    TASK_STATUS_SKIPPED,
    TASK_TERMINAL_STATUSES,
    TASK_TYPES,
    Task,
)
from app.models.task_event import (
    TASK_EVENT_ASSIGNED,
    TASK_EVENT_CANCELLED,
    TASK_EVENT_COMPLETED,
    TASK_EVENT_CREATED,
    TASK_EVENT_DUE_NOTIFIED,
    TASK_EVENT_NOTE_ADDED,
    TASK_EVENT_PRIORITY_CHANGED,
    TASK_EVENT_REASSIGNED,
    TASK_EVENT_REOPENED,
    TASK_EVENT_RESCHEDULED,
    TASK_EVENT_SKIPPED,
    TASK_EVENT_SNOOZED,
    TASK_EVENT_STATUS_CHANGED,
    TaskEvent,
)
from app.models.user import User
from app.models.vi_domain import KycCase, ReactivationCase
from app.repositories.task import (
    SORT_COMPLETED_AT,
    SORT_CREATED_AT,
    SORT_DUE_AT,
    SORT_PRIORITY,
    TaskRepository,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService
from app.services.notification_service import NotificationService

_UTC = ZoneInfo("UTC")
_VALID_SORTS = {SORT_DUE_AT, SORT_CREATED_AT, SORT_PRIORITY, SORT_COMPLETED_AT}
_BUCKET_TODAY = "today"
_BUCKET_OVERDUE = "overdue"
_BUCKET_UPCOMING = "upcoming"
_BUCKET_COMPLETED = "completed"
_BUCKET_ALL = "all"
_VALID_VIEWS = {_BUCKET_TODAY, _BUCKET_OVERDUE, _BUCKET_UPCOMING, _BUCKET_COMPLETED, _BUCKET_ALL}


class TaskStateError(ConflictError):
    """The transition does not apply from the task's current state (Doc 14 §4.4 → 409)."""

    code = "task_state"
    title = "Task State Conflict"


#: Which status changes project onto the contact timeline (Doc 14 §5.3 defines five constants;
#: ``skipped`` and ``reopened`` have none, so they stay task-history-only).
_STATUS_PROJECTION: dict[str, str] = {
    TASK_STATUS_COMPLETED: EVENT_TASK_COMPLETED,
    TASK_STATUS_CANCELLED: EVENT_TASK_CANCELLED,
}


# --- Views (API projections) ------------------------------------------------------------------
@dataclass(slots=True)
class TaskView:
    public_id: str
    contact_id: str
    contact_name: str | None
    conversation_id: str | None
    reference_type: str | None
    reference_id: str | None
    title: str
    task_type: str
    status: str
    priority: str
    due_at: datetime
    has_time: bool
    reminder_at: datetime | None
    description: str | None
    assigned_agent_id: str
    assigned_agent_name: str | None
    created_by: str | None
    created_by_name: str | None
    completion_notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    row_version: int
    due_notified_at: datetime | None = None


@dataclass(slots=True)
class TaskEventView:
    id: int
    event_type: str
    actor_user_id: str | None
    actor_name: str | None
    from_value: dict[str, Any] | None
    to_value: dict[str, Any] | None
    note: str | None
    created_at: datetime


@dataclass(slots=True)
class TaskListResult:
    tasks: list[TaskView]
    has_more: bool
    next_cursor: str | None


@dataclass(slots=True)
class TaskStats:
    overdue: int
    due_today: int
    upcoming: int
    completed_today: int


@dataclass(slots=True)
class BulkOutcome:
    total: int
    processed: int
    succeeded: int
    failed: int
    skipped: int


def _encode_composite(rank: int, due: datetime | None, task_id: int) -> str:
    """Encode the ``priority`` sort's two-part key.

    The frozen ``encode_cursor`` codec carries exactly one datetime key, which the ``(rank, due_at)``
    ordering of the priority sort cannot express. This is that sort's own self-describing cursor;
    ``app/api/pagination.py`` stays unmodified (Doc 14 §3 reuse map).
    """
    payload = {"r": rank, "t": due.isoformat() if due is not None else None, "id": task_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode("ascii").rstrip("=")


def _decode_composite(cursor: str) -> tuple[list[object], int]:
    """Inverse of :func:`_encode_composite`; a malformed cursor is a 400 (Doc 04 §5)."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        due = datetime.fromisoformat(data["t"]) if data["t"] is not None else None
        return [int(data["r"]), due], int(data["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise BadRequestError("Invalid pagination cursor.") from exc


def _day_bounds_utc(tz_name: str) -> tuple[datetime, datetime]:
    """Start/end of "today" in ``tz_name``, expressed as naive-UTC (the stored form, Doc 14 §7.3)."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = _UTC
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1) - timedelta(microseconds=1)
    start_utc = start_local.astimezone(_UTC).replace(tzinfo=None)
    end_utc = end_local.astimezone(_UTC).replace(tzinfo=None)
    return start_utc, end_utc


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TaskRepository(session)
        #: The frozen timeline writer — task lifecycle projects through it, never around it.
        self._timeline = ContactEventService(session)
        self._audit = AuditService(session)

    # --- Reads --------------------------------------------------------------------------------
    async def get(self, *, organization_id: int, public_id: uuidlib.UUID) -> TaskView:
        task = await self._require_task(organization_id, public_id)
        return (await self._build_views([task]))[0]

    async def list(
        self,
        *,
        organization_id: int,
        actor: User,
        view: str = _BUCKET_ALL,
        assignee_id: uuidlib.UUID | None = None,
        assigned_by_id: uuidlib.UUID | None = None,
        contact_id: uuidlib.UUID | None = None,
        conversation_id: uuidlib.UUID | None = None,
        statuses: list[str] | None = None,
        types: list[str] | None = None,
        priorities: list[str] | None = None,
        due_from: datetime | None = None,
        due_to: datetime | None = None,
        q: str | None = None,
        sort: str = SORT_DUE_AT,
        cursor: str | None = None,
        limit: int,
    ) -> TaskListResult:
        if view not in _VALID_VIEWS:
            raise BadRequestError(f"view must be one of {sorted(_VALID_VIEWS)}")
        sort_key, descending = self._parse_sort(sort, view)
        self._validate_enums(types, priorities)

        # Resolve public-id filters to internal ids.
        assignee_int = await self._resolve_user_id(organization_id, assignee_id)
        assigned_by_int = await self._resolve_user_id(organization_id, assigned_by_id)
        contact_int = await self._resolve_contact_id(organization_id, contact_id)
        conversation_int = await self._resolve_conversation_id(organization_id, conversation_id)

        bucket_statuses, b_from, b_to = self._bucket_window(view, actor.timezone)
        effective_statuses = statuses or bucket_statuses
        effective_from = due_from if due_from is not None else b_from
        effective_to = due_to if due_to is not None else b_to

        decoded = self._decode_cursor(cursor, sort_key)
        tasks, has_more = await self._repo.list_page(
            organization_id,
            assignee_id=assignee_int,
            assigned_by_id=assigned_by_int,
            contact_id=contact_int,
            conversation_id=conversation_int,
            statuses=effective_statuses,
            types=types,
            priorities=priorities,
            due_from=effective_from,
            due_to=effective_to,
            q=q,
            sort=sort_key,
            descending=descending,
            cursor=decoded,
            limit=limit,
        )
        next_cursor = None
        if has_more and tasks:
            last = tasks[-1]
            next_cursor = self._encode_cursor(
                self._repo.cursor_values(last, sort_key), last.id, sort_key
            )
        views = await self._build_views(tasks)
        return TaskListResult(tasks=views, has_more=has_more, next_cursor=next_cursor)

    async def history(
        self,
        *,
        organization_id: int,
        public_id: uuidlib.UUID,
        # `builtins.list`, because this class defines a method named `list` (above) which shadows the
        # builtin for every annotation that follows it in the class body. `from __future__ import
        # annotations` keeps that harmless at run time — annotations are never evaluated — but the
        # name still resolves to the method, so this signature reads as "returns TaskService.list"
        # to any type checker, and `typing.get_type_hints()` on it would raise.
    ) -> builtins.list[TaskEventView]:
        task = await self._require_task(organization_id, public_id)
        events = await self._repo.list_events(task.id)
        actor_ids = {e.actor_user_id for e in events if e.actor_user_id is not None}
        users = await self._user_map(actor_ids)
        return [
            TaskEventView(
                id=e.id,
                event_type=e.event_type,
                actor_user_id=users[e.actor_user_id][0] if e.actor_user_id in users else None,
                actor_name=users[e.actor_user_id][1] if e.actor_user_id in users else None,
                from_value=e.from_json,
                to_value=e.to_json,
                note=e.note,
                created_at=e.created_at,
            )
            for e in events
        ]

    async def stats(
        self, *, organization_id: int, actor: User, assignee_id: uuidlib.UUID | None
    ) -> TaskStats:
        target = actor.id
        if assignee_id is not None:
            resolved = await self._resolve_user_id(organization_id, assignee_id)
            if resolved is None:
                raise NotFoundError("Assignee not found.")
            target = resolved
        start, end = _day_bounds_utc(actor.timezone)
        counts = await self._repo.bucket_counts(
            organization_id, target, today_start=start, today_end=end
        )
        return TaskStats(**counts)

    # --- Writes -------------------------------------------------------------------------------
    async def create(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_id: uuidlib.UUID,
        conversation_id: uuidlib.UUID | None,
        title: str,
        task_type: str,
        priority: str,
        due_at: datetime,
        has_time: bool,
        reminder_at: datetime | None,
        description: str | None,
        assigned_agent_id: uuidlib.UUID | None,
        reference_type: str | None = None,
        reference_id: int | None = None,
        idempotency_key: bytes | None = None,
        request_hash: str | None = None,
        commit: bool = True,
    ) -> TaskView:
        self._validate_enums([task_type], [priority])
        contact = await self._require_contact(organization_id, contact_id)
        conversation_int = await self._resolve_conversation_id(organization_id, conversation_id)
        if conversation_id is not None and conversation_int is None:
            raise NotFoundError("Conversation not found.")
        assignee = (
            await self._require_user(organization_id, assigned_agent_id)
            if assigned_agent_id is not None
            else actor
        )
        task = Task(
            organization_id=organization_id,
            contact_id=contact.id,
            conversation_id=conversation_int,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            assigned_agent_id=assignee.id,
            title=title,
            description=description,
            task_type=task_type,
            status=TASK_STATUS_OPEN,
            priority=priority,
            due_at=due_at,
            has_time=has_time,
            reminder_at=reminder_at,
            created_by=actor.id,
        )
        await self._repo.add(task)
        self._add_event(task, TASK_EVENT_CREATED, actor.id, to_json=self._snapshot(task))
        await self._project(task, EVENT_TASK_CREATED)
        await self._audit_task(
            task, AuditAction.TASK_CREATED, actor_id=actor.id, after=self._snapshot(task)
        )
        if assignee.id != actor.id:
            self._add_event(
                task, TASK_EVENT_ASSIGNED, actor.id, to_json={"assigned_agent": assignee.public_id}
            )
            await self._project(task, EVENT_TASK_ASSIGNED)
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    async def domain_views(self, tasks: builtins.list[Task]) -> builtins.list[TaskView]:
        """Build public task projections for an owning domain service without duplicating joins."""
        return await self._build_views(tasks)

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        title: str | None,
        description: str | None,
        task_type: str | None,
        priority: str | None,
        due_at: datetime | None,
        has_time: bool | None,
        reminder_at: datetime | None,
        commit: bool = True,
    ) -> TaskView:
        self._validate_enums([task_type] if task_type else None, [priority] if priority else None)
        task = await self._require_task(organization_id, public_id)
        before = self._snapshot(task)
        self._check_version(task, expected_row_version)
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if task_type is not None:
            task.task_type = task_type
        if priority is not None and priority != task.priority:
            self._add_event(
                task,
                TASK_EVENT_PRIORITY_CHANGED,
                actor.id,
                from_json={"priority": task.priority},
                to_json={"priority": priority},
            )
            task.priority = priority
        rescheduled = False
        if due_at is not None and due_at != task.due_at:
            self._add_event(
                task,
                TASK_EVENT_RESCHEDULED,
                actor.id,
                from_json={"due_at": task.due_at.isoformat()},
                to_json={"due_at": due_at.isoformat()},
            )
            task.due_at = due_at
            rescheduled = True
        if has_time is not None:
            task.has_time = has_time
        if reminder_at is not None:
            task.reminder_at = reminder_at
        if rescheduled:
            task.due_notified_at = None
            await NotificationService(self._session).resolve_task(task)
            await self._project(task, EVENT_TASK_RESCHEDULED)
        self._bump(task, actor.id)
        await self._audit_task(
            task,
            AuditAction.TASK_UPDATED,
            actor_id=actor.id,
            before=before,
            after=self._snapshot(task),
        )
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    async def complete(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        completion_notes: str | None,
        create_timeline_note: bool,
        commit: bool = True,
    ) -> TaskView:
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        self._require_open(task, "completed")
        previous = task.status
        task.status = TASK_STATUS_COMPLETED
        task.completed_at = utcnow()
        task.completed_by = actor.id
        task.completion_notes = completion_notes
        self._add_event(
            task,
            TASK_EVENT_COMPLETED,
            actor.id,
            from_json={"status": previous},
            to_json={"status": TASK_STATUS_COMPLETED},
            note=completion_notes,
        )
        # TA-INV 6: the projection is unconditional. ``create_timeline_note`` decides only whether
        # the completion note is surfaced on the customer-visible timeline (FR-TASK-07).
        surfaced = completion_notes if create_timeline_note else None
        await self._project(task, EVENT_TASK_COMPLETED, note=surfaced)
        if surfaced:
            self._add_event(task, TASK_EVENT_NOTE_ADDED, actor.id, note=surfaced)
        self._bump(task, actor.id)
        await self._audit_task(
            task,
            AuditAction.TASK_COMPLETED,
            actor_id=actor.id,
            before={"status": previous},
            after={"status": task.status},
        )
        await NotificationService(self._session).resolve_task(task)
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    async def skip(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        reason: str | None,
    ) -> TaskView:
        return await self._terminal(
            organization_id,
            actor,
            public_id,
            expected_row_version,
            status=TASK_STATUS_SKIPPED,
            event=TASK_EVENT_SKIPPED,
            reason=reason,
        )

    async def cancel(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        reason: str | None,
        commit: bool = True,
    ) -> TaskView:
        return await self._terminal(
            organization_id,
            actor,
            public_id,
            expected_row_version,
            status=TASK_STATUS_CANCELLED,
            event=TASK_EVENT_CANCELLED,
            reason=reason,
            project=EVENT_TASK_CANCELLED,
            commit=commit,
        )

    async def reopen(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
    ) -> TaskView:
        """Return a terminal task to ``open``, clearing every completion field (TA-INV 4)."""
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        if not task.is_terminal:
            raise TaskStateError(f"A {task.status} task cannot be reopened.")
        cleared = {
            "status": task.status,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "completed_by": task.completed_by,
            "completion_notes": task.completion_notes,
        }
        task.status = TASK_STATUS_OPEN
        task.completed_at = None
        task.completed_by = None
        task.completion_notes = None
        self._add_event(
            task,
            TASK_EVENT_REOPENED,
            actor.id,
            from_json=cleared,
            to_json={"status": TASK_STATUS_OPEN},
        )
        self._bump(task, actor.id)
        await self._session.commit()
        return (await self._build_views([task]))[0]

    async def reschedule(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        due_at: datetime,
        has_time: bool | None,
        reminder_at: datetime | None,
        commit: bool = True,
    ) -> TaskView:
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        previous_due = task.due_at
        self._add_event(
            task,
            TASK_EVENT_RESCHEDULED,
            actor.id,
            from_json={"due_at": task.due_at.isoformat()},
            to_json={"due_at": due_at.isoformat()},
        )
        task.due_at = due_at
        task.due_notified_at = None
        await NotificationService(self._session).resolve_task(task)
        if has_time is not None:
            task.has_time = has_time
        if reminder_at is not None:
            task.reminder_at = reminder_at
        await self._project(task, EVENT_TASK_RESCHEDULED)
        self._bump(task, actor.id)
        await self._audit_task(
            task,
            AuditAction.TASK_RESCHEDULED,
            actor_id=actor.id,
            before={"due_at": previous_due.isoformat()},
            after={"due_at": due_at.isoformat()},
        )
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    async def snooze(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        minutes: int,
    ) -> TaskView:
        """Move an open reminder forward from now while retaining a distinct immutable action."""
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        self._require_open(task, "snoozed")
        previous_due = task.due_at
        task.due_at = utcnow() + timedelta(minutes=minutes)
        task.reminder_at = None
        task.due_notified_at = None
        await NotificationService(self._session).resolve_task(task)
        self._add_event(
            task,
            TASK_EVENT_SNOOZED,
            actor.id,
            from_json={"due_at": previous_due.isoformat()},
            to_json={"due_at": task.due_at.isoformat(), "minutes": minutes},
        )
        await self._project(task, EVENT_TASK_SNOOZED)
        self._bump(task, actor.id)
        await self._audit_task(
            task,
            AuditAction.TASK_SNOOZED,
            actor_id=actor.id,
            before={"due_at": previous_due.isoformat()},
            after={"due_at": task.due_at.isoformat(), "minutes": minutes},
        )
        await self._session.commit()
        return (await self._build_views([task]))[0]

    async def dispatch_due_notifications(
        self, *, now: datetime | None = None, limit: int = 500
    ) -> dict[str, int]:
        """Publish one durable assigned-user due notice per due-date revision."""
        effective_now = now or utcnow()
        tasks = await self._repo.due_for_notification(now=effective_now, limit=limit)
        for task in tasks:
            task.due_notified_at = effective_now
            self._add_event(
                task,
                TASK_EVENT_DUE_NOTIFIED,
                None,
                to_json={
                    "assigned_agent_id": task.assigned_agent_id,
                    "due_at": task.due_at.isoformat(),
                },
            )
            await self._project(task, EVENT_TASK_DUE_NOTIFIED)
            await self._audit_task(
                task,
                AuditAction.TASK_DUE_NOTIFIED,
                actor_id=None,
                after={
                    "assigned_agent_id": task.assigned_agent_id,
                    "due_at": task.due_at.isoformat(),
                },
            )
            is_follow_up = task.task_type == "reminder"
            await NotificationService(self._session).emit(
                organization_id=task.organization_id,
                recipient_user_id=task.assigned_agent_id,
                notification_type="follow_up_due" if is_follow_up else "release_date_due",
                title="Follow-up is due" if is_follow_up else "Release date is due",
                body=(
                    "A customer follow-up needs attention."
                    if is_follow_up
                    else "A name-change release action needs attention."
                ),
                dedup_key=f"task:{task.public_id}:due:{task.due_at.isoformat()}",
                contact_id=task.contact_id,
                reactivation_case_id=(
                    task.reference_id if task.reference_type == "reactivation_case" else None
                ),
                task_id=task.id,
                due_at=task.due_at,
            )
        await self._session.commit()
        return {"notified": len(tasks)}

    async def reassign(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        assigned_agent_id: uuidlib.UUID,
        commit: bool = True,
    ) -> TaskView:
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        assignee = await self._require_user(organization_id, assigned_agent_id)
        previous = await self._public_user_id(task.assigned_agent_id)
        self._add_event(
            task,
            TASK_EVENT_REASSIGNED,
            actor.id,
            from_json={"assigned_agent": previous},
            to_json={"assigned_agent": assignee.public_id},
        )
        task.assigned_agent_id = assignee.id
        task.due_notified_at = None
        await NotificationService(self._session).resolve_task(task)
        await self._project(task, EVENT_TASK_ASSIGNED)
        self._bump(task, actor.id)
        await self._audit_task(
            task,
            AuditAction.TASK_REASSIGNED,
            actor_id=actor.id,
            before={"assigned_agent": previous},
            after={"assigned_agent": assignee.public_id},
        )
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    async def delete(self, *, organization_id: int, actor: User, public_id: uuidlib.UUID) -> None:
        """Soft-delete — data cleanup, distinct from ``cancel`` (Doc 14 TA-INV 5)."""
        task = await self._require_task(organization_id, public_id)
        task.deleted_at = utcnow()
        self._bump(task, actor.id)
        await self._session.commit()

    async def bulk_update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_ids: builtins.list[uuidlib.UUID],
        status: str | None,
        priority: str | None,
        due_at: datetime | None,
        assigned_agent_id: uuidlib.UUID | None,
    ) -> BulkOutcome:
        self._validate_enums(None, [priority] if priority else None)
        if status is not None and status not in {
            TASK_STATUS_OPEN,
            TASK_STATUS_COMPLETED,
            TASK_STATUS_SKIPPED,
            TASK_STATUS_CANCELLED,
        }:
            raise BadRequestError("Invalid status.")
        assignee = (
            await self._require_user(organization_id, assigned_agent_id)
            if assigned_agent_id is not None
            else None
        )
        tasks = await self._repo.resolve_ids(organization_id, public_ids)
        found = {t.uuid for t in tasks}
        succeeded = 0
        failed = 0
        for task in tasks:
            try:
                await self._apply_bulk_change(task, actor, status, priority, due_at, assignee)
            except TaskStateError:
                # An illegal transition fails that item only — the rest of the batch still
                # applies (partial success, Doc 04 §29).
                failed += 1
                continue
            succeeded += 1
        await self._session.commit()
        missing = len(public_ids) - len({pid.bytes for pid in public_ids} & found)
        return BulkOutcome(
            total=len(public_ids),
            processed=len(public_ids),
            succeeded=succeeded,
            failed=failed,
            skipped=missing,
        )

    async def _apply_bulk_change(
        self,
        task: Task,
        actor: User,
        status: str | None,
        priority: str | None,
        due_at: datetime | None,
        assignee: User | None,
    ) -> None:
        """One task's share of a bulk update — the same typed history the single-task paths write.

        The status transition is validated **before** anything is mutated, so a rejected item is
        left entirely untouched rather than half-applied.
        """
        if status is not None and status != task.status:
            self._check_transition(task, status)
        if priority is not None and priority != task.priority:
            self._add_event(
                task,
                TASK_EVENT_PRIORITY_CHANGED,
                actor.id,
                from_json={"priority": task.priority},
                to_json={"priority": priority},
            )
            task.priority = priority
        if due_at is not None and due_at != task.due_at:
            self._add_event(
                task,
                TASK_EVENT_RESCHEDULED,
                actor.id,
                from_json={"due_at": task.due_at.isoformat()},
                to_json={"due_at": due_at.isoformat()},
            )
            task.due_at = due_at
            await self._project(task, EVENT_TASK_RESCHEDULED)
        if assignee is not None and assignee.id != task.assigned_agent_id:
            previous = await self._public_user_id(task.assigned_agent_id)
            self._add_event(
                task,
                TASK_EVENT_REASSIGNED,
                actor.id,
                from_json={"assigned_agent": previous},
                to_json={"assigned_agent": assignee.public_id},
            )
            task.assigned_agent_id = assignee.id
            await self._project(task, EVENT_TASK_ASSIGNED)
        if status is not None and status != task.status:
            previous_status = task.status
            self._apply_status(task, status, actor.id)  # raises on an illegal transition
            self._add_event(
                task,
                TASK_EVENT_STATUS_CHANGED,
                actor.id,
                from_json={"status": previous_status},
                to_json={"status": status},
            )
            projection = _STATUS_PROJECTION.get(status)
            if projection is not None:
                await self._project(task, projection)
        self._bump(task, actor.id)

    async def bulk_delete(
        self, *, organization_id: int, actor: User, public_ids: builtins.list[uuidlib.UUID]
    ) -> BulkOutcome:
        tasks = await self._repo.resolve_ids(organization_id, public_ids)
        found = {t.uuid for t in tasks}
        for task in tasks:
            task.deleted_at = utcnow()
            self._bump(task, actor.id)
        await self._session.commit()
        missing = len(public_ids) - len({pid.bytes for pid in public_ids} & found)
        return BulkOutcome(
            total=len(public_ids),
            processed=len(public_ids),
            succeeded=len(tasks),
            failed=0,
            skipped=missing,
        )

    # --- Internals ----------------------------------------------------------------------------
    async def _terminal(
        self,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        *,
        status: str,
        event: str,
        reason: str | None,
        project: str | None = None,
        commit: bool = True,
    ) -> TaskView:
        task = await self._require_task(organization_id, public_id)
        self._check_version(task, expected_row_version)
        self._require_open(task, status)
        previous = task.status
        task.status = status
        self._add_event(
            task,
            event,
            actor.id,
            from_json={"status": previous},
            to_json={"status": status},
            note=reason,
        )
        if project is not None:
            await self._project(task, project, note=reason)
        self._bump(task, actor.id)
        action = (
            AuditAction.TASK_CANCELLED
            if status == TASK_STATUS_CANCELLED
            else AuditAction.TASK_UPDATED
        )
        await self._audit_task(
            task,
            action,
            actor_id=actor.id,
            before={"status": previous},
            after={"status": status, "reason": reason},
        )
        await NotificationService(self._session).resolve_task(task)
        if commit:
            await self._session.commit()
        return (await self._build_views([task]))[0]

    @staticmethod
    def _require_open(task: Task, target: str) -> None:
        """Only an ``open`` task may be completed, skipped or cancelled (Doc 14 §4.4)."""
        if not task.is_open:
            raise TaskStateError(f"A {task.status} task cannot be {target}.")

    @staticmethod
    def _check_transition(task: Task, status: str) -> None:
        """Validate a status change without mutating — the guard for every write path (§4.4)."""
        if status == TASK_STATUS_OPEN:
            if not task.is_terminal:
                raise TaskStateError(f"A {task.status} task cannot be reopened.")
        elif status in TASK_TERMINAL_STATUSES:
            TaskService._require_open(task, status)
        else:  # pragma: no cover - the schema layer rejects unknown statuses first
            raise BadRequestError(f"Invalid status {status!r}.")

    def _apply_status(self, task: Task, status: str, actor_id: int) -> None:
        """Apply a bulk status change, enforcing the same state machine as the single-task paths."""
        self._check_transition(task, status)
        if status == TASK_STATUS_OPEN:
            task.completed_at = None
            task.completed_by = None
            task.completion_notes = None
        elif status == TASK_STATUS_COMPLETED:
            task.completed_at = utcnow()
            task.completed_by = actor_id
        task.status = status

    def _add_event(
        self,
        task: Task,
        event_type: str,
        actor_id: int | None,
        *,
        from_json: dict[str, Any] | None = None,
        to_json: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> None:
        self._session.add(
            TaskEvent(
                organization_id=task.organization_id,
                task_id=task.id,
                event_type=event_type,
                actor_user_id=actor_id,
                from_json=from_json,
                to_json=to_json,
                note=note,
            )
        )

    async def _project(self, task: Task, event_type: str, *, note: str | None = None) -> None:
        """Project a task lifecycle event onto the contact activity timeline (Doc 14 §5.3).

        Routed through the frozen :class:`ContactEventService` rather than constructing the row
        here: that is the platform's single writer for the partitioned ``contact_events`` table and
        the place referential integrity to ``contacts`` is enforced (the table carries no FK). The
        append shares this service's transaction, preserving the single-transaction invariant.
        """
        payload: dict[str, Any] = {
            "title": task.title,
            "task_type": task.task_type,
            "priority": task.priority,
            "status": task.status,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        }
        if note:
            payload["note"] = note
        await self._timeline.record(
            organization_id=task.organization_id,
            contact_id=task.contact_id,
            event_type=event_type,
            ref_type=REF_TYPE_TASK,
            ref_id=task.id,
            payload=payload,
        )

    async def _audit_task(
        self,
        task: Task,
        action: str,
        *,
        actor_id: int | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await self._audit.record(
            action,
            actor_user_id=actor_id,
            organization_id=task.organization_id,
            entity_type="task",
            entity_id=task.id,
            before=before,
            after=after,
        )

    def _bump(self, task: Task, actor_id: int) -> None:
        task.updated_by = actor_id
        task.row_version = (task.row_version or 0) + 1

    def _check_version(self, task: Task, expected: int | None) -> None:
        if expected is not None and expected != task.row_version:
            raise VersionConflictError(
                "This task was changed by someone else; reload and try again."
            )

    @staticmethod
    def _snapshot(task: Task) -> dict[str, Any]:
        return {
            "title": task.title,
            "task_type": task.task_type,
            "priority": task.priority,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "due_notified_at": (task.due_notified_at.isoformat() if task.due_notified_at else None),
        }

    @staticmethod
    def _validate_enums(
        types: builtins.list[str] | None, priorities: builtins.list[str] | None
    ) -> None:
        for t in types or []:
            if t not in TASK_TYPES:
                raise BadRequestError(f"Invalid task_type {t!r}.")
        for p in priorities or []:
            if p not in TASK_PRIORITIES:
                raise BadRequestError(f"Invalid priority {p!r}.")

    @staticmethod
    def _parse_sort(sort: str, view: str) -> tuple[str, bool]:
        descending = sort.startswith("-")
        key = sort[1:] if descending else sort
        if view == _BUCKET_COMPLETED and sort == SORT_DUE_AT:
            # The completed bucket defaults to most-recently-completed first; an explicit
            # ``sort`` (including ``-completed_at``, Doc 14 §10) is always honoured.
            return SORT_COMPLETED_AT, True
        if key not in _VALID_SORTS:
            raise BadRequestError(
                f"sort must be one of {sorted(_VALID_SORTS)} (optionally '-'-prefixed)"
            )
        return key, descending

    def _bucket_window(
        self, view: str, tz_name: str
    ) -> tuple[builtins.list[str] | None, datetime | None, datetime | None]:
        if view == _BUCKET_ALL:
            return None, None, None
        if view == _BUCKET_COMPLETED:
            return [TASK_STATUS_COMPLETED], None, None
        start, end = _day_bounds_utc(tz_name)
        if view == _BUCKET_OVERDUE:
            return [TASK_STATUS_OPEN], None, start - timedelta(microseconds=1)
        if view == _BUCKET_UPCOMING:
            return [TASK_STATUS_OPEN], end + timedelta(microseconds=1), None
        return [TASK_STATUS_OPEN], start, end  # today

    @staticmethod
    def _encode_cursor(values: builtins.list[object], task_id: int, sort_key: str) -> str:
        if sort_key == SORT_PRIORITY:
            if len(values) != 2:
                raise BadRequestError("The priority cursor has an invalid shape.")
            rank, due = values
            if not isinstance(rank, int) or isinstance(rank, bool):
                raise BadRequestError("The priority cursor has an invalid rank.")
            if due is not None and not isinstance(due, datetime):
                raise BadRequestError("The priority cursor has an invalid due date.")
            return _encode_composite(rank, due, task_id)
        primary = values[0]
        if not isinstance(primary, datetime):  # pragma: no cover - guarded by the repository
            raise BadRequestError("This sort cannot be paginated over the current result set.")
        return encode_cursor(primary, task_id)

    @staticmethod
    def _decode_cursor(
        cursor: str | None, sort_key: str
    ) -> tuple[builtins.list[object], int] | None:
        if cursor is None:
            return None
        if sort_key == SORT_PRIORITY:
            return _decode_composite(cursor)
        ts, entity_id = decode_cursor(cursor)
        return [ts], entity_id

    # --- Resolution & view building -----------------------------------------------------------
    async def _require_task(self, organization_id: int, public_id: uuidlib.UUID) -> Task:
        task = await self._repo.get_active_by_uuid(organization_id, public_id.bytes)
        if task is None:
            raise NotFoundError("Task not found.")
        return task

    async def _require_contact(self, organization_id: int, public_id: uuidlib.UUID) -> Contact:
        stmt = select(Contact).where(
            Contact.organization_id == organization_id,
            Contact.uuid == public_id.bytes,
            Contact.deleted_at.is_(None),
        )
        contact = (await self._session.scalars(stmt)).first()
        if contact is None:
            raise NotFoundError("Contact not found.")
        return contact

    async def _require_user(self, organization_id: int, public_id: uuidlib.UUID) -> User:
        stmt = select(User).where(
            User.organization_id == organization_id,
            User.uuid == public_id.bytes,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        user = (await self._session.scalars(stmt)).first()
        if user is None:
            raise BadRequestError("Assigned agent not found or inactive.")
        return user

    async def _resolve_user_id(
        self, organization_id: int, public_id: uuidlib.UUID | None
    ) -> int | None:
        if public_id is None:
            return None
        stmt = select(User.id).where(
            User.organization_id == organization_id, User.uuid == public_id.bytes
        )
        return (await self._session.scalars(stmt)).first()

    async def _resolve_contact_id(
        self, organization_id: int, public_id: uuidlib.UUID | None
    ) -> int | None:
        if public_id is None:
            return None
        stmt = select(Contact.id).where(
            Contact.organization_id == organization_id, Contact.uuid == public_id.bytes
        )
        return (await self._session.scalars(stmt)).first()

    async def _resolve_conversation_id(
        self, organization_id: int, public_id: uuidlib.UUID | None
    ) -> int | None:
        if public_id is None:
            return None
        stmt = select(Conversation.id).where(
            Conversation.organization_id == organization_id,
            Conversation.uuid == public_id.bytes,
            Conversation.deleted_at.is_(None),
        )
        return (await self._session.scalars(stmt)).first()

    async def _public_user_id(self, user_id: int | None) -> str | None:
        """The public uuid of an internal user id — internal ids never reach a payload."""
        if user_id is None:
            return None
        users = await self._user_map({user_id})
        return users[user_id][0] if user_id in users else None

    async def _user_map(self, ids: set[int]) -> dict[int, tuple[str, str]]:
        if not ids:
            return {}
        rows = (await self._session.scalars(select(User).where(User.id.in_(ids)))).all()
        return {u.id: (u.public_id, u.full_name) for u in rows}

    # `builtins.list` for the same reason as `history` above — the `list` method shadows the
    # builtin here, and this signature is the one every read path funnels through, so leaving it
    # unresolvable made each caller's `[0]` look like an index into a non-indexable value.
    async def _build_views(self, tasks: builtins.list[Task]) -> builtins.list[TaskView]:
        if not tasks:
            return []
        contact_ids = {t.contact_id for t in tasks}
        conversation_ids = {t.conversation_id for t in tasks if t.conversation_id is not None}
        user_ids: set[int] = set()
        kyc_reference_ids = {
            t.reference_id
            for t in tasks
            if t.reference_type == "kyc_case" and t.reference_id is not None
        }
        reactivation_reference_ids = {
            t.reference_id
            for t in tasks
            if t.reference_type == "reactivation_case" and t.reference_id is not None
        }
        for t in tasks:
            user_ids.add(t.assigned_agent_id)
            if t.created_by is not None:
                user_ids.add(t.created_by)

        contacts = {
            c.id: c
            for c in (
                await self._session.scalars(select(Contact).where(Contact.id.in_(contact_ids)))
            ).all()
        }
        conversations = (
            {
                c.id: c
                for c in (
                    await self._session.scalars(
                        select(Conversation).where(Conversation.id.in_(conversation_ids))
                    )
                ).all()
            }
            if conversation_ids
            else {}
        )
        users = await self._user_map(user_ids)
        kyc_references = (
            {
                row.id: row.public_id
                for row in (
                    await self._session.scalars(
                        select(KycCase).where(KycCase.id.in_(kyc_reference_ids))
                    )
                ).all()
            }
            if kyc_reference_ids
            else {}
        )
        reactivation_references = (
            {
                row.id: row.public_id
                for row in (
                    await self._session.scalars(
                        select(ReactivationCase).where(
                            ReactivationCase.id.in_(reactivation_reference_ids)
                        )
                    )
                ).all()
            }
            if reactivation_reference_ids
            else {}
        )

        views: list[TaskView] = []
        for t in tasks:
            contact = contacts.get(t.contact_id)
            contact_name = None
            contact_public = ""
            if contact is not None:
                contact_public = contact.public_id
                contact_name = contact.full_name or contact.profile_name
            conversation_public = None
            if t.conversation_id is not None and t.conversation_id in conversations:
                conversation_public = conversations[t.conversation_id].public_id
            agent_public, agent_name = users.get(t.assigned_agent_id, ("", None))
            creator_public, creator_name = (None, None)
            if t.created_by is not None and t.created_by in users:
                creator_public, creator_name = users[t.created_by]
            views.append(
                TaskView(
                    public_id=t.public_id,
                    contact_id=contact_public,
                    contact_name=contact_name,
                    conversation_id=conversation_public,
                    reference_type=t.reference_type,
                    reference_id=(
                        (
                            kyc_references.get(t.reference_id)
                            if t.reference_type == "kyc_case"
                            else reactivation_references.get(t.reference_id)
                        )
                        if t.reference_id is not None
                        else None
                    ),
                    title=t.title,
                    task_type=t.task_type,
                    status=t.status,
                    priority=t.priority,
                    due_at=t.due_at,
                    has_time=t.has_time,
                    reminder_at=t.reminder_at,
                    due_notified_at=t.due_notified_at,
                    description=t.description,
                    assigned_agent_id=agent_public,
                    assigned_agent_name=agent_name,
                    created_by=creator_public,
                    created_by_name=creator_name,
                    completion_notes=t.completion_notes,
                    completed_at=t.completed_at,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                    row_version=t.row_version,
                )
            )
        return views
