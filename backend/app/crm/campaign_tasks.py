"""Campaign dispatch tasks (Doc 06 §2.3 ``campaigns.control`` / ``sends.bulk``) — FR-CAM-05/09.

Thin adapters, as everywhere: the Celery binding lives here, priority/timeouts/retry caps and
failure destination come from the queue registry, and the work stays in
:class:`~app.services.campaign_dispatch_service.CampaignDispatchService`.

Two lanes, for the reason Doc 06 §2.3 gives them: **control** is low-concurrency and must stay
responsive, so it only decides what to send; **bulk** carries the millions and is paced per number
by the rate gate inside ``SendService``. A control task that sent would make a campaign's
orchestration as slow as its slowest message.
"""

from __future__ import annotations

from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import TrackedTask, register_task, run_async
from app.queue.registry import CAMPAIGNS_CONTROL, SCHEDULER_TICK, SENDS_BULK, SENDS_RETRY
from app.services.campaign_dispatch_service import CampaignDispatchService
from app.services.campaign_retry_service import CampaignRetryService
from app.services.campaign_schedule_service import CampaignScheduleService


async def _plan(campaign_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await CampaignDispatchService(session).plan(campaign_pk)


async def _fan_out(batch_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await CampaignDispatchService(session).fan_out(batch_pk)


async def _send(recipient_pk: int) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await CampaignDispatchService(session).send_recipient(recipient_pk)


@register_task(queue=CAMPAIGNS_CONTROL, name="app.crm.campaign_tasks.dispatch_campaign")
def dispatch_campaign(self: TrackedTask, campaign_pk: int) -> dict[str, Any]:
    """Batch the roster and fan the batches out (FR-CAM-05/09).

    Idempotent by re-derivation (Doc 06 §2.3): a redelivered task — or a restart mid-campaign —
    finds the batches already planned and dispatches only the ones still owed.
    """
    try:
        result = run_async(_plan(campaign_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for batch_pk in result.get("batches") or []:
        dispatch_campaign_batch.apply_async(args=[batch_pk])
    return result


@register_task(queue=CAMPAIGNS_CONTROL, name="app.crm.campaign_tasks.dispatch_campaign_batch")
def dispatch_campaign_batch(self: TrackedTask, batch_pk: int) -> dict[str, Any]:
    """Enqueue one send per recipient the batch still owes (FR-CAM-05)."""
    try:
        result = run_async(_fan_out(batch_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for recipient_pk in result.get("recipients") or []:
        send_campaign_recipient.apply_async(args=[recipient_pk])
    return {"batch": batch_pk, "dispatched": len(result.get("recipients") or [])}


@register_task(queue=SENDS_BULK, name="app.crm.campaign_tasks.send_campaign_recipient")
def send_campaign_recipient(self: TrackedTask, recipient_pk: int) -> dict[str, Any]:
    """Send one campaign message through SendService (FR-CAM-05/10).

    Everything a send owes — the rate gate, the ledger, the conversation, the 24-hour rules — comes
    from SendService, because a campaign message is an ordinary message that happens to be one of
    many. Throttling arrives here as `THROTTLE` and is re-queued with backoff (Doc 06 §5.3/§6.2);
    the recipient row keeps the outcome either way (Doc 03 §8.3).
    """
    try:
        return run_async(_send(recipient_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _tick() -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await CampaignScheduleService(session).tick()


@register_task(queue=SCHEDULER_TICK, name="app.crm.campaign_tasks.scheduler_tick")
def scheduler_tick(self: TrackedTask) -> dict[str, Any]:
    """Fire every campaign schedule that has come due (FR-CAM-03/04; Doc 06 §10.2).

    Beat's heartbeat, not Beat's schedule: the cadence is fixed, the schedules live in the database
    and are edited through the API at runtime (D14). Beat must run as a **singleton** (§10.2's
    leader lock) — two tickers would fire the same slot twice.

    Fire-and-scan, so the tick is idempotent by claiming: each due row is advanced and committed
    before its campaign is handed over, and the scan is bounded by ``scheduler_tick_scan_limit``.
    """
    try:
        result = run_async(_tick())
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for campaign_pk in result.get("fired") or []:
        dispatch_campaign.apply_async(args=[campaign_pk])
    return result


async def _due_retries(limit: int) -> list[int]:
    async with get_sessionmaker()() as session:
        service = CampaignRetryService(session)
        due = await service.due(limit=limit)
        for row in due:
            await service.claim(row)
        return [row.recipient_id for row in due]


#: How many due re-attempts one scan hands back to the send lane.
RETRY_SCAN_LIMIT = 500


@register_task(queue=SENDS_RETRY, name="app.crm.campaign_tasks.scan_campaign_retries")
def scan_campaign_retries(self: TrackedTask) -> dict[str, Any]:
    """Hand every due re-attempt back to the send lane (FR-CAM-08; Doc 03 §8.4's scanner).

    The durable half of smart retry: the backoff was computed by the retry engine and stored on the
    row, so a Redis flush costs throughput rather than the re-attempt itself (NFR-DR-06).
    """
    try:
        recipients = run_async(_due_retries(RETRY_SCAN_LIMIT))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for recipient_pk in recipients:
        retry_campaign_recipient.apply_async(args=[recipient_pk])
    return {"claimed": len(recipients)}


@register_task(queue=SENDS_RETRY, name="app.crm.campaign_tasks.retry_campaign_recipient")
def retry_campaign_recipient(self: TrackedTask, recipient_pk: int) -> dict[str, Any]:
    """Re-attempt one recipient (FR-CAM-08).

    The same send path as a first attempt — it has to be, or a retry would skip the rate gate, the
    ledger or the campaign's paused status.
    """
    try:
        return run_async(_send(recipient_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise
