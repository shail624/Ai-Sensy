"""Conversation-tag junction (Doc 03 §9.7) — Phase 7 Step 5.

The M:N link between conversations and the shared ``tags`` taxonomy (§6.2), an exact mirror of
``contact_tags``: a Core association table (no ORM entity), composite PK, and a reverse index
``(tag_id, conversation_id)`` for the inbox by-tag filter. No soft delete — removing a tag
hard-deletes the join row; ``tagged_at``/``tagged_by`` carry lightweight attribution.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Table

from app.db.base import Base
from app.db.mixins import utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

# --- conversations ↔ tags junction (Doc 03 §9.7) ----------------------------
conversation_tags = Table(
    "conversation_tags",
    Base.metadata,
    Column(
        "conversation_id",
        big_id(),
        ForeignKey("conversations.id", name="fk_convtag_conversation", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "tag_id",
        big_id(),
        ForeignKey("tags.id", name="fk_convtag_tag", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column("tagged_at", datetime6(), nullable=False, default=utcnow),
    Column("tagged_by", big_id(), nullable=True),
    Index("ix_convtag_tag", "tag_id", "conversation_id"),
    **MYSQL_TABLE_ARGS,
)
