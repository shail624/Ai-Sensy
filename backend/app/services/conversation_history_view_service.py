"""Governed lifecycle for organization-shared Chat History filter views."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.conversation_history_view import ConversationHistoryView
from app.models.organization import Organization
from app.models.user import User
from app.repositories.conversation_history_view import ConversationHistoryViewRepository
from app.schemas.conversation_history import ConversationHistoryViewCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.rbac_service import RBACService

MAX_SHARED_HISTORY_VIEWS = 25


class ConversationHistoryViewService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ConversationHistoryViewRepository(session)
        self._audit = AuditService(session)
        self._rbac = RBACService(session)

    async def list(self, actor: User) -> list[ConversationHistoryView]:
        include_audit = await self._rbac.has_permissions(actor, {"audit:read"})
        return await self._repo.list_for_org(actor.organization_id, include_audit=include_audit)

    async def create(
        self, actor: User, payload: ConversationHistoryViewCreate
    ) -> ConversationHistoryView:
        await self._lock_org(actor.organization_id)
        if payload.filters.has_audit and not await self._rbac.has_permissions(
            actor, {"audit:read"}
        ):
            raise ForbiddenError("Audit-scoped views require audit:read permission.")
        if await self._repo.count_for_org(actor.organization_id) >= MAX_SHARED_HISTORY_VIEWS:
            raise ValidationError(
                f"An organization can save at most {MAX_SHARED_HISTORY_VIEWS} shared Chat History views."
            )
        if await self._repo.name_exists(actor.organization_id, payload.name):
            raise ConflictError(
                f"A shared Chat History view named {payload.name!r} already exists."
            )
        filters = payload.filters.model_dump(mode="json", by_alias=True, exclude_none=True)
        row = ConversationHistoryView(
            organization_id=actor.organization_id,
            created_by_user_id=actor.id,
            name=payload.name,
            filters_json=filters,
        )
        await self._repo.add(row)
        await self._audit.record(
            AuditAction.CONVERSATION_HISTORY_VIEW_CREATED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="conversation_history_view",
            entity_id=row.id,
            after={"name": row.name, "filters": filters},
        )
        await self._session.commit()
        return row

    async def delete(self, actor: User, public_id: uuidlib.UUID) -> None:
        row = await self._repo.get_for_org(actor.organization_id, public_id)
        if row is None:
            raise NotFoundError("Shared Chat History view not found.")
        before = {"name": row.name, "filters": row.filters_json}
        row_id = row.id
        await self._repo.delete(row)
        await self._audit.record(
            AuditAction.CONVERSATION_HISTORY_VIEW_DELETED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="conversation_history_view",
            entity_id=row_id,
            before=before,
        )
        await self._session.commit()

    async def _lock_org(self, organization_id: int) -> None:
        await self._session.execute(
            select(Organization.id).where(Organization.id == organization_id).with_for_update()
        )
