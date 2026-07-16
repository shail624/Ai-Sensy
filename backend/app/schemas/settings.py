"""Settings and feature-flag schemas (Doc 04 §22)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.settings import FeatureFlag, Setting


class SettingResponse(BaseModel):
    key: str
    value: Any | None
    scope: str
    value_type: str
    is_secret: bool
    updated_at: datetime

    @classmethod
    def from_setting(cls, setting: Setting) -> SettingResponse:
        # Secret values are never returned (Doc 04 §13.2 principle).
        return cls(
            key=setting.key_name,
            value=None if setting.is_secret else setting.value_json,
            scope=setting.scope,
            value_type=setting.value_type,
            is_secret=setting.is_secret,
            updated_at=setting.updated_at,
        )


class SettingsUpdateRequest(BaseModel):
    values: dict[str, Any] = Field(min_length=1)


class FeatureFlagResponse(BaseModel):
    key: str
    description: str | None
    is_enabled: bool
    rollout: dict[str, Any] | None
    updated_at: datetime

    @classmethod
    def from_flag(cls, flag: FeatureFlag) -> FeatureFlagResponse:
        return cls(
            key=flag.key_name,
            description=flag.description,
            is_enabled=flag.is_enabled,
            rollout=flag.rollout_json,
            updated_at=flag.updated_at,
        )


class FeatureFlagPatchRequest(BaseModel):
    is_enabled: bool | None = None
    description: str | None = Field(default=None, max_length=255)
    rollout: dict[str, Any] | None = None
