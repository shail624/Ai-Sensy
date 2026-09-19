"""API key repository (Doc 03 §4.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models.api_key import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    async def list_for_org(self, organization_id: int) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.organization_id == organization_id)
            .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> ApiKey | None:
        stmt = select(ApiKey).where(
            ApiKey.organization_id == organization_id,
            ApiKey.uuid == public_id,
            ApiKey.revoked_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def create(
        self,
        *,
        organization_id: int,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: list[str] | None,
        expires_at: datetime | None,
        created_by: int | None,
    ) -> ApiKey:
        api_key = ApiKey(
            organization_id=organization_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes_json=scopes,
            expires_at=expires_at,
            created_by=created_by,
        )
        return await self.add(api_key)

    async def revoke(self, api_key: ApiKey, now: datetime) -> None:
        if api_key.revoked_at is None:
            api_key.revoked_at = now
            await self.session.flush()

    async def replace_secret(self, api_key: ApiKey, *, key_prefix: str, key_hash: str) -> None:
        """Swap the stored secret in place, keeping the row's identity, name and scopes.

        The previous hash is overwritten rather than retained: there is one secret per key, so the
        old one stops authenticating the moment this flushes. A grace period would need a second
        stored hash and is deliberately not implied here.
        """
        api_key.key_prefix = key_prefix
        api_key.key_hash = key_hash
        await self.session.flush()
