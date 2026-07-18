"""Conversation-tag service (Doc 04 §18.1 v1.3; Doc 03 §9.7) — Phase 7 Step 5.

Add/remove classification tags on a conversation, reusing the org ``tags`` taxonomy (§14.2). The
rules the frozen amendment fixes:

* **Existing tags only** — a tag must already exist in the caller's org; a cross-org, unknown, or
  soft-deleted tag is rejected (422). Tag *creation* stays with ``POST /tags`` (``contacts:write``).
* **Idempotent add** — re-adding a present tag is a no-op (never 409); the response is the thread's
  full tag set.
* **Shared team resource** — any ``inbox:write`` member may tag/untag any thread; ``tagged_by``
  records who applied it. Not audited, and ``tags.usage_count`` (a contact-tag counter, §6.2) is left
  untouched — the amendment scopes neither to conversation tagging.
"""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.tag import Tag
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.repositories.conversation_tag import ConversationTagRepository
from app.repositories.tag import TagRepository


class ConversationTagService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._tags = TagRepository(session)
        self._links = ConversationTagRepository(session)

    async def add_tags(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        tag_uuids: list[uuidlib.UUID],
    ) -> list[Tag]:
        """Attach existing tags to a conversation; returns the thread's full tag set (Doc 04 §18.1)."""
        conversation = await self._conversation(organization_id, public_id)
        raw_ids = [t.bytes for t in dict.fromkeys(tag_uuids)]
        tags = await self._tags.get_by_uuids(organization_id, raw_ids)
        if len(tags) != len(raw_ids):
            # Any id not resolved in-org is unknown, cross-org, or soft-deleted — all "no such tag".
            found = {t.uuid for t in tags}
            raise ValidationError(
                "One or more tags do not exist.",
                errors=[
                    {"field": "tag_ids", "code": "unknown_tag", "message": str(uuidlib.UUID(bytes=r))}
                    for r in raw_ids
                    if r not in found
                ],
            )
        for tag in tags:
            await self._links.attach(conversation.id, tag.id, tagged_by=actor.id)
        await self._session.commit()
        current = await self._links.tags_for_conversations([conversation.id])
        return current.get(conversation.id, [])

    async def remove_tag(
        self,
        *,
        organization_id: int,
        public_id: uuidlib.UUID,
        tag_public_id: uuidlib.UUID,
    ) -> None:
        """Detach one tag from a conversation (Doc 04 §18.1).

        A tag that isn't in the org, or isn't attached to this thread, is a 404 — the association the
        caller named does not exist.
        """
        conversation = await self._conversation(organization_id, public_id)
        tag = await self._tags.get_active_by_uuid(organization_id, tag_public_id.bytes)
        if tag is None or not await self._links.detach(conversation.id, tag.id):
            raise NotFoundError("Tag is not attached to this conversation.")
        await self._session.commit()

    async def _conversation(self, organization_id: int, public_id: uuidlib.UUID):
        conversation = await self._conversations.get_active_by_uuid(
            organization_id, public_id.bytes
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation
