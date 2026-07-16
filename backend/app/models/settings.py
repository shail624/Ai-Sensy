"""System settings and feature-flag models (Doc 03 §11.5, §11.7).

``settings`` is a typed, scoped key/value store (system/organization/user); ``feature_flags``
lets modules ship dark and roll out progressively. Both carry only ``updated_at`` (no
created_at / soft delete) per Doc 03.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

SCOPE_SYSTEM = "system"
SCOPE_ORGANIZATION = "organization"
SCOPE_USER = "user"


class Setting(Base):
    """A typed, scoped configuration value (Doc 03 §11.5)."""

    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "key_name", name="uq_settings_scope_key"),
        Index("ix_settings_org", "organization_id"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = mapped_column(big_id(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default=SCOPE_ORGANIZATION)
    scope_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    key_name: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False, default="json")
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        datetime6(), nullable=False, default=utcnow, onupdate=utcnow, server_default=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Setting {self.scope}:{self.key_name!r}>"


class FeatureFlag(Base):
    """A feature flag with optional targeting/rollout (Doc 03 §11.7)."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("key_name", "organization_id", name="uq_ff_key_org"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = mapped_column(big_id(), primary_key=True, autoincrement=True)
    key_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollout_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        datetime6(), nullable=False, default=utcnow, onupdate=utcnow, server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<FeatureFlag {self.key_name!r} enabled={self.is_enabled}>"
