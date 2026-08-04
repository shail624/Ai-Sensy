"""M13-02 feature flag resolved through the existing server-owned FeatureFlag authority."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.settings import FeatureFlag

IDENTITY_RESOLUTION_FLAG = "omnichannel_identity_resolution"


class IdentityResolutionFeatureFlag:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_enabled(self, organization_id: int) -> bool:
        rows = list(
            (
                await self._session.scalars(
                    select(FeatureFlag).where(
                        FeatureFlag.key_name == IDENTITY_RESOLUTION_FLAG,
                        or_(
                            FeatureFlag.organization_id.is_(None),
                            FeatureFlag.organization_id == organization_id,
                        ),
                    )
                )
            ).all()
        )
        enabled = False
        for row in rows:
            if row.organization_id is None:
                enabled = row.is_enabled
        for row in rows:
            if row.organization_id == organization_id:
                enabled = row.is_enabled
        return enabled

    async def require_enabled(self, organization_id: int) -> None:
        if not await self.is_enabled(organization_id):
            raise NotFoundError("Customer identity resolution is not enabled.")
