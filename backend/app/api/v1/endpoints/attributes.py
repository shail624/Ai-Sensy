"""Custom attribute definition endpoints (Doc 04 §14.4) — FR-CON-11.

Reads require ``contacts:read``; writes require ``contacts:write`` (Owner superuser bypasses).
``key_name`` and ``data_type`` are immutable after creation (they determine the storage column
and are referenced by segment rules); label / indexing / enum values are updatable.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.attribute import (
    AttributeDefinitionCreateRequest,
    AttributeDefinitionResponse,
    AttributeDefinitionUpdateRequest,
)
from app.services.attribute_service import AttributeService

router = APIRouter()

AttrReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
AttrWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]


@router.get(
    "/custom-attributes",
    response_model=list[AttributeDefinitionResponse],
    summary="List attribute definitions",
)
async def list_attributes(
    session: SessionDep, actor: AttrReadActor
) -> list[AttributeDefinitionResponse]:
    definitions = await AttributeService(session).list_definitions(actor.organization_id)
    return [AttributeDefinitionResponse.from_definition(d) for d in definitions]


@router.post(
    "/custom-attributes",
    response_model=AttributeDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define a typed attribute",
)
async def create_attribute(
    payload: AttributeDefinitionCreateRequest, session: SessionDep, actor: AttrWriteActor
) -> AttributeDefinitionResponse:
    definition = await AttributeService(session).create_definition(
        organization_id=actor.organization_id,
        actor=actor,
        key_name=payload.key_name,
        label=payload.label,
        data_type=payload.data_type,
        enum_values=payload.enum_values,
        is_indexed=payload.is_indexed,
        is_pii=payload.is_pii,
    )
    return AttributeDefinitionResponse.from_definition(definition)


@router.patch(
    "/custom-attributes/{attribute_id}",
    response_model=AttributeDefinitionResponse,
    summary="Update label / indexing / enum values",
)
async def update_attribute(
    attribute_id: uuidlib.UUID,
    payload: AttributeDefinitionUpdateRequest,
    session: SessionDep,
    actor: AttrWriteActor,
) -> AttributeDefinitionResponse:
    definition = await AttributeService(session).update_definition(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=attribute_id,
        label=payload.label,
        enum_values=payload.enum_values,
        is_indexed=payload.is_indexed,
        is_pii=payload.is_pii,
    )
    return AttributeDefinitionResponse.from_definition(definition)


@router.delete(
    "/custom-attributes/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a definition (and its values)",
)
async def delete_attribute(
    attribute_id: uuidlib.UUID, session: SessionDep, actor: AttrWriteActor
) -> None:
    await AttributeService(session).delete_definition(
        organization_id=actor.organization_id, actor=actor, public_id=attribute_id
    )
