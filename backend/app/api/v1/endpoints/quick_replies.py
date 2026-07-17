"""Quick-reply endpoints (Doc 04 §18.2) — Shared Inbox canned messages (FR-INB-04).

Personal (owned by the caller) and shared (org-wide) canned replies an agent inserts by ``/shortcut``
in the composer. CRUD only — list (own personal + all shared), create, edit, delete — over the
``quick_replies`` table (Doc 03 §9.5). Reads need ``inbox:read``; writes need ``inbox:write``. A
duplicate shortcut in a scope is a ``409``; a uuid the caller can't see is a ``404``. No sending, no
variable expansion, no usage tracking here — those belong to the composer/send path.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.quick_reply import (
    QuickRepliesListResponse,
    QuickReplyCreateRequest,
    QuickReplyResponse,
    QuickReplyUpdateRequest,
)
from app.services.quick_reply_service import QuickReplyService

router = APIRouter()

InboxReader = Annotated[User, Depends(require_permissions("inbox:read"))]
InboxWriter = Annotated[User, Depends(require_permissions("inbox:write"))]


@router.get(
    "/quick-replies", response_model=QuickRepliesListResponse, summary="List quick replies"
)
async def list_quick_replies(
    session: SessionDep, actor: InboxReader
) -> QuickRepliesListResponse:
    """The caller's personal replies plus all shared ones (Doc 04 §18.2)."""
    views = await QuickReplyService(session).list(
        organization_id=actor.organization_id, user_id=actor.id
    )
    return QuickRepliesListResponse(data=[QuickReplyResponse.of(v) for v in views])


@router.post(
    "/quick-replies",
    response_model=QuickReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quick reply",
)
async def create_quick_reply(
    payload: QuickReplyCreateRequest, session: SessionDep, actor: InboxWriter
) -> QuickReplyResponse:
    """Create a personal (default) or shared canned reply; duplicate shortcut in-scope → 409."""
    view = await QuickReplyService(session).create(
        organization_id=actor.organization_id,
        user_id=actor.id,
        shortcut=payload.shortcut,
        title=payload.title,
        body=payload.body,
        shared=payload.shared,
    )
    return QuickReplyResponse.of(view)


@router.patch(
    "/quick-replies/{quick_reply_id}",
    response_model=QuickReplyResponse,
    summary="Edit a quick reply",
)
async def update_quick_reply(
    quick_reply_id: uuidlib.UUID,
    payload: QuickReplyUpdateRequest,
    session: SessionDep,
    actor: InboxWriter,
) -> QuickReplyResponse:
    """Edit shortcut/title/body (partial). Unknown/foreign uuid → 404; shortcut clash → 409."""
    view = await QuickReplyService(session).update(
        organization_id=actor.organization_id,
        user_id=actor.id,
        public_id=quick_reply_id,
        shortcut=payload.shortcut,
        title=payload.title,
        body=payload.body,
    )
    return QuickReplyResponse.of(view)


@router.delete(
    "/quick-replies/{quick_reply_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a quick reply",
)
async def delete_quick_reply(
    quick_reply_id: uuidlib.UUID, session: SessionDep, actor: InboxWriter
) -> None:
    """Soft-delete a reply (Doc 04 §18.2). Unknown/foreign uuid → 404."""
    await QuickReplyService(session).delete(
        organization_id=actor.organization_id, user_id=actor.id, public_id=quick_reply_id
    )
