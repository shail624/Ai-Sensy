"""Contact timeline service (Doc 03 §6.5, FR-CON-14).

Records and reads the contact activity timeline. Events are appended inside the caller's
transaction so the event commits atomically with the action it describes. Referential
integrity to ``contacts`` is enforced here (the partitioned table carries no DB foreign key).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact_event import ContactEvent
from app.repositories.contact_event import ContactEventRepository


class ContactEventService:
    def __init__(self, session: AsyncSession) -> None:
        self._events = ContactEventRepository(session)

    async def record(
        self,
        *,
        organization_id: int,
        contact_id: int,
        event_type: str,
        ref_type: str | None = None,
        ref_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ContactEvent:
        """Append one timeline event (does not commit — shares the caller's transaction)."""
        return await self._events.record(
            ContactEvent(
                organization_id=organization_id,
                contact_id=contact_id,
                event_type=event_type,
                ref_type=ref_type,
                ref_id=ref_id,
                payload_json=payload,
            )
        )

    async def list_for_contact(
        self,
        contact_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        event_type: str | None,
    ) -> tuple[list[ContactEvent], bool, int]:
        events, has_more = await self._events.paginate_for_contact(
            contact_id, limit=limit, cursor=cursor, event_type=event_type
        )
        total = await self._events.count_for_contact(contact_id, event_type=event_type)
        return events, has_more, total
