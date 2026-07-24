"""User repository (Doc 03 §4.2)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.role import Role, UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def _list_filters(
        self, organization_id: int, *, is_active: bool | None, role_name: str | None, q: str | None
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [
            User.organization_id == organization_id,
            User.deleted_at.is_(None),
        ]
        if is_active is not None:
            clauses.append(User.is_active.is_(is_active))
        if q:
            like = f"%{q.strip().lower()}%"
            clauses.append(
                or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like))
            )
        if role_name:
            clauses.append(
                User.id.in_(
                    select(UserRole.user_id)
                    .join(Role, Role.id == UserRole.role_id)
                    .where(Role.name == role_name, Role.organization_id == organization_id)
                )
            )
        return clauses

    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        is_active: bool | None = None,
        role_name: str | None = None,
        q: str | None = None,
    ) -> tuple[list[User], bool]:
        """Keyset page ordered by (created_at, id) desc; returns (rows, has_more)."""
        clauses = self._list_filters(
            organization_id, is_active=is_active, role_name=role_name, q=q
        )
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                or_(
                    User.created_at < c_created,
                    and_(User.created_at == c_created, User.id < c_id),
                )
            )
        stmt = (
            select(User)
            .where(*clauses)
            .order_by(User.created_at.desc(), User.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count(
        self,
        organization_id: int,
        *,
        is_active: bool | None = None,
        role_name: str | None = None,
        q: str | None = None,
    ) -> int:
        clauses = self._list_filters(
            organization_id, is_active=is_active, role_name=role_name, q=q
        )
        stmt = select(func.count()).select_from(User).where(*clauses)
        return int((await self.session.scalar(stmt)) or 0)

    async def get_by_email(self, email: str) -> User | None:
        """Look up an active (non-deleted) user by normalized email (login path)."""
        stmt = select(User).where(
            func.lower(User.email) == email.strip().lower(),
            User.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(
            func.lower(User.email) == email.strip().lower(),
            User.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def list_by_organization(self, organization_id: int) -> list[User]:
        stmt = (
            select(User)
            .where(User.organization_id == organization_id, User.deleted_at.is_(None))
            .order_by(User.id)
        )
        return list((await self.session.scalars(stmt)).all())
