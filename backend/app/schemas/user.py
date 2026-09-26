"""User management schemas (Doc 04 §12.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.pagination import Page
from app.core.security import validate_password_policy
from app.models.role import Role
from app.models.user import User
from app.services.team_workload_service import TeamWorkloadSnapshot


class UserResponse(BaseModel):
    id: str
    type: str = "user"
    email: str
    full_name: str
    phone: str | None
    avatar_url: str | None
    timezone: str
    locale: str
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    roles: list[str]
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    row_version: int

    @classmethod
    def from_user(cls, user: User, roles: list[Role]) -> UserResponse:
        return cls(
            id=user.public_id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            locale=user.locale,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            mfa_enabled=user.mfa_enabled,
            roles=[role.name for role in roles],
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            row_version=user.row_version,
        )


class UsersPage(BaseModel):
    data: list[UserResponse]
    page: Page


class TeamWorkloadRow(BaseModel):
    user_id: str | None
    user_name: str
    is_active: bool | None
    unresolved_conversations: int
    unread_conversations: int
    unread_messages: int
    open_tasks: int
    overdue_tasks: int
    due_today_tasks: int
    attention_required: bool


class TeamWorkloadTotals(BaseModel):
    unresolved_conversations: int
    unread_conversations: int
    unread_messages: int
    open_tasks: int
    overdue_tasks: int
    due_today_tasks: int


class TeamWorkloadResponse(BaseModel):
    data: list[TeamWorkloadRow]
    totals: TeamWorkloadTotals
    as_of: datetime
    timezone: str

    @classmethod
    def from_snapshot(cls, snapshot: TeamWorkloadSnapshot) -> TeamWorkloadResponse:
        rows = [
            TeamWorkloadRow(
                user_id=str(row.user_id) if row.user_id is not None else None,
                user_name=row.user_name,
                is_active=row.is_active,
                unresolved_conversations=row.unresolved_conversations,
                unread_conversations=row.unread_conversations,
                unread_messages=row.unread_messages,
                open_tasks=row.open_tasks,
                overdue_tasks=row.overdue_tasks,
                due_today_tasks=row.due_today_tasks,
                attention_required=row.attention_required,
            )
            for row in snapshot.data
        ]
        return cls(
            data=rows,
            totals=TeamWorkloadTotals(
                unresolved_conversations=sum(row.unresolved_conversations for row in rows),
                unread_conversations=sum(row.unread_conversations for row in rows),
                unread_messages=sum(row.unread_messages for row in rows),
                open_tasks=sum(row.open_tasks for row in rows),
                overdue_tasks=sum(row.overdue_tasks for row in rows),
                due_today_tasks=sum(row.due_today_tasks for row in rows),
            ),
            as_of=snapshot.as_of,
            timezone=snapshot.timezone,
        )


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    password: str
    phone: str | None = Field(default=None, max_length=32)
    timezone: str = Field(default="UTC", max_length=64)
    locale: str = Field(default="en", max_length=10)
    roles: list[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        validate_password_policy(value)
        return value


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None
    roles: list[str] | None = None
    row_version: int | None = None


class PreferencesResponse(BaseModel):
    preferences: dict[str, Any]


class PreferencesUpdateRequest(BaseModel):
    preferences: dict[str, Any] = Field(min_length=1)
