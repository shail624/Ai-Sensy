"""Lead pipeline & stage configuration endpoints (Doc 07 §19, §23.2).

Doc 04 predates Doc 07's additive lead model, so these routes follow Doc 04's conventions and
reuse the seeded CRM permissions: reads require ``contacts:read``, writes ``contacts:write``
(leads are CRM services per Doc 07 §3/§4.1, alongside tags which Doc 04 §14.2 gates the same
way). Owner superuser bypasses. Pipelines/stages are configuration only — attaching a stage to
a lead is per-conversation and belongs to the Inbox/Messaging module.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.lead import (
    LeadPipelineCreateRequest,
    LeadPipelineResponse,
    LeadPipelineUpdateRequest,
    LeadStageCreateRequest,
    LeadStageResponse,
    LeadStageUpdateRequest,
)
from app.services.lead_service import LeadService

router = APIRouter()

LeadsReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
LeadsWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]


@router.get(
    "/lead-pipelines",
    response_model=list[LeadPipelineResponse],
    summary="List lead pipelines (with stages)",
)
async def list_pipelines(session: SessionDep, actor: LeadsReadActor) -> list[LeadPipelineResponse]:
    pipelines = await LeadService(session).list_pipelines(actor.organization_id)
    return [LeadPipelineResponse.from_pipeline(p) for p in pipelines]


@router.post(
    "/lead-pipelines",
    response_model=LeadPipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lead pipeline",
)
async def create_pipeline(
    payload: LeadPipelineCreateRequest, session: SessionDep, actor: LeadsWriteActor
) -> LeadPipelineResponse:
    pipeline = await LeadService(session).create_pipeline(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        is_default=payload.is_default,
    )
    return LeadPipelineResponse.from_pipeline(pipeline)


@router.get(
    "/lead-pipelines/{pipeline_id}",
    response_model=LeadPipelineResponse,
    summary="Get a lead pipeline",
)
async def get_pipeline(
    pipeline_id: uuidlib.UUID, session: SessionDep, actor: LeadsReadActor
) -> LeadPipelineResponse:
    pipeline = await LeadService(session).get_pipeline(actor.organization_id, pipeline_id)
    return LeadPipelineResponse.from_pipeline(pipeline)


@router.patch(
    "/lead-pipelines/{pipeline_id}",
    response_model=LeadPipelineResponse,
    summary="Rename a pipeline / set default",
)
async def update_pipeline(
    pipeline_id: uuidlib.UUID,
    payload: LeadPipelineUpdateRequest,
    session: SessionDep,
    actor: LeadsWriteActor,
) -> LeadPipelineResponse:
    pipeline = await LeadService(session).update_pipeline(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=pipeline_id,
        name=payload.name,
        is_default=payload.is_default,
    )
    return LeadPipelineResponse.from_pipeline(pipeline)


@router.delete(
    "/lead-pipelines/{pipeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a pipeline (not the default)",
)
async def delete_pipeline(
    pipeline_id: uuidlib.UUID, session: SessionDep, actor: LeadsWriteActor
) -> None:
    await LeadService(session).delete_pipeline(
        organization_id=actor.organization_id, actor=actor, public_id=pipeline_id
    )


@router.post(
    "/lead-pipelines/{pipeline_id}/stages",
    response_model=LeadStageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a stage to a pipeline",
)
async def add_stage(
    pipeline_id: uuidlib.UUID,
    payload: LeadStageCreateRequest,
    session: SessionDep,
    actor: LeadsWriteActor,
) -> LeadStageResponse:
    stage = await LeadService(session).add_stage(
        organization_id=actor.organization_id,
        actor=actor,
        pipeline_uuid=pipeline_id,
        name=payload.name,
        is_terminal=payload.is_terminal,
        position=payload.position,
    )
    return LeadStageResponse.from_stage(stage)


@router.patch(
    "/lead-stages/{stage_id}",
    response_model=LeadStageResponse,
    summary="Rename / reorder a stage",
)
async def update_stage(
    stage_id: uuidlib.UUID,
    payload: LeadStageUpdateRequest,
    session: SessionDep,
    actor: LeadsWriteActor,
) -> LeadStageResponse:
    stage = await LeadService(session).update_stage(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=stage_id,
        name=payload.name,
        position=payload.position,
        is_terminal=payload.is_terminal,
    )
    return LeadStageResponse.from_stage(stage)


@router.delete(
    "/lead-stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a stage",
)
async def delete_stage(
    stage_id: uuidlib.UUID, session: SessionDep, actor: LeadsWriteActor
) -> None:
    await LeadService(session).delete_stage(
        organization_id=actor.organization_id, actor=actor, public_id=stage_id
    )
