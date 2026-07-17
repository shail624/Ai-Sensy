"""Internal note repository (Doc 03 §9.5)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.internal_note import InternalNote
from app.repositories.base import BaseRepository


class InternalNoteRepository(BaseRepository[InternalNote]):
    model = InternalNote

    async def list_for_conversation(self, conversation_pk: int) -> list[InternalNote]:
        """A conversation's active notes, oldest first — the ``ix_note_conversation`` order.

        Soft-deleted notes are excluded: a removed note is retained for audit, not for reading.
        """
        stmt = (
            select(InternalNote)
            .where(
                InternalNote.conversation_id == conversation_pk,
                InternalNote.deleted_at.is_(None),
            )
            .order_by(InternalNote.created_at, InternalNote.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_for_conversation(
        self, conversation_pk: int, public_id: bytes
    ) -> InternalNote | None:
        """One active note by uuid, constrained to the conversation it belongs to.

        The conversation constraint is what makes a note-uuid from another thread a 404 rather than
        a cross-thread delete.
        """
        stmt = select(InternalNote).where(
            InternalNote.conversation_id == conversation_pk,
            InternalNote.uuid == public_id,
            InternalNote.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()
