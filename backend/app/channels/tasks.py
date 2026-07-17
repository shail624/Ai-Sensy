"""Channel background tasks (Doc 06 §2.3 ``templates.sync`` queue).

A thin adapter, like the CRM tasks: the Celery binding lives here, priority/timeouts/retry caps and
failure destination come from the queue registry, and the work itself stays in
:class:`~app.services.waba_service.WabaService` so it is testable without a broker.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task
from app.queue.registry import TEMPLATES_SYNC
from app.services.waba_service import WabaService


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
