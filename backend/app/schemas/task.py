"""Task schemas (Doc 14 §7, §8) — request/response shapes for the follow-up engine.

Enumerations render as OpenAPI ``enum`` strings via ``Literal`` and are kept in lockstep with the
model constants (a test asserts equality). Incoming datetimes are normalised to naive-UTC (the
stored form, Doc 03 §1.3). The bulk **result** reuses the frozen ``BulkSummary`` (``schemas/bulk``);
``Page`` is reused for the collection envelope.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.api.pagination import Page
from app.models.task import BODY_MAX, TITLE_LENGTH
from app.schemas.bulk import BulkSummary
from app.services.task_service import (
    BulkOutcome,
    TaskEventView,
    TaskStats,
    TaskView,
)

TaskTypeLiteral = Literal[
    "call", "whatsapp", "collect_documents", "verification", "reminder", "meeting", "custom"
]
TaskStatusLiteral = Literal["open", "completed", "skipped", "cancelled"]
TaskPriorityLiteral = Literal["low", "medium", "high", "critical"]
SortLiteral = Literal[
    "due_at", "-due_at",
    "created_at", "-created_at",
    "priority", "-priority",
    "completed_at", "-completed_at",
]
ViewLiteral = Literal["today", "overdue", "upcoming", "completed", "all"]

REASON_MAX = 500


def _to_naive_utc(value: datetime) -> datetime:
    """Normalise an (optionally tz-aware) datetime to naive-UTC for storage/comparison."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


NaiveUTC = Annotated[datetime, AfterValidator(_to_naive_utc)]


class TaskCreateRequest(BaseModel):
    """Create a follow-up task (Doc 14 §7.4). ``assigned_agent_id`` defaults to the caller."""

    contact_id: uuidlib.UUID
    conversation_id: uuidlib.UUID | None = None
    title: str = Field(min_length=1, max_length=TITLE_LENGTH)
    task_type: TaskTypeLiteral
    priority: TaskPriorityLiteral = "medium"
    due_at: NaiveUTC
    has_time: bool = True
    reminder_at: NaiveUTC | None = None
    description: str | None = Field(default=None, max_length=BODY_MAX)
    assigned_agent_id: uuidlib.UUID | None = None


class TaskUpdateRequest(BaseModel):
    """Edit task fields (Doc 14 §7.1). Every field optional — only those present change."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=BODY_MAX)
    task_type: TaskTypeLiteral | None = None
    priority: TaskPriorityLiteral | None = None
    due_at: NaiveUTC | None = None
    has_time: bool | None = None
    reminder_at: NaiveUTC | None = None
    expected_row_version: int | None = Field(default=None, ge=0)


class TaskCompleteRequest(BaseModel):
    completion_notes: str | None = Field(default=None, max_length=BODY_MAX)
    create_timeline_note: bool = False
    expected_row_version: int | None = Field(default=None, ge=0)


class TaskRescheduleRequest(BaseModel):
    due_at: NaiveUTC
    has_time: bool | None = None
    reminder_at: NaiveUTC | None = None
    expected_row_version: int | None = Field(default=None, ge=0)


class TaskReassignRequest(BaseModel):
    assigned_agent_id: uuidlib.UUID
    expected_row_version: int | None = Field(default=None, ge=0)


class TaskReasonRequest(BaseModel):
    """Shared body for skip / cancel (Doc 14 §8) — an optional reason plus the concurrency guard."""

    reason: str | None = Field(default=None, max_length=REASON_MAX)
    expected_row_version: int | None = Field(default=None, ge=0)


class TaskReopenRequest(BaseModel):
    """Body for reopen — no reason field: reopening carries no outcome (Doc 14 §4.4)."""

    expected_row_version: int | None = Field(default=None, ge=0)


class TaskResponse(BaseModel):
    """A task as returned by the CRUD and action endpoints (Doc 14 §7.4)."""

    id: str
    contact_id: str
    contact_name: str | None
    conversation_id: str | None
    title: str
    task_type: str
    status: str
    priority: str
    due_at: datetime
    has_time: bool
    reminder_at: datetime | None
    description: str | None
    assigned_agent_id: str
    assigned_agent_name: str | None
    created_by: str | None
    created_by_name: str | None
    completion_notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    row_version: int

    @classmethod
    def of(cls, view: TaskView) -> TaskResponse:
        return cls(
            id=view.public_id,
            contact_id=view.contact_id,
            contact_name=view.contact_name,
            conversation_id=view.conversation_id,
            title=view.title,
            task_type=view.task_type,
            status=view.status,
            priority=view.priority,
            due_at=view.due_at,
            has_time=view.has_time,
            reminder_at=view.reminder_at,
            description=view.description,
            assigned_agent_id=view.assigned_agent_id,
            assigned_agent_name=view.assigned_agent_name,
            created_by=view.created_by,
            created_by_name=view.created_by_name,
            completion_notes=view.completion_notes,
            completed_at=view.completed_at,
            created_at=view.created_at,
            updated_at=view.updated_at,
            row_version=view.row_version,
        )


class TasksPage(BaseModel):
    """A keyset page of tasks (Doc 04 §3 envelope)."""

    data: list[TaskResponse]
    page: Page


class TaskEventResponse(BaseModel):
    id: int
    event_type: str
    actor_user_id: str | None
    actor_name: str | None
    from_value: dict[str, Any] | None
    to_value: dict[str, Any] | None
    note: str | None
    created_at: datetime

    @classmethod
    def of(cls, view: TaskEventView) -> TaskEventResponse:
        return cls(
            id=view.id,
            event_type=view.event_type,
            actor_user_id=view.actor_user_id,
            actor_name=view.actor_name,
            from_value=view.from_value,
            to_value=view.to_value,
            note=view.note,
            created_at=view.created_at,
        )


class TaskHistoryResponse(BaseModel):
    """A task's immutable history, oldest→newest (Doc 14 §5.2)."""

    data: list[TaskEventResponse]


class TaskStatsResponse(BaseModel):
    """Work-queue counts for the widget (Doc 14 §7.3, §11)."""

    overdue: int
    due_today: int
    upcoming: int
    completed_today: int

    @classmethod
    def of(cls, stats: TaskStats) -> TaskStatsResponse:
        return cls(
            overdue=stats.overdue,
            due_today=stats.due_today,
            upcoming=stats.upcoming,
            completed_today=stats.completed_today,
        )


class TaskBulkUpdateRequest(BaseModel):
    """``POST /tasks/bulk-update`` — apply a change set to a selection (Doc 14 §7.1)."""

    task_ids: list[uuidlib.UUID] = Field(min_length=1)
    status: TaskStatusLiteral | None = None
    priority: TaskPriorityLiteral | None = None
    due_at: NaiveUTC | None = None
    assigned_agent_id: uuidlib.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> TaskBulkUpdateRequest:
        if not any(
            v is not None for v in (self.status, self.priority, self.due_at, self.assigned_agent_id)
        ):
            raise ValueError("provide at least one of status/priority/due_at/assigned_agent_id")
        return self


class TaskBulkDeleteRequest(BaseModel):
    """``POST /tasks/bulk-delete`` — soft-delete a selection (Doc 14 §7.1)."""

    task_ids: list[uuidlib.UUID] = Field(min_length=1)


class TaskBulkResultResponse(BaseModel):
    """Partial-success summary for a bulk task op (reuses the frozen ``BulkSummary``)."""

    summary: BulkSummary

    @classmethod
    def of(cls, outcome: BulkOutcome) -> TaskBulkResultResponse:
        return cls(
            summary=BulkSummary(
                total=outcome.total,
                processed=outcome.processed,
                succeeded=outcome.succeeded,
                failed=outcome.failed,
                skipped=outcome.skipped,
            )
        )
