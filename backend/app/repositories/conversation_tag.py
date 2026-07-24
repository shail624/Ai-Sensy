"""Conversation-tag repository (Doc 03 §9.7) — Phase 7 Step 5.

Manages the ``conversation_tags`` junction (Core table, no ORM entity), mirroring
:class:`~app.repositories.tag.ContactTagRepository`. Attach is idempotent; detach reports whether a
row was removed; the batch resolver loads a page's tags in one query (no N+1).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.conversation_tag import conversation_tags
from app.models.tag import Tag
from app.repositories._result import affected_rows


class ConversationTagRepository:
    """Manages the ``conversation_tags`` junction (Core table, no ORM entity)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def attach(self, conversation_id: int, tag_id: int, tagged_by: int | None) -> bool:
        """Attach a tag; returns True if newly attached (idempotent — a present tag is a no-op)."""
        existing = await self.session.scalar(
            select(conversation_tags.c.tag_id).where(
                conversation_tags.c.conversation_id == conversation_id,
                conversation_tags.c.tag_id == tag_id,
            )
        )
        if existing is not None:
            return False
        await self.session.execute(
            insert(conversation_tags).values(
                conversation_id=conversation_id,
                tag_id=tag_id,
                tagged_at=utcnow(),
                tagged_by=tagged_by,
            )
        )
        await self.session.flush()
        return True

    async def detach(self, conversation_id: int, tag_id: int) -> bool:
        """Detach a tag; returns True if a row was removed (hard delete, no soft delete)."""
        result = await self.session.execute(
            delete(conversation_tags).where(
                conversation_tags.c.conversation_id == conversation_id,
                conversation_tags.c.tag_id == tag_id,
            )
        )
        await self.session.flush()
        return bool(affected_rows(result))

    async def tags_for_conversations(
        self, conversation_ids: list[int]
    ) -> dict[int, list[Tag]]:
        """Active tags for each conversation, keyed by conversation id — one query for the page.

        Soft-deleted tags are excluded so a removed tag never surfaces on a thread.
        """
        if not conversation_ids:
            return {}
        stmt = (
            select(conversation_tags.c.conversation_id, Tag)
            .join(Tag, Tag.id == conversation_tags.c.tag_id)
            .where(
                conversation_tags.c.conversation_id.in_(conversation_ids),
                Tag.deleted_at.is_(None),
            )
            .order_by(Tag.name, Tag.id)
        )
        result: dict[int, list[Tag]] = defaultdict(list)
        for conversation_id, tag in (await self.session.execute(stmt)).all():
            result[conversation_id].append(tag)
        return dict(result)
