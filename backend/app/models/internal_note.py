"""Internal note model (Doc 03 §9.5) — Shared Inbox collaboration (Doc 04 §18.1).

A staff-only annotation on a conversation: what one agent wants the next to know, never sent to the
customer. It hangs off ``conversations`` and is authored by a user — the two foreign keys are the
whole model.

Soft-deleted (``deleted_at``), because a note is a record of what a colleague said and a removed one
should stay auditable rather than vanish; the list read filters deleted rows out.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id


class InternalNote(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A private note on a conversation (Doc 03 §9.5)."""

    __tablename__ = "internal_notes"
    __table_args__ = (
        # The list read: a conversation's notes, oldest→newest (Doc 03 §9.5).
        Index("ix_note_conversation", "conversation_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    conversation_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("conversations.id", name="fk_note_conversation", ondelete="CASCADE"),
        nullable=False,
    )
    #: RESTRICT, not SET NULL: a note without an author is unattributable, and attribution is the
    #: point of a shared-inbox note (Doc 03 §9.5).
    author_user_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_note_author", ondelete="RESTRICT"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<InternalNote id={self.id} conversation={self.conversation_id}>"
