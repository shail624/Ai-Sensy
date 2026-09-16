"""User management endpoints (Doc 04 §12.1).

Reads require ``users:read``; mutations require ``users:manage`` (Owner superuser bypasses).
The current workload snapshot instead requires ``analytics:read`` + ``tasks:assign`` and exposes
only teammate names and pending-work counts. Users are scoped to the caller's organization.
Listing is cursor-paginated (Doc 04 §3/§6)
with the filters ``filter[is_active][bool]`` / ``filter[role][eq]`` and quick search ``q``.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, encode_cursor
from app.models.user import User
from app.schemas.audit import AuditLogPage, AuditLogResponse
from app.schemas.user import (
    PreferencesResponse,
    PreferencesUpdateRequest,
    TeamWorkloadResponse,
    UserCreateRequest,
    UserResponse,
    UsersPage,
    UserUpdateRequest,
)
from app.services.audit_query_service import AuditQueryService
from app.services.settings_service import SettingsService
from app.services.team_workload_service import TeamWorkloadService
from app.services.user_service import UserService

router = APIRouter()

UsersReadActor = Annotated[User, Depends(require_permissions("users:read"))]
UsersManageActor = Annotated[User, Depends(require_permissions("users:manage"))]
SelfActor = Annotated[User, Depends(require_permissions("auth:self"))]
TeamWorkloadActor = Annotated[
    User, Depends(require_permissions("analytics:read", "tasks:assign"))
]


def _bool_param(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"true", "1", "yes"}


@router.get("/users", response_model=UsersPage, summary="List users")
async def list_users(
    request: Request,
    session: SessionDep,
    actor: UsersReadActor,
    limit_param: Annotated[
        int | None, Query(alias="limit", ge=1, le=MAX_LIMIT, description="Page size (default 50).")
    ] = None,
    cursor_param: Annotated[
        str | None, Query(alias="cursor", description="Opaque token from a prior next_cursor.")
    ] = None,
    q: Annotated[str | None, Query(description="Match a user's name or email.")] = None,
) -> UsersPage:
    """The organization's users.

    Pagination and search are declared (Doc 04 §6, §7.3); the `filter[field][op]` grammar of §7.1
    stays on the raw request because it spans any field crossed with eleven operators.
    """
    params = request.query_params
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    cursor = decode_cursor(cursor_param) if cursor_param else None
    result = await UserService(session).list_users(
        actor.organization_id,
        limit=limit,
        cursor=cursor,
        is_active=_bool_param(params.get("filter[is_active][bool]")),
        role_name=params.get("filter[role][eq]"),
        q=q,
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


@router.get(
    "/users/me/preferences",
    response_model=PreferencesResponse,
    summary="Get own preferences",
)
async def get_preferences(session: SessionDep, actor: SelfActor) -> PreferencesResponse:
    prefs = await SettingsService(session).get_preferences(actor)
    return PreferencesResponse(preferences=prefs)


@router.put(
    "/users/me/preferences",
    response_model=PreferencesResponse,
    summary="Update own preferences",
)
async def update_preferences(
    payload: PreferencesUpdateRequest, session: SessionDep, actor: SelfActor
) -> PreferencesResponse:
    prefs = await SettingsService(session).update_preferences(
        user=actor, preferences=payload.preferences
    )
    return PreferencesResponse(preferences=prefs)


@router.get(
    "/users/workload",
    response_model=TeamWorkloadResponse,
    summary="Current team workload snapshot",
)
async def team_workload(
    session: SessionDep,
    actor: TeamWorkloadActor,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
) -> TeamWorkloadResponse:
    """Pending work by teammate; conversation/task tables remain the live authorities."""
    snapshot = await TeamWorkloadService(session).snapshot(
        organization_id=actor.organization_id,
        timezone_name=timezone or actor.timezone,
    )
    return TeamWorkloadResponse.from_snapshot(snapshot)


@router.get(
    "/users/{user_id}/login-history",
    response_model=AuditLogPage,
    summary="A user's sign-in history",
)
async def user_login_history(
    user_id: uuidlib.UUID,
    session: SessionDep,
    actor: UsersReadActor,
    limit_param: Annotated[
        int | None, Query(alias="limit", ge=1, le=MAX_LIMIT, description="Page size (default 50).")
    ] = None,
    cursor_param: Annotated[
        str | None, Query(alias="cursor", description="Opaque token from a prior next_cursor.")
    ] = None,
) -> AuditLogPage:
    """Successful sign-ins, rejected passwords and lockouts for one user, newest first.

    The audit trail already records all three with their source address, so this reads that rather
    than keeping a second copy of the same truth. Failures and lockouts are included deliberately:
    a list of successes answers "when did they last sign in", but only the failures answer "is
    somebody trying to get in", which is the question worth asking.

    Gated on `users:read` — the same permission as viewing the user — and scoped to the caller's
    organization, so one tenant cannot read another's sign-in activity.
    """
    user, _ = await UserService(session).get_user(actor.organization_id, user_id)
    service = AuditQueryService(session)
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    result = await service.login_history(
        actor.organization_id,
        user_id=user.id,
        limit=limit,
        cursor=decode_cursor(cursor_param) if cursor_param else None,
    )
    next_cursor = (
        encode_cursor(result.entries[-1].created_at, result.entries[-1].id)
        if result.has_more and result.entries
        else None
    )
    return AuditLogPage(
        data=[
            AuditLogResponse.from_entry(entry, result.actor_uuids.get(entry.actor_user_id or -1))
            for entry in result.entries
        ],
        page=Page(
            limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total
        ),
    )


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
