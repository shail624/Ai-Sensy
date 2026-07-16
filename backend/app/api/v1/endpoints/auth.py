"""Authentication & session endpoints (Doc 04 §11).

Login/refresh are public (rate-limited via the ``auth`` bucket); the rest require a Bearer
token and the ``auth:self`` permission. Success/failure of every action is audited inside
the service layer. MFA enrolment endpoints (§11 rows) arrive with the MFA step.
"""

from __future__ import annotations

import uuid as uuidlib

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SelfAuthDep, SessionDep
from app.core.rate_limit import rate_limit
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    SessionResponse,
    TokenResponse,
    UserSummary,
)
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    agent = request.headers.get("user-agent")
    return agent[:255] if agent else None


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth"))],
    summary="Exchange email + password for tokens",
)
async def login(payload: LoginRequest, request: Request, session: SessionDep) -> TokenResponse:
    result = await AuthService(session).authenticate(
        email=str(payload.email),
        password=payload.password,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        refresh_token=result.refresh_token,
        user=UserSummary.from_user(result.user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth"))],
    summary="Rotate a refresh token (with reuse detection)",
)
async def refresh(payload: RefreshRequest, request: Request, session: SessionDep) -> TokenResponse:
    result = await AuthService(session).refresh(
        refresh_token=payload.refresh_token,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        refresh_token=result.refresh_token,
        user=UserSummary.from_user(result.user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the current session")
async def logout(auth: SelfAuthDep, session: SessionDep) -> None:
    await AuthService(session).logout(user=auth.user, jti=auth.claims.jti)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all sessions for the current user",
)
async def logout_all(auth: SelfAuthDep, session: SessionDep) -> None:
    await AuthService(session).logout_all(user=auth.user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
)
async def change_password(
    payload: ChangePasswordRequest, auth: SelfAuthDep, session: SessionDep
) -> None:
    await AuthService(session).change_password(
        user=auth.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )


@router.get("/me", response_model=MeResponse, summary="Current user + effective permissions")
async def me(auth: SelfAuthDep, session: SessionDep) -> MeResponse:
    rbac = RBACService(session)
    roles = await rbac.roles_for_user(auth.user)
    permissions = await rbac.effective_permissions(auth.user)
    user = auth.user
    return MeResponse(
        id=user.public_id,
        email=user.email,
        full_name=user.full_name,
        is_superuser=user.is_superuser,
        roles=[role.name for role in roles],
        permissions=sorted(permissions),
        timezone=user.timezone,
        locale=user.locale,
        mfa_enabled=user.mfa_enabled,
    )


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List own active sessions/devices",
)
async def list_sessions(auth: SelfAuthDep, session: SessionDep) -> list[SessionResponse]:
    rows = await AuthService(session).list_sessions(user=auth.user)
    return [SessionResponse.from_session(row) for row in rows]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke one session",
)
async def revoke_session(
    session_id: uuidlib.UUID, auth: SelfAuthDep, session: SessionDep
) -> None:
    await AuthService(session).revoke_session(user=auth.user, session_public_id=session_id)
