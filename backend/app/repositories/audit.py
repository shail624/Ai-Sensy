"""Audit-log repository (Doc 03 §11.2) — append-only.

Only inserts and read-back are permitted; audit rows are immutable (never updated or
deleted), so no mutation helpers are exposed.
"""

from __future__ import annotations

from sqlalchemy import select

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
