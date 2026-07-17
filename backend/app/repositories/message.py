"""Message ledger repositories (Doc 03 §9.2/§9.3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select

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

    async def list_for_conversation(
        self,
        conversation_pk: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[Message], bool]:
        """A keyset page of a thread's messages, newest first (Doc 04 §18.1).

        Keyed on ``(created_at, id)`` — the ``ix_msg_conversation`` order and the partition key, so
        the scan stays inside recent partitions of the 10M+ ledger rather than offset-paging it.
        """
        clauses = [Message.conversation_id == conversation_pk]
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                or_(
                    Message.created_at < c_created,
                    and_(Message.created_at == c_created, Message.id < c_id),
                )
            )
        stmt = (
            select(Message)
            .where(*clauses)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

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
