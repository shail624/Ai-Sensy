"""Persistence queries for the shared governed-workspace view store."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import and_, func, or_, select

from app.models.reactivation_view import WorkspaceView
from app.repositories.base import BaseRepository


class WorkspaceViewRepository(BaseRepository[WorkspaceView]):
    model = WorkspaceView

    async def list_visible(
        self, organization_id: int, actor_user_id: int, workspace: str
    ) -> list[WorkspaceView]:
        stmt = (
            select(WorkspaceView)
            .where(
                WorkspaceView.organization_id == organization_id,
                WorkspaceView.workspace == workspace,
                or_(
                    WorkspaceView.visibility == "shared",
                    and_(
                        WorkspaceView.visibility == "private",
                        WorkspaceView.created_by_user_id == actor_user_id,
                    ),
                ),
            )
            .order_by(
                WorkspaceView.visibility.desc(),
                func.lower(WorkspaceView.name),
                WorkspaceView.id,
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_scope(
        self,
        organization_id: int,
        visibility: str,
        workspace: str,
        *,
        actor_user_id: int,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(WorkspaceView)
            .where(
                WorkspaceView.organization_id == organization_id,
                WorkspaceView.workspace == workspace,
                WorkspaceView.visibility == visibility,
            )
        )
        if visibility == "private":
            stmt = stmt.where(WorkspaceView.created_by_user_id == actor_user_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def name_exists(
        self,
        organization_id: int,
        visibility: str,
        name: str,
        workspace: str,
        *,
        actor_user_id: int,
    ) -> bool:
        stmt = select(WorkspaceView.id).where(
            WorkspaceView.organization_id == organization_id,
            WorkspaceView.workspace == workspace,
            WorkspaceView.visibility == visibility,
            func.lower(WorkspaceView.name) == name.strip().lower(),
        )
        if visibility == "private":
            stmt = stmt.where(WorkspaceView.created_by_user_id == actor_user_id)
        return (await self.session.scalar(stmt)) is not None

    async def get_for_org(
        self, organization_id: int, public_id: uuidlib.UUID, workspace: str
    ) -> WorkspaceView | None:
        stmt = select(WorkspaceView).where(
            WorkspaceView.organization_id == organization_id,
            WorkspaceView.workspace == workspace,
            WorkspaceView.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()


ReactivationViewRepository = WorkspaceViewRepository
