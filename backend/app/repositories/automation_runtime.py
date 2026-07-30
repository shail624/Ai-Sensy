"""Persistence helpers for deterministic automation test runs (Design Book 23)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.automation import (
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SUCCEEDED,
    AutomationFlowVersion,
    AutomationRun,
    AutomationStepAttempt,
)
from app.repositories.base import BaseRepository


class AutomationRunRepository(BaseRepository[AutomationRun]):
    model = AutomationRun

    async def by_idempotency_key(
        self, organization_id: int, key: bytes
    ) -> AutomationRun | None:
        stmt = select(AutomationRun).where(
            AutomationRun.organization_id == organization_id,
            AutomationRun.idempotency_key == key,
        )
        return (await self.session.scalars(stmt)).first()

    async def by_public_id(
        self, organization_id: int, public_id: bytes
    ) -> AutomationRun | None:
        stmt = select(AutomationRun).where(
            AutomationRun.organization_id == organization_id,
            AutomationRun.uuid == public_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def by_pk(self, run_id: int, *, for_update: bool = False) -> AutomationRun | None:
        stmt = select(AutomationRun).where(AutomationRun.id == run_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def list_for_flow(
        self, organization_id: int, flow_id: int, *, limit: int
    ) -> list[AutomationRun]:
        stmt = (
            select(AutomationRun)
            .where(
                AutomationRun.organization_id == organization_id,
                AutomationRun.flow_id == flow_id,
            )
            .order_by(AutomationRun.created_at.desc(), AutomationRun.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def version(self, version_id: int) -> AutomationFlowVersion | None:
        return await self.session.get(AutomationFlowVersion, version_id)


class AutomationAttemptRepository(BaseRepository[AutomationStepAttempt]):
    model = AutomationStepAttempt

    async def for_run(self, run_id: int) -> list[AutomationStepAttempt]:
        stmt = (
            select(AutomationStepAttempt)
            .where(AutomationStepAttempt.run_id == run_id)
            .order_by(
                AutomationStepAttempt.started_at.asc(), AutomationStepAttempt.id.asc()
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def successful_node_ids(self, run_id: int) -> set[str]:
        stmt = select(AutomationStepAttempt.node_id).where(
            AutomationStepAttempt.run_id == run_id,
            AutomationStepAttempt.status == AUTOMATION_ATTEMPT_SUCCEEDED,
        )
        return set((await self.session.scalars(stmt)).all())

    async def running(self, run_id: int) -> list[AutomationStepAttempt]:
        stmt = select(AutomationStepAttempt).where(
            AutomationStepAttempt.run_id == run_id,
            AutomationStepAttempt.status == AUTOMATION_ATTEMPT_RUNNING,
        )
        return list((await self.session.scalars(stmt)).all())

    async def next_attempt_no(self, run_id: int, node_id: str) -> int:
        stmt = select(func.max(AutomationStepAttempt.attempt_no)).where(
            AutomationStepAttempt.run_id == run_id,
            AutomationStepAttempt.node_id == node_id,
        )
        return int((await self.session.scalar(stmt)) or 0) + 1
