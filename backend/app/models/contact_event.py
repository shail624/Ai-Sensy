"""Contact activity-timeline model (Doc 03 §6.5) — FR-CON-14.

Append-only, high-volume event stream feeding the contact timeline. Deliberately has **no
database foreign key** (the table is range-partitioned on MySQL); referential integrity is
enforced in the service layer. On MySQL the physical table uses a composite ``(id, created_at)``
primary key plus monthly RANGE partitioning (applied in the migration); the ORM maps the
surrogate ``id`` as the identity key.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

# Canonical event types recorded by this module (Doc 03 §6.5 examples).
EVENT_CONTACT_CREATED = "contact_created"
EVENT_CONTACT_UPDATED = "contact_updated"
EVENT_CONTACT_MERGED = "contact_merged"
EVENT_OPTIN_CHANGED = "optin_changed"
EVENT_TAG_ADDED = "tag_added"
EVENT_TAG_REMOVED = "tag_removed"

# Task lifecycle projected onto the contact timeline (Doc 14 §5.3). Additive string constants
# only — the partitioned table is reused as-is with ``ref_type="task"``, ``ref_id=task.id`` and a
# compact ``payload_json``; no column, index, or DDL change.
EVENT_TASK_CREATED = "task_created"
EVENT_TASK_ASSIGNED = "task_assigned"
EVENT_TASK_RESCHEDULED = "task_rescheduled"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_CANCELLED = "task_cancelled"

#: The ``ref_type`` used for all task timeline projections.
REF_TYPE_TASK = "task"


class ContactEvent(Base):
    """One immutable contact-timeline event (Doc 03 §6.5)."""

    __tablename__ = "contact_events"
    __table_args__ = (
        Index("ix_cevents_contact", "contact_id", "created_at"),
        Index("ix_cevents_org_type", "organization_id", "event_type", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = mapped_column(big_id(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ContactEvent id={self.id} type={self.event_type!r}>"
