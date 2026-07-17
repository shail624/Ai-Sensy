"""Quick-reply repository (Doc 03 §9.5) — queries only, no rules.

The visibility query (own personal + all shared), the org-scoped fetch by uuid, and the
scope-aware shortcut-collision probe that the ``409(shortcut)`` contract (Doc 04 §18.2) rests on.
"""

from __future__ import annotations

from sqlalchemy import or_, select

from app.models.quick_reply import QuickReply
from app.repositories.base import BaseRepository


class QuickReplyRepository(BaseRepository[QuickReply]):
    model = QuickReply

    async def list_visible(self, organization_id: int, user_id: int) -> list[QuickReply]:
        """Active replies the caller may see: their own personal ones + all shared (Doc 04 §18.2).

        Ordered by ``shortcut`` — the token the composer autocompletes on — so the picker is stable.
        """
        stmt = (
            select(QuickReply)
            .where(
                QuickReply.organization_id == organization_id,
                QuickReply.deleted_at.is_(None),
                or_(
                    QuickReply.owner_user_id == user_id,
                    QuickReply.owner_user_id.is_(None),
                ),
            )
            .order_by(QuickReply.shortcut, QuickReply.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> QuickReply | None:
        """One active reply by uuid, constrained to the organization (a foreign uuid is a 404)."""
        stmt = select(QuickReply).where(
            QuickReply.organization_id == organization_id,
            QuickReply.uuid == public_id,
            QuickReply.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def shortcut_taken(
        self,
        organization_id: int,
        owner_user_id: int | None,
        shortcut: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        """Whether an active reply already uses ``shortcut`` in the given scope (Doc 04 §18.2 → 409).

        Scope is ``(organization, owner)`` — the granularity of ``ix_qr_org_owner``: a shared
        shortcut is unique org-wide, a personal one unique per user. Soft-deleted rows don't count,
        so a shortcut frees up once its reply is deleted. ``exclude_id`` lets an edit ignore itself.
        """
        stmt = select(QuickReply.id).where(
            QuickReply.organization_id == organization_id,
            QuickReply.shortcut == shortcut,
            QuickReply.deleted_at.is_(None),
        )
        if owner_user_id is None:
            stmt = stmt.where(QuickReply.owner_user_id.is_(None))
        else:
            stmt = stmt.where(QuickReply.owner_user_id == owner_user_id)
        if exclude_id is not None:
            stmt = stmt.where(QuickReply.id != exclude_id)
        return (await self.session.scalars(stmt)).first() is not None
