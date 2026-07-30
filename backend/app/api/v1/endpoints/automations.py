"""Versioned automation-definition endpoints (Design Book 22, MD5 Phase 2A)."""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.automation import (
    AutomationCreateRequest,
    AutomationFlowResponse,
    AutomationListResponse,
    AutomationUpdateRequest,
    AutomationValidationResponse,
    AutomationVersionGuardRequest,
    AutomationVersionResponse,
    AutomationVersionsResponse,
)
from app.services.automation_service import AutomationService

router = APIRouter()

AutomationReader = Annotated[User, Depends(require_permissions("automations:read"))]
AutomationWriter = Annotated[User, Depends(require_permissions("automations:write"))]
AutomationPublisher = Annotated[User, Depends(require_permissions("automations:publish"))]
AutomationStatus = Literal["draft", "published", "disabled"]


@router.get(
    "/automations", response_model=AutomationListResponse, summary="List automations"
)
async def list_automations(
    session: SessionDep,
    actor: AutomationReader,
    q: Annotated[str | None, Query(max_length=120)] = None,
    flow_status: Annotated[list[AutomationStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AutomationListResponse:
    views, total = await AutomationService(session).list_flows(
        organization_id=actor.organization_id,
        q=q,
        statuses=list(flow_status) if flow_status else None,
        limit=limit,
    )
    return AutomationListResponse(
        data=[AutomationFlowResponse.of(view) for view in views], total=total
    )


@router.post(
    "/automations",
    response_model=AutomationFlowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an automation draft",
)
async def create_automation(
    payload: AutomationCreateRequest, session: SessionDep, actor: AutomationWriter
) -> AutomationFlowResponse:
    view = await AutomationService(session).create(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        description=payload.description,
        graph=payload.graph.model_dump(mode="json"),
    )
    return AutomationFlowResponse.of(view)


@router.get(
    "/automations/{automation_id}",
    response_model=AutomationFlowResponse,
    summary="Get an automation draft",
)
async def get_automation(
    automation_id: uuidlib.UUID, session: SessionDep, actor: AutomationReader
) -> AutomationFlowResponse:
    view = await AutomationService(session).get(
        organization_id=actor.organization_id, public_id=automation_id
    )
    return AutomationFlowResponse.of(view)


@router.patch(
    "/automations/{automation_id}",
    response_model=AutomationFlowResponse,
    summary="Update an automation draft",
)
async def update_automation(
    automation_id: uuidlib.UUID,
    payload: AutomationUpdateRequest,
    session: SessionDep,
    actor: AutomationWriter,
) -> AutomationFlowResponse:
    changes = payload.model_dump(
        mode="json", exclude_unset=True, exclude={"expected_row_version"}
    )
    view = await AutomationService(session).update(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=automation_id,
        changes=changes,
        expected_row_version=payload.expected_row_version,
    )
    return AutomationFlowResponse.of(view)


@router.post(
    "/automations/{automation_id}/validate",
    response_model=AutomationValidationResponse,
    summary="Validate an automation draft for publication",
)
async def validate_automation(
    automation_id: uuidlib.UUID, session: SessionDep, actor: AutomationReader
) -> AutomationValidationResponse:
    issues = await AutomationService(session).validate(
        organization_id=actor.organization_id, public_id=automation_id
    )
    return AutomationValidationResponse.of(issues)


@router.post(
    "/automations/{automation_id}/publish",
    response_model=AutomationFlowResponse,
    summary="Publish an immutable automation version",
)
async def publish_automation(
    automation_id: uuidlib.UUID,
    payload: AutomationVersionGuardRequest,
    session: SessionDep,
    actor: AutomationPublisher,
) -> AutomationFlowResponse:
    view = await AutomationService(session).publish(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=automation_id,
        expected_row_version=payload.expected_row_version,
    )
    return AutomationFlowResponse.of(view)


@router.get(
    "/automations/{automation_id}/versions",
    response_model=AutomationVersionsResponse,
    summary="List immutable automation versions",
)
async def list_automation_versions(
    automation_id: uuidlib.UUID, session: SessionDep, actor: AutomationReader
) -> AutomationVersionsResponse:
    views = await AutomationService(session).versions(
        organization_id=actor.organization_id, public_id=automation_id
    )
    return AutomationVersionsResponse(
        data=[AutomationVersionResponse.of(view) for view in views]
    )


@router.post(
    "/automations/{automation_id}/versions/{version_no}/restore",
    response_model=AutomationFlowResponse,
    summary="Restore an automation version to the draft",
)
async def restore_automation_version(
    automation_id: uuidlib.UUID,
    version_no: Annotated[int, Path(ge=1)],
    payload: AutomationVersionGuardRequest,
    session: SessionDep,
    actor: AutomationWriter,
) -> AutomationFlowResponse:
    view = await AutomationService(session).restore(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=automation_id,
        version_no=version_no,
        expected_row_version=payload.expected_row_version,
    )
    return AutomationFlowResponse.of(view)


@router.post(
    "/automations/{automation_id}/disable",
    response_model=AutomationFlowResponse,
    summary="Disable an automation",
)
async def disable_automation(
    automation_id: uuidlib.UUID,
    payload: AutomationVersionGuardRequest,
    session: SessionDep,
    actor: AutomationPublisher,
) -> AutomationFlowResponse:
    view = await AutomationService(session).disable(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=automation_id,
        expected_row_version=payload.expected_row_version,
    )
    return AutomationFlowResponse.of(view)


@router.post(
    "/automations/{automation_id}/enable",
    response_model=AutomationFlowResponse,
    summary="Enable an automation's active version",
)
async def enable_automation(
    automation_id: uuidlib.UUID,
    payload: AutomationVersionGuardRequest,
    session: SessionDep,
    actor: AutomationPublisher,
) -> AutomationFlowResponse:
    view = await AutomationService(session).enable(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=automation_id,
        expected_row_version=payload.expected_row_version,
    )
    return AutomationFlowResponse.of(view)
