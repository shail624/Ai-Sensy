"""Durable-first contact event recording and automation trigger projection."""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.automation import (
    AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
    AUTOMATION_TRIGGER_RECEIPT_RECEIVED,
    AUTOMATION_WAIT_MATCHED,
    AUTOMATION_WAIT_TIMED_OUT,
    AutomationTriggerReceipt,
)
from app.models.business_event import (
    BUSINESS_EVENT_ACTOR_CONNECTOR,
    BUSINESS_EVENT_ACTOR_SYSTEM,
    BUSINESS_EVENT_AUTOMATIC_REPLY_ACCEPTED,
    BUSINESS_EVENT_AUTOMATION_SCHEDULED,
    BUSINESS_EVENT_CONTACT_CREATED,
    BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
    BUSINESS_EVENT_LEAD_STAGE_CHANGED,
    BUSINESS_EVENT_MESSAGE_RECEIVED,
    BUSINESS_EVENT_REACTIVATION_TRANSITIONED,
    BUSINESS_EVENT_TASK_COMPLETED,
    BusinessEvent,
)
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.task import Task
from app.repositories.automation import AutomationRepository
from app.repositories.automation_runtime import AutomationWaitSubscriptionRepository
from app.repositories.business_event import (
    AutomationTriggerReceiptRepository,
    BusinessEventRepository,
)

CONTACT_CREATED_SCHEMA = "internal://events/contact.created/v1"
CONTACT_EVENT_NAMESPACE = uuidlib.UUID("4798466e-7955-49ae-841d-288cf7e009ec")
AUTOMATIC_REPLY_EVENT_NAMESPACE = uuidlib.UUID("880cc1df-9bba-4ec6-93de-ed5e9cf43682")
AUTO_RESOLVE_EVENT_NAMESPACE = uuidlib.UUID("130a33c6-b5a6-4fe6-bc5b-79d0185da67a")
MESSAGE_RECEIVED_EVENT_NAMESPACE = uuidlib.UUID("72ba5e9d-9629-4aac-a503-c60986b2f1a4")
AUTOMATION_SCHEDULE_EVENT_NAMESPACE = uuidlib.UUID("0f5a84cb-f9fc-43ba-a111-ec4fc78c29b7")
TASK_COMPLETED_EVENT_NAMESPACE = uuidlib.UUID("5a64ba46-4bfd-438f-88df-0690c3292235")
AUTOMATION_SCHEDULE_SCHEMA = "internal://events/automation.schedule/v1"
MAX_WAIT_MATCHES_PER_EVENT = 500


@dataclass(frozen=True, slots=True)
class AutomationReceiptDispatch:
    receipt_pk: int
    task_id: str


class BusinessEventService:
    """Append immutable facts and receipts inside the caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = BusinessEventRepository(session)
        self._receipts = AutomationTriggerReceiptRepository(session)
        self._automations = AutomationRepository(session)
        self._waits = AutomationWaitSubscriptionRepository(session)

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

    async def record_domain_event(
        self,
        *,
        organization_id: int,
        event_id: uuidlib.UUID,
        event_type: str,
        actor_id: int | None,
        subject_type: str,
        subject_id: int,
        contact_id: int | None,
        occurred_at: datetime,
        source: str,
        payload: dict[str, Any],
        actor_type: str | None = None,
    ) -> BusinessEvent:
        """Append a governed domain fact idempotently and reuse automation receipts."""
        existing = await self._events.by_event_uuid(organization_id, event_id.bytes)
        if existing is not None:
            return existing
        event = BusinessEvent(
            uuid=event_id.bytes,
            organization_id=organization_id,
            event_type=event_type,
            event_version=1,
            occurred_at=occurred_at,
            actor_type=actor_type or ("user" if actor_id is not None else "system"),
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            contact_id=contact_id,
            source=source,
            schema_ref=f"internal://events/{event_type}/v1",
            payload_json=payload,
        )
        await self._events.add(event)
        await self._project_automation_receipts(event)
        return event

    async def record_message_received(
        self,
        *,
        message: Message,
        conversation: Conversation,
        contact: Contact,
        occurred_at: datetime,
        source: str,
    ) -> tuple[BusinessEvent, list[AutomationReceiptDispatch]]:
        """Record an inbound fact without copying message content or provider identity."""
        event_id = self.message_received_event_id(
            organization_id=message.organization_id, message_id=message.public_id
        )
        event = await self.record_domain_event(
            organization_id=message.organization_id,
            event_id=event_id,
            event_type=BUSINESS_EVENT_MESSAGE_RECEIVED,
            actor_id=None,
            actor_type=BUSINESS_EVENT_ACTOR_CONNECTOR,
            subject_type="message",
            subject_id=message.id,
            contact_id=contact.id,
            occurred_at=occurred_at,
            source=source,
            payload={
                "message_id": message.public_id,
                "conversation_id": conversation.public_id,
                "contact_id": contact.public_id,
                "direction": "inbound",
                "message_type": message.message_type,
            },
        )
        await self._session.flush()
        return event, await self.receipt_dispatches_for_event(
            message.organization_id, event_id
        )

    async def receipt_dispatches_for_message(
        self, message: Message
    ) -> list[AutomationReceiptDispatch]:
        event_id = self.message_received_event_id(
            organization_id=message.organization_id, message_id=message.public_id
        )
        if await self._events.by_event_uuid(message.organization_id, event_id.bytes) is None:
            return []
        return await self.receipt_dispatches_for_event(message.organization_id, event_id)

    async def receipt_dispatches_for_event(
        self, organization_id: int, event_id: uuidlib.UUID
    ) -> list[AutomationReceiptDispatch]:
        await self._session.flush()
        rows = await self._receipts.for_event(organization_id, event_id.bytes)
        for wait in await self._waits.for_matched_event(organization_id, event_id.bytes):
            receipt = await self._receipts.by_pk(wait.receipt_id)
            if receipt is not None:
                rows.append(receipt)
        retry_before = utcnow() - timedelta(minutes=5)
        seen: set[int] = set()
        dispatches: list[AutomationReceiptDispatch] = []
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            if (
                row.status == AUTOMATION_TRIGGER_RECEIPT_RECEIVED
                or (
                    row.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
                    and (
                        row.processing_started_at is None
                        or row.processing_started_at <= retry_before
                    )
                )
            ):
                dispatches.append(
                    AutomationReceiptDispatch(receipt_pk=row.id, task_id=row.public_id)
                )
        return dispatches

    async def claim_automation_receipt_dispatches(
        self, *, limit: int
    ) -> list[AutomationReceiptDispatch]:
        """Claim new or stale receipts for the shared Automation worker dispatcher."""
        now = utcnow()
        due_waits = await self._waits.due_timeouts(now=now, limit=limit)
        for wait in due_waits:
            wait.status = AUTOMATION_WAIT_TIMED_OUT
            wait.resolved_at = now
            receipt = await self._receipts.by_pk(wait.receipt_id, for_update=True)
            if (
                receipt is not None
                and receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
                and receipt.processing_started_at is None
            ):
                receipt.status = AUTOMATION_TRIGGER_RECEIPT_RECEIVED
                receipt.processed_at = None
        await self._session.flush()
        rows = await self._receipts.dispatchable(
            retry_before=now - timedelta(minutes=5),
            limit=limit,
        )
        dispatches: list[AutomationReceiptDispatch] = []
        for row in rows:
            if row.status == AUTOMATION_TRIGGER_RECEIPT_RECEIVED:
                row.status = AUTOMATION_TRIGGER_RECEIPT_PROCESSING
                row.processing_started_at = now
            # Stale processing rows retain their old lease time so the consumer can distinguish
            # this recovery dispatch from genuinely concurrent work. Paused Delay/Wait rows use a
            # NULL lease and are intentionally paused until a scheduled or event/timeout resume.
            dispatches.append(
                AutomationReceiptDispatch(receipt_pk=row.id, task_id=row.public_id)
            )
        await self._session.commit()
        return dispatches

    async def claim_due_automation_schedules(
        self, *, now: datetime | None = None, limit: int
    ) -> list[AutomationReceiptDispatch]:
        """Project due schedule slots to exact flow/version receipts and advance them once."""
        # Deferred to keep contact-event recording independent of the campaign/send import graph.
        from app.services.campaign_schedule_service import next_fire

        now = now or utcnow()
        due = await self._automations.due_schedules(now, limit=limit)
        claimed: list[AutomationTriggerReceipt] = []
        for flow, version, organization in due:
            scheduled_for = flow.next_run_at
            cron_expr = self._schedule_cron(version.graph_json)
            if scheduled_for is None or cron_expr is None:
                # A corrupt/stale projection must fail closed instead of producing a broad event.
                flow.next_run_at = None
                continue

            event_id = uuidlib.uuid5(
                AUTOMATION_SCHEDULE_EVENT_NAMESPACE,
                f"{flow.organization_id}:{flow.id}:{version.id}:{scheduled_for.isoformat()}",
            )
            event = await self._events.by_event_uuid(flow.organization_id, event_id.bytes)
            if event is None:
                event = BusinessEvent(
                    uuid=event_id.bytes,
                    organization_id=flow.organization_id,
                    event_type=BUSINESS_EVENT_AUTOMATION_SCHEDULED,
                    event_version=1,
                    occurred_at=scheduled_for,
                    actor_type=BUSINESS_EVENT_ACTOR_SYSTEM,
                    actor_id=None,
                    subject_type="automation_flow",
                    subject_id=flow.id,
                    contact_id=None,
                    source="automation_scheduler",
                    schema_ref=AUTOMATION_SCHEDULE_SCHEMA,
                    payload_json={
                        "automation_id": flow.public_id,
                        "version_no": version.version_no,
                        "scheduled_for": scheduled_for.isoformat(),
                        "timezone": organization.timezone,
                    },
                )
                await self._events.add(event)

            receipt = await self._receipts.by_lineage(flow.id, version.id, event_id.bytes)
            if receipt is None:
                receipt = AutomationTriggerReceipt(
                    organization_id=flow.organization_id,
                    flow_id=flow.id,
                    version_id=version.id,
                    event_uuid=event_id.bytes,
                    event_type=BUSINESS_EVENT_AUTOMATION_SCHEDULED,
                    event_version=1,
                    event_occurred_at=scheduled_for,
                    source="automation_scheduler",
                    status=AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
                    processing_started_at=now,
                )
                await self._receipts.add(receipt)
                claimed.append(receipt)
            elif receipt.status == AUTOMATION_TRIGGER_RECEIPT_RECEIVED:
                receipt.status = AUTOMATION_TRIGGER_RECEIPT_PROCESSING
                receipt.processing_started_at = now
                claimed.append(receipt)

            # Skip missed occurrences and realign to the first future slot, as campaign schedules do.
            flow.next_run_at = next_fire(
                cron_expr,
                after=now,
                timezone=organization.timezone,
            )

        await self._session.flush()
        dispatches = [
            AutomationReceiptDispatch(receipt_pk=row.id, task_id=row.public_id)
            for row in claimed
        ]
        await self._session.commit()
        return dispatches

    @staticmethod
    def message_received_event_id(
        *, organization_id: int, message_id: str
    ) -> uuidlib.UUID:
        return uuidlib.uuid5(
            MESSAGE_RECEIVED_EVENT_NAMESPACE,
            f"{organization_id}:{message_id}:{BUSINESS_EVENT_MESSAGE_RECEIVED}",
        )

    @staticmethod
    def task_completed_event_id(
        *, organization_id: int, task_id: str, completion_revision: int
    ) -> uuidlib.UUID:
        """Identify one completion cycle, including a completion after a task is reopened."""
        return uuidlib.uuid5(
            TASK_COMPLETED_EVENT_NAMESPACE,
            f"{organization_id}:{task_id}:{completion_revision}:{BUSINESS_EVENT_TASK_COMPLETED}",
        )

    async def record_task_completed(
        self,
        *,
        task: Task,
        actor_id: int,
        completion_revision: int,
        occurred_at: datetime,
    ) -> BusinessEvent:
        """Append a privacy-safe task completion fact in the task mutation transaction."""
        return await self.record_domain_event(
            organization_id=task.organization_id,
            event_id=self.task_completed_event_id(
                organization_id=task.organization_id,
                task_id=task.public_id,
                completion_revision=completion_revision,
            ),
            event_type=BUSINESS_EVENT_TASK_COMPLETED,
            actor_id=actor_id,
            subject_type="task",
            subject_id=task.id,
            contact_id=task.contact_id,
            occurred_at=occurred_at,
            source="tasks",
            payload={
                "task_id": task.public_id,
                "task_type": task.task_type,
                "priority": task.priority,
                "status": task.status,
                "completion_revision": completion_revision,
            },
        )

    async def find_domain_event(
        self, organization_id: int, event_id: uuidlib.UUID
    ) -> BusinessEvent | None:
        return await self._events.by_event_uuid(organization_id, event_id.bytes)

    @staticmethod
    def automatic_reply_event_id(
        *, organization_id: int, conversation_id: int, source_message_id: int, kind: str
    ) -> uuidlib.UUID:
        return uuidlib.uuid5(
            AUTOMATIC_REPLY_EVENT_NAMESPACE,
            f"{organization_id}:{conversation_id}:{source_message_id}:{kind}",
        )

    async def record_automatic_reply(
        self,
        *,
        organization_id: int,
        conversation_id: int,
        contact_id: int,
        source_message_id: int,
        reply_message_id: int,
        kind: str,
        occurred_at: datetime,
    ) -> BusinessEvent:
        event_id = self.automatic_reply_event_id(
            organization_id=organization_id,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            kind=kind,
        )
        return await self.record_domain_event(
            organization_id=organization_id,
            event_id=event_id,
            event_type=BUSINESS_EVENT_AUTOMATIC_REPLY_ACCEPTED,
            actor_id=None,
            subject_type="conversation",
            subject_id=conversation_id,
            contact_id=contact_id,
            occurred_at=occurred_at,
            source="inbox_operations",
            payload={
                "kind": kind,
                "source_message_id": source_message_id,
                "reply_message_id": reply_message_id,
            },
        )

    async def automatic_reply_for_source(
        self,
        *,
        organization_id: int,
        conversation_id: int,
        source_message_id: int,
    ) -> BusinessEvent | None:
        for kind in ("consent_opt_in", "consent_opt_out", "welcome", "off_hours"):
            event_id = self.automatic_reply_event_id(
                organization_id=organization_id,
                conversation_id=conversation_id,
                source_message_id=source_message_id,
                kind=kind,
            )
            event = await self._events.by_event_uuid(organization_id, event_id.bytes)
            if event is not None:
                return event
        return None

    async def record_conversation_auto_resolved(
        self,
        *,
        organization_id: int,
        conversation_id: int,
        contact_id: int,
        activity_at: datetime,
        resolved_at: datetime,
        previous_status: str,
        inactive_after_hours: int,
    ) -> BusinessEvent:
        """Append one deterministic fact for one inactivity cycle of a conversation."""
        event_id = uuidlib.uuid5(
            AUTO_RESOLVE_EVENT_NAMESPACE,
            f"{organization_id}:{conversation_id}:{activity_at.isoformat()}",
        )
        return await self.record_domain_event(
            organization_id=organization_id,
            event_id=event_id,
            event_type=BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
            actor_id=None,
            subject_type="conversation",
            subject_id=conversation_id,
            contact_id=contact_id,
            occurred_at=resolved_at,
            source="inbox_operations",
            payload={
                "previous_status": previous_status,
                "inactive_after_hours": inactive_after_hours,
                "activity_at": activity_at.isoformat(),
            },
        )

    async def has_recent_automatic_reply(
        self,
        *,
        organization_id: int,
        conversation_id: int,
        kind: str,
        since: datetime,
    ) -> bool:
        rows = await self._events.recent_for_subject(
            organization_id=organization_id,
            event_type=BUSINESS_EVENT_AUTOMATIC_REPLY_ACCEPTED,
            subject_type="conversation",
            subject_id=conversation_id,
            since=since,
        )
        return any((row.payload_json or {}).get("kind") == kind for row in rows)

    async def _project_automation_receipts(self, event: BusinessEvent) -> None:
        automation_event_type = self._automation_event_type(event.event_type)
        candidates = await self._automations.event_candidates(event.organization_id)
        for flow, version in candidates:
            if not self._matches(version.graph_json, automation_event_type):
                continue
            if await self._receipts.exists(flow.id, version.id, event.uuid):
                continue
            await self._receipts.add(
                AutomationTriggerReceipt(
                    organization_id=event.organization_id,
                    flow_id=flow.id,
                    version_id=version.id,
                    event_uuid=event.uuid,
                    event_type=automation_event_type,
                    event_version=event.event_version,
                    event_occurred_at=event.occurred_at,
                    source=event.source,
                )
            )
        await self._project_wait_resumes(event)

    async def _project_wait_resumes(self, event: BusinessEvent) -> None:
        """Resolve future contact-scoped waits while preserving their original receipt."""
        if event.contact_id is None:
            return
        waits = await self._waits.matching_event(
            organization_id=event.organization_id,
            event_type=self._automation_event_type(event.event_type),
            contact_id=event.contact_id,
            occurred_at=event.occurred_at,
            recorded_at=event.recorded_at,
            limit=MAX_WAIT_MATCHES_PER_EVENT,
        )
        for wait in waits:
            wait.status = AUTOMATION_WAIT_MATCHED
            wait.matched_event_uuid = event.uuid
            wait.resolved_at = event.recorded_at
            receipt = await self._receipts.by_pk(wait.receipt_id, for_update=True)
            if (
                receipt is not None
                and receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
                and receipt.processing_started_at is None
            ):
                receipt.status = AUTOMATION_TRIGGER_RECEIPT_RECEIVED
                receipt.processed_at = None

    @staticmethod
    def _automation_event_type(event_type: str) -> str:
        """Expose the approved Automation name without duplicating the domain fact."""
        if event_type == BUSINESS_EVENT_REACTIVATION_TRANSITIONED:
            return BUSINESS_EVENT_LEAD_STAGE_CHANGED
        return event_type

    @staticmethod
    def _matches(graph: dict[str, Any], event_type: str) -> bool:
        return any(
            node.get("kind") == "trigger" and node.get("config", {}).get("event") == event_type
            for node in graph.get("nodes", [])
        )

    @staticmethod
    def _schedule_cron(graph: dict[str, Any]) -> str | None:
        for node in graph.get("nodes", []):
            config = node.get("config", {})
            if node.get("kind") == "trigger" and config.get("event") == "schedule":
                value = config.get("schedule_cron")
                return str(value) if value else None
        return None
