"""Organization endpoints (Doc 04 §13.1).

Single-tenant: operates on the caller's own organization. Read requires ``settings:read``;
update requires ``settings:manage`` (Owner superuser bypasses).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdateRequest
from app.services.organization_service import OrganizationService

router = APIRouter()

SettingsReadActor = Annotated[User, Depends(require_permissions("settings:read"))]
SettingsManageActor = Annotated[User, Depends(require_permissions("settings:manage"))]


@router.get("/organization", response_model=OrganizationResponse, summary="Get the current organization")
async def get_organization(session: SessionDep, actor: SettingsReadActor) -> OrganizationResponse:
    org = await OrganizationService(session).get(actor.organization_id)
    return OrganizationResponse.from_org(org)


@router.patch("/organization", response_model=OrganizationResponse, summary="Update the organization")
async def update_organization(
    payload: OrganizationUpdateRequest, session: SessionDep, actor: SettingsManageActor
) -> OrganizationResponse:
    org = await OrganizationService(session).update(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        timezone=payload.timezone,
        default_locale=payload.default_locale,
        settings=payload.settings,
        expected_version=payload.row_version,
    )
    return OrganizationResponse.from_org(org)
