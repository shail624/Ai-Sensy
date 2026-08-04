"""Shared API dependencies (dependency injection composition point).

Foundation dependencies plus the authentication/authorization chain (Doc 01 §2.6, Doc 04 §4):

- :data:`SessionDep` / :data:`SettingsDep` — request-scoped session and settings.
- :func:`get_current_auth` — decode/verify the Bearer access token and load the user.
- :func:`get_current_user` — the authenticated :class:`User`.
- :func:`require_self` — enforce the ``auth:self`` permission for self-service endpoints.
- :func:`require_permissions` — RBAC guard factory (Owner superuser bypasses; else 403).
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.dependencies import (
    ChannelFoundation,
    build_channel_feature_flag_resolver,
    get_channel_foundation,
)
from app.channels.flags import ChannelFeatureFlagResolver
from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import AccessTokenClaims, decode_access_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.rbac_service import RBACService

# Re-exported typed dependencies for concise endpoint signatures.
SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ChannelFoundationDep = Annotated[ChannelFoundation, Depends(get_channel_foundation)]


def get_channel_feature_flag_resolver(
    session: SessionDep,
) -> ChannelFeatureFlagResolver:
    return build_channel_feature_flag_resolver(session)


ChannelFeatureFlagResolverDep = Annotated[
    ChannelFeatureFlagResolver, Depends(get_channel_feature_flag_resolver)
]

# HTTP Bearer scheme (documented in OpenAPI); auto_error off so we raise RFC 7807 problems.
_bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


@dataclass(frozen=True, slots=True)
class CurrentAuth:
    """The authenticated user together with the verified access-token claims."""

    user: User
    claims: AccessTokenClaims


async def get_current_auth(session: SessionDep, credentials: BearerDep) -> CurrentAuth:
    """Authenticate the request from its Bearer access token (Doc 04 §4.1)."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Not authenticated.")
    try:
        claims = decode_access_token(credentials.credentials)
        subject = uuidlib.UUID(claims.subject)
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedError("Invalid or expired token.") from None

    user = await UserRepository(session).get_by_uuid(subject)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("Invalid or expired token.")
    return CurrentAuth(user=user, claims=claims)


CurrentAuthDep = Annotated[CurrentAuth, Depends(get_current_auth)]


async def get_current_user(auth: CurrentAuthDep) -> User:
    return auth.user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def require_self(session: SessionDep, auth: CurrentAuthDep) -> CurrentAuth:
    """Guard self-service endpoints with the ``auth:self`` permission (Doc 04 §11)."""
    if not await RBACService(session).has_permissions(auth.user, {"auth:self"}):
        raise ForbiddenError("You do not have permission to perform this action.")
    return auth


SelfAuthDep = Annotated[CurrentAuth, Depends(require_self)]


def require_permissions(
    *codes: str,
) -> Callable[[SessionDep, CurrentAuthDep], Awaitable[User]]:
    """Build a dependency enforcing that the caller holds all ``codes`` (Doc 04 §4.2)."""
    required = set(codes)

    async def _dependency(session: SessionDep, auth: CurrentAuthDep) -> User:
        if not await RBACService(session).has_permissions(auth.user, required):
            raise ForbiddenError("You do not have permission to perform this action.")
        return auth.user

    return _dependency
