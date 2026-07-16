"""Export job repository (Doc 03 §11.6)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.job_records import ExportJob
from app.repositories.base import BaseRepository


class ExportRepository(BaseRepository[ExportJob]):
    model = ExportJob

    async def get_for_org(self, organization_id: int, public_id: bytes) -> ExportJob | None:
        stmt = select(ExportJob).where(
            ExportJob.organization_id == organization_id, ExportJob.uuid == public_id
        )
        return (await self.session.scalars(stmt)).first()
