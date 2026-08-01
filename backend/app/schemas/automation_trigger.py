"""API contract for durable automation trigger receipts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.services.automation_trigger_service import AutomationTriggerReceiptView


class AutomationTriggerReceiptResponse(BaseModel):
    id: str
    event_id: str
    event_type: str
    event_version: int
    version_no: int
    status: Literal["received"]
    source: str | None
    occurred_at: datetime
    received_at: datetime

    @classmethod
    def of(cls, view: AutomationTriggerReceiptView) -> AutomationTriggerReceiptResponse:
        return cls(
            id=view.id,
            event_id=view.event_id,
            event_type=view.event_type,
            event_version=view.event_version,
            version_no=view.version_no,
            status="received",
            source=view.source,
            occurred_at=view.occurred_at,
            received_at=view.received_at,
        )


class AutomationTriggerReceiptsResponse(BaseModel):
    data: list[AutomationTriggerReceiptResponse]
