"""Generic base repository.

Provides the small set of persistence operations every aggregate repository shares
(get-by-id, get-by-uuid, add, delete, flush). Concrete repositories subclass this and add
their domain queries. Kept deliberately thin — no business rules live here (Doc 01 §2.6).
"""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[TModel: Base]:
    """Common async persistence operations for a single model."""

    model: type[TModel]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: int) -> TModel | None:
        return await self.session.get(self.model, entity_id)

    async def get_by_uuid(self, public_id: uuidlib.UUID | bytes) -> TModel | None:
        """Fetch by the public UUIDv7 identifier (models carrying a ``uuid`` column)."""
        raw = public_id.bytes if isinstance(public_id, uuidlib.UUID) else public_id
        stmt = select(self.model).where(self.model.uuid == raw)  # type: ignore[attr-defined]
        return (await self.session.scalars(stmt)).first()

    async def add(self, entity: TModel) -> TModel:
        """Persist a new/dirty entity and flush so identity/defaults are assigned."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: TModel) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()
