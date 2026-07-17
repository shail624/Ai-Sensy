"""Channel background tasks (Doc 06 §2.3 — ``templates.sync``, ``webhooks.ingest/process``).

Thin adapters, like the CRM tasks: the Celery binding lives here, priority/timeouts/retry caps and
failure destination come from the queue registry, and the work itself stays in the services so it
is testable without a broker.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task
from app.queue.registry import (
    INBOUND_PROCESS,
    MEDIA,
    SENDS_PRIORITY,
    TEMPLATES_SYNC,
    WEBHOOKS_INGEST,
    WEBHOOKS_PROCESS,
)
from app.queue.retry import classify, should_retry
from app.services.media_ingest_service import MediaIngestService
from app.services.message_service import MessageService
from app.services.send_service import SendService
from app.services.waba_service import WabaService
from app.services.webhook_service import WebhookService


async def _run_sync(waba_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        result = await WabaService(session).run_sync(waba_id)
        return {"waba_id": waba_id} | result


@register_task(queue=TEMPLATES_SYNC, name="app.channels.tasks.run_waba_sync")
def run_waba_sync(self, waba_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
"""Reconcile a WABA's phone numbers with Meta. Templates join this job when M5 lands."""
    try:
        return asyncio.run(_run_sync(waba_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


# --- Inbound webhooks (Doc 06 §11.2) ----------------------------------------
@register_task(queue=WEBHOOKS_INGEST, name="app.channels.tasks.ingest_webhook_events")
def ingest_webhook_events(self, event_ids: list[int]) -> dict[str, Any]:  # noqa: ANN001
    """Fan a persisted delivery out into one processing task per event (Doc 06 §2.3).

    Kept separate from processing so the ack path enqueues exactly one message however many events
    a delivery batched, and so a slow processor cannot back-pressure ingestion (§11.6).
    """
    try:
        for event_id in event_ids:
            process_webhook_event.apply_async(args=[event_id])
        return {"dispatched": len(event_ids)}
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _process(event_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await WebhookService(session).process(
            event_pk,
            dispatch_inbound=lambda pk: process_inbound_message.apply_async(args=[pk]),
        )


async def _apply_inbound(event_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await MessageService(session).apply_inbound(event_pk)


async def _download_media(message_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await MediaIngestService(session).download_inbound(message_pk)


@register_task(queue=MEDIA, name="app.channels.tasks.download_inbound_media")
def download_inbound_media(self, message_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Fetch an inbound message's attachment and link it (FR-WA-11; Doc 07 §17.2).

    Standard parking applies: the `media` queue's failure destination is the DLQ (Doc 06 §2.3), and
    a lost attachment is a task failure, not a lost event — the message it belongs to is already in
    the ledger and stays readable without it (§17.4).
    """
    try:
        return asyncio.run(_download_media(message_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _dead_letter(event_pk: int, error: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        entry = await WebhookService(session).dead_letter(event_pk, error=error)
        return {"status": "dead_lettered", "event_pk": event_pk, "dead_letter_id": entry.public_id}


@register_task(queue=WEBHOOKS_PROCESS, name="app.channels.tasks.process_webhook_event")
def process_webhook_event(self, event_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Apply one persisted webhook event, idempotently (FR-WA-07).

    Exhausted retries park in ``webhook_dead_letter`` rather than the generic ``dead_letter``
    (Doc 03 §9.4 gives events their own store with their own replay path), which is why this
    returns instead of raising: the task **succeeded** at isolating a bad event (§11.6), and
    letting it fail would park the same thing twice, in two stores, for one problem.
    """
    try:
        return asyncio.run(_process(event_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs dead-letter
        if should_retry(classify(exc), self.request.retries + 1):
            self.smart_retry(exc)  # re-queues with backoff (§6.3)
            raise  # unreachable: smart_retry always raises
        return asyncio.run(_dead_letter(event_pk, f"{type(exc).__name__}: {exc}"))


# --- Outbound sends (Doc 04 §18.2; Doc 06 §2.3) ------------------------------
async def _deliver(message_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await SendService(session).deliver(message_pk)


async def _fail_send(message_pk: int, error: str, code: str | None) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await SendService(session).fail(message_pk, error=error, code=code)


@register_task(queue=SENDS_PRIORITY, name="app.channels.tasks.send_message")
def send_message(self, message_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Deliver an accepted message to the channel (FR-WA-10).

    A terminal failure is recorded **on the message** rather than parked as a task: `failed` plus
    an `error_code` and a status-history row is what the operator, the inbox and analytics read
    (Doc 03 §9.2/§9.3). Meta's own error map decides retry vs terminal (Doc 06 §6.6).
    """
    try:
        return asyncio.run(_deliver(message_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        if should_retry(classify(exc), self.request.retries + 1):
            self.smart_retry(exc)
            raise  # unreachable: smart_retry always raises
        code = getattr(exc, "code", None)
        return asyncio.run(
            _fail_send(message_pk, f"{type(exc).__name__}: {exc}", str(code) if code else None)
        )


@register_task(queue=INBOUND_PROCESS, name="app.channels.tasks.process_inbound_message")
def process_inbound_message(self, event_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Apply a routed inbound message: contact, thread, window, ledger (Doc 06 §2.3).

    Parks in ``webhook_dead_letter`` for the same reason ``process_webhook_event`` does: this lane
    handles the same events, so its failures belong in the same store with the same replay path.
    """
    try:
        result = asyncio.run(_apply_inbound(event_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs dead-letter
        if should_retry(classify(exc), self.request.retries + 1):
            self.smart_retry(exc)
            raise  # unreachable: smart_retry always raises
        return asyncio.run(_dead_letter(event_pk, f"{type(exc).__name__}: {exc}"))

    if result.get("media_pending"):
        # The attachment travels on its own lane so a 15 MB video cannot delay the message that
        # carried it (Doc 07 §17.2/§17.4).
        download_inbound_media.apply_async(args=[result["message_pk"]])
    return result
