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

import asyncio
from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task
from app.queue.registry import CAMPAIGNS_CONTROL, SENDS_BULK
from app.services.campaign_dispatch_service import CampaignDispatchService


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
def dispatch_campaign(self, campaign_pk: int) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Batch the roster and fan the batches out (FR-CAM-05/09).

    Idempotent by re-derivation (Doc 06 §2.3): a redelivered task — or a restart mid-campaign —
    finds the batches already planned and dispatches only the ones still owed.
    """
    try:
        result = asyncio.run(_plan(campaign_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for batch_pk in result.get("batches") or []:
        dispatch_campaign_batch.apply_async(args=[batch_pk])
    return result


@register_task(queue=CAMPAIGNS_CONTROL, name="app.crm.campaign_tasks.dispatch_campaign_batch")
def dispatch_campaign_batch(self, batch_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Enqueue one send per recipient the batch still owes (FR-CAM-05)."""
    try:
        result = asyncio.run(_fan_out(batch_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise

    for recipient_pk in result.get("recipients") or []:
        send_campaign_recipient.apply_async(args=[recipient_pk])
    return {"batch": batch_pk, "dispatched": len(result.get("recipients") or [])}


@register_task(queue=SENDS_BULK, name="app.crm.campaign_tasks.send_campaign_recipient")
def send_campaign_recipient(self, recipient_pk: int) -> dict[str, Any]:  # noqa: ANN001
    """Send one campaign message through SendService (FR-CAM-05/10).

    Everything a send owes — the rate gate, the ledger, the conversation, the 24-hour rules — comes
    from SendService, because a campaign message is an ordinary message that happens to be one of
    many. Throttling arrives here as `THROTTLE` and is re-queued with backoff (Doc 06 §5.3/§6.2);
    the recipient row keeps the outcome either way (Doc 03 §8.3).
    """
    try:
        return asyncio.run(_send(recipient_pk))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise
