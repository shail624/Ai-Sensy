"""Organization repository (Doc 03 §4.1)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(
            Organization.slug == slug, Organization.deleted_at.is_(None)
        )
        return (await self.session.scalars(stmt)).first()

    async def get_default(self) -> Organization | None:
        """The single active organization (single-tenant deployment, Doc 03 §4.1)."""
        stmt = (
            select(Organization)
            .where(Organization.deleted_at.is_(None), Organization.is_active.is_(True))
            .order_by(Organization.id)
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()
