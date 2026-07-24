"""Tag repositories (Doc 03 §6.2)."""

from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.tag import Tag, contact_tags
from app.repositories._result import affected_rows
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    model = Tag

    async def list_for_org(self, organization_id: int) -> list[Tag]:
        stmt = (
            select(Tag)
            .where(Tag.organization_id == organization_id, Tag.deleted_at.is_(None))
            .order_by(Tag.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> Tag | None:
        stmt = select(Tag).where(
            Tag.organization_id == organization_id,
            Tag.uuid == public_id,
            Tag.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_name(self, organization_id: int, name: str) -> Tag | None:
        stmt = select(Tag).where(
            Tag.organization_id == organization_id,
            Tag.name == name,
            Tag.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_uuids(self, organization_id: int, public_ids: list[bytes]) -> list[Tag]:
        if not public_ids:
            return []
        stmt = select(Tag).where(
            Tag.organization_id == organization_id,
            Tag.uuid.in_(public_ids),
            Tag.deleted_at.is_(None),
        )
        return list((await self.session.scalars(stmt)).all())


class ContactTagRepository:
    """Manages the ``contact_tags`` junction (Core table, no ORM entity)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def tag_ids_for_contact(self, contact_id: int) -> set[int]:
        stmt = select(contact_tags.c.tag_id).where(contact_tags.c.contact_id == contact_id)
        return set((await self.session.scalars(stmt)).all())

    async def attach(self, contact_id: int, tag_id: int, tagged_by: int | None) -> bool:
        """Attach a tag; returns True if newly attached (idempotent)."""
        existing = await self.session.scalar(
            select(contact_tags.c.tag_id).where(
                contact_tags.c.contact_id == contact_id, contact_tags.c.tag_id == tag_id
            )
        )
        if existing is not None:
            return False
        await self.session.execute(
            insert(contact_tags).values(
                contact_id=contact_id, tag_id=tag_id, tagged_at=utcnow(), tagged_by=tagged_by
            )
        )
        await self.session.flush()
        return True

    async def detach(self, contact_id: int, tag_id: int) -> bool:
        """Detach a tag; returns True if a row was removed."""
        result = await self.session.execute(
            delete(contact_tags).where(
                contact_tags.c.contact_id == contact_id, contact_tags.c.tag_id == tag_id
            )
        )
        await self.session.flush()
        return bool(affected_rows(result))

    async def detach_tag_everywhere(self, tag_id: int) -> int:
        """Remove a tag from every contact (tag deletion detaches, Doc 04 §14.2)."""
        result = await self.session.execute(
            delete(contact_tags).where(contact_tags.c.tag_id == tag_id)
        )
        await self.session.flush()
        return affected_rows(result)
