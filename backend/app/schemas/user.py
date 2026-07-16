"""User management schemas (Doc 04 §12.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.pagination import Page
from app.core.security import validate_password_policy
from app.models.role import Role
from app.models.user import User


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
