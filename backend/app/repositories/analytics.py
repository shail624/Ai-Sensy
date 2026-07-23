"""Analytics rollup repository (Doc 15 §9) — persistence only, no business rules.

Owns the two persistence primitives the rollup pipeline needs: the **bucket replacement** of
Doc 15 §6.3 (delete a bucket's rows so the service can re-insert them) and the **watermark**
accessors of §9.7. The aggregate *read* queries (grain planning, range scans, dimension grouping)
attach here in A6 with the query service, so persistence stays out of both services per the
platform's Repository→Service→API layering.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from app.models.analytics import AnalyticsRollupRun
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[AnalyticsRollupRun]):
    """Reads and writes the rollup fact tables and their watermark control rows."""

    model = AnalyticsRollupRun

    async def clear_bucket(
        self, fact_model: type, organization_id: int, grain: str, bucket_start: datetime
    ) -> int:
        """Delete one bucket's rows so the service can re-insert them (Doc 15 §6.3).

        Deleting rather than upserting is what makes a dimension combination that disappeared from
        the recomputed bucket disappear from the table too — an UPSERT would leave it behind.
        """
        result = await self.session.execute(
            delete(fact_model).where(
                fact_model.organization_id == organization_id,
                fact_model.grain == grain,
                fact_model.bucket_start == bucket_start,
            )
        )
        return result.rowcount or 0

    async def prune_before(self, fact_model: type, grain: str, cutoff: datetime) -> int:
        """Drop rows older than ``cutoff`` at one grain (Doc 15 §21.3 retention)."""
        result = await self.session.execute(
            delete(fact_model).where(
                fact_model.grain == grain, fact_model.bucket_start < cutoff
            )
        )
        return result.rowcount or 0

    async def fetch_range(
        self,
        fact_model: type,
        organization_id: int,
        grain: str,
        start: datetime,
        end: datetime,
    ) -> list:
        """One fact table's rows for ``[start, end)`` at one grain, oldest first.

        The single read primitive behind every analytics query: the service folds these UTC buckets
        into the caller's local periods (Doc 15 §10). Reads never touch a partitioned operational
        table, which is what makes the §22 latency targets reachable.
        """
        stmt = (
            select(fact_model)
            .where(
                fact_model.organization_id == organization_id,
                fact_model.grain == grain,
                fact_model.bucket_start >= start,
                fact_model.bucket_start < end,
            )
            .order_by(fact_model.bucket_start)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_run(self, organization_id: int, kind: str) -> AnalyticsRollupRun | None:
        """The watermark row for one organization and rollup kind (Doc 15 §9.7)."""
        stmt = select(AnalyticsRollupRun).where(
            AnalyticsRollupRun.organization_id == organization_id,
            AnalyticsRollupRun.kind == kind,
        )
        return (await self.session.scalars(stmt)).first()

    async def upsert_run(self, organization_id: int, kind: str) -> AnalyticsRollupRun:
        """Fetch the watermark row, creating it on first use."""
        run = await self.get_run(organization_id, kind)
        if run is None:
            run = AnalyticsRollupRun(organization_id=organization_id, kind=kind)
            await self.add(run)
        return run

    async def runs_for(self, organization_id: int) -> list[AnalyticsRollupRun]:
        """Every watermark for one organization — the source of ``GET /analytics/freshness``."""
        stmt = (
            select(AnalyticsRollupRun)
            .where(AnalyticsRollupRun.organization_id == organization_id)
            .order_by(AnalyticsRollupRun.kind)
        )
        return list((await self.session.scalars(stmt)).all())
