"""Authentication service (Doc 01 FR-AUTH-01..04, Doc 04 §11).

Owns the credential + session lifecycle: login (with Argon2id verification, failed-login
lockout, and rehash-on-login), refresh-token **rotation with reuse detection**, logout /
logout-all, self-service password change, and session listing/revocation. Every security
action is audited in the same transaction (Audit Integration). Generic messages never reveal
whether an email exists (Doc 04 §11 — no user enumeration).
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import LockedError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    new_jti,
    pack_ip,
    password_needs_rehash,
    permissions_hash,
    verify_password,
)
from app.db.mixins import utcnow
from app.models.token import RefreshToken, UserSession
from app.models.user import User
from app.repositories.token import RefreshTokenRepository, SessionRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.rbac_service import RBACService


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Issued token bundle returned to the API layer (Doc 04 §11 login/refresh response)."""

    access_token: str
    expires_in: int
    refresh_token: str
    user: User
    token_type: str = "bearer"  # noqa: S105 - token *type*, not a secret


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh = RefreshTokenRepository(session)
        self._sessions = SessionRepository(session)
        self._rbac = RBACService(session)
        self._audit = AuditService(session)

    # --- Token minting -------------------------------------------------------
    async def _mint(
        self,
        user: User,
        *,
        jti: str,
        parent_id: int | None,
        ip_bytes: bytes | None,
        user_agent: str | None,
    ) -> tuple[str, int, str, RefreshToken]:
        """Create a refresh row and a matching access token for a token family."""
        refresh_plain = generate_refresh_token()
        expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)
        row = await self._refresh.create(
            user_id=user.id,
            token_hash=hash_token(refresh_plain),
            jti=jti,
            expires_at=expires_at,
            parent_id=parent_id,
            user_agent=user_agent,
            ip_address=ip_bytes,
        )
        perms = await self._rbac.effective_permissions(user)
        access, expires_in = create_access_token(
            subject=user.public_id, jti=jti, perms_hash=permissions_hash(perms)
        )
        return access, expires_in, refresh_plain, row

    # --- Login ---------------------------------------------------------------
    async def authenticate(
        self, *, email: str, password: str, ip: str | None, user_agent: str | None
    ) -> LoginResult:
        user = await self._users.get_by_email(email)
        now = utcnow()
        ip_bytes = pack_ip(ip)

        # Unknown email → generic failure (no enumeration).
        if user is None:
            raise UnauthorizedError("Invalid email or password.")

        # Already locked out.
        if user.locked_until is not None and user.locked_until > now:
            await self._audit.record(
                AuditAction.LOGIN_LOCKED,
                actor_user_id=user.id,
                organization_id=user.organization_id,
                ip_address=ip_bytes,
            )
            await self._session.commit()
            raise LockedError("Account is temporarily locked. Try again later.")

        if not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("Invalid email or password.")

        # Wrong password → count the failure, lock at the threshold.
        if not verify_password(password, user.password_hash):
            user.failed_logins += 1
            locked = user.failed_logins >= settings.max_failed_logins
            action = AuditAction.LOGIN_FAILED
            if locked:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                user.failed_logins = 0
                action = AuditAction.LOGIN_LOCKED
            await self._users.flush()
            await self._audit.record(
                action,
                actor_user_id=user.id,
                organization_id=user.organization_id,
                ip_address=ip_bytes,
            )
            await self._session.commit()
            if locked:
                raise LockedError("Account locked after too many failed attempts.")
            raise UnauthorizedError("Invalid email or password.")

        # Success — upgrade the hash if parameters changed, reset lockout state.
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.failed_logins = 0
        user.locked_until = None
        user.last_login_at = now
        await self._users.flush()

        session_row = await self._sessions.create(
            user_id=user.id, user_agent=user_agent, ip_address=ip_bytes
        )
        jti = new_jti()
        access, expires_in, refresh_plain, row = await self._mint(
            user, jti=jti, parent_id=None, ip_bytes=ip_bytes, user_agent=user_agent
        )
        session_row.refresh_token_id = row.id
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.LOGIN,
            actor_user_id=user.id,
            organization_id=user.organization_id,
            entity_type="session",
            entity_id=session_row.id,
            ip_address=ip_bytes,
        )
        await self._session.commit()
        return LoginResult(
            access_token=access, expires_in=expires_in, refresh_token=refresh_plain, user=user
        )

    # --- Refresh (rotation + reuse detection) --------------------------------
    async def refresh(
        self, *, refresh_token: str, ip: str | None, user_agent: str | None
    ) -> LoginResult:
        now = utcnow()
        ip_bytes = pack_ip(ip)
        row = await self._refresh.get_by_hash(hash_token(refresh_token))
        if row is None:
            raise UnauthorizedError("Invalid refresh token.")

        # Presenting an already-rotated token = theft/replay → burn the whole family.
        if row.revoked_at is not None:
            await self._refresh.revoke_family(row.jti, now)
            family_ids = await self._refresh.ids_for_jti(row.jti)
            await self._sessions.revoke_by_refresh_ids(family_ids, now)
            await self._audit.record(
                AuditAction.TOKEN_REUSE_DETECTED,
                actor_user_id=row.user_id,
                entity_type="refresh_token",
                entity_id=row.id,
                ip_address=ip_bytes,
            )
            await self._session.commit()
            raise UnauthorizedError("Refresh token has been revoked.")

        if row.expires_at <= now:
            raise UnauthorizedError("Refresh token has expired.")

        user = await self._users.get_by_id(row.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("Invalid refresh token.")

        # Rotate: revoke the presented token, mint a successor in the same family.
        await self._refresh.revoke(row, now)
        access, expires_in, refresh_plain, new_row = await self._mint(
            user, jti=row.jti, parent_id=row.id, ip_bytes=ip_bytes, user_agent=user_agent
        )
        session_row = await self._sessions.get_by_refresh_token_id(row.id)
        if session_row is not None:
            session_row.refresh_token_id = new_row.id
            await self._sessions.touch(session_row, now)
        await self._audit.record(
            AuditAction.TOKEN_REFRESH,
            actor_user_id=user.id,
            organization_id=user.organization_id,
            ip_address=ip_bytes,
        )
        await self._session.commit()
        return LoginResult(
            access_token=access, expires_in=expires_in, refresh_token=refresh_plain, user=user
        )

    # --- Logout --------------------------------------------------------------
    async def logout(self, *, user: User, jti: str) -> None:
        """Revoke the current token family and its session (idempotent, Doc 04 §11)."""
        now = utcnow()
        await self._refresh.revoke_family(jti, now)
        await self._sessions.revoke_by_refresh_ids(await self._refresh.ids_for_jti(jti), now)
        await self._audit.record(
            AuditAction.LOGOUT, actor_user_id=user.id, organization_id=user.organization_id
        )
        await self._session.commit()

    async def logout_all(self, *, user: User) -> None:
        """Revoke every refresh token and session for the user (Doc 04 §11 logout-all)."""
        now = utcnow()
        await self._refresh.revoke_all_for_user(user.id, now)
        await self._sessions.revoke_all_for_user(user.id, now)
        await self._audit.record(
            AuditAction.LOGOUT_ALL, actor_user_id=user.id, organization_id=user.organization_id
        )
        await self._session.commit()

    # --- Password change -----------------------------------------------------
    async def change_password(
        self, *, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")
        now = utcnow()
        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        await self._users.flush()
        # Force re-authentication everywhere after a credential change (best practice).
        await self._refresh.revoke_all_for_user(user.id, now)
        await self._sessions.revoke_all_for_user(user.id, now)
        await self._audit.record(
            AuditAction.PASSWORD_CHANGED,
            actor_user_id=user.id,
            organization_id=user.organization_id,
        )
        await self._session.commit()

    # --- Sessions ------------------------------------------------------------
    async def list_sessions(self, *, user: User) -> list[UserSession]:
        return await self._sessions.list_active_for_user(user.id)

    async def revoke_session(self, *, user: User, session_public_id: uuidlib.UUID) -> None:
        row = await self._sessions.get_active_by_uuid(user.id, session_public_id.bytes)
        if row is None:
            raise NotFoundError("Session not found.")
        now = utcnow()
        await self._sessions.revoke(row, now)
        if row.refresh_token_id is not None:
            rt = await self._refresh.get_by_id(row.refresh_token_id)
            if rt is not None:
                await self._refresh.revoke(rt, now)
        await self._audit.record(
            AuditAction.SESSION_REVOKED,
            actor_user_id=user.id,
            organization_id=user.organization_id,
            entity_type="session",
            entity_id=row.id,
        )
        await self._session.commit()
