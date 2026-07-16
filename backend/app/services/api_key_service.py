"""API key service (Doc 03 §4.4, Doc 12 §58).

Manages the lifecycle of organization API keys: create (returns the secret **once**), list,
and revoke. Only the SHA-256 hash and short prefix are stored. Optional scopes are validated
against the seeded permission catalog. Inbound API-key authentication is out of Module 1
scope (future public-API module).
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import generate_api_key, hash_token
from app.db.mixins import utcnow
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.api_key import ApiKeyRepository
from app.repositories.role import PermissionRepository
from app.services.audit_service import AuditAction, AuditService


@dataclass(slots=True)
class CreatedApiKey:
    api_key: ApiKey
    secret: str  # shown once, never persisted in plaintext


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._keys = ApiKeyRepository(session)
        self._perms = PermissionRepository(session)
        self._audit = AuditService(session)

    async def list_keys(self, organization_id: int) -> list[ApiKey]:
        return await self._keys.list_for_org(organization_id)

    async def _validate_scopes(self, scopes: list[str]) -> None:
        if not scopes:
            return
        known = await self._perms.existing_codes(scopes)
        unknown = [code for code in dict.fromkeys(scopes) if code not in known]
        if unknown:
            raise ValidationError(
                "One or more scopes are not valid permissions.",
                errors=[
                    {"field": "scopes", "code": "unknown_permission", "message": c}
                    for c in unknown
                ],
            )

    async def create_key(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> CreatedApiKey:
        await self._validate_scopes(scopes)
        secret, key_prefix = generate_api_key()
        api_key = await self._keys.create(
            organization_id=organization_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=hash_token(secret),
            scopes=scopes or None,
            expires_at=expires_at,
            created_by=actor.id,
        )
        await self._audit.record(
            AuditAction.API_KEY_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="api_key",
            entity_id=api_key.id,
            after={"name": name, "key_prefix": key_prefix, "scopes": scopes},
        )
        await self._session.commit()
        return CreatedApiKey(api_key=api_key, secret=secret)

    async def revoke_key(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        api_key = await self._keys.get_active_by_uuid(organization_id, public_id.bytes)
        if api_key is None:
            raise NotFoundError("API key not found.")
        key_id = api_key.id
        await self._keys.revoke(api_key, utcnow())
        await self._audit.record(
            AuditAction.API_KEY_REVOKED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="api_key",
            entity_id=key_id,
        )
        await self._session.commit()
