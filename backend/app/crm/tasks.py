"""CRM background tasks (Doc 06 §2.3 ``imports`` queue).

Thin adapters: the task owns nothing but the Celery binding — priority, timeouts, retry caps and
failure destination come from the queue registry, and the work itself lives in
:class:`~app.services.import_service.ImportService`. Keeping the body in the service is what lets
the same code be unit-tested without a broker and reused by any future caller.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task
from app.queue.registry import IMPORTS
from app.services.import_service import ImportService


async def _run_import(import_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        job = await ImportService(session).run(import_id)
        return {
            "import_id": job.public_id,
            "status": job.status,
            "total_rows": job.total_rows,
            "success_rows": job.success_rows,
            "error_rows": job.error_rows,
        }


@register_task(queue=IMPORTS, name="app.crm.tasks.run_contact_import")
def run_contact_import(self, import_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Execute a contact import. Retries are classified/backed off by the queue framework."""
    try:
        return asyncio.run(_run_import(import_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise
