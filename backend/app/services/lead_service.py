"""Lead pipeline & stage service (Doc 07 §19, §23.2).

Manages pipeline/stage **configuration**: create/rename/archive pipelines, add/rename/
reorder/archive stages. Exactly one pipeline per organization is the default. Deleting a
stage or pipeline is a soft delete (archive, Doc 07 §19.2). Every change is audited.

Attaching a stage to a lead is per-conversation (``conversation_lead``) and belongs to the
Inbox/Messaging module — not implemented here.
"""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.mixins import utcnow
from app.models.lead import LeadPipeline, LeadStage
from app.models.user import User
from app.repositories.lead import LeadPipelineRepository, LeadStageRepository
from app.services.audit_service import AuditAction, AuditService


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pipelines = LeadPipelineRepository(session)
        self._stages = LeadStageRepository(session)
        self._audit = AuditService(session)

    # --- Pipelines -----------------------------------------------------------
    async def list_pipelines(self, organization_id: int) -> list[LeadPipeline]:
        return await self._pipelines.list_for_org(organization_id)

    async def get_pipeline(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> LeadPipeline:
        pipeline = await self._pipelines.get_active_by_uuid(organization_id, public_id.bytes)
        if pipeline is None:
            raise NotFoundError("Pipeline not found.")
        return pipeline

    async def create_pipeline(
        self, *, organization_id: int, actor: User, name: str, is_default: bool
    ) -> LeadPipeline:
        if await self._pipelines.get_by_name(organization_id, name) is not None:
            raise ConflictError(f"A pipeline named {name!r} already exists.")
        if is_default:
            await self._pipelines.clear_default(organization_id)
        pipeline = LeadPipeline(
            organization_id=organization_id, name=name, is_default=is_default
        )
        await self._pipelines.add(pipeline)
        await self._audit.record(
            AuditAction.LEAD_PIPELINE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_pipeline",
            entity_id=pipeline.id,
            after={"name": name, "is_default": is_default},
        )
        await self._session.commit()
        await self._session.refresh(pipeline, ["stages"])
        return pipeline

    async def update_pipeline(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        name: str | None,
        is_default: bool | None,
    ) -> LeadPipeline:
        pipeline = await self.get_pipeline(organization_id, public_id)
        before = {"name": pipeline.name, "is_default": pipeline.is_default}
        if name is not None and name != pipeline.name:
            if await self._pipelines.get_by_name(organization_id, name) is not None:
                raise ConflictError(f"A pipeline named {name!r} already exists.")
            pipeline.name = name
        if is_default:
            await self._pipelines.clear_default(organization_id)
            pipeline.is_default = True
        await self._pipelines.flush()
        await self._audit.record(
            AuditAction.LEAD_PIPELINE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_pipeline",
            entity_id=pipeline.id,
            before=before,
            after={"name": pipeline.name, "is_default": pipeline.is_default},
        )
        await self._session.commit()
        return pipeline

    async def delete_pipeline(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        pipeline = await self.get_pipeline(organization_id, public_id)
        if pipeline.is_default:
            raise ConflictError("The default pipeline cannot be deleted.")
        now = utcnow()
        for stage in await self._stages.list_for_pipeline(pipeline.id):
            stage.deleted_at = now
        pipeline.deleted_at = now
        await self._pipelines.flush()
        await self._audit.record(
            AuditAction.LEAD_PIPELINE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_pipeline",
            entity_id=pipeline.id,
            before={"name": pipeline.name},
        )
        await self._session.commit()

    # --- Stages --------------------------------------------------------------
    async def _place_stage(self, pipeline_id: int, stage: LeadStage, target: int) -> None:
        """Move ``stage`` to ``target`` index and re-index siblings densely (0..n-1).

        Drag-and-drop ordering (Doc 07 §19.2): a move shifts the other stages rather than
        leaving duplicate positions whose order would depend on insertion id.
        """
        siblings = [
            s for s in await self._stages.list_for_pipeline(pipeline_id) if s.id != stage.id
        ]
        index = max(0, min(target, len(siblings)))
        siblings.insert(index, stage)
        for position, item in enumerate(siblings):
            item.position = position
        await self._stages.flush()

    async def get_stage(self, organization_id: int, public_id: uuidlib.UUID) -> LeadStage:
        stage = await self._stages.get_active_by_uuid(public_id.bytes)
        if stage is None:
            raise NotFoundError("Stage not found.")
        # Enforce org scoping through the parent pipeline.
        pipeline = await self._pipelines.get_by_id(stage.pipeline_id)
        if pipeline is None or pipeline.organization_id != organization_id:
            raise NotFoundError("Stage not found.")
        return stage

    async def add_stage(
        self,
        *,
        organization_id: int,
        actor: User,
        pipeline_uuid: uuidlib.UUID,
        name: str,
        is_terminal: bool,
        position: int | None,
    ) -> LeadStage:
        pipeline = await self.get_pipeline(organization_id, pipeline_uuid)
        if await self._stages.get_by_name(pipeline.id, name) is not None:
            raise ConflictError(f"A stage named {name!r} already exists in this pipeline.")
        stage = LeadStage(
            pipeline_id=pipeline.id,
            name=name,
            is_terminal=is_terminal,
            position=await self._stages.next_position(pipeline.id),
        )
        await self._stages.add(stage)
        if position is not None:
            await self._place_stage(pipeline.id, stage, position)
        await self._audit.record(
            AuditAction.LEAD_STAGE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_stage",
            entity_id=stage.id,
            after={"name": name, "position": stage.position, "pipeline": pipeline.name},
        )
        await self._session.commit()
        return stage

    async def update_stage(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        name: str | None,
        position: int | None,
        is_terminal: bool | None,
    ) -> LeadStage:
        stage = await self.get_stage(organization_id, public_id)
        before = {"name": stage.name, "position": stage.position}
        if name is not None and name != stage.name:
            if await self._stages.get_by_name(stage.pipeline_id, name) is not None:
                raise ConflictError(f"A stage named {name!r} already exists in this pipeline.")
            stage.name = name
        if is_terminal is not None:
            stage.is_terminal = is_terminal
        if position is not None and position != stage.position:
            await self._place_stage(stage.pipeline_id, stage, position)
        await self._stages.flush()
        await self._audit.record(
            AuditAction.LEAD_STAGE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_stage",
            entity_id=stage.id,
            before=before,
            after={"name": stage.name, "position": stage.position},
        )
        await self._session.commit()
        return stage

    async def delete_stage(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        stage = await self.get_stage(organization_id, public_id)
        stage.deleted_at = utcnow()
        await self._stages.flush()
        await self._audit.record(
            AuditAction.LEAD_STAGE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="lead_stage",
            entity_id=stage.id,
            before={"name": stage.name},
        )
        await self._session.commit()
