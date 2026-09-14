"""Persistence queries for personal Analytics report schedules."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from sqlalchemy import func, select

from app.models.report_schedule import ReportSchedule
from app.repositories.base import BaseRepository


class ReportScheduleRepository(BaseRepository[ReportSchedule]):
    model = ReportSchedule

    async def list_for_owner(self, organization_id: int, owner_user_id: int) -> list[ReportSchedule]:
        stmt = (
            select(ReportSchedule)
            .where(
                ReportSchedule.organization_id == organization_id,
                ReportSchedule.owner_user_id == owner_user_id,
            )
            .order_by(ReportSchedule.created_at.desc(), ReportSchedule.id.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_for_owner(self, organization_id: int, owner_user_id: int) -> int:
        stmt = select(func.count()).select_from(ReportSchedule).where(
            ReportSchedule.organization_id == organization_id,
            ReportSchedule.owner_user_id == owner_user_id,
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def name_exists(
        self,
        organization_id: int,
        owner_user_id: int,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        stmt = select(ReportSchedule.id).where(
            ReportSchedule.organization_id == organization_id,
            ReportSchedule.owner_user_id == owner_user_id,
            func.lower(ReportSchedule.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(ReportSchedule.id != exclude_id)
        return (await self.session.scalar(stmt.limit(1))) is not None

    async def get_for_owner(
        self,
        organization_id: int,
        owner_user_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> ReportSchedule | None:
        stmt = select(ReportSchedule).where(
            ReportSchedule.organization_id == organization_id,
            ReportSchedule.owner_user_id == owner_user_id,
            ReportSchedule.uuid == public_id.bytes,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def due(self, now: datetime, *, limit: int) -> list[ReportSchedule]:
        stmt = (
            select(ReportSchedule)
            .where(
                ReportSchedule.is_active.is_(True),
                ReportSchedule.next_run_at.is_not(None),
                ReportSchedule.next_run_at <= now,
            )
            .order_by(ReportSchedule.next_run_at, ReportSchedule.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(stmt)).all())
