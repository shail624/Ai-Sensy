"""Audit-log repository (Doc 03 §11.2) — append-only.

Only inserts and read-back are permitted; audit rows are immutable (never updated or
deleted), so no mutation helpers are exposed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def record(self, entry: AuditLog) -> AuditLog:
        """Append one immutable audit entry."""
        return await self.add(entry)

    async def list_recent(self, limit: int = 50) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    def _filters(
        self,
        organization_id: int,
        *,
        actor_user_id: int | None,
        entity_type: str | None,
        action: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[ColumnElement[bool]]:
        # The org's own events plus system events (organization_id IS NULL).
        clauses: list[ColumnElement[bool]] = [
            or_(AuditLog.organization_id == organization_id, AuditLog.organization_id.is_(None))
        ]
        if actor_user_id is not None:
            clauses.append(AuditLog.actor_user_id == actor_user_id)
        if entity_type:
            clauses.append(AuditLog.entity_type == entity_type)
        if action:
            clauses.append(AuditLog.action == action)
        if date_from is not None:
            clauses.append(AuditLog.created_at >= date_from)
        if date_to is not None:
            clauses.append(AuditLog.created_at <= date_to)
        return clauses

    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        actor_user_id: int | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AuditLog], bool]:
        """Keyset page ordered by (created_at, id) desc; returns (rows, has_more)."""
        clauses = self._filters(
            organization_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                or_(
                    AuditLog.created_at < c_created,
                    (AuditLog.created_at == c_created) & (AuditLog.id < c_id),
                )
            )
        stmt = (
            select(AuditLog)
            .where(*clauses)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count(
        self,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        clauses = self._filters(
            organization_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = select(func.count()).select_from(AuditLog).where(*clauses)
        return int((await self.session.scalar(stmt)) or 0)
