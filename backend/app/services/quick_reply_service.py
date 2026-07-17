"""Quick-reply service (Doc 04 §18.2; Doc 03 §9.5) — Phase 7 Step 4.

CRUD for the shared inbox's canned messages, personal and shared (FR-INB-04). The rules the frozen
contract implies, in one place:

* **Visibility** — a caller sees their own personal replies plus every shared one; another user's
  personal reply is invisible, so acting on it by uuid is a ``404`` (never leak its existence).
* **Shared replies are a team resource** — any ``inbox:write`` member may edit or delete them; the
  frozen API grants no elevated role for this.
* **Shortcut uniqueness** — unique within its ``(organization, owner)`` scope; a duplicate on create,
  or on an edit that changes the shortcut, is a ``409`` (Doc 04 §18.2).

Not audited (a canned-message edit is org configuration, not a customer-facing action, and the frozen
spec requires audit only where it says so). No variable expansion, no usage tracking, no sending —
those are the composer/send path, out of scope.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.mixins import utcnow
from app.models.quick_reply import QuickReply
from app.repositories.quick_reply import QuickReplyRepository


class QuickReplyShortcutConflict(ConflictError):
    """The shortcut is already used by a reply in the same scope (Doc 04 §18.2 → 409)."""

    code = "quick_reply_shortcut_conflict"
    title = "Quick Reply Shortcut In Use"


@dataclass(slots=True)
class QuickReplyView:
    """A quick reply as the API renders it (Doc 04 §18.2)."""

    public_id: str
    shortcut: str
    title: str
    body: str
    shared: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, qr: QuickReply) -> QuickReplyView:
        return cls(
            public_id=qr.public_id,
            shortcut=qr.shortcut,
            title=qr.title,
            body=qr.body,
            shared=qr.is_shared,
            usage_count=qr.usage_count,
            created_at=qr.created_at,
            updated_at=qr.updated_at,
        )


class QuickReplyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = QuickReplyRepository(session)

    async def list(self, *, organization_id: int, user_id: int) -> list[QuickReplyView]:
        """The caller's own personal replies plus all shared ones (Doc 04 §18.2)."""
        rows = await self._repo.list_visible(organization_id, user_id)
        return [QuickReplyView.of(r) for r in rows]

    async def create(
        self,
        *,
        organization_id: int,
        user_id: int,
        shortcut: str,
        title: str,
        body: str,
        shared: bool,
    ) -> QuickReplyView:
        """Create a personal (default) or shared canned reply (Doc 04 §18.2)."""
        owner_user_id = None if shared else user_id
        if await self._repo.shortcut_taken(organization_id, owner_user_id, shortcut):
            raise QuickReplyShortcutConflict(
                f"The shortcut {shortcut!r} is already used by a "
                f"{'shared' if shared else 'personal'} quick reply."
            )
        qr = QuickReply(
            organization_id=organization_id,
            owner_user_id=owner_user_id,
            shortcut=shortcut,
            title=title,
            body=body,
            created_by=user_id,
        )
        await self._repo.add(qr)
        await self._session.commit()
        return QuickReplyView.of(qr)

    async def update(
        self,
        *,
        organization_id: int,
        user_id: int,
        public_id: uuidlib.UUID,
        shortcut: str | None,
        title: str | None,
        body: str | None,
    ) -> QuickReplyView:
        """Edit a reply's shortcut/title/body (Doc 04 §18.2). Partial: only provided fields change.

        Scope (personal vs shared) is fixed at creation and not editable here — there is no frozen
        semantics for moving a reply between scopes.
        """
        qr = await self._get_manageable(organization_id, user_id, public_id)
        if shortcut is not None and shortcut != qr.shortcut:
            if await self._repo.shortcut_taken(
                organization_id, qr.owner_user_id, shortcut, exclude_id=qr.id
            ):
                raise QuickReplyShortcutConflict(
                    f"The shortcut {shortcut!r} is already used by a "
                    f"{'shared' if qr.is_shared else 'personal'} quick reply."
                )
            qr.shortcut = shortcut
        if title is not None:
            qr.title = title
        if body is not None:
            qr.body = body
        await self._repo.flush()
        await self._session.commit()
        return QuickReplyView.of(qr)

    async def delete(
        self, *, organization_id: int, user_id: int, public_id: uuidlib.UUID
    ) -> None:
        """Soft-delete a reply (Doc 04 §18.2). Soft, per the ``deleted_at`` column in Doc 03 §9.5."""
        qr = await self._get_manageable(organization_id, user_id, public_id)
        qr.deleted_at = utcnow()
        await self._repo.flush()
        await self._session.commit()

    async def _get_manageable(
        self, organization_id: int, user_id: int, public_id: uuidlib.UUID
    ) -> QuickReply:
        """Fetch a reply the caller may edit/delete, or raise 404.

        A personal reply belonging to another user is invisible to this caller, so a uuid pointing at
        one is a ``404`` — the same answer as a uuid that doesn't exist, so ownership never leaks.
        Shared replies (no owner) are manageable by any ``inbox:write`` member.
        """
        qr = await self._repo.get_active_by_uuid(organization_id, public_id.bytes)
        if qr is None or (qr.owner_user_id is not None and qr.owner_user_id != user_id):
            raise NotFoundError("Quick reply not found.")
        return qr
