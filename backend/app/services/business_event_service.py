"""Durable-first contact event recording and automation trigger projection."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationTriggerReceipt
from app.models.business_event import (
    BUSINESS_EVENT_CONTACT_CREATED,
    BusinessEvent,
)
from app.models.contact import Contact
from app.repositories.automation import AutomationRepository
from app.repositories.business_event import (
    AutomationTriggerReceiptRepository,
    BusinessEventRepository,
)

CONTACT_CREATED_SCHEMA = "internal://events/contact.created/v1"
CONTACT_EVENT_NAMESPACE = uuidlib.UUID("4798466e-7955-49ae-841d-288cf7e009ec")


class BusinessEventService:
    """Append immutable facts and receipts inside the caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._events = BusinessEventRepository(session)
        self._receipts = AutomationTriggerReceiptRepository(session)
        self._automations = AutomationRepository(session)

    async def record_contact_created(
        self,
        *,
        contact: Contact,
        actor_type: str,
        actor_id: int | None,
        occurred_at: datetime,
        source: str,
    ) -> BusinessEvent:
        event_id = uuidlib.uuid5(
            CONTACT_EVENT_NAMESPACE,
            f"{contact.organization_id}:{contact.public_id}:{BUSINESS_EVENT_CONTACT_CREATED}",
        )
        existing = await self._events.by_event_uuid(contact.organization_id, event_id.bytes)
        if existing is not None:
            return existing

        event = BusinessEvent(
            uuid=event_id.bytes,
            organization_id=contact.organization_id,
            event_type=BUSINESS_EVENT_CONTACT_CREATED,
            event_version=1,
            occurred_at=occurred_at,
            actor_type=actor_type,
            actor_id=actor_id,
            subject_type="contact",
            subject_id=contact.id,
            contact_id=contact.id,
            source=source,
            schema_ref=CONTACT_CREATED_SCHEMA,
            payload_json={
                "contact_id": contact.public_id,
                "source": contact.source,
                "opt_in_status": contact.opt_in_status,
            },
        )
        await self._events.add(event)
        await self._project_automation_receipts(event)
        return event

    async def _project_automation_receipts(self, event: BusinessEvent) -> None:
        candidates = await self._automations.event_candidates(event.organization_id)
        for flow, version in candidates:
            if not self._matches(version.graph_json, event.event_type):
                continue
            if await self._receipts.exists(flow.id, version.id, event.uuid):
                continue
            await self._receipts.add(
                AutomationTriggerReceipt(
                    organization_id=event.organization_id,
                    flow_id=flow.id,
                    version_id=version.id,
                    event_uuid=event.uuid,
                    event_type=event.event_type,
                    event_version=event.event_version,
                    event_occurred_at=event.occurred_at,
                    source=event.source,
                )
            )

    @staticmethod
    def _matches(graph: dict[str, Any], event_type: str) -> bool:
        return any(
            node.get("kind") == "trigger" and node.get("config", {}).get("event") == event_type
            for node in graph.get("nodes", [])
        )
