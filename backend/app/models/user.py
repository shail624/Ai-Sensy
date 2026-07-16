"""User model (Doc 03 §4.2).

Authenticates with email + Argon2id password hash (Doc 01 FR-AUTH-01). Carries lockout
state (FR-AUTH-04), the Owner superuser bypass flag (FR-AUTH-06), and MFA columns whose
enrolment endpoints arrive in a later step (the columns are part of the frozen schema).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, small_uint, varbinary


class User(
    IntPKMixin,
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    Base,
):
    """A platform user (Doc 03 §4.2)."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_org", "organization_id"),
        Index("ix_users_active", "organization_id", "is_active"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_users_org", ondelete="RESTRICT"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret_enc: Mapped[bytes | None] = mapped_column(varbinary(255), nullable=True)
    failed_logins: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<User id={self.id} email={self.email!r}>"
