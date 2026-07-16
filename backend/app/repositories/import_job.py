"""Import job repository (Doc 03 §11.6)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.job_records import ImportJob
from app.repositories.base import BaseRepository


class ImportRepository(BaseRepository[ImportJob]):
    model = ImportJob

    async def get_for_org(self, organization_id: int, public_id: bytes) -> ImportJob | None:
        stmt = select(ImportJob).where(
            ImportJob.organization_id == organization_id, ImportJob.uuid == public_id
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_org(self, organization_id: int, limit: int = 50) -> list[ImportJob]:
        stmt = (
            select(ImportJob)
            .where(ImportJob.organization_id == organization_id)
            .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())
