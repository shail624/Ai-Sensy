"""User management endpoints (Doc 04 §12.1).

Reads require ``users:read``; mutations require ``users:manage`` (Owner superuser bypasses).
Users are scoped to the caller's organization. Listing is cursor-paginated (Doc 04 §3/§6)
with the filters ``filter[is_active][bool]`` / ``filter[role][eq]`` and quick search ``q``.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.models.user import User
from app.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UsersPage,
    UserUpdateRequest,
)
from app.services.user_service import UserService

router = APIRouter()

UsersReadActor = Annotated[User, Depends(require_permissions("users:read"))]
UsersManageActor = Annotated[User, Depends(require_permissions("users:manage"))]


def _bool_param(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"true", "1", "yes"}


@router.get("/users", response_model=UsersPage, summary="List users")
async def list_users(request: Request, session: SessionDep, actor: UsersReadActor) -> UsersPage:
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    cursor = decode_cursor(raw_cursor) if raw_cursor else None
    result = await UserService(session).list_users(
        actor.organization_id,
        limit=limit,
        cursor=cursor,
        is_active=_bool_param(params.get("filter[is_active][bool]")),
        role_name=params.get("filter[role][eq]"),
        q=params.get("q"),
    )
    data = [
        UserResponse.from_user(user, result.roles_by_user[user.id]) for user in result.users
    ]
    next_cursor = (
        encode_cursor(result.users[-1].created_at, result.users[-1].id)
        if result.has_more and result.users
        else None
    )
    return UsersPage(
        data=data,
        page=Page(limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total),
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    payload: UserCreateRequest, session: SessionDep, actor: UsersManageActor
) -> UserResponse:
    user, roles = await UserService(session).create_user(
        organization_id=actor.organization_id,
        actor=actor,
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
        phone=payload.phone,
        timezone=payload.timezone,
        locale=payload.locale,
        roles=payload.roles,
    )
    return UserResponse.from_user(user, roles)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get a user")
async def get_user(
    user_id: uuidlib.UUID, session: SessionDep, actor: UsersReadActor
) -> UserResponse:
    user, roles = await UserService(session).get_user(actor.organization_id, user_id)
    return UserResponse.from_user(user, roles)


@router.patch("/users/{user_id}", response_model=UserResponse, summary="Update a user")
async def update_user(
    user_id: uuidlib.UUID,
    payload: UserUpdateRequest,
    session: SessionDep,
    actor: UsersManageActor,
) -> UserResponse:
    user, roles = await UserService(session).update_user(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=user_id,
        full_name=payload.full_name,
        phone=payload.phone,
        timezone=payload.timezone,
        locale=payload.locale,
        is_active=payload.is_active,
        roles=payload.roles,
        expected_version=payload.row_version,
    )
    return UserResponse.from_user(user, roles)


@router.delete(
    "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a user"
)
async def delete_user(
    user_id: uuidlib.UUID, session: SessionDep, actor: UsersManageActor
) -> None:
    await UserService(session).delete_user(
        organization_id=actor.organization_id, actor=actor, public_id=user_id
    )


@router.post("/users/{user_id}/activate", response_model=UserResponse, summary="Activate a user")
async def activate_user(
    user_id: uuidlib.UUID, session: SessionDep, actor: UsersManageActor
) -> UserResponse:
    user, roles = await UserService(session).set_active(
        organization_id=actor.organization_id, actor=actor, public_id=user_id, active=True
    )
    return UserResponse.from_user(user, roles)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate a user (revokes sessions)",
)
async def deactivate_user(
    user_id: uuidlib.UUID, session: SessionDep, actor: UsersManageActor
) -> UserResponse:
    user, roles = await UserService(session).set_active(
        organization_id=actor.organization_id, actor=actor, public_id=user_id, active=False
    )
    return UserResponse.from_user(user, roles)
