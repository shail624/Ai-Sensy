"""Governed automation-to-Live-Chat human handoff.

This is deliberately one bounded live automation effect. A caller must identify a handoff node in
the clean active immutable version; the service then reuses Conversation status/assignment, Audit
and Business Event authorities. It does not turn the side-effect-free test runner into a live flow
engine and it never sends a customer message.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM as AUDIT_ACTOR_SYSTEM
from app.models.audit import ACTOR_USER as AUDIT_ACTOR_USER
from app.models.automation import (
    AUTOMATION_STATUS_PUBLISHED,
    AutomationFlow,
    AutomationFlowVersion,
)
from app.models.business_event import (
    BUSINESS_EVENT_ACTOR_SYSTEM,
    BUSINESS_EVENT_ACTOR_USER,
    BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED,
)
from app.models.conversation import CONV_OPEN, CONV_PENDING, Conversation
from app.models.user import User
from app.repositories.automation import AutomationRepository
from app.repositories.business_event import BusinessEventRepository
from app.repositories.conversation import ConversationRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.business_event_service import BusinessEventService
from app.services.inbox_service import ConversationState

AUTOMATION_HANDOFF_NAMESPACE = uuidlib.UUID("7259d93f-749d-4d3e-94d4-d19cf317d59d")
AutomationHandoffOutcome = Literal["requested", "already_requested", "already_intervened"]


class AutomationHandoffConflict(ConflictError):
    code = "automation_handoff_conflict"
    title = "Automation Handoff Conflict"


class AutomationHandoffInvalid(ValidationError):
    code = "automation_handoff_invalid"
    title = "Automation Handoff Invalid"


@dataclass(frozen=True, slots=True)
class AutomationHandoffResult:
    event_id: str
    automation_id: str
    version_no: int
    node_id: str
    reason: str
    outcome: AutomationHandoffOutcome
    replayed: bool
    conversation: ConversationState


class AutomationHandoffService:
    """Execute one idempotent handoff node from a published automation version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._automations = AutomationRepository(session)
        self._conversations = ConversationRepository(session)
        self._events = BusinessEventRepository(session)
        self._business_events = BusinessEventService(session)
        self._audit = AuditService(session)

    async def request_handoff(
        self,
        *,
        organization_id: int,
        actor: User | None,
        automation_id: uuidlib.UUID,
        conversation_id: uuidlib.UUID,
        node_id: str,
        idempotency_key: uuidlib.UUID,
        expected_version_id: int | None = None,
    ) -> AutomationHandoffResult:
        flow, version, reason = await self._published_handoff(
            organization_id=organization_id,
            automation_id=automation_id,
            node_id=node_id,
        )
        if expected_version_id is not None and version.id != expected_version_id:
            raise AutomationHandoffConflict(
                "The receipt's immutable version is no longer the active version."
            )
        actor_user_id = actor.id if actor is not None else None
        audit_actor_type = AUDIT_ACTOR_USER if actor is not None else AUDIT_ACTOR_SYSTEM
        event_actor_type = (
            BUSINESS_EVENT_ACTOR_USER if actor is not None else BUSINESS_EVENT_ACTOR_SYSTEM
        )
        conversation = await self._conversations.get_active_by_uuid(
            organization_id, conversation_id.bytes
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        conversation = (
            await self._conversations.lock_by_id(organization_id, conversation.id) or conversation
        )
        event_id = self._event_id(
            organization_id=organization_id,
            automation_id=flow.public_id,
            version_no=version.version_no,
            node_id=node_id,
            conversation_id=conversation.public_id,
            idempotency_key=idempotency_key,
        )

        existing = await self._events.by_event_uuid(organization_id, event_id.bytes)
        if existing is not None:
            return await self._replayed_result(
                event_id=event_id,
                flow_id=flow.public_id,
                version=version,
                node_id=node_id,
                reason=reason,
                conversation=conversation,
                outcome=self._outcome(existing.payload_json),
            )

        self._assert_executable(flow)

        before_status = conversation.status
        before_assignee = conversation.assigned_user_id
        outcome: AutomationHandoffOutcome
        if conversation.assigned_user_id is not None and conversation.status in {
            CONV_OPEN,
            CONV_PENDING,
        }:
            outcome = "already_intervened"
        elif conversation.status == CONV_PENDING:
            outcome = "already_requested"
        else:
            outcome = "requested"
            conversation.status = CONV_PENDING
            conversation.assigned_user_id = None
            conversation.row_version += 1
            await self._conversations.flush()
            if before_assignee is not None:
                await self._audit.record(
                    AuditAction.CONVERSATION_ASSIGNED,
                    actor_user_id=actor_user_id,
                    actor_type=audit_actor_type,
                    organization_id=organization_id,
                    entity_type="conversation",
                    entity_id=conversation.id,
                    before={"assigned_user_id": before_assignee},
                    after={"assigned_user_id": None},
                    metadata={"source": "automation_handoff", "event_id": str(event_id)},
                )
            if before_status != CONV_PENDING:
                await self._audit.record(
                    AuditAction.CONVERSATION_STATUS_CHANGED,
                    actor_user_id=actor_user_id,
                    actor_type=audit_actor_type,
                    organization_id=organization_id,
                    entity_type="conversation",
                    entity_id=conversation.id,
                    before={"status": before_status},
                    after={"status": CONV_PENDING},
                    metadata={"source": "automation_handoff", "event_id": str(event_id)},
                )

        try:
            await self._business_events.record_domain_event(
                organization_id=organization_id,
                event_id=event_id,
                event_type=BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED,
                actor_id=actor_user_id,
                actor_type=event_actor_type,
                subject_type="conversation",
                subject_id=conversation.id,
                contact_id=conversation.contact_id,
                occurred_at=utcnow(),
                source="automation",
                payload={
                    "automation_id": flow.public_id,
                    "version_no": version.version_no,
                    "node_id": node_id,
                    "reason": reason,
                    "outcome": outcome,
                },
            )
            await self._audit.record(
                AuditAction.AUTOMATION_HANDOFF_REQUESTED,
                actor_user_id=actor_user_id,
                actor_type=audit_actor_type,
                organization_id=organization_id,
                entity_type="conversation",
                entity_id=conversation.id,
                before={"status": before_status, "assigned_user_id": before_assignee},
                after={
                    "status": conversation.status,
                    "assigned_user_id": conversation.assigned_user_id,
                },
                metadata={
                    "automation_id": flow.public_id,
                    "version_no": version.version_no,
                    "node_id": node_id,
                    "event_id": str(event_id),
                    "outcome": outcome,
                },
            )
            await self._session.commit()
        except IntegrityError:
            # A simultaneous retry can race on the deterministic unique Business Event UUID. The
            # losing transaction rolls back all candidate effects and returns the winner's state.
            await self._session.rollback()
            existing = await self._events.by_event_uuid(organization_id, event_id.bytes)
            current = await self._conversations.get_active_by_uuid(
                organization_id, conversation_id.bytes
            )
            if existing is None or current is None:
                raise
            return await self._replayed_result(
                event_id=event_id,
                flow_id=flow.public_id,
                version=version,
                node_id=node_id,
                reason=reason,
                conversation=current,
                outcome=self._outcome(existing.payload_json),
            )

        return AutomationHandoffResult(
            event_id=str(event_id),
            automation_id=flow.public_id,
            version_no=version.version_no,
            node_id=node_id,
            reason=reason,
            outcome=outcome,
            replayed=False,
            conversation=await self._state(conversation),
        )

    async def _published_handoff(
        self, *, organization_id: int, automation_id: uuidlib.UUID, node_id: str
    ) -> tuple[AutomationFlow, AutomationFlowVersion, str]:
        flow = await self._automations.get_by_public_id(organization_id, automation_id.bytes)
        if flow is None:
            raise NotFoundError("Automation not found.")
        if flow.active_version_no is None:
            raise AutomationHandoffConflict(
                "Publish an automation version before executing a handoff."
            )
        version = await self._automations.get_version(
            organization_id, flow.id, flow.active_version_no
        )
        if version is None:
            raise AutomationHandoffConflict("The active automation version is unavailable.")
        node = next(
            (
                item
                for item in version.graph_json.get("nodes", [])
                if item.get("id") == node_id and item.get("kind") == "handoff"
            ),
            None,
        )
        if node is None:
            raise AutomationHandoffInvalid(
                "Choose a Human handoff node from the active immutable version."
            )
        reason = str(node.get("config", {}).get("reason", "")).strip()
        if not reason:
            raise AutomationHandoffInvalid("The Human handoff node needs a reason.")
        return flow, version, reason

    @staticmethod
    def _assert_executable(flow: AutomationFlow) -> None:
        if (
            flow.status != AUTOMATION_STATUS_PUBLISHED
            or flow.active_content_hash != flow.draft_content_hash
        ):
            raise AutomationHandoffConflict(
                "Publish a clean enabled automation version before executing a handoff."
            )

    async def _replayed_result(
        self,
        *,
        event_id: uuidlib.UUID,
        flow_id: str,
        version: AutomationFlowVersion,
        node_id: str,
        reason: str,
        conversation: Conversation,
        outcome: AutomationHandoffOutcome,
    ) -> AutomationHandoffResult:
        return AutomationHandoffResult(
            event_id=str(event_id),
            automation_id=flow_id,
            version_no=version.version_no,
            node_id=node_id,
            reason=reason,
            outcome=outcome,
            replayed=True,
            conversation=await self._state(conversation),
        )

    async def _state(self, conversation: Conversation) -> ConversationState:
        assignee = (
            await self._session.get(User, conversation.assigned_user_id)
            if conversation.assigned_user_id is not None
            else None
        )
        return ConversationState(
            public_id=conversation.public_id,
            status=conversation.status,
            assigned_to=assignee.public_id if assignee is not None else None,
            row_version=conversation.row_version,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _event_id(
        *,
        organization_id: int,
        automation_id: str,
        version_no: int,
        node_id: str,
        conversation_id: str,
        idempotency_key: uuidlib.UUID,
    ) -> uuidlib.UUID:
        return uuidlib.uuid5(
            AUTOMATION_HANDOFF_NAMESPACE,
            ":".join(
                (
                    str(organization_id),
                    automation_id,
                    str(version_no),
                    node_id,
                    conversation_id,
                    str(idempotency_key),
                )
            ),
        )

    @staticmethod
    def _outcome(payload: dict[str, object] | None) -> AutomationHandoffOutcome:
        value = (payload or {}).get("outcome")
        if value in {"requested", "already_requested", "already_intervened"}:
            return value
        return "requested"
