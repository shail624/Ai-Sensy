"""Notification Center API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.api.pagination import Page

NotificationType = Literal[
    "follow_up_due",
    "release_date_due",
    "case_assigned",
    "case_status_changed",
    "automation_attention",
    "report_ready",
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
    action_url: str | None = None


class NotificationsPage(BaseModel):
    data: list[NotificationResponse]
    page: Page


class UnreadCountResponse(BaseModel):
    unread: int


class NotificationSettings(BaseModel):
    """Which categories the signed-in user has chosen not to see.

    Muting is a display choice, not a delivery one: the notification is still recorded, and a
    supervisor's team view still shows it. Nothing an operator is accountable for disappears
    because they tidied their own list.
    """

    muted_types: list[NotificationType] = Field(default_factory=list)

    @field_validator("muted_types")
    @classmethod
    def _stable_set(cls, value: list[NotificationType]) -> list[NotificationType]:
        """Deduplicated and ordered, so what a client reads back is what it sent."""
        return sorted(set(value))


class MarkAllReadResponse(BaseModel):
    updated: int
