"""Task model (Doc 14 §4–§5) — CRM Follow-up Engine.

A **task** is a typed, scheduled, assignable follow-up action anchored to a **contact**
(required) and optionally to a **conversation** (which carries lead/pipeline context via the
frozen ``conversation_lead``, Doc 07 §19.2). It is owned by an **assigned agent** and recorded
against its **creator** ("assigned by"). This is the multi-task system the single per-conversation
``reminder_at``/``follow_up_date`` fields could not provide (Doc 13 GAP-01).

Additive per Doc 14: reuses the frozen identity/timestamp/soft-delete/audit/version mixins and the
cross-dialect column types verbatim; introduces no new architectural pattern. Enumerations are
``VARCHAR`` + canonical constants + ``CHECK`` (matching ``contact_event.EVENT_*`` / ``lead``),
never native DB enums.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, uuid_binary

# --- Value objects (Doc 14 §4.2) --------------------------------------------------------------
TASK_TYPE_CALL = "call"
TASK_TYPE_WHATSAPP = "whatsapp"
TASK_TYPE_COLLECT_DOCUMENTS = "collect_documents"
TASK_TYPE_VERIFICATION = "verification"
TASK_TYPE_REMINDER = "reminder"
TASK_TYPE_MEETING = "meeting"
TASK_TYPE_CUSTOM = "custom"
TASK_TYPES: tuple[str, ...] = (
    TASK_TYPE_CALL,
    TASK_TYPE_WHATSAPP,
    TASK_TYPE_COLLECT_DOCUMENTS,
    TASK_TYPE_VERIFICATION,
    TASK_TYPE_REMINDER,
    TASK_TYPE_MEETING,
    TASK_TYPE_CUSTOM,
)

TASK_STATUS_OPEN = "open"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_SKIPPED = "skipped"
TASK_STATUS_CANCELLED = "cancelled"
TASK_STATUSES: tuple[str, ...] = (
    TASK_STATUS_OPEN,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_SKIPPED,
    TASK_STATUS_CANCELLED,
)
#: Terminal states — reachable from ``open`` and returnable to it via reopen (Doc 14 §4.4).
TASK_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {TASK_STATUS_COMPLETED, TASK_STATUS_SKIPPED, TASK_STATUS_CANCELLED}
)

TASK_PRIORITY_LOW = "low"
TASK_PRIORITY_MEDIUM = "medium"
TASK_PRIORITY_HIGH = "high"
TASK_PRIORITY_CRITICAL = "critical"
TASK_PRIORITIES: tuple[str, ...] = (
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_MEDIUM,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_CRITICAL,
)

#: Column lengths (mirrored by the schemas, Doc 14 §8).
TITLE_LENGTH = 160
TYPE_LENGTH = 24
STATUS_LENGTH = 16
PRIORITY_LENGTH = 12
#: TEXT bodies are capped in the schema layer, as internal notes are, to bound request size.
BODY_MAX = 4096


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    rendered = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({rendered})"


class Task(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A CRM follow-up task (Doc 14 §5.1)."""

    __tablename__ = "tasks"
    __table_args__ = (
        # The per-agent work queue: bucket by (assignee, status) ordered by due (Doc 14 §5.1/§11).
        Index(
            "ix_tasks_organization_id_assigned_agent_id_status_due_at",
            "organization_id",
            "assigned_agent_id",
            "status",
            "due_at",
        ),
        # Team-wide Today/Overdue/Upcoming.
        Index("ix_tasks_organization_id_status_due_at", "organization_id", "status", "due_at"),
        # Customer Profile tasks (Doc 14 §9).
        Index(
            "ix_tasks_organization_id_contact_id_created_at",
            "organization_id",
            "contact_id",
            "created_at",
        ),
        # Conversation / lead tasks.
        Index("ix_tasks_organization_id_conversation_id", "organization_id", "conversation_id"),
        Index(
            "ix_tasks_organization_reference_status_due",
            "organization_id",
            "reference_type",
            "reference_id",
            "status",
            "due_at",
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_tasks_idempotency"),
        CheckConstraint(
            "(reference_type IS NULL AND reference_id IS NULL) OR "
            "(reference_type = 'kyc_case' AND reference_id IS NOT NULL)",
            name="ck_tasks_reference_pair",
        ),
        # "Assigned by me" (Doc 14 §10).
        Index(
            "ix_tasks_organization_id_created_by_status",
            "organization_id",
            "created_by",
            "status",
        ),
        CheckConstraint(_in_clause("task_type", TASK_TYPES), name="ck_tasks_task_type"),
        CheckConstraint(_in_clause("status", TASK_STATUSES), name="ck_tasks_status"),
        CheckConstraint(_in_clause("priority", TASK_PRIORITIES), name="ck_tasks_priority"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_tasks_organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    #: The customer the task is about — required, RESTRICT so the subject stays attributable.
    contact_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("contacts.id", name="fk_tasks_contact_id", ondelete="RESTRICT"),
        nullable=False,
    )
    #: Optional link to the lead thread; SET NULL so deleting a conversation detaches, not deletes.
    conversation_id: Mapped[int | None] = mapped_column(
        big_id(),
        ForeignKey("conversations.id", name="fk_tasks_conversation_id", ondelete="SET NULL"),
        nullable=True,
    )
    #: Optional governed-domain anchor. The task remains the appointment lifecycle authority.
    reference_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    idempotency_key: Mapped[bytes | None] = mapped_column(uuid_binary(), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: The owner/doer — required, RESTRICT (a task must always have an assignee).
    assigned_agent_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_tasks_assigned_agent_id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(TITLE_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(TYPE_LENGTH), nullable=False)
    status: Mapped[str] = mapped_column(
        String(STATUS_LENGTH), nullable=False, default=TASK_STATUS_OPEN
    )
    priority: Mapped[str] = mapped_column(
        String(PRIORITY_LENGTH), nullable=False, default=TASK_PRIORITY_MEDIUM
    )
    #: Effective due moment (UTC) — drives the buckets (Doc 14 §7.3).
    due_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    #: ``false`` = date-only ("Due Date" with no "Due Time" → all-day in the UI).
    has_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reminder_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    #: User who completed the task; no FK (mirrors ``quick_replies.created_by`` — outlives the row).
    completed_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    @property
    def is_open(self) -> bool:
        return self.status == TASK_STATUS_OPEN

    @property
    def is_terminal(self) -> bool:
        return self.status in TASK_TERMINAL_STATUSES

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Task id={self.id} type={self.task_type!r} status={self.status!r}>"
