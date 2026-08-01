"""Tenant-scoped persistence for versioned automation definitions."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.automation import AutomationFlow, AutomationFlowVersion
from app.models.user import User
from app.repositories.base import BaseRepository


class AutomationRepository(BaseRepository[AutomationFlow]):
    model = AutomationFlow

    async def get_by_public_id(
        self, organization_id: int, public_id: bytes
    ) -> AutomationFlow | None:
        stmt = select(AutomationFlow).where(
            AutomationFlow.organization_id == organization_id,
            AutomationFlow.uuid == public_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_for_update(self, organization_id: int, public_id: bytes) -> AutomationFlow | None:
        stmt = (
            select(AutomationFlow)
            .where(
                AutomationFlow.organization_id == organization_id,
                AutomationFlow.uuid == public_id,
            )
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def list_flows(
        self,
        organization_id: int,
        *,
        q: str | None,
        statuses: list[str] | None,
        limit: int,
    ) -> tuple[list[AutomationFlow], int]:
        clauses = [AutomationFlow.organization_id == organization_id]
        if q:
            like = f"%{q.strip().lower()}%"
            clauses.append(func.lower(AutomationFlow.name).like(like))
        if statuses:
            clauses.append(AutomationFlow.status.in_(statuses))
        stmt = (
            select(AutomationFlow)
            .where(*clauses)
            .order_by(AutomationFlow.updated_at.desc(), AutomationFlow.id.desc())
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(AutomationFlow).where(*clauses)
        rows = list((await self.session.scalars(stmt)).all())
        total = int((await self.session.scalar(count_stmt)) or 0)
        return rows, total

    async def count_for_org(self, organization_id: int) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(AutomationFlow)
            .where(AutomationFlow.organization_id == organization_id)
        )
        return int(value or 0)

    async def next_version_no(self, flow_id: int) -> int:
        value = await self.session.scalar(
            select(func.max(AutomationFlowVersion.version_no)).where(
                AutomationFlowVersion.flow_id == flow_id
            )
        )
        return int(value or 0) + 1

    async def list_versions(self, flow_id: int) -> list[AutomationFlowVersion]:
        stmt = (
            select(AutomationFlowVersion)
            .where(AutomationFlowVersion.flow_id == flow_id)
            .order_by(AutomationFlowVersion.version_no.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_version(
        self, organization_id: int, flow_id: int, version_no: int
    ) -> AutomationFlowVersion | None:
        stmt = select(AutomationFlowVersion).where(
            AutomationFlowVersion.organization_id == organization_id,
            AutomationFlowVersion.flow_id == flow_id,
            AutomationFlowVersion.version_no == version_no,
        )
        return (await self.session.scalars(stmt)).first()

    async def users_by_id(self, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        rows = list((await self.session.scalars(select(User).where(User.id.in_(user_ids)))).all())
        return {row.id: row.public_id for row in rows}

    async def event_candidates(
        self, organization_id: int
    ) -> list[tuple[AutomationFlow, AutomationFlowVersion]]:
        """Return enabled, clean publications eligible for real event matching."""
        stmt = (
            select(AutomationFlow, AutomationFlowVersion)
            .join(
                AutomationFlowVersion,
                (AutomationFlowVersion.flow_id == AutomationFlow.id)
                & (AutomationFlowVersion.version_no == AutomationFlow.active_version_no),
            )
            .where(
                AutomationFlow.organization_id == organization_id,
                AutomationFlow.status == "published",
                AutomationFlow.active_version_no.is_not(None),
                AutomationFlow.active_content_hash == AutomationFlow.draft_content_hash,
            )
        )
        return list((await self.session.execute(stmt)).tuples().all())
