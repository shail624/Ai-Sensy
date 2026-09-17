"""Webhook operations reads (Doc 04 §23).

Kept out of ``webhooks.py`` on purpose. That module's whole contract is "everything in here is
public and unauthenticated, gated only by the provider's signature", and that invariant is worth
being able to read off the file. These routes are the opposite: authenticated, permission-gated
and tenant-scoped. They share the ``/webhooks`` prefix because Doc 04 §23 places them there, not
because they share a security model.

Reads require ``webhooks:manage`` (Doc 04 §23), the same permission as replay: there is no
separate read scope in the catalogue, and the audience for "why did this delivery fail" is the
same operator who would act on the answer.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, encode_cursor
from app.models.user import User
from app.models.webhook import WH_STATUSES, WHDL_DISCARDED, WHDL_PENDING, WHDL_REPLAYED
from app.schemas.webhook import (
    WebhookDeadLetterPage,
    WebhookDeadLetterResponse,
    WebhookEventResponse,
    WebhookEventsPage,
)
from app.services.webhook_operations_service import WebhookOperationsService

router = APIRouter(prefix="/webhooks")

WebhookOperator = Annotated[User, Depends(require_permissions("webhooks:manage"))]

EventStatus = Annotated[
    str | None,
    Query(description=f"Filter by delivery status: {', '.join(WH_STATUSES)}."),
]
DeadLetterStatus = Annotated[
    str | None,
    Query(
        description=(
            "Filter by entry status: "
            f"{', '.join((WHDL_PENDING, WHDL_REPLAYED, WHDL_DISCARDED))}."
        )
    ),
]
LimitParam = Annotated[
    int | None, Query(alias="limit", ge=1, le=MAX_LIMIT, description="Page size (default 50).")
]
CursorParam = Annotated[
    str | None, Query(alias="cursor", description="Opaque token from a prior next_cursor.")
]


@router.get("/events", response_model=WebhookEventsPage, summary="List received webhook events")
async def list_webhook_events(
    session: SessionDep,
    actor: WebhookOperator,
    status: EventStatus = None,
    limit_param: LimitParam = None,
    cursor_param: CursorParam = None,
) -> WebhookEventsPage:
    """Inbound deliveries for this organization, newest first.

    The health view for the ingest path: whether deliveries are arriving, whether their signatures
    verified, and whether they reached `processed` or stalled at `received`. Payload bodies are not
    returned — message content belongs to the Inbox, behind `inbox:read`, not to a second copy on
    an operations screen.
    """
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    result = await WebhookOperationsService(session).list_events(
        actor.organization_id,
        limit=limit,
        cursor=decode_cursor(cursor_param) if cursor_param else None,
        status=status,
    )
    next_cursor = (
        encode_cursor(result.events[-1].created_at, result.events[-1].id)
        if result.has_more and result.events
        else None
    )
    return WebhookEventsPage(
        data=[WebhookEventResponse.from_event(row) for row in result.events],
        page=Page(
            limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total
        ),
    )


@router.get(
    "/dead-letter", response_model=WebhookDeadLetterPage, summary="List the dead-letter queue"
)
async def list_webhook_dead_letters(
    session: SessionDep,
    actor: WebhookOperator,
    status: DeadLetterStatus = None,
    limit_param: LimitParam = None,
    cursor_param: CursorParam = None,
) -> WebhookDeadLetterPage:
    """Events that could not be processed, with the error that stopped each one.

    An event reaches this queue after its retries are exhausted (Doc 04 §23.1: capped exponential
    backoff, at most five attempts, then parked as `pending` for a human). Until now nothing
    exposed the queue, so the parking was real but the human was never told — which is the whole
    failure mode this closes.
    """
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    result = await WebhookOperationsService(session).list_dead_letters(
        actor.organization_id,
        limit=limit,
        cursor=decode_cursor(cursor_param) if cursor_param else None,
        status=status,
    )
    next_cursor = (
        encode_cursor(result.entries[-1].created_at, result.entries[-1].id)
        if result.has_more and result.entries
        else None
    )
    return WebhookDeadLetterPage(
        data=[WebhookDeadLetterResponse.from_entry(row) for row in result.entries],
        page=Page(
            limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total
        ),
    )


@router.post(
    "/dead-letter/{entry_id}/replay",
    response_model=WebhookDeadLetterResponse,
    summary="Replay a dead-lettered event",
)
async def replay_dead_letter(
    entry_id: uuidlib.UUID, session: SessionDep, actor: WebhookOperator
) -> WebhookDeadLetterResponse:
    """Put a parked event back through processing.

    Idempotent (Doc 04 §23): replaying an entry that is already replayed returns it unchanged
    rather than queueing a second pass. An operator who clicks twice — or a request the browser
    retried — must not double-apply an event whose whole point was that it applies once.

    Refused once the source event has passed its 90-day retention (§23.1). The payload stays here
    for inspection, but the row the processor works from is gone, and recreating one would make a
    second event out of the same delivery.
    """
    from app.channels.tasks import process_webhook_event

    entry = await WebhookOperationsService(session).replay(
        actor.organization_id,
        entry_id,
        actor_user_id=actor.id,
        dispatch=lambda event_pk: process_webhook_event.apply_async(args=[event_pk]),
    )
    return WebhookDeadLetterResponse.from_entry(entry)


@router.post(
    "/dead-letter/{entry_id}/discard",
    response_model=WebhookDeadLetterResponse,
    summary="Discard a dead-lettered event",
)
async def discard_dead_letter(
    entry_id: uuidlib.UUID, session: SessionDep, actor: WebhookOperator
) -> WebhookDeadLetterResponse:
    """Close a parked event without processing it.

    The queue exists so somebody decides; discarding is that decision written down, and it is
    audited like any other. Discarding an already-replayed entry is refused — the event was
    applied, and recording it as discarded afterwards would leave the queue claiming nothing
    happened when something did.
    """
    entry = await WebhookOperationsService(session).discard(
        actor.organization_id, entry_id, actor_user_id=actor.id
    )
    return WebhookDeadLetterResponse.from_entry(entry)
