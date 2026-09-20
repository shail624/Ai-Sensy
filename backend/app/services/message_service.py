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
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, get_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD, CONNECTOR_WAHA
from app.channels.models import InboundMessage, StatusUpdate
from app.channels.waha.identity import (
    normalize_direct_jid,
    optional_direct_jid,
    phone_wa_id,
    route_identity_namespace,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.contact import OPT_IN_OPTED_OUT, Contact
from app.models.conversation import Conversation
from app.models.message import (
    DIRECTION_INBOUND,
    MSG_ACCEPTED,
    STATUS_TIMESTAMP_COLUMN,
    Message,
    MessageStatusHistory,
    advances,
)
from app.repositories.campaign import (
    CampaignRecipientRepository,
    CampaignRepository,
)
from app.repositories.channel_connection import (
    ChannelConnectionRepository,
    ChannelEndpointRepository,
)
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository, MessageStatusHistoryRepository
from app.repositories.waba import PhoneNumberRepository
from app.repositories.webhook import WebhookEventRepository
from app.schemas.settings import InboxOperationsResponse
from app.services.business_event_service import BusinessEventService
from app.services.conversation_service import ConversationService
from app.services.inbox_operations_service import InboxOperationsService
from app.services.media_ingest_service import media_reference
from app.services.send_service import SendService

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
        self._endpoints = ChannelEndpointRepository(session)
        self._connections = ChannelConnectionRepository(session)
        self._contacts = ContactRepository(session)
        self._events = WebhookEventRepository(session)
        self._conversations = ConversationService(session)
        self._recipients = CampaignRecipientRepository(session)
        self._campaigns = CampaignRepository(session)
        self._operations = InboxOperationsService(session)
        self._business_events = BusinessEventService(session)
        self._send = SendService(session)

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
    async def _note_campaign_reply(self, contact: Contact, occurred_at: datetime) -> None:
        """Mark that this contact answered the campaign that last reached them.

        ``campaigns.replied_count`` has been on the model, in the API and on the campaign screen
        since the schema was written, and nothing ever wrote it -- so every campaign reported
        "Replies: 0 (0% of delivered)" for its whole life, on the one number a reactivation
        campaign exists to produce.

        Recorded here rather than counted later because the alternative is a self-join across the
        message ledger on every progress refresh, and that refresh runs after every send. One
        indexed lookup per *inbound* message is the cheaper side of that trade by a wide margin:
        inbound volume is a fraction of outbound, and ``ix_crecip_contact`` already exists.

        Deliberately not fatal. A reply is recorded in the ledger whatever happens here, and losing
        an inbound customer message because a counter could not be updated would be the wrong way
        round.
        """
        try:
            campaign_id = await self._recipients.mark_replied(contact.id, occurred_at)
            if campaign_id is not None:
                await self._campaigns.refresh_replied(campaign_id)
        except Exception:  # noqa: BLE001 - a counter must never cost an inbound message
            logger.warning(
                "campaign_reply_not_recorded", extra={"contact": contact.id}, exc_info=True
            )

    async def apply_inbound(self, event_pk: int) -> dict[str, Any]:
        """Turn a persisted inbound event into contact + thread + ledger row (FR-WA-06).

        Commits: this is the top of its own task, and the contact, the thread, the window and the
        message are one fact about one moment — a partial application would be worse than none.

        Routes on the event's own persisted ownership (``phone_number_id`` vs
        ``channel_endpoint_id``), not on how this service was constructed: the dispatching task
        (``process_inbound_message``) has no reason to know which provider owns any given event
        before reading its row, so the row itself is the single source of truth for which path runs.
        """
        row = await self._events.get_by_id(event_pk)
        if row is None:
            logger.warning("inbound_event_missing", extra={"event_pk": event_pk})
            return {"status": "missing", "event_pk": event_pk}
        if row.channel_endpoint_id is not None:
            return await self._apply_inbound_endpoint(
                event_pk, row.channel_endpoint_id, row.payload_json
            )
        if row.phone_number_id is None:
            raise LedgerError("inbound event is not routed to a phone number")

        number = await self._numbers.get_by_id(row.phone_number_id)
        if number is None:
            raise LedgerError(f"phone number {row.phone_number_id} no longer exists")

        message = self._to_inbound_message(row.payload_json, connector_type=CONNECTOR_META_CLOUD)
        # Redelivery lands here as a second task for the same provider message id (Doc 06 §2.3
        # idempotency key): the thread must not gain a second copy or a second unread. Scoped to
        # the receiving endpoint — a provider message id is only unique inside it (ADR-0020).
        existing = await self._messages.get_by_provider_message_id(
            message.channel_message_id, phone_number_id=number.id
        )
        if existing is not None:
            return await self._duplicate_inbound_result(event_pk=event_pk, existing=existing)

        occurred_at = message.occurred_at or utcnow()
        contact = await self._conversations.resolve_contact(
            organization_id=number.organization_id,
            wa_id=message.from_id,
            profile_name=message.profile_name,
            occurred_at=occurred_at,
        )
        policy = await self._operations.get(contact.organization_id)
        consent_change = await self._operations.apply_consent_keyword(
            contact=contact,
            message_type=message.message_type,
            content=message.content,
            occurred_at=occurred_at,
            policy=policy,
        )
        conversation, opened_new_window = await self._conversations.open_for_inbound_with_window(
            number=number, contact=contact, occurred_at=occurred_at
        )
        # The conversation lock closes the race between the optimistic lookup above and another
        # worker committing the same provider delivery. Refresh under that lock before appending.
        existing = await self._messages.get_by_provider_message_id(
            message.channel_message_id, phone_number_id=number.id
        )
        if existing is not None:
            return await self._duplicate_inbound_result(event_pk=event_pk, existing=existing)

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
        await self._messages.flush()
        await self._conversations.record_inbound_message(
            conversation,
            preview=ConversationService.preview_of(message.message_type, message.content),
            occurred_at=occurred_at,
        )
        await self._note_campaign_reply(contact, occurred_at)
        _, automation_receipts = await self._business_events.record_message_received(
            message=stored,
            conversation=conversation,
            contact=contact,
            occurred_at=occurred_at,
            source=CONNECTOR_META_CLOUD,
        )
        auto_reply_message_pk = await self._accept_automatic_reply(
            policy=policy,
            conversation=conversation,
            contact=contact,
            source_message=stored,
            occurred_at=occurred_at,
            opened_new_window=opened_new_window,
            consent_change=consent_change,
        )
        await self._session.commit()
        result = {
            "status": APPLIED,
            "event_pk": event_pk,
            "message_id": stored.public_id,
            "message_pk": stored.id,
            "conversation_id": conversation.public_id,
            "contact_id": contact.public_id,
            # The bytes are fetched on the `media` lane, not here: an attachment must never hold
            # up the message it came with (Doc 07 §17.2/§17.4). The caller owns the dispatch.
            "media_pending": self._media_pending(stored),
            "automation_receipts": self._automation_dispatch_payload(automation_receipts),
        }
        if auto_reply_message_pk is not None:
            result["auto_reply_message_pk"] = auto_reply_message_pk
        return result

    async def _apply_inbound_endpoint(
        self, event_pk: int, channel_endpoint_id: int, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        """The channel-endpoint-owned analogue of the body of :meth:`apply_inbound` (QR-08).

        Same contract, same idempotency guarantee, same commit boundary — kept as its own
        straight-line method (see :mod:`app.services.conversation_service`'s equivalent note) so a
        WAHA event can never resolve against a Meta number or vice versa.
        """
        endpoint = await self._endpoints.get_by_id(channel_endpoint_id)
        if endpoint is None:
            raise LedgerError(f"channel endpoint {channel_endpoint_id} no longer exists")
        connector_type = await self._endpoints.connector_type_for_id(endpoint.id)
        if connector_type is None:
            raise LedgerError(f"channel connection for endpoint {endpoint.id} no longer exists")
        connection = await self._connections.get_by_id(endpoint.connection_id)
        if connection is None:
            raise LedgerError(f"channel connection {endpoint.connection_id} no longer exists")

        message = self._to_inbound_message(payload, connector_type=connector_type)
        occurred_at = message.occurred_at or utcnow()
        provider_address: str | None = None
        route_namespace: str | None = None
        contact_phone_wa_id: str | None = None
        if connector_type == CONNECTOR_WAHA:
            try:
                provider_address = normalize_direct_jid(message.from_id)
                alternate_address = optional_direct_jid(message.alternate_from_id)
                route_namespace = route_identity_namespace(provider_address)
                contact_phone_wa_id = phone_wa_id(provider_address, alternate_address)
            except Exception as exc:  # noqa: BLE001 - invalid provider identity is poison
                raise LedgerError(f"WAHA sender identity cannot be resolved: {exc}") from exc
        existing = await self._messages.get_by_provider_message_id_for_endpoint(
            message.channel_message_id, channel_endpoint_id=endpoint.id
        )
        if existing is not None:
            # A historical message can predate provider-identity persistence. Re-applying it stays
            # a message no-op but durably repairs the routing alias through the normal service path.
            if provider_address is not None and route_namespace is not None:
                contact = await self._contacts.get_by_id(existing.contact_id)
                if contact is None:
                    raise LedgerError(f"message {existing.id} has no recipient Contact")
                try:
                    await self._conversations.remember_endpoint_contact_identity(
                        endpoint=endpoint,
                        connection=connection,
                        contact=contact,
                        provider_address=provider_address,
                        route_namespace=route_namespace,
                        phone_wa_id=contact_phone_wa_id,
                        occurred_at=occurred_at,
                    )
                except ValueError as exc:
                    raise LedgerError(f"WAHA sender identity cannot be linked: {exc}") from exc
                await self._session.commit()
            return await self._duplicate_inbound_result(event_pk=event_pk, existing=existing)

        # Provider routing identity and Contact telephone identity stay separate: a LID may use
        # digits, but only a provider-supplied phone JID can establish the canonical phone alias.
        if provider_address is None or route_namespace is None:
            raise LedgerError(
                f"endpoint connector {connector_type!r} has no recipient identity resolver"
            )
        try:
            contact = await self._conversations.resolve_endpoint_contact_identity(
                endpoint=endpoint,
                connection=connection,
                provider_address=provider_address,
                route_namespace=route_namespace,
                phone_wa_id=contact_phone_wa_id,
                profile_name=message.profile_name,
                occurred_at=occurred_at,
            )
        except ValueError as exc:
            raise LedgerError(f"WAHA sender identity cannot be resolved: {exc}") from exc
        policy = await self._operations.get(contact.organization_id)
        consent_change = await self._operations.apply_consent_keyword(
            contact=contact,
            message_type=message.message_type,
            content=message.content,
            occurred_at=occurred_at,
            policy=policy,
        )
        (
            conversation,
            opened_new_window,
        ) = await self._conversations.open_for_inbound_endpoint_with_window(
            endpoint=endpoint, contact=contact, occurred_at=occurred_at
        )
        existing = await self._messages.get_by_provider_message_id_for_endpoint(
            message.channel_message_id, channel_endpoint_id=endpoint.id
        )
        if existing is not None:
            return await self._duplicate_inbound_result(event_pk=event_pk, existing=existing)

        stored = Message(
            organization_id=endpoint.organization_id,
            conversation_id=conversation.id,
            channel_endpoint_id=endpoint.id,
            contact_id=contact.id,
            direction=DIRECTION_INBOUND,
            wamid=message.channel_message_id,
            message_type=message.message_type,
            content_json=message.content,
            status=MSG_ACCEPTED,
            created_at=occurred_at,
        )
        await self._messages.add(stored)
        await self._messages.flush()
        await self._conversations.record_inbound_message(
            conversation,
            preview=ConversationService.preview_of(message.message_type, message.content),
            occurred_at=occurred_at,
        )
        await self._note_campaign_reply(contact, occurred_at)
        _, automation_receipts = await self._business_events.record_message_received(
            message=stored,
            conversation=conversation,
            contact=contact,
            occurred_at=occurred_at,
            source=connector_type,
        )
        auto_reply_message_pk = await self._accept_automatic_reply(
            policy=policy,
            conversation=conversation,
            contact=contact,
            source_message=stored,
            occurred_at=occurred_at,
            opened_new_window=opened_new_window,
            consent_change=consent_change,
        )
        await self._session.commit()
        result = {
            "status": APPLIED,
            "event_pk": event_pk,
            "message_id": stored.public_id,
            "message_pk": stored.id,
            "conversation_id": conversation.public_id,
            "contact_id": contact.public_id,
            "media_pending": self._media_pending(stored),
            "automation_receipts": self._automation_dispatch_payload(automation_receipts),
        }
        if auto_reply_message_pk is not None:
            result["auto_reply_message_pk"] = auto_reply_message_pk
        return result

    async def _duplicate_inbound_result(
        self, *, event_pk: int, existing: Message
    ) -> dict[str, Any]:
        automation_receipts = await self._business_events.receipt_dispatches_for_message(existing)
        result = {
            "status": DUPLICATE,
            "event_pk": event_pk,
            "message_id": existing.public_id,
            "message_pk": existing.id,
            # A redelivery still reports pending effects: the first attempt may have committed the
            # durable rows and died before their post-commit tasks were queued.
            "media_pending": self._media_pending(existing),
            "automation_receipts": self._automation_dispatch_payload(automation_receipts),
        }
        auto_reply_pk = await self._automatic_reply_for_existing_source(existing)
        if auto_reply_pk is not None:
            result["auto_reply_message_pk"] = auto_reply_pk
        return result

    async def _automatic_reply_for_existing_source(self, source: Message) -> int | None:
        event = await self._business_events.automatic_reply_for_source(
            organization_id=source.organization_id,
            conversation_id=source.conversation_id,
            source_message_id=source.id,
        )
        reply_id = (event.payload_json or {}).get("reply_message_id") if event else None
        return (
            int(reply_id) if isinstance(reply_id, (int, str)) and str(reply_id).isdigit() else None
        )

    async def _accept_automatic_reply(
        self,
        *,
        policy: InboxOperationsResponse,
        conversation: Conversation,
        contact: Contact,
        source_message: Message,
        occurred_at: datetime,
        opened_new_window: bool,
        consent_change: str | None,
    ) -> int | None:
        now = utcnow()
        decision = self._operations.consent_reply_decision(
            policy=policy,
            consent_status=consent_change,
            occurred_at=occurred_at,
            now=now,
        )
        if decision is None:
            if contact.opt_in_status == OPT_IN_OPTED_OUT:
                return None
            decision = self._operations.automatic_reply_decision(
                policy=policy,
                occurred_at=occurred_at,
                opened_new_window=opened_new_window,
                has_recent_off_hours_reply=False,
                now=now,
            )
        if decision is None:
            return None
        if decision.kind == "off_hours" and await self._business_events.has_recent_automatic_reply(
            organization_id=conversation.organization_id,
            conversation_id=conversation.id,
            kind="off_hours",
            since=now - timedelta(hours=24),
        ):
            return None
        existing = await self._business_events.automatic_reply_for_source(
            organization_id=conversation.organization_id,
            conversation_id=conversation.id,
            source_message_id=source_message.id,
        )
        if existing is not None:
            reply_id = (existing.payload_json or {}).get("reply_message_id")
            return (
                int(reply_id)
                if isinstance(reply_id, (int, str)) and str(reply_id).isdigit()
                else None
            )

        reply = await self._send.accept_system_text_for_conversation(
            conversation=conversation,
            contact=contact,
            body=decision.body,
            kind=decision.kind,
            source_message_id=source_message.id,
            allow_opted_out=decision.kind == "consent_opt_out",
        )
        await self._business_events.record_automatic_reply(
            organization_id=conversation.organization_id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            source_message_id=source_message.id,
            reply_message_id=reply.id,
            kind=decision.kind,
            occurred_at=reply.created_at,
        )
        return reply.id

    @staticmethod
    def _media_pending(message: Message) -> bool:
        return message.media_asset_id is None and media_reference(message) is not None

    @staticmethod
    def _automation_dispatch_payload(receipts: list[Any]) -> list[dict[str, Any]]:
        return [
            {"receipt_pk": receipt.receipt_pk, "task_id": receipt.task_id}
            for receipt in receipts
        ]

    def _to_inbound_message(
        self, payload: dict[str, Any] | None, *, connector_type: str
    ) -> InboundMessage:
        try:
            return get_adapter(connector_type).to_inbound_message(payload or {})
        except Exception as exc:  # noqa: BLE001 - any translation failure is the same verdict
            raise LedgerError(f"inbound payload cannot be read: {exc}") from exc

    # --- Status callbacks (Doc 06 §11.3/§11.4) ------------------------------
    async def apply_status(
        self,
        update: StatusUpdate,
        *,
        phone_number_id: int | None = None,
        channel_endpoint_id: int | None = None,
    ) -> str:
        """Advance a message's delivery state (FR-WA-06/07).

        Does **not** commit: the caller settles the webhook event in the same transaction, so an
        applied status and the event that carried it can never disagree.

        Exactly one of ``phone_number_id``/``channel_endpoint_id`` — the endpoint the callback
        arrived on — must be given. Required, not optional, so a delivery receipt can only ever
        advance a message belonging to that one endpoint — reconciliation must not cross an
        endpoint or tenant boundary (ADR-0020; Doc 33 §6.1 "Message identity").
        """
        if (phone_number_id is None) == (channel_endpoint_id is None):
            raise LedgerError(
                "apply_status requires exactly one of phone_number_id/channel_endpoint_id"
            )
        if channel_endpoint_id is not None:
            message = await self._messages.get_by_provider_message_id_for_endpoint(
                update.channel_message_id, channel_endpoint_id=channel_endpoint_id
            )
            endpoint_label = f"channel endpoint {channel_endpoint_id}"
        else:
            assert phone_number_id is not None
            message = await self._messages.get_by_provider_message_id(
                update.channel_message_id, phone_number_id=phone_number_id
            )
            endpoint_label = f"endpoint {phone_number_id}"
        if message is None:
            raise MessageNotFound(
                f"no message for provider message id {update.channel_message_id!r} "
                f"on {endpoint_label}"
            )

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
