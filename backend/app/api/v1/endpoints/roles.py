"""Role & permission management endpoints (Doc 04 §12.2).

Administrative RBAC resources. Reads require ``roles:read``; mutations require ``roles:write``
(the Owner superuser bypasses both). Roles are organization-scoped to the caller's org.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.rbac import (
    PermissionResponse,
    RoleCreateRequest,
    RolePermissionsRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.services.rbac_service import RBACService

router = APIRouter()

# RBAC guards as reusable Annotated dependencies (Doc 04 §12.2 permissions).
RolesReadActor = Annotated[User, Depends(require_permissions("roles:read"))]
RolesWriteActor = Annotated[User, Depends(require_permissions("roles:write"))]


@router.get("/roles", response_model=list[RoleResponse], summary="List roles")
async def list_roles(session: SessionDep, actor: RolesReadActor) -> list[RoleResponse]:
    roles = await RBACService(session).list_roles(actor.organization_id)
    return [RoleResponse.from_role(role) for role in roles]


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
)
async def create_role(
    payload: RoleCreateRequest, session: SessionDep, actor: RolesWriteActor
) -> RoleResponse:
    role = await RBACService(session).create_role(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        description=payload.description,
        permission_codes=payload.permissions,
    )
    return RoleResponse.from_role(role)


@router.get("/roles/{role_id}", response_model=RoleResponse, summary="Get a role")
async def get_role(
    role_id: uuidlib.UUID, session: SessionDep, actor: RolesReadActor
) -> RoleResponse:
    role = await RBACService(session).get_role(actor.organization_id, role_id)
    return RoleResponse.from_role(role)


@router.patch("/roles/{role_id}", response_model=RoleResponse, summary="Rename / edit a role")
async def update_role(
    role_id: uuidlib.UUID,
    payload: RoleUpdateRequest,
    session: SessionDep,
    actor: RolesWriteActor,
) -> RoleResponse:
    role = await RBACService(session).update_role(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=role_id,
        name=payload.name,
        description=payload.description,
    )
    return RoleResponse.from_role(role)


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
    summary="Replace a role's permission set",
)
async def set_role_permissions(
    role_id: uuidlib.UUID,
    payload: RolePermissionsRequest,
    session: SessionDep,
    actor: RolesWriteActor,
) -> RoleResponse:
    role = await RBACService(session).set_role_permissions(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=role_id,
        permission_codes=payload.permissions,
    )
    return RoleResponse.from_role(role)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role (if unused and non-system)",
)
async def delete_role(
    role_id: uuidlib.UUID, session: SessionDep, actor: RolesWriteActor
) -> None:
    await RBACService(session).delete_role(
        organization_id=actor.organization_id, actor=actor, public_id=role_id
    )


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    summary="List the permission catalog",
)
async def list_permissions(
    session: SessionDep, actor: RolesReadActor
) -> list[PermissionResponse]:
    permissions = await RBACService(session).list_permissions()
    return [PermissionResponse.from_permission(permission) for permission in permissions]
