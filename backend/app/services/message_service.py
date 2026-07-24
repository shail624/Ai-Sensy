"""Message ledger service (Doc 03 §9.2/§9.3; Doc 06 §11.3/§11.4) — FR-WA-06/07.

The two halves of "receive": a customer's message becomes a ledger row on a thread
(:meth:`MessageService.apply_inbound`), and a delivery callback advances the row it refers to
(:meth:`MessageService.apply_status`).

**Ordering without global ordering (Doc 06 §11.3, decision D16).** Webhooks arrive out of order and
more than once. Rather than serialize the firehose, both paths are written so that order cannot
corrupt state: an inbound message is keyed on its `wamid`, and a status only ever moves *forward*,
so a late `delivered` landing after `read` is a no-op instead of a regression. A conversation lock
(Doc 06 §9) is a latency optimization on top of this, never the thing that makes it correct — §9.4
is explicit that the data layer is the ultimate guard.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, get_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD
from app.channels.models import InboundMessage, StatusUpdate
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.message import (
    DIRECTION_INBOUND,
    MSG_ACCEPTED,
    STATUS_TIMESTAMP_COLUMN,
    Message,
    MessageStatusHistory,
    advances,
)
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository, MessageStatusHistoryRepository
from app.repositories.waba import PhoneNumberRepository
from app.repositories.webhook import WebhookEventRepository
from app.services.conversation_service import ConversationService
from app.services.media_ingest_service import media_reference

logger = get_logger(__name__)

# Application outcomes — returned rather than raised, because none of them is a failure.
APPLIED = "applied"
DUPLICATE = "duplicate"
#: A status that does not move the message forward (D16) — the whole point of monotonicity.
IGNORED_STALE = "ignored_stale"


class LedgerError(Exception):
    """The event cannot be applied to the ledger at all — poison, not a retry (Doc 06 §11.6)."""


class MessageNotFound(Exception):
    """A status arrived for a `wamid` the ledger does not (yet) hold.

    Retryable on purpose: the only thing that legitimately produces this is a race with the send
    that created the message, which a moment's backoff resolves (Doc 06 §11.3). If it is still
    unknown after the engine's attempts, it dead-letters and stays visible — dropping a delivery
    receipt silently would leave the ledger quietly wrong.
    """


class MessageService:
    def __init__(
        self, session: AsyncSession, *, connector_type: str = CONNECTOR_META_CLOUD
    ) -> None:
        self._session = session
        self._connector_type = connector_type
        self._messages = MessageRepository(session)
        self._history = MessageStatusHistoryRepository(session)
        self._conversation_repo = ConversationRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._events = WebhookEventRepository(session)
        self._conversations = ConversationService(session)

    def adapter(self) -> ChannelAdapter:
        return get_adapter(self._connector_type)

    # --- Reads (Doc 04 §18.2) -----------------------------------------------
    async def get_message(self, organization_id: int, public_id: uuidlib.UUID) -> Message:
        message = await self._messages.get_for_org(organization_id, public_id.bytes)
        if message is None:
            raise NotFoundError("Message not found.")
        return message

    async def status_history(self, message: Message) -> list[MessageStatusHistory]:
        return await self._history.list_for_message(message.id)

    async def conversation_public_id(self, message: Message) -> str:
        conversation = await self._conversation_repo.get_by_id(message.conversation_id)
        return conversation.public_id if conversation else ""

    # --- Inbound (Doc 06 §2.3 ``inbound.process``) --------------------------
    async def apply_inbound(self, event_pk: int) -> dict[str, Any]:
        """Turn a persisted inbound event into contact + thread + ledger row (FR-WA-06).

        Commits: this is the top of its own task, and the contact, the thread, the window and the
        message are one fact about one moment — a partial application would be worse than none.
        """
        row = await self._events.get_by_id(event_pk)
        if row is None:
            logger.warning("inbound_event_missing", extra={"event_pk": event_pk})
            return {"status": "missing", "event_pk": event_pk}
        if row.phone_number_id is None:
            raise LedgerError("inbound event is not routed to a phone number")

        number = await self._numbers.get_by_id(row.phone_number_id)
        if number is None:
            raise LedgerError(f"phone number {row.phone_number_id} no longer exists")

        message = self._to_inbound_message(row.payload_json)
        # Redelivery lands here as a second task for the same `wamid` (Doc 06 §2.3 idempotency
        # key): the thread must not gain a second copy or a second unread.
        existing = await self._messages.get_by_wamid(message.channel_message_id)
        if existing is not None:
            return {
                "status": DUPLICATE,
                "event_pk": event_pk,
                "message_id": existing.public_id,
                "message_pk": existing.id,
                # A redelivery still reports pending media: the first attempt may have stored the
                # message and died before the download was queued (Doc 07 §17.2).
                "media_pending": self._media_pending(existing),
            }

        occurred_at = message.occurred_at or utcnow()
        contact = await self._conversations.resolve_contact(
            organization_id=number.organization_id,
            wa_id=message.from_id,
            profile_name=message.profile_name,
            occurred_at=occurred_at,
        )
        conversation = await self._conversations.open_for_inbound(
            number=number, contact=contact, occurred_at=occurred_at
        )

        stored = Message(
            organization_id=number.organization_id,
            conversation_id=conversation.id,
            phone_number_id=number.id,
            contact_id=contact.id,
            direction=DIRECTION_INBOUND,
            wamid=message.channel_message_id,
            message_type=message.message_type,
            content_json=message.content,
            # An inbound message has no delivery lifecycle of ours to track: it is simply here.
            status=MSG_ACCEPTED,
            created_at=occurred_at,
        )
        await self._messages.add(stored)
        await self._conversations.record_inbound_message(
            conversation,
            preview=ConversationService.preview_of(message.message_type, message.content),
            occurred_at=occurred_at,
        )
        await self._session.commit()
        return {
            "status": APPLIED,
            "event_pk": event_pk,
            "message_id": stored.public_id,
            "message_pk": stored.id,
            "conversation_id": conversation.public_id,
            "contact_id": contact.public_id,
            # The bytes are fetched on the `media` lane, not here: an attachment must never hold
            # up the message it came with (Doc 07 §17.2/§17.4). The caller owns the dispatch.
            "media_pending": self._media_pending(stored),
        }

    @staticmethod
    def _media_pending(message: Message) -> bool:
        return message.media_asset_id is None and media_reference(message) is not None

    def _to_inbound_message(self, payload: dict[str, Any] | None) -> InboundMessage:
        try:
            return self.adapter().to_inbound_message(payload or {})
        except Exception as exc:  # noqa: BLE001 - any translation failure is the same verdict
            raise LedgerError(f"inbound payload cannot be read: {exc}") from exc

    # --- Status callbacks (Doc 06 §11.3/§11.4) ------------------------------
    async def apply_status(self, update: StatusUpdate) -> str:
        """Advance a message's delivery state (FR-WA-06/07).

        Does **not** commit: the caller settles the webhook event in the same transaction, so an
        applied status and the event that carried it can never disagree.
        """
        message = await self._messages.get_by_wamid(update.channel_message_id)
        if message is None:
            raise MessageNotFound(f"no message for wamid {update.channel_message_id!r}")

        # Append first: the log is the record of what the channel *told* us, which is true even
        # when the transition it describes is stale (Doc 03 §9.3 — append-only).
        await self._history.add(
            MessageStatusHistory(
                message_id=message.id,
                wamid=update.channel_message_id,
                status=update.status,
                error_code=update.error_code,
                error_title=update.error_title,
                error_detail=(update.error_detail or None) and update.error_detail[:512],
                recipient_id=update.recipient_id,
                occurred_at=update.occurred_at or utcnow(),
            )
        )

        if not advances(message.status, update.status):
            return IGNORED_STALE

        message.status = update.status
        if update.error_code:
            message.error_code = update.error_code[:24]
        column = STATUS_TIMESTAMP_COLUMN.get(update.status)
        if column is not None:
            setattr(message, column, update.occurred_at or utcnow())
        await self._messages.flush()
        return APPLIED

    def to_status_update(self, payload: dict[str, Any] | None) -> StatusUpdate:
        try:
            return self.adapter().to_status_update(payload or {})
        except Exception as exc:  # noqa: BLE001 - any translation failure is the same verdict
            raise LedgerError(f"status payload cannot be read: {exc}") from exc
