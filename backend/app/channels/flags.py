"""Server-owned feature-flag scaffolding for the generic channel foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.settings import FeatureFlag


class OmnichannelFeatureFlag(StrEnum):
    """Provider-neutral M13-01 flags frozen by Design Document 33 §15."""

    CONNECTIONS_READ = "omnichannel_connections_read"
    CONNECTIONS_WRITE = "omnichannel_connections_write"
    SESSIONS_READ = "omnichannel_sessions_read"
    SESSIONS_WRITE = "omnichannel_sessions_write"
    QR_PROVIDER = "omnichannel_qr_provider"
    QR_AUTH = "omnichannel_qr_auth"


@dataclass(frozen=True, slots=True)
class ChannelFeatureFlagSnapshot:
    organization_id: int
    enabled: frozenset[OmnichannelFeatureFlag] = field(default_factory=frozenset)
    evaluated_at: datetime = field(default_factory=utcnow)

    def is_enabled(self, flag: OmnichannelFeatureFlag) -> bool:
        return flag in self.enabled


class ChannelFeatureFlagResolver:
    """Resolve global defaults with organization-specific overrides; absent flags are off."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, organization_id: int) -> ChannelFeatureFlagSnapshot:
        keys = tuple(flag.value for flag in OmnichannelFeatureFlag)
        rows = list(
            (
                await self._session.scalars(
                    select(FeatureFlag).where(
                        FeatureFlag.key_name.in_(keys),
                        or_(
                            FeatureFlag.organization_id.is_(None),
                            FeatureFlag.organization_id == organization_id,
                        ),
                    )
                )
            ).all()
        )

        values = dict.fromkeys(OmnichannelFeatureFlag, False)
        for row in rows:
            if row.organization_id is None:
                values[OmnichannelFeatureFlag(row.key_name)] = row.is_enabled
        for row in rows:
            if row.organization_id == organization_id:
                values[OmnichannelFeatureFlag(row.key_name)] = row.is_enabled

        return ChannelFeatureFlagSnapshot(
            organization_id=organization_id,
            enabled=frozenset(flag for flag, enabled in values.items() if enabled),
        )
