"""Audit-log read/query service (Doc 04 §22).

Read-only, cursor-paginated access to the immutable audit trail with actor/entity/action/date
filters. Separate from :class:`AuditService` (which is append-only) to keep the read and write
paths distinct. Actor internal ids are resolved to public UUIDs so internal ids are not leaked.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit import AuditRepository
from app.repositories.user import UserRepository


@dataclass(slots=True)
class AuditPage:
    entries: list[AuditLog]
    actor_uuids: dict[int, str]
    has_more: bool
    total: int


class AuditQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._audit = AuditRepository(session)
        self._users = UserRepository(session)

    async def resolve_actor_id(self, actor_uuid: uuidlib.UUID) -> int | None:
        user = await self._users.get_by_uuid(actor_uuid)
        return user.id if user is not None else None

    async def list_entries(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        actor_user_id: int | None,
        entity_type: str | None,
        action: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> AuditPage:
        entries, has_more = await self._audit.paginate(
            organization_id,
            limit=limit,
            cursor=cursor,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        total = await self._audit.count(
            organization_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        actor_ids = {e.actor_user_id for e in entries if e.actor_user_id is not None}
        actor_uuids: dict[int, str] = {}
        for actor_id in actor_ids:
            user = await self._users.get_by_id(actor_id)
            if user is not None:
                actor_uuids[actor_id] = user.public_id
        return AuditPage(
            entries=entries, actor_uuids=actor_uuids, has_more=has_more, total=total
        )
