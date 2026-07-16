"""Organization service (Doc 04 §13.1).

Read and update the caller's single-tenant organization profile (name, timezone, locale,
settings). Enforces optimistic concurrency (``row_version`` → 409) and audits updates.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, VersionConflictError
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.services.audit_service import AuditAction, AuditService


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orgs = OrganizationRepository(session)
        self._audit = AuditService(session)

    async def get(self, organization_id: int) -> Organization:
        org = await self._orgs.get_by_id(organization_id)
        if org is None or org.deleted_at is not None:
            raise NotFoundError("Organization not found.")
        return org

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str | None,
        timezone: str | None,
        default_locale: str | None,
        settings: dict[str, Any] | None,
        expected_version: int | None,
    ) -> Organization:
        org = await self.get(organization_id)
        if expected_version is not None and expected_version != org.row_version:
            raise VersionConflictError(
                "The organization was modified by someone else; reload and retry."
            )
        before = {
            "name": org.name,
            "timezone": org.timezone,
            "default_locale": org.default_locale,
        }
        if name is not None:
            org.name = name
        if timezone is not None:
            org.timezone = timezone
        if default_locale is not None:
            org.default_locale = default_locale
        if settings is not None:
            org.settings_json = settings
        org.row_version += 1
        await self._orgs.flush()
        await self._audit.record(
            AuditAction.ORGANIZATION_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="organization",
            entity_id=org.id,
            before=before,
            after={
                "name": org.name,
                "timezone": org.timezone,
                "default_locale": org.default_locale,
            },
        )
        await self._session.commit()
        return org
