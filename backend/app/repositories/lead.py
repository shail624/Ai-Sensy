"""Lead pipeline & stage repositories (Doc 07 §23.2)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.lead import LeadPipeline, LeadStage
from app.repositories.base import BaseRepository


class LeadPipelineRepository(BaseRepository[LeadPipeline]):
    model = LeadPipeline

    async def list_for_org(self, organization_id: int) -> list[LeadPipeline]:
        stmt = (
            select(LeadPipeline)
            .where(
                LeadPipeline.organization_id == organization_id,
                LeadPipeline.deleted_at.is_(None),
            )
            .order_by(LeadPipeline.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> LeadPipeline | None:
        stmt = select(LeadPipeline).where(
            LeadPipeline.organization_id == organization_id,
            LeadPipeline.uuid == public_id,
            LeadPipeline.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_name(self, organization_id: int, name: str) -> LeadPipeline | None:
        stmt = select(LeadPipeline).where(
            LeadPipeline.organization_id == organization_id,
            LeadPipeline.name == name,
            LeadPipeline.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_default(self, organization_id: int) -> LeadPipeline | None:
        stmt = select(LeadPipeline).where(
            LeadPipeline.organization_id == organization_id,
            LeadPipeline.is_default.is_(True),
            LeadPipeline.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def clear_default(self, organization_id: int) -> None:
        for pipeline in await self.list_for_org(organization_id):
            pipeline.is_default = False
        await self.session.flush()


class LeadStageRepository(BaseRepository[LeadStage]):
    model = LeadStage

    async def list_for_pipeline(self, pipeline_id: int) -> list[LeadStage]:
        stmt = (
            select(LeadStage)
            .where(LeadStage.pipeline_id == pipeline_id, LeadStage.deleted_at.is_(None))
            .order_by(LeadStage.position, LeadStage.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(self, public_id: bytes) -> LeadStage | None:
        stmt = select(LeadStage).where(
            LeadStage.uuid == public_id, LeadStage.deleted_at.is_(None)
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_name(self, pipeline_id: int, name: str) -> LeadStage | None:
        stmt = select(LeadStage).where(
            LeadStage.pipeline_id == pipeline_id,
            LeadStage.name == name,
            LeadStage.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def next_position(self, pipeline_id: int) -> int:
        stmt = select(func.max(LeadStage.position)).where(
            LeadStage.pipeline_id == pipeline_id, LeadStage.deleted_at.is_(None)
        )
        current = await self.session.scalar(stmt)
        return 0 if current is None else int(current) + 1
