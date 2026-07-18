"""Conversation-tag write schemas (Doc 04 §18.1 v1.3) — Phase 7 Step 5.

The add request and its response. Adding references existing tags by uuid (1–50); the response and
the ``tags`` array on conversation reads both use the shared ``TagSummary`` ({id, name, color}).
"""

from __future__ import annotations

import uuid as uuidlib

from pydantic import BaseModel, Field

from app.schemas.tag import TagSummary

#: Per-request batch bound (Doc 04 §18.1 v1.3): a conversation may hold unlimited tags across calls.
MAX_TAGS_PER_REQUEST = 50


class ConversationTagsRequest(BaseModel):
    """Add existing tag(s) to a conversation (Doc 04 §18.1 v1.3)."""

    tag_ids: list[uuidlib.UUID] = Field(min_length=1, max_length=MAX_TAGS_PER_REQUEST)


class ConversationTagsResponse(BaseModel):
    """A conversation's full tag set after an add (Doc 04 §18.1 v1.3)."""

    data: list[TagSummary]
