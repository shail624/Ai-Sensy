"""Conversation endpoints (Doc 04 §18.1) — Shared Inbox.

Two concerns, kept apart in their services:
* **Reads** (Step 2) — the inbox list, one thread's detail (+ window state), and its message
  history. Cursor-paginated, filtered by status/assignee/number and searched by ``q`` exactly as the
  frozen contract defines. Backed by :class:`~app.services.inbox_query_service.InboxQueryService`.
* **Writes** (Steps 1 & 3) — assignment, status, internal notes, and the read-state reset, as
  ``POST``/``DELETE`` action sub-paths. Backed by
  :class:`~app.services.inbox_service.InboxService`. All are permission-scoped; the collaboration
  writes are audited, while ``POST /read`` is an idempotent, unaudited counter reset.

Read state in the frozen schema is exactly the denormalized ``unread_count`` (Doc 03 §9.1) — one
team-shared counter, no last-read marker. ``POST /read`` resets it to zero; the *increment* side
lives on the inbound path (:class:`~app.services.conversation_service.ConversationService`) and is
untouched here. Still out and so not mounted rather than stubbed: mentions, quick replies, and any
real-time transport.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.models.user import User
from app.schemas.conversation import (
    ConversationMessagesPage,
    ConversationResponse,
    ConversationsPage,
)
from app.schemas.inbox import (
    ConversationAssignRequest,
    ConversationReadResponse,
    ConversationStateResponse,
    ConversationStatusRequest,
    NoteCreateRequest,
    NoteResponse,
    NotesListResponse,
)
from app.schemas.message import MessageResponse
from app.services.inbox_query_service import InboxQueryService
from app.services.inbox_service import InboxService

router = APIRouter()

InboxReader = Annotated[User, Depends(require_permissions("inbox:read"))]
InboxWriter = Annotated[User, Depends(require_permissions("inbox:write"))]
InboxAssigner = Annotated[User, Depends(require_permissions("inbox:assign"))]


@router.get("/conversations", response_model=ConversationsPage, summary="Inbox list")
async def list_conversations(
    request: Request, session: SessionDep, actor: InboxReader
) -> ConversationsPage:
    """The inbox, newest activity first (Doc 04 §18.1).

    Cursor-paginated by ``last_message_at``; filtered by status/assignee/number and searched by
    ``q`` (the customer's name or number) — exactly the frozen filter set, nothing more.
    """
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    result = await InboxQueryService(session).list_conversations(
        organization_id=actor.organization_id,
        limit=limit,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
        status=params.get("filter[status][eq]") or params.get("status"),
        assignee=params.get("filter[assignee][eq]") or params.get("assignee"),
        number=params.get("filter[number][eq]") or params.get("number"),
        q=params.get("q"),
    )
    data = [
        ConversationResponse.from_conversation(
            c,
            contact=result.contacts.get(c.contact_id),
            phone_number_public_id=result.numbers.get(c.phone_number_id),
            assigned_to=(
                result.assignees.get(c.assigned_user_id)
                if c.assigned_user_id is not None
                else None
            ),
        )
        for c in result.conversations
    ]
    next_cursor = None
    if result.has_more and result.conversations:
        last = result.conversations[-1]
        # The cursor carries the same effective key the list is ordered by (Doc 04 §18.1).
        next_cursor = encode_cursor(last.last_message_at or last.created_at, last.id)
    return ConversationsPage(
        data=data, page=Page(limit=limit, has_more=result.has_more, next_cursor=next_cursor)
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Conversation detail (+ window state)",
)
async def get_conversation(
    conversation_id: uuidlib.UUID, session: SessionDep, actor: InboxReader
) -> ConversationResponse:
    detail = await InboxQueryService(session).get_conversation(
        organization_id=actor.organization_id, public_id=conversation_id
    )
    return ConversationResponse.from_conversation(
        detail.conversation,
        contact=detail.contact,
        phone_number_public_id=detail.phone_number_public_id,
        assigned_to=detail.assigned_to,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesPage,
    summary="Message history (paginated)",
)
async def list_conversation_messages(
    conversation_id: uuidlib.UUID, request: Request, session: SessionDep, actor: InboxReader
) -> ConversationMessagesPage:
    """A thread's messages, newest first, cursor-paginated over the partitioned ledger."""
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    page = await InboxQueryService(session).list_messages(
        organization_id=actor.organization_id,
        public_id=conversation_id,
        limit=limit,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
    )
    data = [
        MessageResponse.from_message(m, conversation_id=page.conversation_public_id)
        for m in page.messages
    ]
    next_cursor = None
    if page.has_more and page.messages:
        last = page.messages[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return ConversationMessagesPage(
        data=data, page=Page(limit=limit, has_more=page.has_more, next_cursor=next_cursor)
    )


@router.post(
    "/conversations/{conversation_id}/assign",
    response_model=ConversationStateResponse,
    summary="Assign or reassign a conversation",
)
async def assign_conversation(
    conversation_id: uuidlib.UUID,
    payload: ConversationAssignRequest,
    session: SessionDep,
    actor: InboxAssigner,
) -> ConversationStateResponse:
    """Hand a thread to a user. The target must be an active member of the org (else 422)."""
    state = await InboxService(session).assign(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=conversation_id,
        assignee_public_id=payload.assignee_id,
    )
    return ConversationStateResponse.from_state(state)


@router.post(
    "/conversations/{conversation_id}/status",
    response_model=ConversationStateResponse,
    summary="Set conversation status",
)
async def set_conversation_status(
    conversation_id: uuidlib.UUID,
    payload: ConversationStatusRequest,
    session: SessionDep,
    actor: InboxWriter,
) -> ConversationStateResponse:
    """Move the thread to open/pending/resolved/snoozed. Snoozed carries no timer this milestone."""
    state = await InboxService(session).set_status(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=conversation_id,
        status=payload.status,
    )
    return ConversationStateResponse.from_state(state)


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=ConversationReadResponse,
    summary="Mark read (reset unread count)",
)
async def mark_conversation_read(
    conversation_id: uuidlib.UUID, session: SessionDep, actor: InboxWriter
) -> ConversationReadResponse:
    """Reset the thread's shared unread counter to zero (Doc 04 §18.1).

    Read state is the denormalized ``unread_count`` (Doc 03 §9.1); the frozen schema has no last-read
    marker. Idempotent and unaudited — see :meth:`InboxService.mark_read`.
    """
    state = await InboxService(session).mark_read(
        organization_id=actor.organization_id, public_id=conversation_id
    )
    return ConversationReadResponse.from_read_state(state)


@router.get(
    "/conversations/{conversation_id}/notes",
    response_model=NotesListResponse,
    summary="List internal notes",
)
async def list_conversation_notes(
    conversation_id: uuidlib.UUID, session: SessionDep, actor: InboxReader
) -> NotesListResponse:
    notes = await InboxService(session).list_notes(
        organization_id=actor.organization_id, public_id=conversation_id
    )
    return NotesListResponse(data=[NoteResponse.from_view(n) for n in notes])


@router.post(
    "/conversations/{conversation_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an internal note",
)
async def add_conversation_note(
    conversation_id: uuidlib.UUID,
    payload: NoteCreateRequest,
    session: SessionDep,
    actor: InboxWriter,
) -> NoteResponse:
    view = await InboxService(session).add_note(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=conversation_id,
        body=payload.body,
    )
    return NoteResponse.from_view(view)


@router.delete(
    "/conversations/{conversation_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an internal note",
)
async def delete_conversation_note(
    conversation_id: uuidlib.UUID,
    note_id: uuidlib.UUID,
    session: SessionDep,
    actor: InboxWriter,
) -> None:
    await InboxService(session).delete_note(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=conversation_id,
        note_public_id=note_id,
    )
