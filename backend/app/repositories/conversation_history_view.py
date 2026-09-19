"""Persistence queries for organization-shared Chat History views."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import func, select

from app.models.conversation_history_view import ConversationHistoryView
from app.repositories.base import BaseRepository


class ConversationHistoryViewRepository(BaseRepository[ConversationHistoryView]):
    model = ConversationHistoryView

    async def list_for_org(
        self, organization_id: int, *, include_audit: bool
    ) -> list[ConversationHistoryView]:
        stmt = select(ConversationHistoryView).where(
            ConversationHistoryView.organization_id == organization_id
        )
        rows = list(
            (
                await self.session.scalars(
                    stmt.order_by(
                        ConversationHistoryView.name,
                        ConversationHistoryView.id,
                    )
                )
            ).all()
        )
        if include_audit:
            return rows
        return [row for row in rows if not bool(row.filters_json.get("has_audit"))]

    async def count_for_org(self, organization_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ConversationHistoryView)
            .where(ConversationHistoryView.organization_id == organization_id)
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def name_exists(self, organization_id: int, name: str) -> bool:
        stmt = select(ConversationHistoryView.id).where(
            ConversationHistoryView.organization_id == organization_id,
            func.lower(ConversationHistoryView.name) == name.strip().lower(),
        )
        return (await self.session.scalar(stmt)) is not None

    async def get_for_org(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> ConversationHistoryView | None:
        stmt = select(ConversationHistoryView).where(
            ConversationHistoryView.organization_id == organization_id,
            ConversationHistoryView.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()
