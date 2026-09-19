"""Shared governance authority for personal and organization workspace views."""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.organization import Organization
from app.models.reactivation_view import WorkspaceView
from app.models.user import User
from app.repositories.reactivation_view import WorkspaceViewRepository
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService

MAX_PRIVATE_WORKSPACE_VIEWS = 25
MAX_SHARED_WORKSPACE_VIEWS = 25


@dataclass(frozen=True)
class WorkspaceViewPolicy:
    """Workspace-specific labels and permissions over the shared persistence policy."""

    workspace: Literal["reactivation", "contacts", "campaigns", "kyc", "reports"]
    label: str
    manage_permission: str
    created_action: str
    deleted_action: str
    entity_type: str


class WorkspaceViewService:
    """Enforce isolation, caps, names, permissions, locking, and audit in one place."""

    def __init__(self, session: AsyncSession, policy: WorkspaceViewPolicy) -> None:
        self._session = session
        self._policy = policy
        self._repo = WorkspaceViewRepository(session)
        self._audit = AuditService(session)
        self._rbac = RBACService(session)

    async def list(self, actor: User) -> tuple[list[WorkspaceView], bool]:
        can_manage_shared = await self.can_manage_shared(actor)
        rows = await self._repo.list_visible(
            actor.organization_id,
            actor.id,
            self._policy.workspace,
        )
        return rows, can_manage_shared

    async def create(
        self,
        actor: User,
        *,
        name: str,
        visibility: Literal["private", "shared"],
        display: Literal["board", "list"],
        filters: dict[str, object],
    ) -> WorkspaceView:
        if visibility == "shared" and not await self.can_manage_shared(actor):
            raise ForbiddenError(self._shared_permission_message())
        await self._lock_org(actor.organization_id)
        maximum = (
            MAX_SHARED_WORKSPACE_VIEWS if visibility == "shared" else MAX_PRIVATE_WORKSPACE_VIEWS
        )
        if (
            await self._repo.count_scope(
                actor.organization_id,
                visibility,
                self._policy.workspace,
                actor_user_id=actor.id,
            )
            >= maximum
        ):
            scope = "organization" if visibility == "shared" else "user"
            raise ValidationError(
                f"A {scope} can save at most {maximum} {visibility} {self._policy.label} views."
            )
        if await self._repo.name_exists(
            actor.organization_id,
            visibility,
            name,
            self._policy.workspace,
            actor_user_id=actor.id,
        ):
            raise ConflictError(
                f"A {visibility} {self._policy.label} view named {name!r} already exists."
            )
        row = WorkspaceView(
            organization_id=actor.organization_id,
            created_by_user_id=actor.id,
            workspace=self._policy.workspace,
            name=name,
            visibility=visibility,
            display=display,
            filters_json=filters,
        )
        await self._repo.add(row)
        await self._audit.record(
            self._policy.created_action,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type=self._policy.entity_type,
            entity_id=row.id,
            after={
                "workspace": row.workspace,
                "name": row.name,
                "visibility": row.visibility,
                "display": row.display,
                "filters": filters,
            },
        )
        await self._session.commit()
        return row

    async def delete(self, actor: User, public_id: uuidlib.UUID) -> None:
        row = await self._repo.get_for_org(
            actor.organization_id,
            public_id,
            self._policy.workspace,
        )
        if row is None or (row.visibility == "private" and row.created_by_user_id != actor.id):
            raise NotFoundError(f"{self._policy.label} view not found.")
        if row.visibility == "shared" and not await self.can_manage_shared(actor):
            raise ForbiddenError(self._shared_permission_message())
        before = {
            "workspace": row.workspace,
            "name": row.name,
            "visibility": row.visibility,
            "display": row.display,
            "filters": row.filters_json,
        }
        row_id = row.id
        await self._repo.delete(row)
        await self._audit.record(
            self._policy.deleted_action,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type=self._policy.entity_type,
            entity_id=row_id,
            before=before,
        )
        await self._session.commit()

    async def can_manage_shared(self, actor: User) -> bool:
        return await self._rbac.has_permissions(actor, {self._policy.manage_permission})

    def _shared_permission_message(self) -> str:
        return f"Shared {self._policy.label} views require {self._policy.manage_permission}."

    async def _lock_org(self, organization_id: int) -> None:
        await self._session.execute(
            select(Organization.id).where(Organization.id == organization_id).with_for_update()
        )
