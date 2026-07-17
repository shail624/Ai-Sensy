"""Conversation collaboration endpoints (Doc 04 §18.1) — Phase 7 Step 1: Shared Inbox Core.

The collaboration layer over the existing conversation primitive: assignment, status, and internal
notes. These are ``POST`` action sub-paths, not ``PATCH``, because they are authorized transitions
with side effects (assignment gates who can act, status drives the inbox), each permission-scoped.

Out of this milestone (and so not mounted rather than stubbed): the inbox list, conversation and
message reads, read/unread state, search, filters and counters. A route that 404s is a clearer
signal than one that returns an empty or misleading body.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.inbox import (
    ConversationAssignRequest,
    ConversationStateResponse,
    ConversationStatusRequest,
    NoteCreateRequest,
    NoteResponse,
    NotesListResponse,
)
from app.services.inbox_service import InboxService

router = APIRouter()

InboxReader = Annotated[User, Depends(require_permissions("inbox:read"))]
InboxWriter = Annotated[User, Depends(require_permissions("inbox:write"))]
InboxAssigner = Annotated[User, Depends(require_permissions("inbox:assign"))]


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
