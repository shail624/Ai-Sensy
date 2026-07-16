"""Contact repository (Doc 03 §6.1).

Keyset (cursor) pagination over the whitelisted, indexed sort columns (Doc 04 §6/§7.2):
``created_at`` (default), ``full_name``, ``last_inbound_at``. Nullable sort columns order
NULLs last with a correct compound keyset predicate. Search covers name/phone/email/wa_id.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select

from app.core.exceptions import BadRequestError
from app.models.contact import Contact
from app.repositories.base import BaseRepository

_SORT_COLUMNS = {
    "created_at": Contact.created_at,
    "full_name": Contact.full_name,
    "last_inbound_at": Contact.last_inbound_at,
}
_NULLABLE_SORTS = {"full_name", "last_inbound_at"}


class ContactRepository(BaseRepository[Contact]):
    model = Contact

    @staticmethod
    def parse_sort(sort: str | None) -> tuple[str, bool]:
        raw = (sort or "-created_at").strip()
        descending = raw.startswith("-")
        name = raw[1:] if descending else raw
        if name not in _SORT_COLUMNS:
            raise BadRequestError(f"Cannot sort by {name!r}.")
        return name, descending

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> Contact | None:
        stmt = select(Contact).where(
            Contact.organization_id == organization_id,
            Contact.uuid == public_id,
            Contact.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_active_by_wa_id(self, organization_id: int, wa_id: str) -> Contact | None:
        """Fetch a live contact by its dedup key (import merge/overwrite path)."""
        stmt = select(Contact).where(
            Contact.organization_id == organization_id,
            Contact.wa_id == wa_id,
            Contact.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def wa_id_exists(self, organization_id: int, wa_id: str) -> bool:
        """Dedup guard — matches the ``(organization_id, wa_id)`` unique key incl. soft-deleted."""
        stmt = select(Contact.id).where(
            Contact.organization_id == organization_id, Contact.wa_id == wa_id
        )
        return (await self.session.scalars(stmt)).first() is not None

    def _filters(
        self,
        organization_id: int,
        *,
        q: str | None,
        opt_in_status: list[str] | None,
        source: str | None,
        is_active_on_wa: bool | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list:
        clauses = [Contact.organization_id == organization_id, Contact.deleted_at.is_(None)]
        if q:
            text = q.strip()
            like = f"%{text.lower()}%"
            clauses.append(
                or_(
                    func.lower(Contact.full_name).like(like),
                    func.lower(Contact.email).like(like),
                    Contact.phone_e164.like(f"%{text}%"),
                    Contact.wa_id.like(f"%{text}%"),
                )
            )
        if opt_in_status:
            clauses.append(Contact.opt_in_status.in_(opt_in_status))
        if source:
            clauses.append(Contact.source == source)
        if is_active_on_wa is not None:
            clauses.append(Contact.is_active_on_wa.is_(is_active_on_wa))
        if created_from is not None:
            clauses.append(Contact.created_at >= created_from)
        if created_to is not None:
            clauses.append(Contact.created_at <= created_to)
        return clauses

    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        sort: str | None,
        cursor: tuple[Any, int, bool] | None,
        q: str | None = None,
        opt_in_status: list[str] | None = None,
        source: str | None = None,
        is_active_on_wa: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Contact], bool, str]:
        """Keyset page; returns (rows, has_more, sort_name)."""
        name, descending = self.parse_sort(sort)
        column = _SORT_COLUMNS[name]
        nullable = name in _NULLABLE_SORTS
        clauses = self._filters(
            organization_id,
            q=q,
            opt_in_status=opt_in_status,
            source=source,
            is_active_on_wa=is_active_on_wa,
            created_from=created_from,
            created_to=created_to,
        )
        if cursor is not None:
            value, last_id, value_is_null = cursor
            if descending:
                before, tie = column < value, and_(column == value, Contact.id < last_id)
                null_tail = and_(column.is_(None), Contact.id < last_id)
            else:
                before, tie = column > value, and_(column == value, Contact.id > last_id)
                null_tail = and_(column.is_(None), Contact.id > last_id)
            if not nullable:
                clauses.append(or_(before, tie))
            elif value_is_null:
                clauses.append(null_tail)
            else:
                # remaining non-null rows, then all NULLs (NULLS LAST)
                clauses.append(or_(before, tie, column.is_(None)))

        order: list = []
        if nullable:
            order.append(column.is_(None))  # False (non-null) first → NULLs last
        order.append(column.desc() if descending else column.asc())
        order.append(Contact.id.desc() if descending else Contact.id.asc())

        stmt = select(Contact).where(*clauses).order_by(*order).limit(limit + 1)
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit, name

    async def count(
        self,
        organization_id: int,
        *,
        q: str | None = None,
        opt_in_status: list[str] | None = None,
        source: str | None = None,
        is_active_on_wa: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        clauses = self._filters(
            organization_id,
            q=q,
            opt_in_status=opt_in_status,
            source=source,
            is_active_on_wa=is_active_on_wa,
            created_from=created_from,
            created_to=created_to,
        )
        stmt = select(func.count()).select_from(Contact).where(*clauses)
        return int((await self.session.scalar(stmt)) or 0)
