"""API key management endpoints (Doc 04 §4.1, Doc 12 §58).

All operations require ``apikeys:manage`` (Owner superuser bypasses). The secret is returned
**once** on creation and never again; only its hash + prefix are stored. Keys are
organization-scoped. Inbound API-key authentication is out of Module 1 scope.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from app.services.api_key_service import ApiKeyService

router = APIRouter()

ApiKeysActor = Annotated[User, Depends(require_permissions("apikeys:manage"))]


@router.get("/api-keys", response_model=list[ApiKeyResponse], summary="List API keys")
async def list_api_keys(session: SessionDep, actor: ApiKeysActor) -> list[ApiKeyResponse]:
    keys = await ApiKeyService(session).list_keys(actor.organization_id)
    return [ApiKeyResponse.from_api_key(key) for key in keys]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key (secret shown once)",
)
async def create_api_key(
    payload: ApiKeyCreateRequest, session: SessionDep, actor: ApiKeysActor
) -> ApiKeyCreateResponse:
    created = await ApiKeyService(session).create_key(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    base = ApiKeyResponse.from_api_key(created.api_key)
    return ApiKeyCreateResponse(**base.model_dump(), secret=created.secret)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: uuidlib.UUID, session: SessionDep, actor: ApiKeysActor
) -> None:
    await ApiKeyService(session).revoke_key(
        organization_id=actor.organization_id, actor=actor, public_id=key_id
    )
