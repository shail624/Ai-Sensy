"""Inbound webhook schemas (Doc 04 §23)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.pagination import Page
from app.models.webhook import WebhookDeadLetter, WebhookEvent


class WebhookAckResponse(BaseModel):
    """The body behind a fast ``200``.

    Meta only reads the status code, so this exists for operators and tests: it states how many
    events the delivery was durably split into (Doc 06 §11.2).
    """

    status: str = Field(default="received", examples=["received"])
    events: int = Field(description="Events persisted from this delivery.", examples=[2])


class WebhookEventResponse(BaseModel):
    """One inbound delivery, as an operator needs to see it.

    Deliberately without ``payload_json``. The payload is the provider's raw body -- customer
    phone numbers and message text -- and the Inbox is where that content belongs, behind
    ``inbox:read``. Reproducing it here would create a second, differently-permissioned copy of
    the conversation for the sake of a health screen. What this answers instead is the operational
    question: are deliveries arriving, are their signatures valid, and are they being processed.
    """

    event_id: str | None = Field(
        description="The provider's own id for the event, for cross-referencing their logs."
    )
    object_type: str | None
    status: str
    attempts: int
    signature_ok: bool
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_event(cls, row: WebhookEvent) -> WebhookEventResponse:
        return cls(
            event_id=row.event_id,
            object_type=row.object_type,
            status=row.status,
            attempts=row.attempts,
            signature_ok=row.signature_ok,
            created_at=row.created_at,
            processed_at=row.processed_at,
        )


class WebhookEventsPage(BaseModel):
    data: list[WebhookEventResponse]
    page: Page


class WebhookDeadLetterResponse(BaseModel):
    """An event that could not be processed, and why.

    ``error_detail`` is the one field here worth the surface: without it an operator can see that
    something failed but not what to do about it, which is the difference between a dashboard and
    a diagnosis. The payload stays out for the same reason as above.
    """

    id: uuidlib.UUID
    error_detail: str | None
    attempts: int
    status: str
    created_at: datetime
    replayed_at: datetime | None

    @classmethod
    def from_entry(cls, row: WebhookDeadLetter) -> WebhookDeadLetterResponse:
        return cls(
            id=uuidlib.UUID(row.public_id),
            error_detail=row.error_detail,
            attempts=row.attempts,
            status=row.status,
            created_at=row.created_at,
            replayed_at=row.replayed_at,
        )


class WebhookDeadLetterPage(BaseModel):
    data: list[WebhookDeadLetterResponse]
    page: Page
