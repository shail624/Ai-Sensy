"""Once-only live automation consumption for supported inbound action paths."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import uuid as uuidlib
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM
from app.models.automation import (
    AUTOMATION_ATTEMPT_FAILED,
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SKIPPED,
    AUTOMATION_ATTEMPT_SUCCEEDED,
    AUTOMATION_RUN_FAILED,
    AUTOMATION_RUN_QUEUED,
    AUTOMATION_RUN_RETRYING,
    AUTOMATION_RUN_RUNNING,
    AUTOMATION_RUN_SUCCEEDED,
    AUTOMATION_STATUS_PUBLISHED,
    AUTOMATION_TRIGGER_RECEIPT_FAILED,
    AUTOMATION_TRIGGER_RECEIPT_PROCESSED,
    AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
    AUTOMATION_WAIT_MATCHED,
    AUTOMATION_WAIT_TIMED_OUT,
    AUTOMATION_WAIT_WAITING,
    AutomationFlow,
    AutomationFlowVersion,
    AutomationRun,
    AutomationStepAttempt,
    AutomationTriggerReceipt,
    AutomationWaitSubscription,
)
from app.models.business_event import (
    BUSINESS_EVENT_AUTOMATION_SCHEDULED,
    BUSINESS_EVENT_CONTACT_CREATED,
    BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
    BUSINESS_EVENT_LEAD_STAGE_CHANGED,
    BUSINESS_EVENT_MESSAGE_RECEIVED,
    BUSINESS_EVENT_REACTIVATION_TRANSITIONED,
    BUSINESS_EVENT_TASK_COMPLETED,
    BusinessEvent,
)
from app.models.notification import NOTIFICATION_AUTOMATION_ATTENTION
from app.models.user import User
from app.queue.registry import AUTOMATION_RUN
from app.repositories.automation_runtime import (
    AutomationAttemptRepository,
    AutomationRunRepository,
    AutomationWaitSubscriptionRepository,
)
from app.repositories.business_event import (
    AutomationTriggerReceiptRepository,
    BusinessEventRepository,
)
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.notification import NotificationRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.automation_handoff_service import AutomationHandoffService
from app.services.automation_service import AutomationService
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.services.tag_service import TagService
from app.services.task_service import TaskService

AUTOMATION_LIVE_TASK = "app.automation.tasks.consume_automation_trigger_receipt"
LIVE_RECEIPT_LEASE = timedelta(minutes=5)
LIVE_CONDITION_FIELDS = frozenset(
    {
        "event_type",
        "source",
        "payload.direction",
        "payload.message_type",
        "payload.source",
        "payload.opt_in_status",
        "payload.previous_status",
        "payload.inactive_after_hours",
        "payload.from_stage",
        "payload.to_stage",
    }
)
LIVE_CONDITION_OPERATORS = frozenset({"exists", "eq", "ne", "contains"})
MAX_LIVE_EFFECTS = 4
MAX_LIVE_DELAYS = 1
MAX_LIVE_WAITS = 1
MIN_LIVE_DELAY_SECONDS = 60
MAX_LIVE_DELAY_SECONDS = 2_592_000
MIN_LIVE_WAIT_SECONDS = 60
MAX_LIVE_WAIT_SECONDS = 2_592_000


class AutomationTaskReferenceError(AppError):
    code = "automation_task_reference_missing"
    title = "Automation Task Reference Missing"


class AutomationTaskAssigneeError(AppError):
    code = "automation_task_assignee_unavailable"
    title = "Automation Task Assignee Unavailable"


class AutomationTaskReplayConflict(AppError):
    code = "automation_task_replay_conflict"
    title = "Automation Task Replay Conflict"


class AutomationConversationReferenceError(AppError):
    code = "conversation_reference_missing"
    title = "Automation Conversation Reference Missing"


class AutomationTagReferenceError(AppError):
    code = "automation_tag_reference_missing"
    title = "Automation Tag Reference Missing"


class AutomationAssignmentReferenceError(AppError):
    code = "automation_assignment_reference_missing"
    title = "Automation Assignment Reference Missing"


class AutomationAssigneeUnavailableError(AppError):
    code = "automation_assignee_unavailable"
    title = "Automation Assignee Unavailable"


class AutomationNotificationReferenceError(AppError):
    code = "automation_notification_reference_missing"
    title = "Automation Notification Reference Missing"


class AutomationNotificationRecipientError(AppError):
    code = "automation_notification_recipient_unavailable"
    title = "Automation Notification Recipient Unavailable"


class AutomationNotificationReplayConflict(AppError):
    code = "automation_notification_replay_conflict"
    title = "Automation Notification Replay Conflict"


class AutomationWaitReferenceError(AppError):
    code = "automation_wait_contact_missing"
    title = "Automation Wait Contact Missing"


class AutomationLiveRuntimeService:
    """Turn one matched receipt into one pinned, resumable live run."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._receipts = AutomationTriggerReceiptRepository(session)
        self._events = BusinessEventRepository(session)
        self._runs = AutomationRunRepository(session)
        self._attempts = AutomationAttemptRepository(session)
        self._waits = AutomationWaitSubscriptionRepository(session)
        self._audit = AuditService(session)
        self.resume_in_seconds: int | None = None

    async def consume_receipt(self, receipt_pk: int) -> str:
        self.resume_in_seconds = None
        return await self._consume_receipt(receipt_pk)

    async def _consume_receipt(self, receipt_pk: int) -> str:
        receipt = await self._receipts.by_pk(receipt_pk, for_update=True)
        if receipt is None:
            return "missing"
        if receipt.status in {
            AUTOMATION_TRIGGER_RECEIPT_PROCESSED,
            AUTOMATION_TRIGGER_RECEIPT_FAILED,
        }:
            return receipt.status

        flow = await self._session.get(AutomationFlow, receipt.flow_id)
        version = await self._session.get(AutomationFlowVersion, receipt.version_id)
        event = await self._events.by_event_uuid(receipt.organization_id, receipt.event_uuid)
        run = await self._existing_run(receipt)
        if (
            receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
            and run is not None
            and run.status == AUTOMATION_RUN_RUNNING
            and receipt.processing_started_at is not None
            and receipt.processing_started_at > utcnow() - LIVE_RECEIPT_LEASE
        ):
            return receipt.status

        if flow is None or version is None or event is None:
            if run is None and flow is not None and version is not None:
                run = await self._create_run(receipt, flow, version, event_payload={})
            if run is not None:
                return await self._fail_run(
                    receipt,
                    run,
                    code="live_lineage_missing",
                    detail="The receipt's immutable event lineage is unavailable.",
                )
            receipt.status = AUTOMATION_TRIGGER_RECEIPT_FAILED
            receipt.processed_at = utcnow()
            await self._session.commit()
            return receipt.status

        event_payload = await self._live_event_payload(event)
        if run is None:
            run = await self._create_run(
                receipt, flow, version, event_payload=event_payload
            )
        elif run.status == AUTOMATION_RUN_SUCCEEDED:
            receipt.status = AUTOMATION_TRIGGER_RECEIPT_PROCESSED
            receipt.processed_at = run.finished_at or utcnow()
            await self._session.commit()
            return receipt.status
        elif run.status == AUTOMATION_RUN_FAILED:
            receipt.status = AUTOMATION_TRIGGER_RECEIPT_FAILED
            receipt.processed_at = run.finished_at or utcnow()
            await self._session.commit()
            return receipt.status

        if not self._is_current_clean_publication(flow, version):
            return await self._fail_run(
                receipt,
                run,
                code="automation_inactive",
                detail="The matched version is no longer the clean enabled publication.",
            )
        issues = AutomationService.validate_graph(version.graph_json)
        if issues:
            return await self._fail_run(
                receipt,
                run,
                code="invalid_published_graph",
                detail="The pinned graph no longer passes structural validation.",
            )
        path = self._supported_path(version.graph_json, receipt.event_type)
        if path is None:
            return await self._fail_run(
                receipt,
                run,
                code="unsupported_live_graph",
                detail=(
                    "Live execution currently supports message.received with the proven internal "
                    "effects; contact.created with Apply tag, Remove tag, or Notification; and "
                    "conversation.auto_resolved with Create task, Apply tag, Remove tag, or "
                    "Notification; lead.stage_changed with Create task, Apply tag, Remove tag, "
                    "or Notification; and schedule with one internal Notification. "
                    "Each path requires Trigger → optional Condition → one to four distinct "
                    "event-safe effects in one linear sequence, or one Condition with one or two "
                    "ordered Yes effects and one or two ordered No effects, optionally followed by "
                    "one shared internal effect under the same four-effect ceiling. That shared "
                    "follow-up may have one bounded durable Delay immediately before it. Linear paths accept at "
                    "most one bounded Delay and one contact-scoped Message received, Task "
                    "completed, or Lead stage changed Wait before a later effect. "
                    "Scheduled paths do not accept a Condition. Conditions on event paths must "
                    "use an approved metadata field and operator. No business "
                    "effect was applied."
                ),
            )

        trigger, condition, matched_steps, unmatched_steps = path
        now = utcnow()
        receipt.status = AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        receipt.processing_started_at = now
        receipt.processed_at = None
        run.status = AUTOMATION_RUN_RUNNING
        run.started_at = run.started_at or now
        run.finished_at = None
        run.error_code = None
        run.error_detail = None
        await self._session.commit()

        completed = await self._attempts.completed_node_ids(run.id)
        trigger_id = str(trigger["id"])
        if trigger_id not in completed:
            attempt = await self._start_attempt(run, trigger, input_json=None)
            attempt.output_json = {
                "accepted": True,
                "event_id": str(uuidlib.UUID(bytes=receipt.event_uuid)),
                "event_type": receipt.event_type,
            }
            await self._finish_attempt(run, attempt)

        condition_matched = True
        if condition is not None:
            condition_config = condition.get("config", {})
            condition_field = str(condition_config["field"])
            condition_operator = str(condition_config["operator"])
            condition_actual = self._lookup(run.trigger_input_json, condition_field)
            condition_matched = self._compare(
                condition_actual, condition_operator, condition_config.get("value")
            )
            condition_id = str(condition["id"])
            completed = await self._attempts.completed_node_ids(run.id)
            if condition_id not in completed:
                attempt = await self._start_attempt(
                    run,
                    condition,
                    input_json={
                        "field": condition_field,
                        "present": condition_actual is not None,
                    },
                )
                attempt.output_json = {
                    "field": condition_field,
                    "operator": condition_operator,
                    "matched": condition_matched,
                }
                await self._finish_attempt(run, attempt)

        selected_steps = matched_steps
        skipped_steps = unmatched_steps
        selected_branch: str | None = None
        if condition is not None:
            if condition_matched:
                selected_branch = "yes" if unmatched_steps else None
            elif unmatched_steps:
                selected_steps = unmatched_steps
                skipped_steps = matched_steps
                selected_branch = "no"
            else:
                selected_steps = []
                skipped_steps = matched_steps

        for step in selected_steps:
            if step.get("kind") == "delay":
                if await self._execute_delay(receipt=receipt, run=run, node=step):
                    return receipt.status
                continue
            if step.get("kind") == "wait":
                try:
                    if await self._execute_wait(
                        receipt=receipt,
                        run=run,
                        node=step,
                        event=event,
                    ):
                        return receipt.status
                except AppError as exc:
                    return await self._fail_run(
                        receipt, run, code=exc.code, detail=exc.detail
                    )
                continue
            try:
                await self._execute_effect(
                    receipt=receipt,
                    flow=flow,
                    version=version,
                    run=run,
                    effect=step,
                    event_payload=event_payload,
                )
            except AppError as exc:
                return await self._fail_run(receipt, run, code=exc.code, detail=exc.detail)

        if skipped_steps:
            assert condition is not None
            for step in skipped_steps:
                completed = await self._attempts.completed_node_ids(run.id)
                if str(step["id"]) in completed:
                    continue
                attempt = await self._start_attempt(run, step, input_json=None)
                output_json: dict[str, Any] = {
                    "reason": (
                        "branch_not_selected"
                        if selected_branch is not None
                        else "condition_not_matched"
                    ),
                    "condition_node_id": str(condition["id"]),
                }
                if selected_branch is not None:
                    output_json["selected_branch"] = selected_branch
                await self._skip_attempt(run, attempt, output_json=output_json)

        return await self._succeed_run(receipt, run)

    async def _live_event_payload(self, event: BusinessEvent) -> dict[str, Any]:
        """Add tenant-checked public references without mutating immutable event evidence."""
        if event.event_type == BUSINESS_EVENT_REACTIVATION_TRANSITIONED:
            source_payload = event.payload_json or {}
            payload = {
                "from_stage": source_payload.get("from_stage"),
                "to_stage": source_payload.get("to_stage"),
            }
        else:
            payload = copy.deepcopy(event.payload_json or {})
        if event.contact_id is not None and "contact_id" not in payload:
            contact = await ContactRepository(self._session).get_by_id(event.contact_id)
            if (
                contact is not None
                and contact.organization_id == event.organization_id
                and contact.deleted_at is None
            ):
                payload["contact_id"] = contact.public_id
        if (
            event.subject_type == "conversation"
            and event.subject_id is not None
            and "conversation_id" not in payload
        ):
            conversation = await ConversationRepository(self._session).get_by_id(event.subject_id)
            if (
                conversation is not None
                and conversation.organization_id == event.organization_id
                and conversation.deleted_at is None
            ):
                payload["conversation_id"] = conversation.public_id
        return payload

    async def _execute_delay(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        run: AutomationRun,
        node: dict[str, Any],
    ) -> bool:
        """Checkpoint one delay and report whether this delivery must pause."""
        node_id = str(node["id"])
        if node_id in await self._attempts.completed_node_ids(run.id):
            return False

        seconds = int(node.get("config", {}).get("seconds", 0))
        running = await self._attempts.running(run.id)
        attempt = next((item for item in reversed(running) if item.node_id == node_id), None)
        if attempt is None:
            attempt = await self._start_attempt(
                run,
                node,
                input_json={"seconds": seconds},
            )

        now = utcnow()
        resume_at = attempt.started_at + timedelta(seconds=seconds)
        attempt.output_json = {
            "seconds": seconds,
            "resume_at": resume_at.isoformat(),
        }
        if now >= resume_at:
            await self._finish_attempt(run, attempt)
            return False

        # A paused run is deliberately retrying, not failed. Clearing the receipt lease lets the
        # deterministic resume delivery re-enter while duplicate deliveries still converge on the
        # same running delay attempt and completed effect checkpoints.
        run.status = AUTOMATION_RUN_RETRYING
        run.error_code = None
        run.error_detail = None
        receipt.processing_started_at = None
        self.resume_in_seconds = max(1, math.ceil((resume_at - now).total_seconds()))
        await self._session.commit()
        return True

    async def _execute_wait(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        run: AutomationRun,
        node: dict[str, Any],
        event: BusinessEvent,
    ) -> bool:
        """Persist one bounded contact-scoped event subscription and pause until resolved."""
        node_id = str(node["id"])
        if node_id in await self._attempts.completed_node_ids(run.id):
            return False
        if event.contact_id is None:
            raise AutomationWaitReferenceError(
                "The trigger event does not carry a tenant-scoped contact reference."
            )

        config = node.get("config", {})
        event_type = str(config.get("event"))
        timeout_seconds = int(config.get("timeout_seconds", 0))
        running = await self._attempts.running(run.id)
        attempt = next((item for item in reversed(running) if item.node_id == node_id), None)
        if attempt is None:
            attempt = await self._start_attempt(
                run,
                node,
                input_json={
                    "event": event_type,
                    "timeout_seconds": timeout_seconds,
                },
            )

        wait = await self._waits.by_run_node(run.id, node_id, for_update=True)
        if wait is None:
            wait = AutomationWaitSubscription(
                organization_id=receipt.organization_id,
                run_id=run.id,
                receipt_id=receipt.id,
                node_id=node_id,
                event_type=event_type,
                contact_id=event.contact_id,
                status=AUTOMATION_WAIT_WAITING,
                started_at=attempt.started_at,
                timeout_at=attempt.started_at + timedelta(seconds=timeout_seconds),
            )
            await self._waits.add(wait)

        if wait.status in {AUTOMATION_WAIT_MATCHED, AUTOMATION_WAIT_TIMED_OUT}:
            attempt.output_json = {
                "event": wait.event_type,
                "outcome": "matched"
                if wait.status == AUTOMATION_WAIT_MATCHED
                else "timed_out",
                "timeout_at": wait.timeout_at.isoformat(),
                "matched_event_id": (
                    str(uuidlib.UUID(bytes=wait.matched_event_uuid))
                    if wait.matched_event_uuid is not None
                    else None
                ),
            }
            await self._finish_attempt(run, attempt)
            return False

        attempt.output_json = {
            "event": wait.event_type,
            "outcome": "waiting",
            "timeout_at": wait.timeout_at.isoformat(),
        }
        run.status = AUTOMATION_RUN_RETRYING
        run.error_code = None
        run.error_detail = None
        receipt.processing_started_at = None
        await self._session.commit()
        return True

    async def _execute_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        flow: AutomationFlow,
        version: AutomationFlowVersion,
        run: AutomationRun,
        effect: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> None:
        effect_id = str(effect["id"])
        if effect_id in await self._attempts.completed_node_ids(run.id):
            return

        kind = str(effect.get("kind"))
        config = effect.get("config", {})
        input_json: dict[str, Any] | None
        if kind == "handoff":
            input_json = {"conversation_id": event_payload.get("conversation_id")}
        elif kind == "action":
            input_json = {
                "contact_id": event_payload.get("contact_id"),
                "conversation_id": event_payload.get("conversation_id"),
            }
        elif kind in {"tag", "remove_tag"}:
            input_json = {
                "contact_id": event_payload.get("contact_id"),
                "tag_id": config.get("tag_id"),
            }
        elif kind == "assignment":
            input_json = {
                "conversation_id": event_payload.get("conversation_id"),
                "mode": config.get("mode"),
                "user_id": config.get("user_id"),
            }
        else:
            input_json = {
                "contact_id": event_payload.get("contact_id"),
                "recipient": "publisher",
            }

        attempt = await self._start_attempt(run, effect, input_json=input_json)
        try:
            if kind == "handoff":
                try:
                    conversation_id = uuidlib.UUID(str(event_payload.get("conversation_id")))
                except (TypeError, ValueError, AttributeError) as exc:
                    raise AutomationConversationReferenceError(
                        "The inbound trigger does not carry a valid conversation reference."
                    ) from exc
                result = await AutomationHandoffService(self._session).request_handoff(
                    organization_id=receipt.organization_id,
                    actor=None,
                    automation_id=uuidlib.UUID(flow.public_id),
                    conversation_id=conversation_id,
                    node_id=effect_id,
                    idempotency_key=uuidlib.UUID(receipt.public_id),
                    expected_version_id=version.id,
                )
                attempt.output_json = {
                    "event_id": result.event_id,
                    "outcome": result.outcome,
                    "replayed": result.replayed,
                    "conversation_status": result.conversation.status,
                }
            elif kind == "action":
                attempt.output_json = await self._create_task_effect(
                    receipt=receipt,
                    version=version,
                    node=effect,
                    event_payload=event_payload,
                )
            elif kind == "tag":
                attempt.output_json = await self._apply_tag_effect(
                    receipt=receipt,
                    node=effect,
                    event_payload=event_payload,
                )
            elif kind == "remove_tag":
                attempt.output_json = await self._remove_tag_effect(
                    receipt=receipt,
                    node=effect,
                    event_payload=event_payload,
                )
            elif kind == "assignment":
                attempt.output_json = await self._assign_conversation_effect(
                    receipt=receipt,
                    node=effect,
                    event_payload=event_payload,
                )
            else:
                attempt.output_json = await self._notification_effect(
                    receipt=receipt,
                    version=version,
                    node=effect,
                    event_payload=event_payload,
                )
        except AppError as exc:
            attempt.status = AUTOMATION_ATTEMPT_FAILED
            attempt.error_code = exc.code[:64]
            attempt.error_detail = exc.detail[:1024]
            attempt.finished_at = utcnow()
            await self._session.commit()
            raise
        await self._finish_attempt(run, attempt)

    async def _create_task_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        version: AutomationFlowVersion,
        node: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            contact_id = uuidlib.UUID(str(event_payload.get("contact_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AutomationTaskReferenceError(
                "The trigger event does not carry a valid contact reference."
            ) from exc
        conversation_value = event_payload.get("conversation_id")
        if conversation_value is None and receipt.event_type == BUSINESS_EVENT_LEAD_STAGE_CHANGED:
            conversation_id = None
        else:
            try:
                conversation_id = uuidlib.UUID(str(conversation_value))
            except (TypeError, ValueError, AttributeError) as exc:
                raise AutomationTaskReferenceError(
                    "The trigger event does not carry a valid conversation reference."
                ) from exc

        publisher = None
        if version.published_by is not None:
            publisher = await self._session.scalar(
                select(User).where(
                    User.id == version.published_by,
                    User.organization_id == receipt.organization_id,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        if publisher is None:
            raise AutomationTaskAssigneeError(
                "The automation publisher is no longer an active task assignee."
            )

        config = node.get("config", {})
        title = str(config["title"])
        task_type = str(config.get("task_type", "custom"))
        priority = str(config.get("priority", "medium"))
        due_at = receipt.event_occurred_at + timedelta(
            minutes=int(config.get("due_in_minutes", 1440))
        )
        command = {
            "version_id": version.id,
            "node_id": str(node["id"]),
            "contact_id": str(contact_id),
            "conversation_id": str(conversation_id) if conversation_id is not None else None,
            "title": title,
            "task_type": task_type,
            "priority": priority,
            "due_at": due_at.isoformat(),
            "assigned_agent_id": publisher.public_id,
        }
        request_hash = self._canonical_hash(command)
        tasks = TaskRepository(self._session)
        existing = await tasks.by_idempotency_key(receipt.organization_id, receipt.uuid)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise AutomationTaskReplayConflict(
                    "The live receipt task key is already bound to a different command."
                )
            return {
                "task_id": existing.public_id,
                "status": existing.status,
                "due_at": existing.due_at.isoformat(),
                "assigned_agent_id": publisher.public_id,
                "replayed": True,
            }

        view = await TaskService(self._session).create(
            organization_id=receipt.organization_id,
            actor=None,
            contact_id=contact_id,
            conversation_id=conversation_id,
            title=title,
            task_type=task_type,
            priority=priority,
            due_at=due_at,
            has_time=True,
            reminder_at=None,
            description=None,
            assigned_agent_id=uuidlib.UUID(publisher.public_id),
            idempotency_key=receipt.uuid,
            request_hash=request_hash,
        )
        return {
            "task_id": view.public_id,
            "status": view.status,
            "due_at": view.due_at.isoformat(),
            "assigned_agent_id": view.assigned_agent_id,
            "replayed": False,
        }

    async def _apply_tag_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        node: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            contact_id = uuidlib.UUID(str(event_payload.get("contact_id")))
            tag_id = uuidlib.UUID(str(node.get("config", {}).get("tag_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AutomationTagReferenceError(
                "The inbound trigger or published action does not carry a valid tag reference."
            ) from exc

        contact, tag, applied = await TagService(self._session).apply_tag_to_contact(
            organization_id=receipt.organization_id,
            actor=None,
            contact_uuid=contact_id,
            tag_uuid=tag_id,
        )
        return {
            "contact_id": contact.public_id,
            "tag_id": tag.public_id,
            "tag_name": tag.name,
            "outcome": "applied" if applied else "already_present",
            "applied": applied,
        }

    async def _assign_conversation_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        node: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Assign without stealing an existing owner, with a deterministic per-flow rotation."""
        try:
            conversation_id = uuidlib.UUID(str(event_payload.get("conversation_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AutomationAssignmentReferenceError(
                "The inbound trigger does not carry a valid conversation reference."
            ) from exc

        conversations = ConversationRepository(self._session)
        conversation = await conversations.get_active_by_uuid(
            receipt.organization_id, conversation_id.bytes
        )
        if conversation is None:
            raise AutomationAssignmentReferenceError(
                "The inbound trigger conversation is unavailable in this organization."
            )
        conversation = await conversations.lock_by_id(receipt.organization_id, conversation.id)
        if conversation is None:
            raise AutomationAssignmentReferenceError(
                "The inbound trigger conversation is unavailable in this organization."
            )

        config = node.get("config", {})
        mode = str(config.get("mode"))
        users = UserRepository(self._session)

        # A manual or earlier automatic owner always wins. This also closes the crash window
        # between the atomic assignment commit and completion of the automation step attempt.
        if conversation.assigned_user_id is not None:
            existing = await users.get_by_id(conversation.assigned_user_id)
            return {
                "conversation_id": conversation.public_id,
                "assignee_id": existing.public_id if existing is not None else None,
                "mode": mode,
                "outcome": "already_assigned",
                "applied": False,
            }

        eligible = await users.list_active_with_permission(receipt.organization_id, "inbox:read")
        assignee: User | None = None
        if mode == "user":
            try:
                requested_user_id = uuidlib.UUID(str(config.get("user_id")))
            except (TypeError, ValueError, AttributeError) as exc:
                raise AutomationAssigneeUnavailableError(
                    "The published assignment does not carry a valid user reference."
                ) from exc
            assignee = next(
                (user for user in eligible if user.uuid == requested_user_id.bytes), None
            )
            if assignee is None:
                raise AutomationAssigneeUnavailableError(
                    "The selected user is no longer an active inbox member of this organization."
                )
        elif mode == "round_robin":
            if not eligible:
                raise AutomationAssigneeUnavailableError(
                    "No active inbox member is available for round-robin assignment."
                )
            ordinal = await self._receipts.ordinal_for_flow(receipt.flow_id, receipt.id)
            assignee = eligible[(ordinal - 1) % len(eligible)]
        else:
            raise AutomationAssigneeUnavailableError(
                "The published assignment mode is not supported."
            )

        conversation.assigned_user_id = assignee.id
        conversation.row_version += 1
        await conversations.flush()
        await self._audit.record(
            AuditAction.CONVERSATION_ASSIGNED,
            actor_user_id=None,
            actor_type=ACTOR_SYSTEM,
            organization_id=receipt.organization_id,
            entity_type="conversation",
            entity_id=conversation.id,
            before={"assigned_user_id": None},
            after={
                "assigned_user_id": assignee.id,
                "policy": f"automation_{mode}",
            },
            metadata={
                "source": "automation",
                "receipt_id": receipt.public_id,
                "flow_id": receipt.flow_id,
                "node_id": str(node["id"]),
            },
        )
        await self._session.commit()
        return {
            "conversation_id": conversation.public_id,
            "assignee_id": assignee.public_id,
            "mode": mode,
            "outcome": "assigned",
            "applied": True,
        }

    async def _remove_tag_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        node: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            contact_id = uuidlib.UUID(str(event_payload.get("contact_id")))
            tag_id = uuidlib.UUID(str(node.get("config", {}).get("tag_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AutomationTagReferenceError(
                "The inbound trigger or published action does not carry a valid tag reference."
            ) from exc

        contact, tag, removed = await TagService(
            self._session
        ).remove_tag_from_contact_if_present(
            organization_id=receipt.organization_id,
            actor=None,
            contact_uuid=contact_id,
            tag_uuid=tag_id,
        )
        return {
            "contact_id": contact.public_id,
            "tag_id": tag.public_id,
            "tag_name": tag.name,
            "outcome": "removed" if removed else "already_absent",
            "removed": removed,
        }

    async def _notification_effect(
        self,
        *,
        receipt: AutomationTriggerReceipt,
        version: AutomationFlowVersion,
        node: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        contact = None
        if receipt.event_type != BUSINESS_EVENT_AUTOMATION_SCHEDULED:
            try:
                contact_id = uuidlib.UUID(str(event_payload.get("contact_id")))
            except (TypeError, ValueError, AttributeError) as exc:
                raise AutomationNotificationReferenceError(
                    "The inbound trigger does not carry a valid contact reference."
                ) from exc

            contact = await ContactRepository(self._session).get_active_by_uuid(
                receipt.organization_id, contact_id.bytes
            )
            if contact is None:
                raise AutomationNotificationReferenceError(
                    "The inbound trigger contact is unavailable in this organization."
                )

        eligible = await UserRepository(self._session).list_active_with_permission(
            receipt.organization_id, "tasks:read"
        )
        recipient = next((user for user in eligible if user.id == version.published_by), None)
        if recipient is None:
            raise AutomationNotificationRecipientError(
                "The automation publisher is no longer an active Notification Center reader."
            )

        title = "Automation needs attention"
        body = str(node.get("config", {}).get("message"))
        dedup_key = f"automation:{receipt.public_id}:{node['id']}"
        notifications = NotificationRepository(self._session)
        existing = await notifications.by_dedup(receipt.organization_id, dedup_key)
        if existing is not None and (
            existing.notification_type != NOTIFICATION_AUTOMATION_ATTENTION
            or existing.recipient_user_id != recipient.id
            or existing.contact_id != (contact.id if contact is not None else None)
            or existing.title != title
            or existing.body != body
        ):
            raise AutomationNotificationReplayConflict(
                "The live receipt notification key is already bound to a different delivery."
            )

        notification = existing or await NotificationService(self._session).emit(
            organization_id=receipt.organization_id,
            recipient_user_id=recipient.id,
            notification_type=NOTIFICATION_AUTOMATION_ATTENTION,
            title=title,
            body=body,
            dedup_key=dedup_key,
            contact_id=contact.id if contact is not None else None,
        )
        await self._session.commit()
        return {
            "notification_id": notification.public_id,
            "recipient_id": recipient.public_id,
            "contact_id": contact.public_id if contact is not None else None,
            "outcome": "already_delivered" if existing is not None else "delivered",
            "delivered": existing is None,
        }

    async def _succeed_run(self, receipt: AutomationTriggerReceipt, run: AutomationRun) -> str:
        run.status = AUTOMATION_RUN_SUCCEEDED
        run.completed_steps = run.total_steps
        run.finished_at = utcnow()
        receipt.status = AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        receipt.processed_at = run.finished_at
        await self._session.commit()
        return receipt.status

    async def mark_task_failure(
        self, receipt_pk: int, *, retrying: bool, error: BaseException
    ) -> None:
        receipt = await self._receipts.by_pk(receipt_pk, for_update=True)
        if receipt is None or receipt.status in {
            AUTOMATION_TRIGGER_RECEIPT_PROCESSED,
            AUTOMATION_TRIGGER_RECEIPT_FAILED,
        }:
            return
        run = await self._existing_run(receipt)
        if run is None:
            if not retrying:
                receipt.status = AUTOMATION_TRIGGER_RECEIPT_FAILED
                receipt.processed_at = utcnow()
                await self._session.commit()
            return
        run.status = AUTOMATION_RUN_RETRYING if retrying else AUTOMATION_RUN_FAILED
        run.error_code = "task_retry" if retrying else "task_failed"
        run.error_detail = f"{type(error).__name__}: {error}"[:1024]
        run.finished_at = None if retrying else utcnow()
        if not retrying:
            receipt.status = AUTOMATION_TRIGGER_RECEIPT_FAILED
            receipt.processed_at = run.finished_at
        await self._session.commit()

    async def _existing_run(self, receipt: AutomationTriggerReceipt) -> AutomationRun | None:
        if receipt.run_id is not None:
            return await self._runs.by_pk(receipt.run_id)
        return await self._runs.by_idempotency_key(receipt.organization_id, receipt.uuid)

    async def _create_run(
        self,
        receipt: AutomationTriggerReceipt,
        flow: AutomationFlow,
        version: AutomationFlowVersion,
        *,
        event_payload: dict[str, Any],
    ) -> AutomationRun:
        trigger_input = {
            "event_id": str(uuidlib.UUID(bytes=receipt.event_uuid)),
            "event_type": receipt.event_type,
            "event_version": receipt.event_version,
            "occurred_at": receipt.event_occurred_at.isoformat(),
            "source": receipt.source,
            "payload": copy.deepcopy(event_payload),
        }
        run = AutomationRun(
            organization_id=receipt.organization_id,
            flow_id=flow.id,
            version_id=version.id,
            mode="live",
            status=AUTOMATION_RUN_QUEUED,
            idempotency_key=receipt.uuid,
            request_hash=self._request_hash(receipt, version, trigger_input),
            correlation_id=receipt.public_id,
            trigger_input_json=trigger_input,
            total_steps=len(version.graph_json.get("nodes", [])),
            created_by=None,
        )
        await self._runs.add(run)
        await self._runs.flush()
        receipt.run_id = run.id
        await JobService(self._session).record_queued(
            task_id=run.correlation_id,
            task_name=AUTOMATION_LIVE_TASK,
            queue=AUTOMATION_RUN,
            ref_type="automation_run",
            ref_id=run.id,
        )
        await self._audit.record(
            AuditAction.AUTOMATION_LIVE_RUN_CREATED,
            actor_user_id=None,
            actor_type=ACTOR_SYSTEM,
            organization_id=receipt.organization_id,
            entity_type="automation_run",
            entity_id=run.id,
            after={
                "automation_id": flow.public_id,
                "version_no": version.version_no,
                "mode": "live",
                "status": run.status,
                "receipt_id": receipt.public_id,
            },
        )
        return run

    async def _start_attempt(
        self,
        run: AutomationRun,
        node: dict[str, Any],
        *,
        input_json: dict[str, Any] | None,
    ) -> AutomationStepAttempt:
        attempt = AutomationStepAttempt(
            organization_id=run.organization_id,
            run_id=run.id,
            node_id=str(node["id"]),
            node_kind=str(node["kind"]),
            attempt_no=await self._attempts.next_attempt_no(run.id, str(node["id"])),
            status=AUTOMATION_ATTEMPT_RUNNING,
            input_json=input_json,
        )
        await self._attempts.add(attempt)
        await self._session.commit()
        return attempt

    async def _finish_attempt(self, run: AutomationRun, attempt: AutomationStepAttempt) -> None:
        attempt.status = AUTOMATION_ATTEMPT_SUCCEEDED
        attempt.finished_at = utcnow()
        completed = await self._attempts.completed_node_ids(run.id)
        run.completed_steps = len(completed | {attempt.node_id})
        await self._session.commit()

    async def _skip_attempt(
        self,
        run: AutomationRun,
        attempt: AutomationStepAttempt,
        *,
        output_json: dict[str, Any],
    ) -> None:
        attempt.status = AUTOMATION_ATTEMPT_SKIPPED
        attempt.output_json = output_json
        attempt.finished_at = utcnow()
        completed = await self._attempts.completed_node_ids(run.id)
        run.completed_steps = len(completed | {attempt.node_id})
        await self._session.commit()

    async def _fail_run(
        self,
        receipt: AutomationTriggerReceipt,
        run: AutomationRun,
        *,
        code: str,
        detail: str,
    ) -> str:
        run.status = AUTOMATION_RUN_FAILED
        run.error_code = code[:64]
        run.error_detail = detail[:1024]
        run.finished_at = utcnow()
        receipt.status = AUTOMATION_TRIGGER_RECEIPT_FAILED
        receipt.processed_at = run.finished_at
        await self._session.commit()
        return receipt.status

    @staticmethod
    def _is_current_clean_publication(flow: AutomationFlow, version: AutomationFlowVersion) -> bool:
        return bool(
            flow.status == AUTOMATION_STATUS_PUBLISHED
            and flow.active_version_no == version.version_no
            and flow.active_content_hash == version.content_hash
            and flow.active_content_hash == flow.draft_content_hash
        )

    @staticmethod
    def _supported_path(
        graph: dict[str, Any], event_type: str
    ) -> tuple[
        dict[str, Any],
        dict[str, Any] | None,
        list[dict[str, Any]],
        list[dict[str, Any]],
    ] | None:
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        if (
            not 2 <= len(nodes) <= MAX_LIVE_EFFECTS + MAX_LIVE_DELAYS + MAX_LIVE_WAITS + 2
            or len(edges) not in {len(nodes) - 1, len(nodes)}
        ):
            return None
        triggers = [node for node in nodes if node.get("kind") == "trigger"]
        conditions = [node for node in nodes if node.get("kind") == "condition"]
        delays = [node for node in nodes if node.get("kind") == "delay"]
        waits = [node for node in nodes if node.get("kind") == "wait"]
        if (
            len(triggers) != 1
            or len(conditions) > 1
            or len(delays) > MAX_LIVE_DELAYS
            or len(waits) > MAX_LIVE_WAITS
        ):
            return None
        for delay in delays:
            seconds = delay.get("config", {}).get("seconds")
            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, int)
                or not MIN_LIVE_DELAY_SECONDS <= seconds <= MAX_LIVE_DELAY_SECONDS
            ):
                return None
        for wait in waits:
            timeout_seconds = wait.get("config", {}).get("timeout_seconds")
            if (
                wait.get("config", {}).get("event")
                not in {
                    BUSINESS_EVENT_MESSAGE_RECEIVED,
                    BUSINESS_EVENT_TASK_COMPLETED,
                    BUSINESS_EVENT_LEAD_STAGE_CHANGED,
                }
                or isinstance(timeout_seconds, bool)
                or not isinstance(timeout_seconds, int)
                or not MIN_LIVE_WAIT_SECONDS <= timeout_seconds <= MAX_LIVE_WAIT_SECONDS
            ):
                return None
        trigger = triggers[0]
        condition = conditions[0] if conditions else None
        effects = [
            node
            for node in nodes
            if node.get("kind")
            in {"handoff", "tag", "remove_tag", "assignment", "notification"}
            or (
                node.get("kind") == "action"
                and node.get("config", {}).get("action") == "create_task"
            )
        ]
        if not 1 <= len(effects) <= MAX_LIVE_EFFECTS:
            return None
        if len(nodes) != 1 + len(conditions) + len(delays) + len(waits) + len(effects):
            return None
        if trigger.get("config", {}).get("event") != event_type:
            return None

        effect_kinds = [
            "create_task" if node.get("kind") == "action" else str(node.get("kind"))
            for node in effects
        ]
        if event_type == BUSINESS_EVENT_MESSAGE_RECEIVED:
            allowed_effect_kinds = {
                "handoff",
                "create_task",
                "tag",
                "remove_tag",
                "assignment",
                "notification",
            }
        elif event_type == BUSINESS_EVENT_CONTACT_CREATED:
            allowed_effect_kinds = {"tag", "remove_tag", "notification"}
        elif event_type in {
            BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
            BUSINESS_EVENT_LEAD_STAGE_CHANGED,
        }:
            allowed_effect_kinds = {"create_task", "tag", "remove_tag", "notification"}
        elif event_type == BUSINESS_EVENT_AUTOMATION_SCHEDULED:
            if condition is not None or waits:
                return None
            allowed_effect_kinds = {"notification"}
        else:
            return None
        if any(kind not in allowed_effect_kinds for kind in effect_kinds):
            return None

        if condition is not None:
            config = condition.get("config", {})
            if (
                config.get("field") not in LIVE_CONDITION_FIELDS
                or config.get("operator") not in LIVE_CONDITION_OPERATORS
            ):
                return None

        node_by_id = {str(node.get("id")): node for node in nodes}
        outgoing: dict[str, list[dict[str, Any]]] = {
            node_id: [] for node_id in node_by_id
        }
        incoming: dict[str, int] = dict.fromkeys(node_by_id, 0)
        for edge in edges:
            source = str(edge.get("source"))
            target = str(edge.get("target"))
            if source not in node_by_id or target not in node_by_id:
                return None
            outgoing[source].append(edge)
            incoming[target] += 1
            if incoming[target] > 2:
                return None

        condition_edges = (
            outgoing[str(condition.get("id"))] if condition is not None else []
        )
        has_branch_labels = any(
            str(edge.get("label") or "").strip() for edge in condition_edges
        )
        if condition is not None and (len(condition_edges) > 1 or has_branch_labels):
            if waits or not 4 <= len(nodes) <= 7 or not 2 <= len(effects) <= 4:
                return None
            trigger_id = str(trigger.get("id"))
            condition_id = str(condition.get("id"))
            trigger_edges = outgoing[trigger_id]
            if (
                incoming[trigger_id] != 0
                or incoming[condition_id] != 1
                or len(trigger_edges) != 1
                or str(trigger_edges[0].get("target")) != condition_id
                or str(trigger_edges[0].get("label") or "").strip()
            ):
                return None
            branch_targets: dict[str, str] = {}
            effect_ids = {str(effect.get("id")) for effect in effects}
            merge_ids = {node_id for node_id, count in incoming.items() if count == 2}
            if len(merge_ids) > 1:
                return None
            merge_id = next(iter(merge_ids), None)
            shared_steps: list[dict[str, Any]] = []
            shared_effect: dict[str, Any] | None = None
            if merge_id is None:
                if delays:
                    return None
            else:
                merge_node = node_by_id[merge_id]
                if merge_id in effect_ids:
                    if delays or outgoing[merge_id]:
                        return None
                    shared_effect = merge_node
                    shared_steps = [merge_node]
                elif merge_node in delays:
                    merge_edges = outgoing[merge_id]
                    if len(delays) != 1 or len(merge_edges) != 1:
                        return None
                    merge_edge = merge_edges[0]
                    shared_effect_id = str(merge_edge.get("target"))
                    if (
                        str(merge_edge.get("label") or "").strip()
                        or shared_effect_id not in effect_ids
                        or incoming[shared_effect_id] != 1
                        or outgoing[shared_effect_id]
                    ):
                        return None
                    shared_effect = node_by_id[shared_effect_id]
                    shared_steps = [merge_node, shared_effect]
                else:
                    return None
            for edge in condition_edges:
                label = str(edge.get("label") or "").strip().lower()
                target = str(edge.get("target"))
                if label not in {"yes", "no"} or label in branch_targets:
                    return None
                if target not in effect_ids or incoming[target] != 1:
                    return None
                branch_targets[label] = target
            if set(branch_targets) != {"yes", "no"}:
                return None

            branch_node_ids: set[str] = set()

            def ordered_branch(
                first_id: str,
            ) -> tuple[list[dict[str, Any]], bool] | None:
                ordered_branch_steps: list[dict[str, Any]] = []
                reaches_shared = False
                current = first_id
                while True:
                    if current in branch_node_ids or current not in effect_ids:
                        return None
                    branch_node_ids.add(current)
                    ordered_branch_steps.append(node_by_id[current])
                    if len(ordered_branch_steps) > 2:
                        return None
                    current_edges = outgoing[current]
                    if not current_edges:
                        break
                    if len(current_edges) != 1:
                        return None
                    edge = current_edges[0]
                    if str(edge.get("label") or "").strip():
                        return None
                    next_id = str(edge.get("target"))
                    if merge_id is not None and next_id == merge_id:
                        reaches_shared = True
                        break
                    if next_id not in effect_ids or incoming[next_id] != 1:
                        return None
                    current = next_id
                branch_kinds = [
                    "create_task" if node.get("kind") == "action" else str(node.get("kind"))
                    for node in ordered_branch_steps
                ]
                if shared_effect is not None:
                    branch_kinds.append(
                        "create_task"
                        if shared_effect.get("kind") == "action"
                        else str(shared_effect.get("kind"))
                    )
                if len(branch_kinds) != len(set(branch_kinds)):
                    return None
                return ordered_branch_steps, reaches_shared

            yes_branch = ordered_branch(branch_targets["yes"])
            no_branch = ordered_branch(branch_targets["no"])
            expected_branch_ids = effect_ids - (
                {str(shared_effect.get("id"))} if shared_effect is not None else set()
            )
            if (
                yes_branch is None
                or no_branch is None
                or branch_node_ids != expected_branch_ids
                or yes_branch[1] != (merge_id is not None)
                or no_branch[1] != (merge_id is not None)
            ):
                return None
            yes_steps, _ = yes_branch
            no_steps, _ = no_branch
            yes_steps.extend(shared_steps)
            no_steps.extend(shared_steps)
            return trigger, condition, yes_steps, no_steps

        if any(count > 1 for count in incoming.values()):
            return None

        if len(effect_kinds) != len(set(effect_kinds)):
            return None

        next_by_id: dict[str, str] = {}
        for source, source_edges in outgoing.items():
            if len(source_edges) > 1:
                return None
            if source_edges:
                next_by_id[source] = str(source_edges[0].get("target"))

        ordered: list[dict[str, Any]] = [trigger]
        visited = {str(trigger.get("id"))}
        current = str(trigger.get("id"))
        while current in next_by_id:
            current = next_by_id[current]
            if current in visited:
                return None
            visited.add(current)
            ordered.append(node_by_id[current])
        if len(ordered) != len(nodes):
            return None
        if condition is not None:
            if (
                ordered[1] is not condition
            ):
                return None
            ordered_steps = ordered[2:]
        else:
            ordered_steps = ordered[1:]
        if any(
            step not in effects and step not in delays and step not in waits
            for step in ordered_steps
        ):
            return None
        if waits:
            wait_index = ordered_steps.index(waits[0])
            if not any(step in effects for step in ordered_steps[wait_index + 1 :]):
                return None
        return trigger, condition, ordered_steps, []

    @staticmethod
    def _lookup(payload: dict[str, Any], dotted: str) -> Any:
        value: Any = payload
        for part in dotted.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        if operator == "exists":
            return actual is not None
        if operator == "eq":
            return bool(actual == expected)
        if operator == "ne":
            return bool(actual != expected)
        if operator == "contains":
            try:
                return expected in actual
            except TypeError:
                return False
        return False

    @staticmethod
    def _canonical_hash(value: dict[str, Any]) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _request_hash(
        receipt: AutomationTriggerReceipt,
        version: AutomationFlowVersion,
        trigger_input: dict[str, Any],
    ) -> str:
        value = {
            "receipt_id": receipt.public_id,
            "version_id": version.id,
            "content_hash": version.content_hash,
            "trigger_input": trigger_input,
        }
        return AutomationLiveRuntimeService._canonical_hash(value)
