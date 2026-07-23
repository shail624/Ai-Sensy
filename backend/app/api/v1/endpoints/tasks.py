"""Task endpoints (Doc 14 §7) — the CRM Follow-up Engine API.

CRUD, business-transition actions (complete/skip/cancel/reopen/reschedule/reassign), immutable
history, work-queue stats, and bulk operations over the ``tasks`` table. Reads need ``tasks:read``;
writes need ``tasks:write``; reassigning to another agent needs ``tasks:assign`` (Doc 14 §6).
Envelopes, cursor pagination and RFC 7807 errors are the frozen platform standards.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.core.exceptions import ForbiddenError
from app.models.user import User
from app.schemas.task import (
    SortLiteral,
    TaskBulkDeleteRequest,
    TaskBulkResultResponse,
    TaskBulkUpdateRequest,
    TaskCompleteRequest,
    TaskCreateRequest,
    TaskEventResponse,
    TaskHistoryResponse,
    TaskPriorityLiteral,
    TaskReasonRequest,
    TaskReassignRequest,
    TaskReopenRequest,
    TaskRescheduleRequest,
    TaskResponse,
    TasksPage,
    TaskStatsResponse,
    TaskStatusLiteral,
    TaskTypeLiteral,
    TaskUpdateRequest,
    ViewLiteral,
)
from app.services.rbac_service import RBACService
from app.services.task_service import TaskService

router = APIRouter()

TaskReader = Annotated[User, Depends(require_permissions("tasks:read"))]
TaskWriter = Annotated[User, Depends(require_permissions("tasks:write"))]
TaskAssigner = Annotated[User, Depends(require_permissions("tasks:assign"))]


def _naive(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


@router.get("/tasks", response_model=TasksPage, summary="List tasks")
async def list_tasks(
    session: SessionDep,
    actor: TaskReader,
    view: Annotated[ViewLiteral, Query()] = "all",
    assignee_id: Annotated[uuidlib.UUID | None, Query()] = None,
    assigned_by_id: Annotated[uuidlib.UUID | None, Query()] = None,
    contact_id: Annotated[uuidlib.UUID | None, Query()] = None,
    conversation_id: Annotated[uuidlib.UUID | None, Query()] = None,
    task_status: Annotated[list[TaskStatusLiteral] | None, Query(alias="status")] = None,
    task_type: Annotated[list[TaskTypeLiteral] | None, Query(alias="type")] = None,
    priority: Annotated[list[TaskPriorityLiteral] | None, Query()] = None,
    due_from: Annotated[datetime | None, Query()] = None,
    due_to: Annotated[datetime | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    sort: Annotated[SortLiteral, Query()] = "due_at",
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> TasksPage:
    """A filtered, bucketed, cursor-paginated page of tasks (Doc 14 §7.2/§7.3)."""
    result = await TaskService(session).list(
        organization_id=actor.organization_id,
        actor=actor,
        view=view,
        assignee_id=assignee_id,
        assigned_by_id=assigned_by_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        statuses=list(task_status) if task_status else None,
        types=list(task_type) if task_type else None,
        priorities=list(priority) if priority else None,
        due_from=_naive(due_from),
        due_to=_naive(due_to),
        q=q,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )
    return TasksPage(
        data=[TaskResponse.of(v) for v in result.tasks],
        page=Page(limit=limit, has_more=result.has_more, next_cursor=result.next_cursor),
    )


@router.get("/tasks/stats", response_model=TaskStatsResponse, summary="Work-queue counts")
async def task_stats(
    session: SessionDep,
    actor: TaskReader,
    assignee_id: Annotated[uuidlib.UUID | None, Query()] = None,
) -> TaskStatsResponse:
    """Overdue / due-today / upcoming / completed-today counts for an agent (Doc 14 §11)."""
    stats = await TaskService(session).stats(
        organization_id=actor.organization_id, actor=actor, assignee_id=assignee_id
    )
    return TaskStatsResponse.of(stats)


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
async def create_task(
    payload: TaskCreateRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).create(
        organization_id=actor.organization_id,
        actor=actor,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        title=payload.title,
        task_type=payload.task_type,
        priority=payload.priority,
        due_at=payload.due_at,
        has_time=payload.has_time,
        reminder_at=payload.reminder_at,
        description=payload.description,
        assigned_agent_id=payload.assigned_agent_id,
    )
    return TaskResponse.of(view)


@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="Get a task")
async def get_task(task_id: uuidlib.UUID, session: SessionDep, actor: TaskReader) -> TaskResponse:
    view = await TaskService(session).get(
        organization_id=actor.organization_id, public_id=task_id
    )
    return TaskResponse.of(view)


@router.patch("/tasks/{task_id}", response_model=TaskResponse, summary="Edit a task")
async def update_task(
    task_id: uuidlib.UUID, payload: TaskUpdateRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).update(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=task_id,
        expected_row_version=payload.expected_row_version,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        priority=payload.priority,
        due_at=payload.due_at,
        has_time=payload.has_time,
        reminder_at=payload.reminder_at,
    )
    return TaskResponse.of(view)


@router.delete(
    "/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task (soft)"
)
async def delete_task(task_id: uuidlib.UUID, session: SessionDep, actor: TaskWriter) -> None:
    await TaskService(session).delete(
        organization_id=actor.organization_id, actor=actor, public_id=task_id
    )


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse, summary="Complete a task")
async def complete_task(
    task_id: uuidlib.UUID, payload: TaskCompleteRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).complete(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=task_id,
        expected_row_version=payload.expected_row_version,
        completion_notes=payload.completion_notes,
        create_timeline_note=payload.create_timeline_note,
    )
    return TaskResponse.of(view)


@router.post("/tasks/{task_id}/skip", response_model=TaskResponse, summary="Skip a task")
async def skip_task(
    task_id: uuidlib.UUID, payload: TaskReasonRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).skip(
        organization_id=actor.organization_id, actor=actor, public_id=task_id,
        expected_row_version=payload.expected_row_version, reason=payload.reason,
    )
    return TaskResponse.of(view)


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse, summary="Cancel a task")
async def cancel_task(
    task_id: uuidlib.UUID, payload: TaskReasonRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).cancel(
        organization_id=actor.organization_id, actor=actor, public_id=task_id,
        expected_row_version=payload.expected_row_version, reason=payload.reason,
    )
    return TaskResponse.of(view)


@router.post("/tasks/{task_id}/reopen", response_model=TaskResponse, summary="Reopen a task")
async def reopen_task(
    task_id: uuidlib.UUID, payload: TaskReopenRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).reopen(
        organization_id=actor.organization_id, actor=actor, public_id=task_id,
        expected_row_version=payload.expected_row_version,
    )
    return TaskResponse.of(view)


@router.post("/tasks/{task_id}/reschedule", response_model=TaskResponse, summary="Reschedule a task")
async def reschedule_task(
    task_id: uuidlib.UUID, payload: TaskRescheduleRequest, session: SessionDep, actor: TaskWriter
) -> TaskResponse:
    view = await TaskService(session).reschedule(
        organization_id=actor.organization_id, actor=actor, public_id=task_id,
        expected_row_version=payload.expected_row_version,
        due_at=payload.due_at, has_time=payload.has_time, reminder_at=payload.reminder_at,
    )
    return TaskResponse.of(view)


@router.post("/tasks/{task_id}/reassign", response_model=TaskResponse, summary="Reassign a task")
async def reassign_task(
    task_id: uuidlib.UUID, payload: TaskReassignRequest, session: SessionDep, actor: TaskAssigner
) -> TaskResponse:
    view = await TaskService(session).reassign(
        organization_id=actor.organization_id, actor=actor, public_id=task_id,
        expected_row_version=payload.expected_row_version,
        assigned_agent_id=payload.assigned_agent_id,
    )
    return TaskResponse.of(view)


@router.get(
    "/tasks/{task_id}/history", response_model=TaskHistoryResponse, summary="Task history"
)
async def task_history(
    task_id: uuidlib.UUID, session: SessionDep, actor: TaskReader
) -> TaskHistoryResponse:
    events = await TaskService(session).history(
        organization_id=actor.organization_id, public_id=task_id
    )
    return TaskHistoryResponse(data=[TaskEventResponse.of(e) for e in events])


@router.post(
    "/tasks/bulk-update", response_model=TaskBulkResultResponse, summary="Bulk-update tasks"
)
async def bulk_update_tasks(
    payload: TaskBulkUpdateRequest, session: SessionDep, actor: TaskWriter
) -> TaskBulkResultResponse:
    """Bulk status/priority/due/assignee. Reassigning also requires ``tasks:assign`` (enforced below)."""
    if payload.assigned_agent_id is not None and not await _can_assign(session, actor):
        raise ForbiddenError("Reassigning tasks requires the tasks:assign permission.")
    outcome = await TaskService(session).bulk_update(
        organization_id=actor.organization_id,
        actor=actor,
        public_ids=payload.task_ids,
        status=payload.status,
        priority=payload.priority,
        due_at=payload.due_at,
        assigned_agent_id=payload.assigned_agent_id,
    )
    return TaskBulkResultResponse.of(outcome)


@router.post(
    "/tasks/bulk-delete", response_model=TaskBulkResultResponse, summary="Bulk-delete tasks (soft)"
)
async def bulk_delete_tasks(
    payload: TaskBulkDeleteRequest, session: SessionDep, actor: TaskWriter
) -> TaskBulkResultResponse:
    outcome = await TaskService(session).bulk_delete(
        organization_id=actor.organization_id, actor=actor, public_ids=payload.task_ids
    )
    return TaskBulkResultResponse.of(outcome)


async def _can_assign(session: SessionDep, actor: User) -> bool:
    """Whether the caller additionally holds ``tasks:assign`` (bulk reassignment guard)."""
    return await RBACService(session).has_permissions(actor, {"tasks:assign"})
