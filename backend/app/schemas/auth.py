"""Authentication & session schemas (Doc 04 §11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import unpack_ip, validate_password_policy
from app.models.token import UserSession
from app.models.user import User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    mfa_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, value: str) -> str:
        validate_password_policy(value)
        return value


class UserSummary(BaseModel):
    id: str
    full_name: str
    email: str
    is_superuser: bool

    @classmethod
    def from_user(cls, user: User) -> UserSummary:
        return cls(
            id=user.public_id,
            full_name=user.full_name,
            email=user.email,
            is_superuser=user.is_superuser,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: UserSummary


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_superuser: bool
    roles: list[str]
    permissions: list[str]
    timezone: str
    locale: str
    mfa_enabled: bool


class SessionResponse(BaseModel):
    id: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime

    @classmethod
    def from_session(cls, session: UserSession) -> SessionResponse:
        return cls(
            id=session.public_id,
            ip_address=unpack_ip(session.ip_address),
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_seen_at=session.last_seen_at,
        )
