"""M13-02 identity resolution and restricted manual-review endpoints."""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.identity.domain import IdentityConflictStatus
from app.models.user import User
from app.schemas.contact_identity import (
    ContactIdentityResponse,
    IdentityConflictPage,
    IdentityConflictResponse,
    IdentityMergeRecommendationCreateRequest,
    IdentityMergeRecommendationResponse,
    IdentityRecommendationDecisionRequest,
    IdentityResolutionRequest,
    IdentityResolutionResponse,
)
from app.services.identity_resolution_service import IdentityResolutionService

router = APIRouter()

IdentityReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
IdentityWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]


@router.post(
    "/identity-resolution/resolve",
    response_model=IdentityResolutionResponse,
    summary="Resolve exact provider/endpoint identities to one canonical Contact",
)
async def resolve_identity(
    payload: IdentityResolutionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityResolutionResponse:
    result = await IdentityResolutionService(session).resolve(
        organization_id=actor.organization_id,
        actor=actor,
        assertions=[assertion.to_domain() for assertion in payload.assertions],
        contact_hint=payload.contact_id,
        new_contact_fields=(
            payload.new_contact.model_dump(exclude_none=True) if payload.new_contact else None
        ),
    )
    return IdentityResolutionResponse.from_result(result)


@router.get(
    "/contacts/{contact_id}/identities",
    response_model=list[ContactIdentityResponse],
    summary="List immutable exact identities linked to a canonical Contact",
)
async def list_contact_identities(
    contact_id: uuidlib.UUID,
    session: SessionDep,
    actor: IdentityReadActor,
) -> list[ContactIdentityResponse]:
    contact, rows = await IdentityResolutionService(session).list_contact_identities(
        actor.organization_id, contact_id
    )
    return [ContactIdentityResponse.from_model(row, contact.public_id) for row in rows]


@router.get(
    "/identity-conflicts",
    response_model=IdentityConflictPage,
    summary="List the tenant-scoped manual identity review queue",
)
async def list_identity_conflicts(
    session: SessionDep,
    actor: IdentityReadActor,
    conflict_status: Annotated[IdentityConflictStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IdentityConflictPage:
    views, total = await IdentityResolutionService(session).list_conflicts(
        actor.organization_id,
        status=conflict_status,
        limit=limit,
        offset=offset,
    )
    return IdentityConflictPage(
        data=[IdentityConflictResponse.from_view(view) for view in views],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/identity-conflicts/{conflict_id}",
    response_model=IdentityConflictResponse,
    summary="Get one identity conflict and its recommendation history",
)
async def get_identity_conflict(
    conflict_id: uuidlib.UUID,
    session: SessionDep,
    actor: IdentityReadActor,
) -> IdentityConflictResponse:
    view = await IdentityResolutionService(session).get_conflict(actor.organization_id, conflict_id)
    return IdentityConflictResponse.from_view(view)


@router.post(
    "/identity-conflicts/{conflict_id}/recommendations",
    response_model=IdentityMergeRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a non-destructive operator merge recommendation",
)
async def create_identity_recommendation(
    conflict_id: uuidlib.UUID,
    payload: IdentityMergeRecommendationCreateRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    view = await IdentityResolutionService(session).recommend_merge(
        organization_id=actor.organization_id,
        actor=actor,
        conflict_id=conflict_id,
        primary_contact_id=payload.primary_contact_id,
        duplicate_contact_id=payload.duplicate_contact_id,
        confidence=payload.confidence,
        reason=payload.reason,
    )
    return IdentityMergeRecommendationResponse.from_view(view)


@router.post(
    "/identity-merge-recommendations/{recommendation_id}/approve",
    response_model=IdentityMergeRecommendationResponse,
    summary="Approve a recommendation without merging or moving identities",
)
async def approve_identity_recommendation(
    recommendation_id: uuidlib.UUID,
    payload: IdentityRecommendationDecisionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    service = IdentityResolutionService(session)
    view = await service.decide_recommendation(
        organization_id=actor.organization_id,
        actor=actor,
        recommendation_id=recommendation_id,
        approve=True,
        expected_version=payload.row_version,
        note=payload.note,
    )
    return IdentityMergeRecommendationResponse.from_view(view)


@router.post(
    "/identity-merge-recommendations/{recommendation_id}/reject",
    response_model=IdentityMergeRecommendationResponse,
    summary="Reject a recommendation without merging or moving identities",
)
async def reject_identity_recommendation(
    recommendation_id: uuidlib.UUID,
    payload: IdentityRecommendationDecisionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    service = IdentityResolutionService(session)
    view = await service.decide_recommendation(
        organization_id=actor.organization_id,
        actor=actor,
        recommendation_id=recommendation_id,
        approve=False,
        expected_version=payload.row_version,
        note=payload.note,
    )
    return IdentityMergeRecommendationResponse.from_view(view)
