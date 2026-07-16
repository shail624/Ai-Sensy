"""Segment endpoints (Doc 04 §14.3) — saved dynamic contact filters (FR-CON-10).

Reads require ``segments:read``; writes require ``segments:write`` (Owner superuser bypasses).
``/segments/{id}/refresh`` recomputes the cached count and follows Doc 04 §14.3, which gates it
with ``segments:read``. Segments are organization-scoped.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.models.user import User
from app.schemas.contact import ContactResponse
from app.schemas.segment import (
    SegmentContactsPage,
    SegmentCreateRequest,
    SegmentResponse,
    SegmentUpdateRequest,
)
from app.services.segment_service import SegmentService

router = APIRouter()

SegmentsReadActor = Annotated[User, Depends(require_permissions("segments:read"))]
SegmentsWriteActor = Annotated[User, Depends(require_permissions("segments:write"))]


@router.get(
    "/segments", response_model=list[SegmentResponse], summary="List segments (+cached counts)"
)
async def list_segments(session: SessionDep, actor: SegmentsReadActor) -> list[SegmentResponse]:
    segments = await SegmentService(session).list_segments(actor.organization_id)
    return [SegmentResponse.from_segment(s) for s in segments]


@router.post(
    "/segments",
    response_model=SegmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a segment (with rules)",
)
async def create_segment(
    payload: SegmentCreateRequest, session: SessionDep, actor: SegmentsWriteActor
) -> SegmentResponse:
    segment = await SegmentService(session).create_segment(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        description=payload.description,
        match_type=payload.match_type,
        rules=[r.model_dump() for r in payload.rules],
    )
    return SegmentResponse.from_segment(segment)


@router.get(
    "/segments/{segment_id}", response_model=SegmentResponse, summary="Get a segment + rules"
)
async def get_segment(
    segment_id: uuidlib.UUID, session: SessionDep, actor: SegmentsReadActor
) -> SegmentResponse:
    segment = await SegmentService(session).get_segment(actor.organization_id, segment_id)
    return SegmentResponse.from_segment(segment)


@router.patch(
    "/segments/{segment_id}", response_model=SegmentResponse, summary="Update rules / name"
)
async def update_segment(
    segment_id: uuidlib.UUID,
    payload: SegmentUpdateRequest,
    session: SessionDep,
    actor: SegmentsWriteActor,
) -> SegmentResponse:
    segment = await SegmentService(session).update_segment(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=segment_id,
        name=payload.name,
        description=payload.description,
        match_type=payload.match_type,
        rules=[r.model_dump() for r in payload.rules] if payload.rules is not None else None,
    )
    return SegmentResponse.from_segment(segment)


@router.delete(
    "/segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a segment",
)
async def delete_segment(
    segment_id: uuidlib.UUID, session: SessionDep, actor: SegmentsWriteActor
) -> None:
    await SegmentService(session).delete_segment(
        organization_id=actor.organization_id, actor=actor, public_id=segment_id
    )


@router.get(
    "/segments/{segment_id}/contacts",
    response_model=SegmentContactsPage,
    summary="Preview matching contacts (paginated)",
)
async def preview_segment(
    segment_id: uuidlib.UUID,
    request: Request,
    session: SessionDep,
    actor: SegmentsReadActor,
) -> SegmentContactsPage:
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    result = await SegmentService(session).preview(
        organization_id=actor.organization_id,
        public_id=segment_id,
        limit=limit,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
    )
    next_cursor = (
        encode_cursor(result.contacts[-1].created_at, result.contacts[-1].id)
        if result.has_more and result.contacts
        else None
    )
    return SegmentContactsPage(
        data=[ContactResponse.from_contact(c) for c in result.contacts],
        page=Page(
            limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total
        ),
    )


@router.post(
    "/segments/{segment_id}/refresh",
    response_model=SegmentResponse,
    summary="Recompute the cached count",
)
async def refresh_segment(
    segment_id: uuidlib.UUID, session: SessionDep, actor: SegmentsReadActor
) -> SegmentResponse:
    segment = await SegmentService(session).refresh_count(
        organization_id=actor.organization_id, actor=actor, public_id=segment_id
    )
    return SegmentResponse.from_segment(segment)
