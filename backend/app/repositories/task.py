"""Task repository (Doc 14 §5, §7) — queries only, no business rules.

The work-queue reads (bucketed by assignee/status/due), the org-scoped fetch by uuid, the
Customer-Profile and conversation reads, the bulk id resolver, and the per-bucket counts behind
``/tasks/stats``. Keyset pagination reuses the frozen envelope; for the ``priority`` sort (a
non-datetime key) a small composite keyset is applied here — ``app/api/pagination.py`` is not
modified.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.sql.elements import ColumnElement, SQLColumnExpression

from app.models.task import (
    TASK_PRIORITIES,
    TASK_PRIORITY_CRITICAL,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_MEDIUM,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_OPEN,
    Task,
)
from app.models.task_event import TaskEvent
from app.repositories.base import BaseRepository

# Severity order for the ``priority`` sort (critical first).
_PRIORITY_RANK: dict[str, int] = {
    TASK_PRIORITY_LOW: 0,
    TASK_PRIORITY_MEDIUM: 1,
    TASK_PRIORITY_HIGH: 2,
    TASK_PRIORITY_CRITICAL: 3,
}

# Supported sort keys (Doc 14 §7.2). ``-`` prefix = descending.
SORT_DUE_AT = "due_at"
SORT_CREATED_AT = "created_at"
SORT_PRIORITY = "priority"
SORT_COMPLETED_AT = "completed_at"
_DATETIME_SORTS = {SORT_DUE_AT, SORT_CREATED_AT, SORT_COMPLETED_AT}


def _priority_rank_expr() -> ColumnElement[int]:
    """A CASE mapping ``priority`` → severity rank, for ordering (critical highest)."""
    return case(_PRIORITY_RANK, value=Task.priority, else_=0)


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> Task | None:
        """One active task by uuid within the org (a foreign uuid is a 404)."""
        stmt = select(Task).where(
            Task.organization_id == organization_id,
            Task.uuid == public_id,
            Task.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def resolve_ids(
        self, organization_id: int, public_ids: list[uuidlib.UUID]
    ) -> list[Task]:
        """Active tasks for a set of uuids (bulk actions, Doc 14 §7.1)."""
        if not public_ids:
            return []
        raw = [pid.bytes for pid in public_ids]
        stmt = select(Task).where(
            Task.organization_id == organization_id,
            Task.uuid.in_(raw),
            Task.deleted_at.is_(None),
        )
        return list((await self.session.scalars(stmt)).all())

    def _apply_filters(
        self,
        stmt: Select[tuple[Task]],
        organization_id: int,
        *,
        assignee_id: int | None,
        assigned_by_id: int | None,
        contact_id: int | None,
        conversation_id: int | None,
        statuses: list[str] | None,
        types: list[str] | None,
        priorities: list[str] | None,
        due_from: datetime | None,
        due_to: datetime | None,
        q: str | None,
    ) -> Select[tuple[Task]]:
        clauses: list[ColumnElement[bool]] = [
            Task.organization_id == organization_id,
            Task.deleted_at.is_(None),
        ]
        if assignee_id is not None:
            clauses.append(Task.assigned_agent_id == assignee_id)
        if assigned_by_id is not None:
            clauses.append(Task.created_by == assigned_by_id)
        if contact_id is not None:
            clauses.append(Task.contact_id == contact_id)
        if conversation_id is not None:
            clauses.append(Task.conversation_id == conversation_id)
        if statuses:
            clauses.append(Task.status.in_(statuses))
        if types:
            clauses.append(Task.task_type.in_(types))
        if priorities:
            clauses.append(Task.priority.in_(priorities))
        if due_from is not None:
            clauses.append(Task.due_at >= due_from)
        if due_to is not None:
            clauses.append(Task.due_at <= due_to)
        if q:
            like = f"%{q}%"
            clauses.append(or_(Task.title.like(like), Task.description.like(like)))
        return stmt.where(*clauses)

    async def list_page(
        self,
        organization_id: int,
        *,
        assignee_id: int | None = None,
        assigned_by_id: int | None = None,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        statuses: list[str] | None = None,
        types: list[str] | None = None,
        priorities: list[str] | None = None,
        due_from: datetime | None = None,
        due_to: datetime | None = None,
        q: str | None = None,
        sort: str = SORT_DUE_AT,
        descending: bool = False,
        cursor: tuple[list[object], int] | None = None,
        limit: int,
    ) -> tuple[list[Task], bool]:
        """A keyset page of tasks (Doc 14 §7). Returns ``(rows, has_more)``.

        ``cursor`` is the decoded ``(primary_values, id)`` of the last row of the previous page,
        where ``primary_values`` matches the active sort's key columns (one datetime for the
        datetime sorts; ``[rank, due_at]`` for the ``priority`` sort).
        """
        stmt = self._apply_filters(
            select(Task),
            organization_id,
            assignee_id=assignee_id,
            assigned_by_id=assigned_by_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            statuses=statuses,
            types=types,
            priorities=priorities,
            due_from=due_from,
            due_to=due_to,
            q=q,
        )

        # Ordered key columns (id is always the final tiebreak, ascending).
        if sort == SORT_PRIORITY:
            rank = _priority_rank_expr()
            keys: list[tuple[SQLColumnExpression[Any], bool]] = [
                (rank, descending),
                (Task.due_at, False),
            ]
        elif sort == SORT_CREATED_AT:
            keys = [(Task.created_at, descending)]
        elif sort == SORT_COMPLETED_AT:
            # A task that was never completed has no position on a completion-ordered list, and a
            # NULL key cannot participate in a keyset comparison — exclude it rather than emit an
            # unstable page.
            stmt = stmt.where(Task.completed_at.is_not(None))
            keys = [(Task.completed_at, descending)]
        else:  # SORT_DUE_AT (default)
            keys = [(Task.due_at, descending)]

        if cursor is not None:
            stmt = stmt.where(self._keyset_after(keys, cursor))

        order_by = [col.desc() if desc else col.asc() for col, desc in keys]
        order_by.append(Task.id.asc())
        stmt = stmt.order_by(*order_by).limit(limit + 1)

        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    @staticmethod
    def _keyset_after(
        keys: list[tuple[SQLColumnExpression[Any], bool]], cursor: tuple[list[object], int]
    ) -> ColumnElement[bool]:
        """Lexicographic keyset predicate: rows strictly after ``cursor`` in ``keys, id`` order."""
        values, last_id = cursor
        # Build from the innermost tiebreak outward: (id > last_id) wrapped by each key.
        predicate: ColumnElement[bool] = Task.id > last_id
        for (col, descending), value in zip(reversed(keys), reversed(values), strict=True):
            strict = col < value if descending else col > value
            predicate = or_(strict, and_(col == value, predicate))
        return predicate

    @staticmethod
    def cursor_values(task: Task, sort: str) -> list[object]:
        """The key values of ``task`` for the active sort (encoded into the next cursor)."""
        if sort == SORT_PRIORITY:
            return [_PRIORITY_RANK.get(task.priority, 0), task.due_at]
        if sort == SORT_CREATED_AT:
            return [task.created_at]
        if sort == SORT_COMPLETED_AT:
            return [task.completed_at]
        return [task.due_at]

    async def list_events(self, task_id: int) -> list[TaskEvent]:
        """A task's immutable history, oldest→newest (Doc 14 §5.2)."""
        stmt = (
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.created_at.asc(), TaskEvent.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def bucket_counts(
        self, organization_id: int, assignee_id: int, *, today_start: datetime, today_end: datetime
    ) -> dict[str, int]:
        """Work-queue counts for one agent (Doc 14 §7.3, §11) → overdue/due_today/upcoming/completed_today."""
        open_base = [
            Task.organization_id == organization_id,
            Task.assigned_agent_id == assignee_id,
            Task.deleted_at.is_(None),
            Task.status == TASK_STATUS_OPEN,
        ]
        overdue = select(func.count()).where(*open_base, Task.due_at < today_start)
        due_today = select(func.count()).where(
            *open_base, Task.due_at >= today_start, Task.due_at <= today_end
        )
        upcoming = select(func.count()).where(*open_base, Task.due_at > today_end)
        completed_today = select(func.count()).where(
            Task.organization_id == organization_id,
            Task.assigned_agent_id == assignee_id,
            Task.deleted_at.is_(None),
            Task.status == TASK_STATUS_COMPLETED,
            Task.completed_at >= today_start,
            Task.completed_at <= today_end,
        )
        return {
            "overdue": int((await self.session.scalar(overdue)) or 0),
            "due_today": int((await self.session.scalar(due_today)) or 0),
            "upcoming": int((await self.session.scalar(upcoming)) or 0),
            "completed_today": int((await self.session.scalar(completed_today)) or 0),
        }

    async def due_for_notification(self, *, now: datetime, limit: int) -> list[Task]:
        """Claim candidates are rechecked by the service; ``due_notified_at`` makes scans converge."""
        stmt = (
            select(Task)
            .where(
                Task.reference_type == "reactivation_case",
                Task.status == TASK_STATUS_OPEN,
                Task.due_at <= now,
                Task.due_notified_at.is_(None),
                Task.deleted_at.is_(None),
            )
            .order_by(Task.due_at, Task.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(stmt)).all())


__all__ = ["TaskRepository", "TASK_PRIORITIES", "SORT_DUE_AT", "SORT_CREATED_AT", "SORT_PRIORITY"]
