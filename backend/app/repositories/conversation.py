"""Conversation repository (Doc 03 §9.1)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def get_for_number_contact(
        self, phone_number_pk: int, contact_pk: int
    ) -> Conversation | None:
        """The thread for a (number, contact) pair — the ``uq_conv_number_contact`` key.

        Soft-deleted rows still hold the unique key, so this deliberately ignores ``deleted_at``:
        an inbound message on an archived thread revives it rather than colliding with it.
        """
        stmt = select(Conversation).where(
            Conversation.phone_number_id == phone_number_pk,
            Conversation.contact_id == contact_pk,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> Conversation | None:
        """An active thread by its public id, scoped to the caller's org (Doc 04 §18.1).

        Org-scoped so a valid uuid from another tenant reads as a 404, not another org's thread.
        """
        stmt = select(Conversation).where(
            Conversation.organization_id == organization_id,
            Conversation.uuid == public_id,
            Conversation.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()
