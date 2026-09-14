"""Typed Campaigns adapter over the shared workspace-view authority."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reactivation_view import WorkspaceView
from app.models.user import User
from app.schemas.campaign import CampaignViewCreate
from app.services.audit_service import AuditAction
from app.services.workspace_view_service import WorkspaceViewPolicy, WorkspaceViewService

MANAGE_SHARED_PERMISSION = "campaigns:views_manage"
POLICY = WorkspaceViewPolicy(
    workspace="campaigns",
    label="Campaigns",
    manage_permission=MANAGE_SHARED_PERMISSION,
    created_action=AuditAction.CAMPAIGN_VIEW_CREATED,
    deleted_action=AuditAction.CAMPAIGN_VIEW_DELETED,
    entity_type="campaign_view",
)


class CampaignViewService:
    def __init__(self, session: AsyncSession) -> None:
        self._service = WorkspaceViewService(session, POLICY)

    async def list(self, actor: User) -> tuple[list[WorkspaceView], bool]:
        return await self._service.list(actor)

    async def create(self, actor: User, payload: CampaignViewCreate) -> WorkspaceView:
        filters = payload.filters.model_dump(mode="json", exclude_none=True)
        return await self._service.create(
            actor,
            name=payload.name,
            visibility=payload.visibility,
            display=payload.display,
            filters=filters,
        )

    async def delete(self, actor: User, public_id: uuidlib.UUID) -> None:
        await self._service.delete(actor, public_id)
