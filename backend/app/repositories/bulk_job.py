"""Bulk job repository (Doc 03 §11.6 family; Doc 04 §30)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.job_records import BulkJob
from app.repositories.base import BaseRepository


class BulkJobRepository(BaseRepository[BulkJob]):
    model = BulkJob

    async def get_for_org(self, organization_id: int, public_id: bytes) -> BulkJob | None:
        stmt = select(BulkJob).where(
            BulkJob.organization_id == organization_id, BulkJob.uuid == public_id
        )
        return (await self.session.scalars(stmt)).first()
