"""Organization model (Doc 03 §4.1).

Single-tenant today, but every scoped table carries ``organization_id`` so a future
multi-workspace split needs no redesign (Doc 01 §2.1 / NFR-EXT). Owns users and roles.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin
from app.db.types import MYSQL_TABLE_ARGS


class Organization(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base
):
    """A tenant / workspace (Doc 03 §4.1)."""

    __tablename__ = "organizations"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    default_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    settings_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Organization id={self.id} slug={self.slug!r}>"
