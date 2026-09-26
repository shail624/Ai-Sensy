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

import uuid as uuidlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.mixins import utcnow
from app.models.webhook import (
    WHDL_DISCARDED,
    WHDL_PENDING,
    WHDL_REPLAYED,
    WebhookDeadLetter,
    WebhookEvent,
)
from app.repositories.webhook import WebhookDeadLetterRepository, WebhookEventRepository
from app.services.audit_service import AuditAction, AuditService


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
        self._session = session
        self._events = WebhookEventRepository(session)
        self._dlq = WebhookDeadLetterRepository(session)
        self._audit = AuditService(session)

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

    # --- Replay and discard (Doc 04 §23) --------------------------------------------------
    async def _owned(self, organization_id: int, public_id: uuidlib.UUID) -> WebhookDeadLetter:
        entry = await self._dlq.get_for_organization(organization_id, public_id.bytes)
        if entry is None:
            raise NotFoundError("Dead-letter entry not found.")
        return entry

    async def replay(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        actor_user_id: int,
        dispatch: Callable[[int], Any],
    ) -> WebhookDeadLetter:
        """Put a parked event back through processing.

        Idempotent by the letter of §23: replaying an entry that is already replayed returns it
        unchanged rather than queueing a second pass. An operator who clicks twice, or a retried
        request, must not double-apply an event whose whole point was that it is applied once.

        §23.1 keeps `webhook_events` 90 days against the dead letter's 180, and "only events still
        within retention are replayable". That rule needs no check here: ownership is read through
        the source event, so once it ages out the entry is not visible to any organization and
        :meth:`_owned` answers 404 — the same answer the listing gives. A 409 saying "too old"
        would have to describe a row the operator was never shown.
        """
        entry = await self._owned(organization_id, public_id)
        if entry.status == WHDL_REPLAYED:
            return entry
        if entry.status == WHDL_DISCARDED:
            raise ConflictError("That entry was discarded and cannot be replayed.")

        source_event_id = entry.source_event_id
        if source_event_id is None:
            # Unreachable through :meth:`_owned`: the ownership clause matches on
            # ``source_event_id IN (...)``, and ``NULL IN (...)`` is never true, so an entry
            # without a source is invisible. Kept as a guard rather than an ``assert`` because
            # asserts vanish under ``python -O`` -- and dispatching ``None`` would queue a task
            # that fails a long way from the mistake.
            raise ConflictError("That entry no longer has a source event to replay.")

        # Queued *before* the entry is marked, which is the opposite of this repository's usual
        # commit-then-dispatch order and is deliberate here. Everywhere else a failed dispatch
        # leaves a job an operator can see is stuck and press again. Here the marking is what makes
        # replay idempotent, so a broker that refused the task after the commit left the entry
        # reading "replayed" with nothing queued -- and the second press, the one that would have
        # fixed it, returned that same row unchanged. The event was then lost in the one queue
        # whose entire purpose is that nothing is lost.
        #
        # Reversed, the two failures are both recoverable: a refused dispatch changes nothing and
        # says so, and a failed commit leaves the entry pending after the task already ran, which
        # costs one redundant pass. ``process_webhook_event`` settles by event id and skips an
        # event already applied (FR-WA-07), so at-least-once here is exactly what it expects.
        dispatch(source_event_id)

        entry.status = WHDL_REPLAYED
        entry.replayed_at = utcnow()
        await self._audit.record(
            AuditAction.WEBHOOK_DEAD_LETTER_REPLAYED,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            entity_type="webhook_dead_letter",
            entity_id=entry.id,
            after={"source_event_id": entry.source_event_id},
        )
        await self._session.commit()
        return entry

    async def discard(
        self, organization_id: int, public_id: uuidlib.UUID, *, actor_user_id: int
    ) -> WebhookDeadLetter:
        """Close a parked event without processing it.

        Discarding an already-discarded entry is a no-op for the same reason replay is. Discarding
        a *replayed* one is refused: the event was applied, and marking it discarded afterwards
        would leave the queue claiming nothing happened when something did.
        """
        entry = await self._owned(organization_id, public_id)
        if entry.status == WHDL_DISCARDED:
            return entry
        if entry.status == WHDL_REPLAYED:
            raise ConflictError("That entry was already replayed and cannot be discarded.")

        entry.status = WHDL_DISCARDED
        await self._audit.record(
            AuditAction.WEBHOOK_DEAD_LETTER_DISCARDED,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            entity_type="webhook_dead_letter",
            entity_id=entry.id,
            before={"status": WHDL_PENDING},
            after={"status": WHDL_DISCARDED},
        )
        await self._session.commit()
        return entry
