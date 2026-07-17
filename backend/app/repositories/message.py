"""Message ledger repositories (Doc 03 §9.2/§9.3)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.message import Message, MessageStatusHistory
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def get_for_org(self, organization_id: int, public_id: bytes) -> Message | None:
        """Fetch by public id, scoped to the tenant. Messages are never soft-deleted (Doc 03 §9.2)."""
        stmt = select(Message).where(
            Message.organization_id == organization_id, Message.uuid == public_id
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_wamid(self, wamid: str) -> Message | None:
        """Lookup by the channel's message id — ``ix_msg_wamid`` (Doc 03 §9.2).

        Serves both webhook paths: the inbound idempotency key (Doc 06 §2.3) and the row a status
        callback advances.
        """
        stmt = select(Message).where(Message.wamid == wamid)
        return (await self.session.scalars(stmt)).first()


class MessageStatusHistoryRepository(BaseRepository[MessageStatusHistory]):
    model = MessageStatusHistory

    async def list_for_message(self, message_pk: int) -> list[MessageStatusHistory]:
        stmt = (
            select(MessageStatusHistory)
            .where(MessageStatusHistory.message_id == message_pk)
            .order_by(MessageStatusHistory.id)
        )
        return list((await self.session.scalars(stmt)).all())
