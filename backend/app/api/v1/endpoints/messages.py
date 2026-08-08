"""Messaging endpoints (Doc 04 §18.2) — Module 4, outbound send.

``POST /messages/send`` answers ``202``: the send is validated, written to the ledger and handed to
``sends.priority``. The compliance rules (opt-out, the 24-hour window) are enforced in the service,
not here — this layer only decides what a failure looks like over HTTP.

``Idempotency-Key`` is **required** (Doc 04 §8). A retried send is the normal case, not an edge
case: the client that times out waiting for this response has no way to know whether the message
went out, so the key is what lets it ask again safely.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.core import idempotency
from app.core.redis import get_redis_client
from app.models.user import User
from app.schemas.message import (
    MessageAcceptedResponse,
    MessageReactionRequest,
    MessageResponse,
    MessageSendRequest,
    StatusHistoryEntry,
    StatusHistoryResponse,
)
from app.services.message_service import MessageService
from app.services.phone_number_service import PhoneNumberService
from app.services.send_service import SendService

router = APIRouter()

SendActor = Annotated[User, Depends(require_permissions("messages:send"))]
InboxReader = Annotated[User, Depends(require_permissions("inbox:read"))]
IdempotencyKey = Annotated[str, Depends(idempotency.require_key)]


@router.post(
    "/messages/send",
    response_model=MessageAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a message (async)",
)
async def send_message(
    payload: MessageSendRequest,
    session: SessionDep,
    # Declared after the actor on purpose: dependencies resolve in order, and an unauthenticated
    # caller must be told it is unauthenticated — not that its header is malformed.
    actor: SendActor,
    key: IdempotencyKey,
) -> MessageAcceptedResponse:
    from app.channels.tasks import send_message as send_task

    redis = get_redis_client()
    replayed = await idempotency.begin(redis, key)
    if replayed is not None:
        # The original answer, not a second message (Doc 04 §8).
        return MessageAcceptedResponse(**replayed)

    try:
        if payload.conversation_id is not None:
            # A reply to an existing thread — the provider is the conversation's own, never a
            # field on this request (QR-08; see `MessageSendRequest`'s docstring).
            message = await SendService(session).accept_for_conversation(
                organization_id=actor.organization_id,
                actor=actor,
                conversation_public_id=payload.conversation_id,
                message_type=payload.message_type(),
                content=payload.content(),
            )
        else:
            assert payload.phone_number_id is not None and payload.to is not None
            number = await PhoneNumberService(session).get_number(
                actor.organization_id, payload.phone_number_id
            )
            message = await SendService(session).accept(
                organization_id=actor.organization_id,
                actor=actor,
                number=number,
                to=payload.to,
                message_type=payload.message_type(),
                content=payload.content(),
            )
    except Exception:
        # Nothing was accepted, so the key must not answer for a send that never happened.
        await idempotency.release(redis, key)
        raise

    service = MessageService(session)
    response = MessageAcceptedResponse.from_message(
        message, conversation_id=await service.conversation_public_id(message)
    )
    await idempotency.complete(redis, key, response=response.model_dump(mode="json"))
    # After the commit, never before: the task must not outrun the row it reads.
    send_task.apply_async(args=[message.id])
    return response


@router.post(
    "/messages/{message_id}/reaction",
    response_model=MessageAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a reaction emoji (async)",
)
async def send_reaction(
    message_id: uuidlib.UUID,
    payload: MessageReactionRequest,
    session: SessionDep,
    actor: SendActor,
    key: IdempotencyKey,
) -> MessageAcceptedResponse:
    """React to a message, or clear a reaction with an empty emoji (Doc 04 §18.2 v1.4).

    A reaction is free-form (needs the open 24-hour window); it is accepted then delivered through
    SendService → the Meta adapter exactly like a send — ``202`` with ``wamid`` null.
    """
    from app.channels.tasks import send_message as send_task

    redis = get_redis_client()
    replayed = await idempotency.begin(redis, key)
    if replayed is not None:
        return MessageAcceptedResponse(**replayed)

    try:
        message = await SendService(session).react(
            organization_id=actor.organization_id,
            actor=actor,
            target_public_id=message_id,
            emoji=payload.emoji,
        )
    except Exception:
        await idempotency.release(redis, key)
        raise

    service = MessageService(session)
    response = MessageAcceptedResponse.from_message(
        message, conversation_id=await service.conversation_public_id(message)
    )
    await idempotency.complete(redis, key, response=response.model_dump(mode="json"))
    send_task.apply_async(args=[message.id])
    return response


@router.get("/messages/{message_id}", response_model=MessageResponse, summary="Get a message")
async def get_message(
    message_id: uuidlib.UUID, session: SessionDep, actor: InboxReader
) -> MessageResponse:
    service = MessageService(session)
    message = await service.get_message(actor.organization_id, message_id)
    return MessageResponse.from_message(
        message, conversation_id=await service.conversation_public_id(message)
    )


@router.get(
    "/messages/{message_id}/status-history",
    response_model=StatusHistoryResponse,
    summary="Delivery/read/failed timeline",
)
async def message_status_history(
    message_id: uuidlib.UUID, session: SessionDep, actor: InboxReader
) -> StatusHistoryResponse:
    """What the channel told us about this message, in the order it told us (Doc 03 §9.3)."""
    service = MessageService(session)
    message = await service.get_message(actor.organization_id, message_id)
    return StatusHistoryResponse(
        data=[StatusHistoryEntry.from_entry(e) for e in await service.status_history(message)]
    )
