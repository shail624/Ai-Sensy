"""Append-only business-event and automation receipt persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select

from app.models.automation import (
    AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
    AUTOMATION_TRIGGER_RECEIPT_RECEIVED,
    AutomationFlowVersion,
    AutomationTriggerReceipt,
)
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

    async def recent_for_subject(
        self,
        *,
        organization_id: int,
        event_type: str,
        subject_type: str,
        subject_id: int,
        since: datetime,
        limit: int = 50,
    ) -> list[BusinessEvent]:
        stmt = (
            select(BusinessEvent)
            .where(
                BusinessEvent.organization_id == organization_id,
                BusinessEvent.event_type == event_type,
                BusinessEvent.subject_type == subject_type,
                BusinessEvent.subject_id == subject_id,
                BusinessEvent.occurred_at >= since,
            )
            .order_by(BusinessEvent.occurred_at.desc(), BusinessEvent.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())


class AutomationTriggerReceiptRepository(BaseRepository[AutomationTriggerReceipt]):
    model = AutomationTriggerReceipt

    async def by_pk(
        self, receipt_id: int, *, for_update: bool = False
    ) -> AutomationTriggerReceipt | None:
        stmt = select(AutomationTriggerReceipt).where(AutomationTriggerReceipt.id == receipt_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def exists(self, flow_id: int, version_id: int, event_uuid: bytes) -> bool:
        stmt = select(AutomationTriggerReceipt.id).where(
            AutomationTriggerReceipt.flow_id == flow_id,
            AutomationTriggerReceipt.version_id == version_id,
            AutomationTriggerReceipt.event_uuid == event_uuid,
        )
        return (await self.session.scalar(stmt)) is not None

    async def by_lineage(
        self, flow_id: int, version_id: int, event_uuid: bytes
    ) -> AutomationTriggerReceipt | None:
        stmt = select(AutomationTriggerReceipt).where(
            AutomationTriggerReceipt.flow_id == flow_id,
            AutomationTriggerReceipt.version_id == version_id,
            AutomationTriggerReceipt.event_uuid == event_uuid,
        )
        return (await self.session.scalars(stmt)).first()

    async def for_event(
        self, organization_id: int, event_uuid: bytes
    ) -> list[AutomationTriggerReceipt]:
        stmt = (
            select(AutomationTriggerReceipt)
            .where(
                AutomationTriggerReceipt.organization_id == organization_id,
                AutomationTriggerReceipt.event_uuid == event_uuid,
            )
            .order_by(AutomationTriggerReceipt.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def dispatchable(
        self,
        *,
        retry_before: datetime,
        limit: int,
    ) -> list[AutomationTriggerReceipt]:
        """Lock new receipts and genuinely stale in-flight receipts for bounded dispatch."""
        stmt = (
            select(AutomationTriggerReceipt)
            .where(
                or_(
                    AutomationTriggerReceipt.status == AUTOMATION_TRIGGER_RECEIPT_RECEIVED,
                    and_(
                        AutomationTriggerReceipt.status
                        == AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
                        AutomationTriggerReceipt.processing_started_at.is_not(None),
                        AutomationTriggerReceipt.processing_started_at <= retry_before,
                    ),
                )
            )
            .order_by(AutomationTriggerReceipt.received_at.asc(), AutomationTriggerReceipt.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(stmt)).all())

    async def ordinal_for_flow(self, flow_id: int, receipt_id: int) -> int:
        """One-based durable receipt position used by deterministic round-robin actions."""
        stmt = (
            select(func.count())
            .select_from(AutomationTriggerReceipt)
            .where(
                AutomationTriggerReceipt.flow_id == flow_id,
                AutomationTriggerReceipt.id <= receipt_id,
            )
        )
        return int((await self.session.scalar(stmt)) or 0)

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
