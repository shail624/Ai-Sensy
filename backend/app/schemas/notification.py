"""Notification Center API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.api.pagination import Page

NotificationType = Literal[
    "follow_up_due", "release_date_due", "case_assigned", "case_status_changed"
]
NotificationStatus = Literal["unread", "read", "overdue", "resolved"]


class EntityReference(BaseModel):
    id: str
    name: str | None = None


class UserReference(BaseModel):
    id: str
    name: str


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    read_status: str
    lifecycle_status: str
    due_at: datetime | None
    read_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    recipient: UserReference
    actor: UserReference | None
    contact: EntityReference | None
    reactivation_case: EntityReference | None
    task: EntityReference | None


class NotificationsPage(BaseModel):
    data: list[NotificationResponse]
    page: Page


class UnreadCountResponse(BaseModel):
    unread: int


class MarkAllReadResponse(BaseModel):
    updated: int
