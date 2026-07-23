"""CRM background tasks (Doc 06 §2.3 ``imports``/``exports`` queues).

Thin adapters: the task owns nothing but the Celery binding — priority, timeouts, retry caps and
failure destination come from the queue registry, and the work itself lives in the services.
Keeping the body in the service is what lets the same code be unit-tested without a broker and
reused by any future caller.
"""

from __future__ import annotations

from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task, run_async
from app.queue.registry import EXPORTS, IMPORTS
from app.services.bulk_service import BulkService
from app.services.export_service import ExportService
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
        return run_async(_run_import(import_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _run_export(export_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        job = await ExportService(session).run(export_id)
        return {"export_id": job.public_id, "status": job.status, "row_count": job.row_count}


@register_task(queue=EXPORTS, name="app.crm.tasks.run_contact_export")
def run_contact_export(self, export_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Generate a contact export. Retries are classified/backed off by the queue framework."""
    try:
        return run_async(_run_export(export_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _run_bulk(bulk_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        job = await BulkService(session).run(bulk_id)
        return {
            "bulk_id": job.public_id,
            "operation": job.operation,
            "status": job.status,
            "result": job.result_status,
            "processed": job.processed_items,
            "succeeded": job.succeeded_items,
            "failed": job.failed_items,
            "skipped": job.skipped_items,
        }


# Bulk work shares the ``imports`` lane: Doc 06 §2.3 scopes that queue to long-running CRM
# "validate, dedup, upsert" work, and Doc 12 §56 gives M3 no other write queue. Separate task
# names keep the three operations independently traceable on the Queue Monitor.
@register_task(queue=IMPORTS, name="app.crm.tasks.run_contact_bulk_update")
def run_contact_bulk_update(self, bulk_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Apply a bulk edit (tags/attributes) across a selection or filter (FR-CON-07)."""
    try:
        return run_async(_run_bulk(bulk_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


@register_task(queue=IMPORTS, name="app.crm.tasks.run_contact_bulk_delete")
def run_contact_bulk_delete(self, bulk_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Soft-delete a selection or filter of contacts (FR-CON-08)."""
    try:
        return run_async(_run_bulk(bulk_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


@register_task(queue=IMPORTS, name="app.crm.tasks.run_contact_deduplicate")
def run_contact_deduplicate(self, bulk_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Scan for duplicates and report or merge them (FR-CON-06)."""
    try:
        return run_async(_run_bulk(bulk_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise
