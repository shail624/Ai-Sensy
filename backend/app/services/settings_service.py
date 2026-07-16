"""System settings & feature-flag service (Doc 04 §22).

Reads/updates organization-scoped settings (system-scoped settings are read-only here) and
manages global feature flags. Every change is audited.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import FeatureFlag, Setting
from app.models.user import User
from app.repositories.settings import FeatureFlagRepository, SettingRepository
from app.services.audit_service import AuditAction, AuditService


def _infer_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "json"


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SettingRepository(session)
        self._flags = FeatureFlagRepository(session)
        self._audit = AuditService(session)

    # --- Settings ------------------------------------------------------------
    async def list_settings(self, organization_id: int) -> list[Setting]:
        return await self._settings.list_visible(organization_id)

    async def update_settings(
        self, *, organization_id: int, actor: User, values: dict[str, Any]
    ) -> list[Setting]:
        for key, value in values.items():
            await self._settings.upsert_org(
                organization_id=organization_id,
                key=key,
                value=value,
                value_type=_infer_value_type(value),
                updated_by=actor.id,
            )
        await self._audit.record(
            AuditAction.SETTING_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="setting",
            after={"keys": sorted(values.keys())},
        )
        await self._session.commit()
        return await self._settings.list_visible(organization_id)

    # --- User preferences (settings user-scope, Doc 04 §12.1) ----------------
    async def get_preferences(self, user: User) -> dict[str, Any]:
        settings = await self._settings.list_user(user.id)
        return {s.key_name: s.value_json for s in settings}

    async def update_preferences(
        self, *, user: User, preferences: dict[str, Any]
    ) -> dict[str, Any]:
        for key, value in preferences.items():
            await self._settings.upsert_user(
                user_id=user.id,
                organization_id=user.organization_id,
                key=key,
                value=value,
                value_type=_infer_value_type(value),
            )
        await self._audit.record(
            AuditAction.PREFERENCES_UPDATED,
            actor_user_id=user.id,
            organization_id=user.organization_id,
            entity_type="user",
            entity_id=user.id,
            after={"keys": sorted(preferences.keys())},
        )
        await self._session.commit()
        return await self.get_preferences(user)

    # --- Feature flags -------------------------------------------------------
    async def list_flags(self) -> list[FeatureFlag]:
        return await self._flags.list_global()

    async def update_flag(
        self,
        *,
        actor: User,
        key: str,
        is_enabled: bool | None,
        description: str | None,
        rollout: dict[str, Any] | None,
    ) -> FeatureFlag:
        flag = await self._flags.upsert_global(
            key=key, is_enabled=is_enabled, description=description, rollout=rollout
        )
        await self._audit.record(
            AuditAction.FEATURE_FLAG_UPDATED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="feature_flag",
            entity_id=flag.id,
            after={"key": key, "is_enabled": flag.is_enabled},
        )
        await self._session.commit()
        return flag
