"""Contact timeline schemas (Doc 03 §6.5, Doc 04 §14.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.pagination import Page
from app.models.contact_event import ContactEvent


class ContactEventResponse(BaseModel):
    id: int
    type: str = "contact_event"
    event_type: str
    ref_type: str | None
    ref_id: int | None
    payload: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_event(cls, event: ContactEvent) -> ContactEventResponse:
        return cls(
            id=event.id,
            event_type=event.event_type,
            ref_type=event.ref_type,
            ref_id=event.ref_id,
            payload=event.payload_json,
            created_at=event.created_at,
        )


class ContactTimelinePage(BaseModel):
    data: list[ContactEventResponse]
    page: Page
