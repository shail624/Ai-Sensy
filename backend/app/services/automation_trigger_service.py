"""Read-only automation trigger receipt history."""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.automation import AutomationRepository
from app.repositories.business_event import AutomationTriggerReceiptRepository


@dataclass(frozen=True, slots=True)
class AutomationTriggerReceiptView:
    id: str
    event_id: str
    event_type: str
    event_version: int
    version_no: int
    status: str
    source: str | None
    occurred_at: datetime
    received_at: datetime


class AutomationTriggerService:
    def __init__(self, session: AsyncSession) -> None:
        self._automations = AutomationRepository(session)
        self._receipts = AutomationTriggerReceiptRepository(session)

    async def list_receipts(
        self,
        *,
        organization_id: int,
        automation_id: uuidlib.UUID,
        limit: int,
    ) -> list[AutomationTriggerReceiptView]:
        flow = await self._automations.get_by_public_id(organization_id, automation_id.bytes)
        if flow is None:
            raise NotFoundError("Automation not found.")
        rows = await self._receipts.list_for_flow(organization_id, flow.id, limit=limit)
        return [
            AutomationTriggerReceiptView(
                id=receipt.public_id,
                event_id=str(uuidlib.UUID(bytes=receipt.event_uuid)),
                event_type=receipt.event_type,
                event_version=receipt.event_version,
                version_no=version_no,
                status=receipt.status,
                source=receipt.source,
                occurred_at=receipt.event_occurred_at,
                received_at=receipt.received_at,
            )
            for receipt, version_no in rows
        ]
