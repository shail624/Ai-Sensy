"""System settings & feature-flag endpoints (Doc 04 §22).

Reads require ``settings:read``; updates require ``settings:manage`` (Owner superuser
bypasses). ``/settings`` operates on the caller's organization (plus read-only system
settings); feature flags are global.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.settings import (
    FeatureFlagPatchRequest,
    FeatureFlagResponse,
    SettingResponse,
    SettingsUpdateRequest,
)
from app.services.settings_service import SettingsService

router = APIRouter()

SettingsReadActor = Annotated[User, Depends(require_permissions("settings:read"))]
SettingsManageActor = Annotated[User, Depends(require_permissions("settings:manage"))]


@router.get("/settings", response_model=list[SettingResponse], summary="Read system & org settings")
async def get_settings(session: SessionDep, actor: SettingsReadActor) -> list[SettingResponse]:
    settings = await SettingsService(session).list_settings(actor.organization_id)
    return [SettingResponse.from_setting(s) for s in settings]


@router.put("/settings", response_model=list[SettingResponse], summary="Update org settings")
async def update_settings(
    payload: SettingsUpdateRequest, session: SessionDep, actor: SettingsManageActor
) -> list[SettingResponse]:
    settings = await SettingsService(session).update_settings(
        organization_id=actor.organization_id, actor=actor, values=payload.values
    )
    return [SettingResponse.from_setting(s) for s in settings]


@router.get("/feature-flags", response_model=list[FeatureFlagResponse], summary="List feature flags")
async def list_feature_flags(
    session: SessionDep, actor: SettingsReadActor
) -> list[FeatureFlagResponse]:
    flags = await SettingsService(session).list_flags()
    return [FeatureFlagResponse.from_flag(flag) for flag in flags]


@router.patch(
    "/feature-flags/{key}",
    response_model=FeatureFlagResponse,
    summary="Toggle/target a feature flag",
)
async def patch_feature_flag(
    key: str,
    payload: FeatureFlagPatchRequest,
    session: SessionDep,
    actor: SettingsManageActor,
) -> FeatureFlagResponse:
    flag = await SettingsService(session).update_flag(
        actor=actor,
        key=key,
        is_enabled=payload.is_enabled,
        description=payload.description,
        rollout=payload.rollout,
    )
    return FeatureFlagResponse.from_flag(flag)
