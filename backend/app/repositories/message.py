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

    async def get_by_provider_message_id(
        self, provider_message_id: str, *, phone_number_id: int
    ) -> Message | None:
        """Lookup by the channel's message id **within one endpoint** (ADR-0020 §"Message, media
        and retry decision": "Provider message identity is scoped by connection/endpoint").

        Serves both webhook paths: the inbound idempotency key (Doc 06 §2.3) and the row a status
        callback advances.

        ``phone_number_id`` is keyword-only and **required** on purpose. A provider message id is
        unique only inside the endpoint that issued it — Meta's ``wamid`` happens to be globally
        unique, but a QR/multi-device provider's id is session-scoped and may legitimately repeat
        across endpoints (ADR-0020, Doc 33 §6.1 "Message identity"). Making the scope impossible to
        omit is what prevents a second provider from resolving — or overwriting — another
        endpoint's or another tenant's message. There is deliberately no unscoped variant.

        ``phone_numbers.organization_id`` is ``NOT NULL``, so the endpoint transitively pins the
        tenant; no separate organization filter is needed to make this tenant-safe.

        Backed by ``ix_msg_endpoint_wamid (phone_number_id, wamid)`` (migration
        ``0042_scope_provider_message_identity``). A unique index cannot express this rule: MySQL
        requires every unique key on a partitioned table to contain the partition columns, and
        ``messages`` is ``PARTITION BY RANGE COLUMNS(created_at)`` — so uniqueness is enforced by
        this scoped read plus the persist-first ingestion path, not by a constraint.
        """
        stmt = select(Message).where(
            Message.phone_number_id == phone_number_id,
            Message.wamid == provider_message_id,
        )
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
