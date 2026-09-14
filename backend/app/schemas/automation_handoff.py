"""Typed contract for a published automation's Live Chat handoff action."""

from __future__ import annotations

import uuid as uuidlib
from typing import Literal

from pydantic import BaseModel

from app.schemas.automation import NodeId, StrictModel
from app.schemas.inbox import ConversationStateResponse
from app.services.automation_handoff_service import AutomationHandoffResult


class AutomationHandoffRequest(StrictModel):
    conversation_id: uuidlib.UUID
    node_id: NodeId


class AutomationHandoffResponse(BaseModel):
    event_id: str
    automation_id: str
    version_no: int
    node_id: str
    reason: str
    outcome: Literal["requested", "already_requested", "already_intervened"]
    replayed: bool
    conversation: ConversationStateResponse

    @classmethod
    def of(cls, result: AutomationHandoffResult) -> AutomationHandoffResponse:
        return cls(
            event_id=result.event_id,
            automation_id=result.automation_id,
            version_no=result.version_no,
            node_id=result.node_id,
            reason=result.reason,
            outcome=result.outcome,
            replayed=result.replayed,
            conversation=ConversationStateResponse.from_state(result.conversation),
        )
