"""Refresh-token and session repositories (Doc 03 §4.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from app.models.token import RefreshToken, UserSession
from app.repositories._result import affected_rows
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def create(
        self,
        *,
        user_id: int,
        token_hash: str,
        jti: str,
        expires_at: datetime,
        parent_id: int | None = None,
        user_agent: str | None = None,
        ip_address: bytes | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
            parent_id=parent_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return await self.add(token)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self.session.scalars(stmt)).first()

    async def revoke(self, token: RefreshToken, now: datetime) -> None:
        if token.revoked_at is None:
            token.revoked_at = now
            await self.session.flush()

    async def revoke_family(self, jti: str, now: datetime) -> int:
        """Revoke every still-active token in a rotation family (reuse detection, Doc 04 §11)."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.jti == jti, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return affected_rows(result)

    async def revoke_all_for_user(self, user_id: int, now: datetime) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return affected_rows(result)

    async def list_active_for_user(self, user_id: int, now: datetime) -> list[RefreshToken]:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return list((await self.session.scalars(stmt)).all())

    async def ids_for_jti(self, jti: str) -> list[int]:
        """All refresh-row ids in a rotation family (used to revoke its sessions)."""
        stmt = select(RefreshToken.id).where(RefreshToken.jti == jti)
        return list((await self.session.scalars(stmt)).all())


class SessionRepository(BaseRepository[UserSession]):
    model = UserSession

    async def create(
        self,
        *,
        user_id: int,
        refresh_token_id: int | None = None,
        user_agent: str | None = None,
        ip_address: bytes | None = None,
    ) -> UserSession:
        session_row = UserSession(
            user_id=user_id,
            refresh_token_id=refresh_token_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return await self.add(session_row)

    async def list_active_for_user(self, user_id: int) -> list[UserSession]:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_seen_at.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(self, user_id: int, public_id: bytes) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.uuid == public_id,
            UserSession.revoked_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_refresh_token_id(self, refresh_token_id: int) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_id == refresh_token_id,
            UserSession.revoked_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def revoke_by_refresh_ids(self, refresh_ids: list[int], now: datetime) -> int:
        """Revoke sessions tied to a set of refresh rows (family-scoped logout/reuse)."""
        if not refresh_ids:
            return 0
        result = await self.session.execute(
            update(UserSession)
            .where(
                UserSession.refresh_token_id.in_(refresh_ids),
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return affected_rows(result)

    async def revoke(self, session_row: UserSession, now: datetime) -> None:
        if session_row.revoked_at is None:
            session_row.revoked_at = now
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: int, now: datetime) -> int:
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return affected_rows(result)

    async def touch(self, session_row: UserSession, now: datetime) -> None:
        session_row.last_seen_at = now
        await self.session.flush()
