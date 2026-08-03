"""Unified, self-scoped Notification Center endpoints."""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationResponse,
    NotificationsPage,
    NotificationStatus,
    NotificationType,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/notifications")
Reader = Annotated[User, Depends(require_permissions("tasks:read"))]


def _naive(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC).replace(tzinfo=None) if value and value.tzinfo else value


@router.get("", response_model=NotificationsPage, summary="List notifications")
async def list_notifications(
    session: SessionDep,
    actor: Reader,
    notification_type: Annotated[NotificationType | None, Query(alias="type")] = None,
    notification_status: Annotated[NotificationStatus | None, Query(alias="status")] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    assignee_id: Annotated[uuidlib.UUID | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> NotificationsPage:
    can_view_team = await RBACService(session).has_permissions(actor, {"tasks:assign"})
    result = await NotificationService(session).list(
        actor=actor,
        assignee_id=assignee_id,
        can_view_team=can_view_team,
        notification_type=notification_type,
        status=notification_status,
        date_from=_naive(date_from),
        date_to=_naive(date_to),
        cursor=cursor,
        limit=limit,
    )
    return NotificationsPage(
        data=[NotificationResponse(**item) for item in result.items],
        page=Page(limit=limit, has_more=result.has_more, next_cursor=result.next_cursor),
    )


@router.get(
    "/unread-count", response_model=UnreadCountResponse, summary="Unread notification count"
)
async def unread_count(session: SessionDep, actor: Reader) -> UnreadCountResponse:
    return UnreadCountResponse(unread=await NotificationService(session).unread_count(actor))


@router.post(
    "/{notification_id}/read", response_model=NotificationResponse, summary="Mark notification read"
)
async def mark_read(
    notification_id: uuidlib.UUID, session: SessionDep, actor: Reader
) -> NotificationResponse:
    return NotificationResponse(
        **(await NotificationService(session).mark_read(actor, notification_id))
    )


@router.post("/read-all", response_model=MarkAllReadResponse, summary="Mark all notifications read")
async def mark_all_read(session: SessionDep, actor: Reader) -> MarkAllReadResponse:
    return MarkAllReadResponse(updated=await NotificationService(session).mark_all_read(actor))
