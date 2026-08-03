"""Tenant-scoped, per-recipient notification projection for existing domain events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

NOTIFICATION_FOLLOW_UP_DUE = "follow_up_due"
NOTIFICATION_RELEASE_DATE_DUE = "release_date_due"
NOTIFICATION_CASE_ASSIGNED = "case_assigned"
NOTIFICATION_CASE_STATUS_CHANGED = "case_status_changed"
NOTIFICATION_TYPES = (
    NOTIFICATION_FOLLOW_UP_DUE,
    NOTIFICATION_RELEASE_DATE_DUE,
    NOTIFICATION_CASE_ASSIGNED,
    NOTIFICATION_CASE_STATUS_CHANGED,
)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Notification(IntPKMixin, UUIDMixin, TimestampMixin, Base):
    """A durable delivery projection; source aggregates remain the workflow authorities."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("organization_id", "dedup_key", name="uq_notifications_dedup"),
        Index(
            "ix_notifications_recipient_read_created",
            "organization_id",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
        Index(
            "ix_notifications_recipient_due_resolved",
            "organization_id",
            "recipient_user_id",
            "due_at",
            "resolved_at",
        ),
        CheckConstraint(
            _in_clause("notification_type", NOTIFICATION_TYPES), name="ck_notification_type"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    reactivation_case_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(190), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
