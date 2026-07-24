"""Segment repository (Doc 03 §6.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.contact import Contact
from app.models.segment import Segment
from app.repositories.base import BaseRepository


class SegmentRepository(BaseRepository[Segment]):
    model = Segment

    async def list_for_org(self, organization_id: int) -> list[Segment]:
        stmt = (
            select(Segment)
            .where(Segment.organization_id == organization_id, Segment.deleted_at.is_(None))
            .order_by(Segment.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> Segment | None:
        stmt = select(Segment).where(
            Segment.organization_id == organization_id,
            Segment.uuid == public_id,
            Segment.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_name(self, organization_id: int, name: str) -> Segment | None:
        stmt = select(Segment).where(
            Segment.organization_id == organization_id,
            Segment.name == name,
            Segment.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    # --- Evaluation over contacts -------------------------------------------
    def _base_clauses(
        self, organization_id: int, condition: ColumnElement[bool] | None
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [
            Contact.organization_id == organization_id,
            Contact.deleted_at.is_(None),
        ]
        if condition is not None:
            clauses.append(condition)
        return clauses

    async def count_matching(
        self, organization_id: int, condition: ColumnElement[bool] | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Contact)
            .where(*self._base_clauses(organization_id, condition))
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def paginate_matching(
        self,
        organization_id: int,
        condition: ColumnElement[bool] | None,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> tuple[list[Contact], bool]:
        """Preview page of matching contacts, keyset-ordered by (created_at, id) desc."""
        clauses = self._base_clauses(organization_id, condition)
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                or_(
                    Contact.created_at < c_created,
                    and_(Contact.created_at == c_created, Contact.id < c_id),
                )
            )
        stmt = (
            select(Contact)
            .where(*clauses)
            .order_by(Contact.created_at.desc(), Contact.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit
