"""Settings and feature-flag repositories (Doc 03 §11.5, §11.7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select

from app.models.settings import (
    SCOPE_ORGANIZATION,
    SCOPE_SYSTEM,
    SCOPE_USER,
    FeatureFlag,
    Setting,
)
from app.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    model = Setting

    async def list_visible(self, organization_id: int) -> list[Setting]:
        """System settings plus the caller org's organization-scoped settings."""
        stmt = (
            select(Setting)
            .where(
                or_(
                    Setting.scope == SCOPE_SYSTEM,
                    and_(
                        Setting.scope == SCOPE_ORGANIZATION,
                        Setting.organization_id == organization_id,
                    ),
                )
            )
            .order_by(Setting.scope, Setting.key_name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_org_setting(self, organization_id: int, key: str) -> Setting | None:
        stmt = select(Setting).where(
            Setting.scope == SCOPE_ORGANIZATION,
            Setting.scope_id == organization_id,
            Setting.key_name == key,
        )
        return (await self.session.scalars(stmt)).first()

    async def upsert_org(
        self,
        *,
        organization_id: int,
        key: str,
        value: Any,
        value_type: str,
        updated_by: int | None,
    ) -> Setting:
        setting = await self.get_org_setting(organization_id, key)
        if setting is None:
            setting = Setting(
                scope=SCOPE_ORGANIZATION,
                scope_id=organization_id,
                organization_id=organization_id,
                key_name=key,
            )
            self.session.add(setting)
        setting.value_json = value
        setting.value_type = value_type
        setting.updated_by = updated_by
        await self.session.flush()
        return setting

    # --- User-scope (preferences, Doc 04 §12.1) ------------------------------
    async def list_user(self, user_id: int) -> list[Setting]:
        stmt = select(Setting).where(
            Setting.scope == SCOPE_USER, Setting.scope_id == user_id
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_user_setting(self, user_id: int, key: str) -> Setting | None:
        stmt = select(Setting).where(
            Setting.scope == SCOPE_USER, Setting.scope_id == user_id, Setting.key_name == key
        )
        return (await self.session.scalars(stmt)).first()

    async def upsert_user(
        self,
        *,
        user_id: int,
        organization_id: int,
        key: str,
        value: Any,
        value_type: str,
    ) -> Setting:
        setting = await self.get_user_setting(user_id, key)
        if setting is None:
            setting = Setting(
                scope=SCOPE_USER,
                scope_id=user_id,
                organization_id=organization_id,
                key_name=key,
            )
            self.session.add(setting)
        setting.value_json = value
        setting.value_type = value_type
        setting.updated_by = user_id
        await self.session.flush()
        return setting


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    model = FeatureFlag

    async def list_global(self) -> list[FeatureFlag]:
        stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.organization_id.is_(None))
            .order_by(FeatureFlag.key_name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_global(self, key: str) -> FeatureFlag | None:
        stmt = select(FeatureFlag).where(
            FeatureFlag.key_name == key, FeatureFlag.organization_id.is_(None)
        )
        return (await self.session.scalars(stmt)).first()

    async def upsert_global(
        self,
        *,
        key: str,
        is_enabled: bool | None,
        description: str | None,
        rollout: Any | None,
    ) -> FeatureFlag:
        flag = await self.get_global(key)
        if flag is None:
            flag = FeatureFlag(key_name=key)
            self.session.add(flag)
        if is_enabled is not None:
            flag.is_enabled = is_enabled
        if description is not None:
            flag.description = description
        if rollout is not None:
            flag.rollout_json = rollout
        await self.session.flush()
        return flag
