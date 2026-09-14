"""Personal and organization-shared filter views for governed workspaces.

The physical table name is retained from the first Reactivation integration so existing
installations can adopt later workspace integrations through additive migrations.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id


class WorkspaceView(IntPKMixin, UUIDMixin, TimestampMixin, Base):
    """A validated, portable workspace filter definition within one tenant."""

    __tablename__ = "reactivation_views"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('private', 'shared')",
            name="ck_reactivation_views_visibility",
        ),
        CheckConstraint(
            "workspace IN ('reactivation', 'contacts', 'campaigns', 'kyc', 'reports')",
            name="ck_reactivation_views_workspace",
        ),
        CheckConstraint(
            "display IN ('board', 'list')",
            name="ck_reactivation_views_display",
        ),
        UniqueConstraint(
            "organization_id",
            "workspace",
            "visibility",
            "created_by_user_id",
            "name",
            name="uq_reactivation_views_scope_creator_name",
        ),
        Index(
            "ix_reactivation_views_org_visibility_created",
            "organization_id",
            "workspace",
            "visibility",
            "created_at",
        ),
        Index(
            "ix_reactivation_views_org_creator",
            "organization_id",
            "workspace",
            "created_by_user_id",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    workspace: Mapped[Literal["reactivation", "contacts", "campaigns", "kyc", "reports"]] = (
        mapped_column(String(24), nullable=False, default="reactivation")
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    visibility: Mapped[Literal["private", "shared"]] = mapped_column(String(16), nullable=False)
    display: Mapped[Literal["board", "list"]] = mapped_column(String(16), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


# Compatibility alias for callers introduced with the first workspace integration.
ReactivationView = WorkspaceView
