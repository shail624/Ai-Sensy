"""Operator-facing reads over the inbound webhook record (Doc 04 §23).

Separate from :class:`~app.services.webhook_service.WebhookService`, which owns the ingest path.
That service runs on the public, signature-gated route with no authenticated user and must stay
fast enough to ack inside Meta's timeout; this one runs behind ``webhooks:manage`` and answers a
different question entirely -- *is the stream healthy, and if not, why*. Keeping them apart stops
a reporting query from ever being reachable from the ack path.

Both tables are read tenant-scoped even though neither carries an ``organization_id``: see
``_event_organization_clause`` in the repository for where ownership actually lives.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookDeadLetter, WebhookEvent
from app.repositories.webhook import WebhookDeadLetterRepository, WebhookEventRepository


@dataclass(slots=True)
class WebhookEventPage:
    events: list[WebhookEvent]
    has_more: bool
    total: int


@dataclass(slots=True)
class DeadLetterPage:
    entries: list[WebhookDeadLetter]
    has_more: bool
    total: int


class WebhookOperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self._events = WebhookEventRepository(session)
        self._dlq = WebhookDeadLetterRepository(session)

    async def list_events(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None,
    ) -> WebhookEventPage:
        events, has_more = await self._events.paginate(
            organization_id, limit=limit, cursor=cursor, status=status
        )
        total = await self._events.count(organization_id, status=status)
        return WebhookEventPage(events=events, has_more=has_more, total=total)

    async def list_dead_letters(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None,
    ) -> DeadLetterPage:
        entries, has_more = await self._dlq.paginate(
            organization_id, limit=limit, cursor=cursor, status=status
        )
        total = await self._dlq.count(organization_id, status=status)
        return DeadLetterPage(entries=entries, has_more=has_more, total=total)
