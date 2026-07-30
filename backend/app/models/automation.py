"""Versioned automation definitions (Design Book 22, MD5 Phase 2A).

The mutable draft and immutable publication snapshots live here.  This module deliberately has no
run, step-attempt, schedule or provider model: authoring is isolated from the future runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import AuditMixin, IntPKMixin, TimestampMixin, UUIDMixin, VersionMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

AUTOMATION_STATUS_DRAFT = "draft"
AUTOMATION_STATUS_PUBLISHED = "published"
AUTOMATION_STATUS_DISABLED = "disabled"
AUTOMATION_STATUSES: tuple[str, ...] = (
    AUTOMATION_STATUS_DRAFT,
    AUTOMATION_STATUS_PUBLISHED,
    AUTOMATION_STATUS_DISABLED,
)


def _status_clause() -> str:
    return f"status IN ({', '.join(repr(value) for value in AUTOMATION_STATUSES)})"


class AutomationFlow(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    """One tenant-scoped mutable automation draft and its selected publication."""

    __tablename__ = "automation_flows"
    __table_args__ = (
        Index("ix_automation_flows_org_updated", "organization_id", "updated_at"),
        Index("ix_automation_flows_org_status_updated", "organization_id", "status", "updated_at"),
        CheckConstraint(_status_clause(), name="ck_automation_flows_status"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_automation_flows_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default=AUTOMATION_STATUS_DRAFT
    )
    draft_graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    draft_content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    active_version_no: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    active_content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)


class AutomationFlowVersion(IntPKMixin, UUIDMixin, Base):
    """An immutable, content-addressed automation publication snapshot."""

    __tablename__ = "automation_flow_versions"
    __table_args__ = (
        UniqueConstraint("flow_id", "version_no", name="uq_automation_flow_version_no"),
        Index("ix_automation_flow_versions_flow_published", "flow_id", "published_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    flow_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("automation_flows.id", name="fk_automation_flow_versions_flow", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(int_id(), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    published_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    published_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
