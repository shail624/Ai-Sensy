"""Analytics rollup tasks (Doc 15 §7) — the ``analytics.rollup`` queue.

Thin adapters, as everywhere in the platform: the Celery binding lives here, priority, timeouts,
retry cap and failure destination come from the queue registry, and the work stays in
:class:`~app.services.analytics_rollup_service.AnalyticsRollupService`.

The queue was declared from the start and is reused unchanged (``queue/registry.py``)::

    QueueSpec(ANALYTICS_ROLLUP, "Build pre-aggregated dashboard/report rollups.",
              Priority.P3, Pool.MAINTENANCE, 3, 120, 300, DEST_PARK)

P3 on the maintenance pool means a rollup never competes with sends, webhooks or control traffic;
parking on failure (rather than a DLQ replay) is right because analytics failure is **not** data
loss — the rollups are derived and a later run recomputes the same window (Doc 15 §4.1, §23.1).

**Intended cadence (Doc 15 §8.1).** Scheduling is deployment configuration, as it already is for
``scheduler_tick`` — no ``beat_schedule`` is declared in code:

===================================  =========================  ==============================
Task                                 Cadence                    Window
===================================  =========================  ==============================
``analytics.rollup_incremental``     every 15 minutes           trailing 6 closed hours
``analytics.rollup_nightly``         daily 02:15 UTC            trailing 48 h + day consolidation
``analytics.rollup_prune``           daily 03:00 UTC            drops rows past retention
``analytics.rollup_backfill``        on demand (operator)       an explicit range
===================================  =========================  ==============================

**Concurrency.** No lock is taken. Bucket replacement is idempotent by re-derivation, so a task
that overlaps a previous run duplicates work but cannot produce a wrong figure (Doc 15 §7). That is
also what makes a Celery redelivery safe: re-running the same window converges.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import register_task
from app.queue.registry import ANALYTICS_ROLLUP, EXPORTS
from app.services.analytics_rollup_service import AnalyticsRollupService


def _summarize(outcomes: list[Any]) -> dict[str, Any]:
    """Collapse per-organization outcomes into one task result (kept small for the result store)."""
    return {
        "organizations": len(outcomes),
        "buckets": sum(outcome.buckets for outcome in outcomes),
        "rows_written": sum(outcome.rows_written for outcome in outcomes),
    }


async def _incremental() -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return _summarize(await AnalyticsRollupService(session).run_incremental())


async def _nightly() -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return _summarize(await AnalyticsRollupService(session).run_nightly())


async def _backfill(
    start: str, end: str, organization_id: int | None, kinds: list[str] | None
) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        outcomes = await AnalyticsRollupService(session).run_backfill(
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            organization_id=organization_id,
            kinds=kinds,
        )
        return _summarize(outcomes)


async def _prune() -> int:
    async with get_sessionmaker()() as session:
        return await AnalyticsRollupService(session).prune()


@register_task(queue=ANALYTICS_ROLLUP, name="app.analytics.tasks.rollup_incremental")
def rollup_incremental(self) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Recompute the trailing 6 closed hours for every organization (Doc 15 §8.1/§8.2).

    Recomputing a *window* rather than only the newest bucket is what absorbs late data: a delivery
    receipt for a 10:59 send can arrive at 11:05, and the retry engine can deliver hours later.

    Intended cadence: **every 15 minutes**, configured in the deployment's beat schedule.
    """
    try:
        return asyncio.run(_incremental())
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


@register_task(queue=ANALYTICS_ROLLUP, name="app.analytics.tasks.rollup_nightly")
def rollup_nightly(self) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Recompute the trailing 48 h, then fold hours into daily rows (Doc 15 §8.1, §21.4).

    The wider window catches anything later than the incremental pass absorbs — a webhook backlog
    drained after an outage, say. The daily consolidation is what lets hourly rows be pruned at 90
    days while long ranges stay answerable for ~26 months.

    Intended cadence: **daily at 02:15 UTC**, configured in the deployment's beat schedule.
    """
    try:
        return asyncio.run(_nightly())
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


@register_task(queue=ANALYTICS_ROLLUP, name="app.analytics.tasks.rollup_backfill")
def rollup_backfill(  # noqa: ANN001 - Celery bind
    self,
    start: str,
    end: str,
    organization_id: int | None = None,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """Recompute an explicit ISO range — the recovery path of Doc 15 §23.1.

    Safe at any overlap: delete-then-insert makes a re-run converge rather than double-count, so a
    backfill needs no cleanup before or after. Operator-triggered, not scheduled.
    """
    try:
        return asyncio.run(_backfill(start, end, organization_id, kinds))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


@register_task(queue=ANALYTICS_ROLLUP, name="app.analytics.tasks.rollup_prune")
def rollup_prune(self) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Drop rollup rows past retention: 90 days hourly, ~26 months daily (Doc 15 §21.3).

    Intended cadence: **daily at 03:00 UTC**, configured in the deployment's beat schedule.
    """
    try:
        return {"removed": asyncio.run(_prune())}
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise


async def _run_report_export(export_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        from app.services.export_service import ExportService

        job = await ExportService(session).run(export_id)
        return {"export_id": job.public_id, "rows": job.row_count, "status": job.status}


@register_task(queue=EXPORTS, name="app.analytics.tasks.run_report_export")
def run_report_export(self, export_id: str) -> dict[str, Any]:  # noqa: ANN001 - Celery bind
    """Generate an analytics report export (Doc 15 §19).

    Bound to the frozen ``exports`` queue and executed by the same ``ExportService.run`` that
    generates contact exports — entity dispatch inside the service decides which rows to stream.
    This is a task binding, not a second pipeline.
    """
    try:
        return asyncio.run(_run_report_export(export_id))
    except Exception as exc:  # noqa: BLE001 - classification decides retry vs terminal
        self.smart_retry(exc)
        raise
