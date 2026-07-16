"""Tag management endpoints (Doc 04 §14.2).

Reads require ``contacts:read``; writes require ``contacts:write`` (Owner superuser bypasses).
Tags are organization-scoped; deleting a tag detaches it from every contact.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.tag import TagCreateRequest, TagResponse, TagUpdateRequest
from app.services.tag_service import TagService

router = APIRouter()

TagsReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
TagsWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]


@router.get("/tags", response_model=list[TagResponse], summary="List tags (with usage counts)")
async def list_tags(session: SessionDep, actor: TagsReadActor) -> list[TagResponse]:
    tags = await TagService(session).list_tags(actor.organization_id)
    return [TagResponse.from_tag(tag) for tag in tags]


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
)
async def create_tag(
    payload: TagCreateRequest, session: SessionDep, actor: TagsWriteActor
) -> TagResponse:
    tag = await TagService(session).create_tag(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        color=payload.color,
        description=payload.description,
    )
    return TagResponse.from_tag(tag)


@router.patch("/tags/{tag_id}", response_model=TagResponse, summary="Rename / recolor a tag")
async def update_tag(
    tag_id: uuidlib.UUID,
    payload: TagUpdateRequest,
    session: SessionDep,
    actor: TagsWriteActor,
) -> TagResponse:
    tag = await TagService(session).update_tag(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=tag_id,
        name=payload.name,
        color=payload.color,
        description=payload.description,
    )
    return TagResponse.from_tag(tag)


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag (detaches from contacts)",
)
async def delete_tag(tag_id: uuidlib.UUID, session: SessionDep, actor: TagsWriteActor) -> None:
    await TagService(session).delete_tag(
        organization_id=actor.organization_id, actor=actor, public_id=tag_id
    )
