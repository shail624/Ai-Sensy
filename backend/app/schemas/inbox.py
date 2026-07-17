"""Shared-inbox schemas (Doc 04 §18.1) — Phase 7 Step 1.

Assignment, status and internal notes. The read/list, search and counter surfaces are a later
milestone; nothing here describes them.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.inbox_service import ConversationState, NoteView

#: The four statuses ``ck_conv_status`` permits (Doc 03 §9.1). A value outside this set is a 422 at
#: request parsing, before the service is reached.
ConversationStatusName = Literal["open", "pending", "resolved", "snoozed"]


class ConversationAssignRequest(BaseModel):
    """Assign or reassign a conversation to a user (Doc 04 §18.1)."""

    assignee_id: uuidlib.UUID


class ConversationStatusRequest(BaseModel):
    """Move a conversation's status (Doc 04 §18.1)."""

    status: ConversationStatusName


class ConversationStateResponse(BaseModel):
    """A conversation after an assignment or status transition (Doc 04 §18.1)."""

    id: str
    status: str
    #: Assignee's public id, or ``null`` when unassigned.
    assigned_to: str | None
    row_version: int
    updated_at: datetime

    @classmethod
    def from_state(cls, state: ConversationState) -> ConversationStateResponse:
        return cls(
            id=state.public_id,
            status=state.status,
            assigned_to=state.assigned_to,
            row_version=state.row_version,
            updated_at=state.updated_at,
        )


class NoteCreateRequest(BaseModel):
    """Add a staff-only note (Doc 04 §18.1)."""

    body: str = Field(min_length=1, max_length=4096)


class NoteResponse(BaseModel):
    """One internal note (Doc 03 §9.5)."""

    id: str
    #: Author's public id.
    author: str | None
    body: str
    created_at: datetime

    @classmethod
    def from_view(cls, view: NoteView) -> NoteResponse:
        return cls(
            id=view.public_id, author=view.author, body=view.body, created_at=view.created_at
        )


class NotesListResponse(BaseModel):
    data: list[NoteResponse]
