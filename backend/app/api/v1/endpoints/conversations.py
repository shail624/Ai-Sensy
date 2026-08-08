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

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import MAX_LIMIT, Page, clamp_limit, decode_cursor, encode_cursor
from app.channels.capabilities import CONNECTOR_META_CLOUD
from app.core.exceptions import BadRequestError
from app.models.user import User
from app.schemas.conversation import (
    ConversationMessagesPage,
    ConversationResponse,
    ConversationsPage,
)
from app.schemas.conversation_tag import ConversationTagsRequest, ConversationTagsResponse
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
from app.schemas.tag import TagSummary
from app.services.conversation_tag_service import ConversationTagService
from app.services.inbox_query_service import InboxQueryService
from app.services.inbox_service import InboxService

router = APIRouter()

InboxReader = Annotated[User, Depends(require_permissions("inbox:read"))]
InboxWriter = Annotated[User, Depends(require_permissions("inbox:write"))]
InboxAssigner = Annotated[User, Depends(require_permissions("inbox:assign"))]


@router.get("/conversations", response_model=ConversationsPage, summary="Inbox list")
async def list_conversations(
    session: SessionDep,
    actor: InboxReader,
    limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    cursor: Annotated[str | None, Query()] = None,
    contact: Annotated[str | None, Query()] = None,
    status_eq: Annotated[str | None, Query(alias="status")] = None,
    assignee: Annotated[str | None, Query()] = None,
    number: Annotated[str | None, Query()] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    filter_status: Annotated[str | None, Query(alias="filter[status][eq]")] = None,
    filter_assignee: Annotated[str | None, Query(alias="filter[assignee][eq]")] = None,
    filter_number: Annotated[str | None, Query(alias="filter[number][eq]")] = None,
    filter_tag: Annotated[list[str] | None, Query(alias="filter[tag][eq]")] = None,
) -> ConversationsPage:
    """The inbox, newest activity first (Doc 04 §18.1).

    Cursor-paginated by ``last_message_at``; filtered by status/assignee/number and searched by
    ``q`` (the customer's name or number) — exactly the frozen filter set, nothing more.

    Both spellings of each filter are accepted and declared: the short form (``status=open``) and
    the frozen bracket form (``filter[status][eq]=open``), the bracket form winning when both are
    sent. Declaring them as parameters (rather than reading them off the raw request) is what puts
    them in the OpenAPI contract, so the generated client can express them.
    """
    # The `tag` filter is single-valued (Doc 04 §18.1 v1.3); more than one tag is a 400.
    tag_values = filter_tag or tag or []
    if len(tag_values) > 1:
        raise BadRequestError(
            "The tag filter accepts a single tag; multi-tag filtering is not supported."
        )
    page_limit = clamp_limit(str(limit) if limit is not None else None)
    result = await InboxQueryService(session).list_conversations(
        organization_id=actor.organization_id,
        limit=page_limit,
        cursor=decode_cursor(cursor) if cursor else None,
        contact=contact,
        status=filter_status or status_eq,
        assignee=filter_assignee or assignee,
        number=filter_number or number,
        tag=tag_values[0] if tag_values else None,
        q=q,
    )
    data = [
        ConversationResponse.from_conversation(
            c,
            contact=result.contacts.get(c.contact_id),
            phone_number_public_id=(
                result.numbers.get(c.phone_number_id) if c.phone_number_id is not None else None
            ),
            assigned_to=(
                result.assignees.get(c.assigned_user_id)
                if c.assigned_user_id is not None
                else None
            ),
            tags=result.tags.get(c.id, []),
            connector_type=(
                result.endpoint_connectors.get(c.channel_endpoint_id, CONNECTOR_META_CLOUD)
                if c.channel_endpoint_id is not None
                else CONNECTOR_META_CLOUD
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
        data=data, page=Page(limit=page_limit, has_more=result.has_more, next_cursor=next_cursor)
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
        tags=detail.tags,
        connector_type=detail.connector_type,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesPage,
    summary="Message history (paginated)",
)
async def list_conversation_messages(
    conversation_id: uuidlib.UUID,
    session: SessionDep,
    actor: InboxReader,
    limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> ConversationMessagesPage:
    """A thread's messages, newest first, cursor-paginated over the partitioned ledger."""
    page_limit = clamp_limit(str(limit) if limit is not None else None)
    page = await InboxQueryService(session).list_messages(
        organization_id=actor.organization_id,
        public_id=conversation_id,
        limit=page_limit,
        cursor=decode_cursor(cursor) if cursor else None,
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
        data=data, page=Page(limit=page_limit, has_more=page.has_more, next_cursor=next_cursor)
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


@router.post(
    "/conversations/{conversation_id}/tags",
    response_model=ConversationTagsResponse,
    summary="Add tag(s) to a conversation",
)
async def add_conversation_tags(
    conversation_id: uuidlib.UUID,
    payload: ConversationTagsRequest,
    session: SessionDep,
    actor: InboxWriter,
) -> ConversationTagsResponse:
    """Attach existing org tags to a thread (Doc 04 §18.1 v1.3).

    Idempotent — a tag already present is a no-op; returns the thread's full tag set. Unknown/foreign
    tag → 422; unknown conversation → 404.
    """
    tags = await ConversationTagService(session).add_tags(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=conversation_id,
        tag_uuids=payload.tag_ids,
    )
    return ConversationTagsResponse(data=[TagSummary.from_tag(t) for t in tags])


@router.delete(
    "/conversations/{conversation_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a tag from a conversation",
)
async def remove_conversation_tag(
    conversation_id: uuidlib.UUID,
    tag_id: uuidlib.UUID,
    session: SessionDep,
    actor: InboxWriter,
) -> None:
    """Detach a tag from a thread (Doc 04 §18.1 v1.3). 404 if the conversation or association is absent."""
    await ConversationTagService(session).remove_tag(
        organization_id=actor.organization_id,
        public_id=conversation_id,
        tag_public_id=tag_id,
    )
