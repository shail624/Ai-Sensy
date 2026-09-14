"""Inbound webhook ingest & processing (Doc 06 §11; Doc 04 §23) — FR-WA-05/07/08.

**Persist-first, process-async.** The request path does the least it can: verify the signature,
write the events, ack. Everything else runs on the ``webhooks.*`` queues. That split is what buys
both halves of FR-WA-05 at once — Meta gets its ``200`` inside the budget, and an event survives a
worker crash because it was durable before it was interesting (§11.2, §11.7).

The order is not negotiable: **verify → persist → ack → enqueue**. Verifying before parsing means
we never interpret an unauthenticated body; persisting before acking means the ack is a promise we
can keep; enqueueing after the commit means a task never races the row it is about to read.

Meta is reached only through the adapter resolved from the registry (Doc 07 §5.4) — this module
handles WhatsApp's inbound stream without containing one line that knows what Meta sends.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, get_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD
from app.channels.errors import ChannelError
from app.channels.models import InboundEvent, InboundEventType
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM
from app.models.webhook import (
    WH_DUPLICATE,
    WH_FAILED,
    WH_PROCESSED,
    WH_RECEIVED,
    WHDL_PENDING,
    WebhookDeadLetter,
    WebhookEvent,
)
from app.queue.retry import FailureClass, register_error_map
from app.repositories.channel_connection import ChannelEndpointRepository
from app.repositories.waba import PhoneNumberRepository
from app.repositories.webhook import WebhookDeadLetterRepository, WebhookEventRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.message_service import LedgerError, MessageNotFound, MessageService

logger = get_logger(__name__)

#: Doc 06 §2.3's webhook lanes: ingest turns persisted rows into work, process applies them.
INGEST_QUEUE = "webhooks.ingest"
PROCESS_QUEUE = "webhooks.process"
#: Doc 06 §2.3's higher-level lane: conversation upsert + active detection, off the webhook lane.
INBOUND_QUEUE = "inbound.process"
INGEST_TASK = "app.channels.tasks.ingest_webhook_events"
PROCESS_TASK = "app.channels.tasks.process_webhook_event"
INBOUND_TASK = "app.channels.tasks.process_inbound_message"

#: Event types this module knows how to complete. Anything else is isolated (Doc 06 §11.6).
_ROUTABLE = (InboundEventType.MESSAGES.value, InboundEventType.STATUSES.value)


class WebhookUnprocessable(Exception):
    """This event will never process, no matter how often it is retried.

    A poison event (unknown type, unroutable number, unreadable payload). Retrying it would burn
    the queue on a certainty; it belongs in the dead-letter store for a human (Doc 06 §7.2/§11.6).
    """


def _classify_webhook(exc: BaseException) -> FailureClass | None:
    """Register the classes this module owns with the retry engine (Doc 06 §6.6, D12)."""
    if isinstance(exc, WebhookUnprocessable | LedgerError):
        return FailureClass.TERMINAL_DATA
    if isinstance(exc, MessageNotFound):
        # A race with the send that created the message; a moment's backoff resolves it, and an
        # exhausted one dead-letters rather than vanishing (Doc 06 §11.3/§11.5).
        return FailureClass.TRANSIENT_PROC
    return None


register_error_map("webhooks", _classify_webhook)


class WebhookService:
    """Ingest and process one channel's inbound stream.

    ``connector_type`` is a parameter, not a constant, because Doc 07 §18.2 puts both channels
    through this same pipeline: a connector's event stream ingests here too, differing only at the
    adapter edge (decision CD14).
    """

    def __init__(
        self, session: AsyncSession, *, connector_type: str = CONNECTOR_META_CLOUD
    ) -> None:
        self._session = session
        self._connector_type = connector_type
        self._events = WebhookEventRepository(session)
        self._dlq = WebhookDeadLetterRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._endpoints = ChannelEndpointRepository(session)
        self._audit = AuditService(session)

    @property
    def _endpoint_routed(self) -> bool:
        """Whether this connector routes by ``channel_endpoints`` rather than ``phone_numbers``.

        Meta is the one connector with a ``phone_numbers`` provisioning record (ADR-0020); every
        other connector — WAHA today — is provisioned through the provider-neutral control plane
        instead (QR-08), so it routes by ``channel_endpoint_id``.
        """
        return self._connector_type != CONNECTOR_META_CLOUD

    def adapter(self) -> ChannelAdapter:
        """The inbound adapter — no per-WABA credentials: a delivery is verified app-wide."""
        return get_adapter(self._connector_type)

    # --- Verification handshake (Doc 04 §23) --------------------------------
    async def challenge(self, params: dict[str, str]) -> str:
        """Answer the subscription handshake, or refuse it (Doc 04 §23 — verify token)."""
        echo = self.adapter().webhook_challenge(params)
        if echo is None:
            logger.warning("webhook_verification_rejected", extra={"mode": params.get("hub.mode")})
            raise ForbiddenError("Webhook verification failed.")
        # Bounded and meaningful: only a caller holding the verify token can write this row.
        await self._audit.record(
            AuditAction.WEBHOOK_VERIFIED,
            actor_type=ACTOR_SYSTEM,
            entity_type="webhook",
            after={"connector_type": self._connector_type},
        )
        await self._session.commit()
        return echo

    # --- Ingest (Doc 06 §11.2 steps 1–3) ------------------------------------
    async def ingest(self, *, body: bytes, signature: str | None) -> list[int]:
        """Verify, persist and return the ids to enqueue. The only work before the ``200``."""
        adapter = self.adapter()
        if not adapter.verify_webhook_signature(body, signature):
            # Not audited: the endpoint is public, so an audit row per rejection would let anyone
            # write to the audit trail. A structured log is the alertable signal (Doc 11 §30).
            logger.warning("webhook_signature_rejected", extra={"bytes": len(body)})
            raise ForbiddenError("Invalid webhook signature.")

        events, unreadable = self._read(adapter, body)
        channel_number_ids = {event.channel_number_id for event in events if event.channel_number_id}
        if self._endpoint_routed:
            endpoint_routing = await self._events.resolve_endpoints(
                channel_number_ids, connector_type=self._connector_type
            )
            number_routing: dict[str, int] = {}
        else:
            endpoint_routing = {}
            number_routing = await self._events.resolve_numbers(channel_number_ids)
        routing = endpoint_routing | number_routing

        rows = [
            WebhookEvent(
                event_id=(event.event_id or None) and event.event_id[:128],
                phone_number_id=number_routing.get(event.channel_number_id),
                channel_endpoint_id=endpoint_routing.get(event.channel_number_id),
                object_type=event.type.value,
                signature_ok=True,
                payload_json=event.payload,
                status=WH_RECEIVED,
            )
            for event in events
        ]
        for row in rows:
            self._session.add(row)
        await self._session.flush()
        await self._session.commit()

        logger.info(
            "webhook_ingested",
            extra={"events": len(rows), "unreadable": unreadable, "routed": len(routing)},
        )
        return [row.id for row in rows]

    def _read(self, adapter: ChannelAdapter, body: bytes) -> tuple[list[InboundEvent], bool]:
        """Signed body → canonical events, never raising.

        A body that survived signature verification is authentic, so a body we cannot read means
        the channel changed its contract. Failing the request would make Meta redeliver it for
        seven days and change nothing; instead the raw bytes are kept as one unknown event and
        isolated downstream (§11.6) — visible, replayable, and out of the stream's way.
        """
        try:
            payload = json.loads(body)
            return adapter.parse_webhook(payload), False
        except (ValueError, TypeError, ChannelError) as exc:
            logger.error("webhook_unreadable", extra={"error": f"{type(exc).__name__}: {exc}"})
            return [
                InboundEvent(
                    event_id=None,
                    type=InboundEventType.UNKNOWN,
                    channel_number_id="",
                    payload={
                        "_unreadable": body.decode("utf-8", errors="replace")[:65535],
                        "_error": f"{type(exc).__name__}: {exc}",
                    },
                )
            ], True

    # --- Process (Doc 06 §11.2 step 4) --------------------------------------
    async def process(self, event_pk: int, *, dispatch_inbound: Callable[[int], Any]) -> dict[str, Any]:
        """Apply one persisted event, idempotently (FR-WA-07).

        Doc 06 §2.3 splits the work by cost: this lane **applies status callbacks** — a cheap
        forward-only update — and **routes inbound messages** onto ``inbound.process``, where the
        conversation upsert and active detection happen without holding up the Meta firehose
        (Doc 06 §11.2's ``WP → INB`` edge).
        """
        row = await self._events.get_by_id(event_pk)
        if row is None:
            # The row aged out or never committed; there is nothing to apply and nothing to park.
            logger.warning("webhook_event_missing", extra={"event_pk": event_pk})
            return {"status": "missing", "event_pk": event_pk}
        if row.is_settled:
            # At-least-once delivery means this task can arrive twice (Doc 06 §8).
            return {"status": row.status, "event_pk": event_pk, "skipped": True}

        # Committed *before* the attempt, not after: everything below either rolls back (leaving
        # `attempts` at zero and hiding the retries) or is a worker crash that records nothing at
        # all. The counter is only true if it is durable before the work it counts.
        row.attempts += 1
        await self._session.commit()

        if row.object_type not in _ROUTABLE:
            raise WebhookUnprocessable(f"unknown event type {row.object_type!r}")
        if row.phone_number_id is None and row.channel_endpoint_id is None:
            raise WebhookUnprocessable(
                "event is for a number or channel endpoint this platform does not own"
            )
        if row.event_id and await self._events.has_processed_sibling(
            row.event_id, exclude_id=row.id
        ):
            row.status = WH_DUPLICATE
            row.processed_at = utcnow()
            await self._session.commit()
            return {"status": WH_DUPLICATE, "event_pk": event_pk, "event_id": row.event_id}

        outcome = None
        if row.object_type == InboundEventType.STATUSES.value:
            # The request-scoped connector has gone by the time this worker runs. Persisted event
            # ownership is authoritative: endpoint -> connection -> connector for provider-neutral
            # events, while phone-number ownership remains the Meta path.
            connector_type = await self._persisted_connector_type(row)
            service = MessageService(self._session, connector_type=connector_type)
            # One transaction for the applied status *and* the event that carried it: settling the
            # event while the transition it describes rolled back would be a durable lie. Exactly
            # one of `phone_number_id`/`channel_endpoint_id` is set (guaranteed non-None above); it
            # scopes the reconciliation to the endpoint the callback arrived on (ADR-0020 provider
            # message identity).
            outcome = await service.apply_status(
                service.to_status_update(row.payload_json),
                phone_number_id=row.phone_number_id,
                channel_endpoint_id=row.channel_endpoint_id,
            )

        row.status = WH_PROCESSED
        row.processed_at = utcnow()
        await self._session.commit()

        if row.object_type == InboundEventType.MESSAGES.value:
            # After the commit, never before: the task must not outrun the row it reads.
            dispatch_inbound(row.id)
            outcome = "routed"
        return {
            "status": WH_PROCESSED,
            "event_pk": event_pk,
            "object_type": row.object_type,
            "outcome": outcome,
        }

    async def _persisted_connector_type(self, row: WebhookEvent) -> str:
        if (row.phone_number_id is None) == (row.channel_endpoint_id is None):
            raise WebhookUnprocessable(
                "event must be owned by exactly one phone number or channel endpoint"
            )
        if row.phone_number_id is not None:
            return CONNECTOR_META_CLOUD
        assert row.channel_endpoint_id is not None
        connector_type = await self._endpoints.connector_type_for_id(row.channel_endpoint_id)
        if connector_type is None:
            raise WebhookUnprocessable(
                f"channel endpoint {row.channel_endpoint_id} has no owning connection"
            )
        return connector_type

    # --- Dead letter (Doc 03 §9.4; Doc 06 §11.5/§11.6) ----------------------
    async def dead_letter(self, event_pk: int, *, error: str) -> WebhookDeadLetter:
        """Isolate an event that cannot be processed — the last safety net (FR-WA-08)."""
        row = await self._events.get_by_id(event_pk)
        entry = WebhookDeadLetter(
            source_event_id=event_pk,
            payload_json=(row.payload_json if row else {}) or {},
            error_detail=error[:1024],
            attempts=row.attempts if row else 0,
            status=WHDL_PENDING,
        )
        await self._dlq.add(entry)
        if row is not None:
            row.status = WH_FAILED
        await self._audit.record(
            AuditAction.WEBHOOK_DEAD_LETTERED,
            actor_type=ACTOR_SYSTEM,
            organization_id=await self._organization_of(row),
            entity_type="webhook_event",
            entity_id=event_pk,
            after={"error": error[:512], "object_type": row.object_type if row else None},
        )
        await self._session.commit()
        logger.error("webhook_dead_lettered", extra={"event_pk": event_pk, "error": error[:512]})
        return entry

    async def _organization_of(self, row: WebhookEvent | None) -> int | None:
        """Scope the audit entry to the owning org when the event routed to a known number."""
        if row is None or row.phone_number_id is None:
            return None
        number = await self._numbers.get_by_id(row.phone_number_id)
        return number.organization_id if number else None
