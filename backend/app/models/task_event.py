"""Task history model (Doc 14 §5.2) — immutable per-task audit (FR-TASK-08).

One append-only row per task lifecycle change (created, assigned, reassigned, rescheduled,
priority changed, status changed, completed, skipped, cancelled, reopened, note added). Unlike the
partitioned ``contact_events`` timeline (Doc 03 §6.5), this table is task-scoped and moderate in
volume, so it keeps a real foreign key to ``tasks`` (CASCADE). Immutable: created-only, no
``updated_at``, no soft-delete.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

# Canonical task-history event types (Doc 14 §5.2).
TASK_EVENT_CREATED = "created"
TASK_EVENT_ASSIGNED = "assigned"
TASK_EVENT_REASSIGNED = "reassigned"
TASK_EVENT_RESCHEDULED = "rescheduled"
TASK_EVENT_PRIORITY_CHANGED = "priority_changed"
TASK_EVENT_STATUS_CHANGED = "status_changed"
TASK_EVENT_COMPLETED = "completed"
TASK_EVENT_SKIPPED = "skipped"
TASK_EVENT_CANCELLED = "cancelled"
TASK_EVENT_REOPENED = "reopened"
TASK_EVENT_NOTE_ADDED = "note_added"

EVENT_TYPE_LENGTH = 32


class TaskEvent(IntPKMixin, Base):
    """One immutable entry in a task's history (Doc 14 §5.2)."""

    __tablename__ = "task_events"
    __table_args__ = (
        # The history read: a task's events, oldest→newest (Doc 14 §5.2).
        Index("ix_task_events_task_id_created_at", "task_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    task_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("tasks.id", name="fk_task_events_task_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(EVENT_TYPE_LENGTH), nullable=False)
    #: Who acted; nullable for system-generated events.
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: Prior / new values of the changed field(s), for a readable diff.
    from_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    to_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<TaskEvent id={self.id} task={self.task_id} type={self.event_type!r}>"
