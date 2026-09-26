"""Export job repository (Doc 03 §11.6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.job_records import STATUS_EXPIRED, STATUS_READY, ExportJob
from app.repositories.base import BaseRepository


class ExportRepository(BaseRepository[ExportJob]):
    model = ExportJob

    async def get_for_org(self, organization_id: int, public_id: bytes) -> ExportJob | None:
        stmt = select(ExportJob).where(
            ExportJob.organization_id == organization_id, ExportJob.uuid == public_id
        )
        return (await self.session.scalars(stmt)).first()

    @staticmethod
    def _status_clause(status: str, now: datetime) -> ColumnElement[bool]:
        """Match the user-facing status, including lazily expired ready artifacts."""
        expired_ready = and_(
            ExportJob.status == STATUS_READY,
            ExportJob.expires_at.is_not(None),
            ExportJob.expires_at <= now,
        )
        if status == STATUS_EXPIRED:
            return or_(ExportJob.status == STATUS_EXPIRED, expired_ready)
        if status == STATUS_READY:
            return and_(
                ExportJob.status == STATUS_READY,
                or_(ExportJob.expires_at.is_(None), ExportJob.expires_at > now),
            )
        return ExportJob.status == status

    @staticmethod
    def _entity_clause(
        *, contacts: bool, reports: bool, transcripts: bool, campaigns: bool
    ) -> ColumnElement[bool]:
        clauses: list[ColumnElement[bool]] = []
        if contacts:
            clauses.append(ExportJob.entity == "contacts")
        if reports:
            clauses.append(ExportJob.entity.like("report:%"))
        if transcripts:
            clauses.append(ExportJob.entity == "conversation_transcript")
        if campaigns:
            clauses.append(ExportJob.entity == "campaign_results")
        # The service never calls this method without at least one allowed entity family.
        return or_(*clauses)

    def _download_filters(
        self,
        organization_id: int,
        requested_by: int,
        *,
        contacts: bool,
        reports: bool,
        transcripts: bool,
        campaigns: bool,
        status: str | None,
        now: datetime,
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [
            ExportJob.organization_id == organization_id,
            ExportJob.requested_by == requested_by,
            self._entity_clause(
                contacts=contacts,
                reports=reports,
                transcripts=transcripts,
                campaigns=campaigns,
            ),
        ]
        if status:
            clauses.append(self._status_clause(status, now))
        return clauses

    async def list_downloads(
        self,
        organization_id: int,
        requested_by: int,
        *,
        contacts: bool,
        reports: bool,
        transcripts: bool,
        campaigns: bool,
        status: str | None,
        now: datetime,
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> tuple[list[ExportJob], bool, int]:
        """Newest-first, keyset-paginated export history for one user in one tenant."""
        filters = self._download_filters(
            organization_id,
            requested_by,
            contacts=contacts,
            reports=reports,
            transcripts=transcripts,
            campaigns=campaigns,
            status=status,
            now=now,
        )
        page_filters = list(filters)
        if cursor:
            created_at, entity_id = cursor
            page_filters.append(
                or_(
                    ExportJob.created_at < created_at,
                    and_(ExportJob.created_at == created_at, ExportJob.id < entity_id),
                )
            )
        rows = list(
            (
                await self.session.scalars(
                    select(ExportJob)
                    .where(*page_filters)
                    .order_by(ExportJob.created_at.desc(), ExportJob.id.desc())
                    .limit(limit + 1)
                )
            ).all()
        )
        total = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(ExportJob).where(*filters)
                )
            )
            or 0
        )
        return rows[:limit], len(rows) > limit, total
