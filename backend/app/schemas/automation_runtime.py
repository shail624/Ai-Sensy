"""API schemas for deterministic automation test runs (Design Book 23)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.services.automation_runtime_service import AutomationAttemptView, AutomationRunView


class AutomationTestRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: dict[str, Any] = Field(default_factory=dict, max_length=50)


class AutomationAttemptResponse(BaseModel):
    id: str
    node_id: str
    node_kind: str
    attempt_no: int
    status: Literal["running", "succeeded", "failed", "interrupted"]
    output: dict[str, Any] | None
    error_code: str | None
    error_detail: str | None
    started_at: datetime
    finished_at: datetime | None

    @classmethod
    def of(cls, view: AutomationAttemptView) -> AutomationAttemptResponse:
        return cls(
            id=view.id,
            node_id=view.node_id,
            node_kind=view.node_kind,
            attempt_no=view.attempt_no,
            status=cast(
                Literal["running", "succeeded", "failed", "interrupted"], view.status
            ),
            output=view.output,
            error_code=view.error_code,
            error_detail=view.error_detail,
            started_at=view.started_at,
            finished_at=view.finished_at,
        )


class AutomationRunResponse(BaseModel):
    id: str
    automation_id: str
    version_no: int
    mode: Literal["test"]
    status: Literal["queued", "running", "retrying", "succeeded", "failed"]
    correlation_id: str
    total_steps: int
    completed_steps: int
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_detail: str | None
    attempts: list[AutomationAttemptResponse]

    @classmethod
    def of(cls, view: AutomationRunView) -> AutomationRunResponse:
        return cls(
            id=view.id,
            automation_id=view.automation_id,
            version_no=view.version_no,
            mode="test",
            status=cast(
                Literal["queued", "running", "retrying", "succeeded", "failed"],
                view.status,
            ),
            correlation_id=view.correlation_id,
            total_steps=view.total_steps,
            completed_steps=view.completed_steps,
            created_by=view.created_by,
            created_at=view.created_at,
            started_at=view.started_at,
            finished_at=view.finished_at,
            error_code=view.error_code,
            error_detail=view.error_detail,
            attempts=[AutomationAttemptResponse.of(attempt) for attempt in view.attempts],
        )


class AutomationRunsResponse(BaseModel):
    data: list[AutomationRunResponse]
