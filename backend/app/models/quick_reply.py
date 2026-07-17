"""Quick-reply model (Doc 03 §9.5) — Shared Inbox canned messages (FR-INB-04).

A reusable, ``/shortcut``-triggered canned message an agent inserts into the composer. Each reply is
either **personal** (``owner_user_id`` set — visible only to that user) or **shared**
(``owner_user_id`` NULL — visible to the whole organization), per the frozen ``owner_user_id``
semantics.

Soft-deleted (``deleted_at``) like the other §9.5 table (internal notes). The frozen schema carries
no ``row_version`` and no foreign key on ``owner_user_id``/``created_by`` — only ``fk_qr_org`` — so
this model declares exactly those columns and nothing more.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, int_id

#: ``shortcut`` is VARCHAR(60); ``title`` VARCHAR(120) (Doc 03 §9.5).
SHORTCUT_LENGTH = 60
TITLE_LENGTH = 120


class QuickReply(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A personal or shared canned reply (Doc 03 §9.5)."""

    __tablename__ = "quick_replies"
    __table_args__ = (
        # The list read filters by (org, owner) — the caller's own personal replies plus the org's
        # shared ones (Doc 03 §9.5; Doc 04 §18.2).
        Index("ix_qr_org_owner", "organization_id", "owner_user_id"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_qr_org", ondelete="CASCADE"),
        nullable=False,
    )
    #: NULL = shared (org-wide); else the owning user's id — a personal reply (FR-INB-04). No FK in
    #: the frozen schema: a reply outlives the user row it names.
    owner_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    shortcut: Mapped[str] = mapped_column(String(SHORTCUT_LENGTH), nullable=False)
    title: Mapped[str] = mapped_column(String(TITLE_LENGTH), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    #: Denormalized use counter (Doc 03 §9.5). Surfaced read-only; the *increment* is a send-path
    #: concern and is out of this milestone.
    usage_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    #: The creating user (audit trail); no FK in the frozen schema.
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    @property
    def is_shared(self) -> bool:
        """A shared reply has no owner (Doc 03 §9.5)."""
        return self.owner_user_id is None

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<QuickReply id={self.id} shortcut={self.shortcut!r} shared={self.is_shared}>"
