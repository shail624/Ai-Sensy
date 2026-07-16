"""Contact-event (timeline) repository (Doc 03 §6.5) — append-only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from app.models.contact_event import ContactEvent
from app.repositories.base import BaseRepository


class ContactEventRepository(BaseRepository[ContactEvent]):
    model = ContactEvent

    async def record(self, event: ContactEvent) -> ContactEvent:
        return await self.add(event)

    async def paginate_for_contact(
        self,
        contact_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        event_type: str | None = None,
    ) -> tuple[list[ContactEvent], bool]:
        """Keyset page ordered by (created_at, id) desc; returns (rows, has_more)."""
        clauses = [ContactEvent.contact_id == contact_id]
        if event_type:
            clauses.append(ContactEvent.event_type == event_type)
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                (ContactEvent.created_at < c_created)
                | ((ContactEvent.created_at == c_created) & (ContactEvent.id < c_id))
            )
        stmt = (
            select(ContactEvent)
            .where(*clauses)
            .order_by(ContactEvent.created_at.desc(), ContactEvent.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count_for_contact(self, contact_id: int, *, event_type: str | None = None) -> int:
        clauses = [ContactEvent.contact_id == contact_id]
        if event_type:
            clauses.append(ContactEvent.event_type == event_type)
        stmt = select(func.count()).select_from(ContactEvent).where(*clauses)
        return int((await self.session.scalar(stmt)) or 0)
