"""Append-only business-event and automation receipt persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.models.automation import AutomationFlowVersion, AutomationTriggerReceipt
from app.models.business_event import BusinessEvent
from app.repositories.base import BaseRepository


class BusinessEventRepository(BaseRepository[BusinessEvent]):
    model = BusinessEvent

    async def by_event_uuid(self, organization_id: int, event_uuid: bytes) -> BusinessEvent | None:
        stmt = select(BusinessEvent).where(
            BusinessEvent.organization_id == organization_id,
            BusinessEvent.uuid == event_uuid,
        )
        return (await self.session.scalars(stmt)).first()


class AutomationTriggerReceiptRepository(BaseRepository[AutomationTriggerReceipt]):
    model = AutomationTriggerReceipt

    async def exists(self, flow_id: int, version_id: int, event_uuid: bytes) -> bool:
        stmt = select(AutomationTriggerReceipt.id).where(
            AutomationTriggerReceipt.flow_id == flow_id,
            AutomationTriggerReceipt.version_id == version_id,
            AutomationTriggerReceipt.event_uuid == event_uuid,
        )
        return (await self.session.scalar(stmt)) is not None

    async def list_for_flow(
        self, organization_id: int, flow_id: int, *, limit: int
    ) -> list[tuple[AutomationTriggerReceipt, int]]:
        stmt = (
            select(AutomationTriggerReceipt, AutomationFlowVersion.version_no)
            .join(
                AutomationFlowVersion,
                AutomationFlowVersion.id == AutomationTriggerReceipt.version_id,
            )
            .where(
                AutomationTriggerReceipt.organization_id == organization_id,
                AutomationTriggerReceipt.flow_id == flow_id,
            )
            .order_by(
                AutomationTriggerReceipt.received_at.desc(),
                AutomationTriggerReceipt.id.desc(),
            )
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).tuples().all())
