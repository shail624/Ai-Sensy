"""Typed Reports adapter over the shared workspace-view authority."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reactivation_view import WorkspaceView
from app.models.user import User
from app.schemas.analytics import ReportViewCreate
from app.services.audit_service import AuditAction
from app.services.workspace_view_service import WorkspaceViewPolicy, WorkspaceViewService

MANAGE_SHARED_PERMISSION = "analytics:views_manage"
POLICY = WorkspaceViewPolicy(
    workspace="reports",
    label="Reports",
    manage_permission=MANAGE_SHARED_PERMISSION,
    created_action=AuditAction.REPORT_VIEW_CREATED,
    deleted_action=AuditAction.REPORT_VIEW_DELETED,
    entity_type="report_view",
)


class ReportViewService:
    def __init__(self, session: AsyncSession) -> None:
        self._service = WorkspaceViewService(session, POLICY)

    async def list(self, actor: User) -> tuple[list[WorkspaceView], bool]:
        return await self._service.list(actor)

    async def create(self, actor: User, payload: ReportViewCreate) -> WorkspaceView:
        filters = payload.filters.model_dump(mode="json", by_alias=True, exclude_none=True)
        return await self._service.create(
            actor,
            name=payload.name,
            visibility=payload.visibility,
            display=payload.display,
            filters=filters,
        )

    async def delete(self, actor: User, public_id: uuidlib.UUID) -> None:
        await self._service.delete(actor, public_id)
