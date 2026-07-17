"""Quick-reply schemas (Doc 04 §18.2; Doc 03 §9.5) — Phase 7 Step 4.

Request/response shapes for the canned-message CRUD. Lengths mirror the frozen columns
(``shortcut`` 60, ``title`` 120); ``body`` follows the note-body convention (≤4096). ``shared``
selects the ``owner_user_id`` semantics — ``true`` = org-wide, ``false`` (default) = personal.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.quick_reply import SHORTCUT_LENGTH, TITLE_LENGTH
from app.services.quick_reply_service import QuickReplyView

#: ``body`` is TEXT in the schema; capped here as internal notes are, to bound request size.
BODY_MAX = 4096


class QuickReplyCreateRequest(BaseModel):
    """Create a personal or shared quick reply (Doc 04 §18.2)."""

    shortcut: str = Field(min_length=1, max_length=SHORTCUT_LENGTH)
    title: str = Field(min_length=1, max_length=TITLE_LENGTH)
    body: str = Field(min_length=1, max_length=BODY_MAX)
    #: ``true`` = shared org-wide (``owner_user_id`` NULL); ``false`` = personal to the caller.
    shared: bool = False


class QuickReplyUpdateRequest(BaseModel):
    """Edit a quick reply (Doc 04 §18.2). Every field optional — only those present change."""

    shortcut: str | None = Field(default=None, min_length=1, max_length=SHORTCUT_LENGTH)
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_LENGTH)
    body: str | None = Field(default=None, min_length=1, max_length=BODY_MAX)


class QuickReplyResponse(BaseModel):
    """A quick reply as returned by the CRUD endpoints (Doc 04 §18.2)."""

    id: str
    shortcut: str
    title: str
    body: str
    #: ``true`` when org-wide (no owner); ``false`` when personal.
    shared: bool
    #: Denormalized use counter, surfaced read-only (Doc 03 §9.5).
    usage_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, view: QuickReplyView) -> QuickReplyResponse:
        return cls(
            id=view.public_id,
            shortcut=view.shortcut,
            title=view.title,
            body=view.body,
            shared=view.shared,
            usage_count=view.usage_count,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class QuickRepliesListResponse(BaseModel):
    """The visible quick replies (Doc 04 §3 envelope). Bounded per org — not paginated."""

    data: list[QuickReplyResponse]
