"""Lifecycle and heartbeat scanner for automatic Analytics report exports."""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError, VersionConflictError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM
from app.models.report_schedule import ReportSchedule
from app.models.user import User
from app.repositories.report_schedule import ReportScheduleRepository
from app.repositories.user import UserRepository
from app.schemas.analytics import ReportScheduleCreate, ReportScheduleUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.campaign_schedule_service import load_timezone, next_fire
from app.services.export_service import ExportService
from app.services.rbac_service import RBACService

MAX_REPORT_SCHEDULES_PER_USER = 25
_REQUIRED_PERMISSIONS = {"analytics:export", "analytics:executive"}
_WEEKDAY_NUMBER = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}


class ReportScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportScheduleRepository(session)
        self._users = UserRepository(session)
        self._rbac = RBACService(session)
        self._audit = AuditService(session)

    async def list(self, actor: User) -> list[ReportSchedule]:
        return await self._repo.list_for_owner(actor.organization_id, actor.id)

    async def create(self, actor: User, payload: ReportScheduleCreate) -> ReportSchedule:
        await self._lock_owner(actor)
        if await self._repo.count_for_owner(actor.organization_id, actor.id) >= MAX_REPORT_SCHEDULES_PER_USER:
            raise ValidationError(
                f"A user can save at most {MAX_REPORT_SCHEDULES_PER_USER} report schedules."
            )
        if await self._repo.name_exists(actor.organization_id, actor.id, payload.name):
            raise ConflictError(f"A report schedule named {payload.name!r} already exists.")
        load_timezone(payload.timezone)
        row = ReportSchedule(
            organization_id=actor.organization_id,
            owner_user_id=actor.id,
            **self._definition(payload),
        )
        row.next_run_at = self._next(row, after=utcnow()) if row.is_active else None
        await self._repo.add(row)
        await self._audit.record(
            AuditAction.REPORT_SCHEDULE_CREATED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="report_schedule",
            entity_id=row.id,
            after=self._snapshot(row),
        )
        await self._session.commit()
        return row

    async def update(
        self, actor: User, public_id: uuidlib.UUID, payload: ReportScheduleUpdate
    ) -> ReportSchedule:
        await self._lock_owner(actor)
        row = await self._owned(actor, public_id, for_update=True)
        if row.row_version != payload.expected_row_version:
            raise VersionConflictError(
                f"The schedule changed after you loaded it (expected version "
                f"{payload.expected_row_version}, current {row.row_version})."
            )
        if await self._repo.name_exists(
            actor.organization_id, actor.id, payload.name, exclude_id=row.id
        ):
            raise ConflictError(f"A report schedule named {payload.name!r} already exists.")
        load_timezone(payload.timezone)
        before = self._snapshot(row)
        for field, value in self._definition(payload).items():
            setattr(row, field, value)
        row.next_run_at = self._next(row, after=utcnow()) if row.is_active else None
        row.row_version += 1
        await self._repo.flush()
        await self._audit.record(
            AuditAction.REPORT_SCHEDULE_UPDATED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="report_schedule",
            entity_id=row.id,
            before=before,
            after=self._snapshot(row),
        )
        await self._session.commit()
        return row

    async def delete(
        self, actor: User, public_id: uuidlib.UUID, *, expected_row_version: int
    ) -> None:
        row = await self._owned(actor, public_id, for_update=True)
        if row.row_version != expected_row_version:
            raise VersionConflictError(
                f"The schedule changed after you loaded it (expected version "
                f"{expected_row_version}, current {row.row_version})."
            )
        before = self._snapshot(row)
        row_id = row.id
        await self._repo.delete(row)
        await self._audit.record(
            AuditAction.REPORT_SCHEDULE_DELETED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="report_schedule",
            entity_id=row_id,
            before=before,
        )
        await self._session.commit()

    async def tick(
        self,
        *,
        dispatch: Callable[[str, str], Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Claim and enqueue due rows one at a time, using ``SKIP LOCKED`` across tick replicas."""
        now = now or utcnow()
        fired: list[str] = []
        disabled: list[str] = []
        scanned = 0
        while scanned < settings.scheduler_tick_scan_limit:
            due = await self._repo.due(now, limit=1)
            if not due:
                break
            row = due[0]
            scanned += 1
            schedule_id = row.public_id
            owner = await self._users.get_by_id(row.owner_user_id)
            permitted = bool(
                owner
                and owner.organization_id == row.organization_id
                and owner.deleted_at is None
                and owner.is_active
                and await self._rbac.has_permissions(owner, _REQUIRED_PERMISSIONS)
            )
            if not permitted or owner is None:
                row.is_active = False
                row.next_run_at = None
                row.row_version += 1
                await self._audit.record(
                    AuditAction.REPORT_SCHEDULE_DISABLED,
                    actor_type=ACTOR_SYSTEM,
                    organization_id=row.organization_id,
                    entity_type="report_schedule",
                    entity_id=row.id,
                    after={"reason": "owner_inactive_or_permission_revoked"},
                )
                await self._session.commit()
                disabled.append(schedule_id)
                continue

            slot = row.next_run_at or now
            row.last_run_at = now
            row.next_run_at = self._next(row, after=now)
            row.is_active = row.next_run_at is not None
            row.row_version += 1
            await self._audit.record(
                AuditAction.REPORT_SCHEDULE_FIRED,
                actor_type=ACTOR_SYSTEM,
                organization_id=row.organization_id,
                entity_type="report_schedule",
                entity_id=row.id,
                after={"scheduled_for": slot.isoformat(), "next_run_at": row.next_run_at.isoformat()},
            )
            job = await ExportService(self._session).start_report(
                organization_id=row.organization_id,
                actor=owner,
                report=row.report,
                file_format=row.format,
                filters={
                    "preset": row.preset,
                    "granularity": row.granularity,
                    "timezone": row.timezone,
                    "_report_schedule_id": schedule_id,
                    "_report_schedule_name": row.name,
                    "_scheduled_for": slot.isoformat(),
                },
                dispatch=dispatch,
            )
            fired.append(job.public_id)
        return {"scanned": scanned, "fired": fired, "disabled": disabled}

    async def _owned(
        self, actor: User, public_id: uuidlib.UUID, *, for_update: bool = False
    ) -> ReportSchedule:
        row = await self._repo.get_for_owner(
            actor.organization_id, actor.id, public_id, for_update=for_update
        )
        if row is None:
            raise NotFoundError("Report schedule not found.")
        return row

    async def _lock_owner(self, actor: User) -> None:
        """Serialize per-user create/rename decisions so limits and names are race-safe."""
        await self._session.execute(
            select(User.id)
            .where(User.id == actor.id, User.organization_id == actor.organization_id)
            .with_for_update()
        )

    @staticmethod
    def _definition(payload: ReportScheduleCreate | ReportScheduleUpdate) -> dict[str, Any]:
        return payload.model_dump(exclude={"expected_row_version"})

    @staticmethod
    def _cron(row: ReportSchedule) -> str:
        hour, minute = (int(value) for value in row.local_time.split(":"))
        if row.cadence == "daily":
            return f"{minute} {hour} * * *"
        if row.cadence == "weekly":
            return f"{minute} {hour} * * {_WEEKDAY_NUMBER[row.weekday or 'monday']}"
        return f"{minute} {hour} {row.month_day or 1} * *"

    @classmethod
    def _next(cls, row: ReportSchedule, *, after: datetime) -> datetime:
        upcoming = next_fire(cls._cron(row), after=after, timezone=row.timezone)
        if upcoming is None:  # monthly days are capped at 28, so this is defensive only.
            raise ValidationError("The report schedule cannot produce a future occurrence.")
        return upcoming

    @staticmethod
    def _snapshot(row: ReportSchedule) -> dict[str, Any]:
        return {
            "name": row.name,
            "report": row.report,
            "format": row.format,
            "preset": row.preset,
            "granularity": row.granularity,
            "cadence": row.cadence,
            "timezone": row.timezone,
            "local_time": row.local_time,
            "weekday": row.weekday,
            "month_day": row.month_day,
            "is_active": row.is_active,
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        }
