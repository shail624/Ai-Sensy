"""Versioned automation definitions and deterministic test-run evidence (Docs 22/23)."""

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
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id, uuid_binary

AUTOMATION_STATUS_DRAFT = "draft"
AUTOMATION_STATUS_PUBLISHED = "published"
AUTOMATION_STATUS_DISABLED = "disabled"
AUTOMATION_STATUSES: tuple[str, ...] = (
    AUTOMATION_STATUS_DRAFT,
    AUTOMATION_STATUS_PUBLISHED,
    AUTOMATION_STATUS_DISABLED,
)

AUTOMATION_RUN_QUEUED = "queued"
AUTOMATION_RUN_RUNNING = "running"
AUTOMATION_RUN_RETRYING = "retrying"
AUTOMATION_RUN_SUCCEEDED = "succeeded"
AUTOMATION_RUN_FAILED = "failed"
AUTOMATION_RUN_STATUSES: tuple[str, ...] = (
    AUTOMATION_RUN_QUEUED,
    AUTOMATION_RUN_RUNNING,
    AUTOMATION_RUN_RETRYING,
    AUTOMATION_RUN_SUCCEEDED,
    AUTOMATION_RUN_FAILED,
)
AUTOMATION_RUN_TERMINAL_STATUSES = (AUTOMATION_RUN_SUCCEEDED, AUTOMATION_RUN_FAILED)

AUTOMATION_ATTEMPT_RUNNING = "running"
AUTOMATION_ATTEMPT_SUCCEEDED = "succeeded"
AUTOMATION_ATTEMPT_FAILED = "failed"
AUTOMATION_ATTEMPT_INTERRUPTED = "interrupted"
AUTOMATION_ATTEMPT_STATUSES: tuple[str, ...] = (
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SUCCEEDED,
    AUTOMATION_ATTEMPT_FAILED,
    AUTOMATION_ATTEMPT_INTERRUPTED,
)

AUTOMATION_TRIGGER_RECEIPT_RECEIVED = "received"
AUTOMATION_TRIGGER_RECEIPT_STATUSES = (AUTOMATION_TRIGGER_RECEIPT_RECEIVED,)


def _status_clause() -> str:
    return f"status IN ({', '.join(repr(value) for value in AUTOMATION_STATUSES)})"


def _run_status_clause() -> str:
    return f"status IN ({', '.join(repr(value) for value in AUTOMATION_RUN_STATUSES)})"


def _attempt_status_clause() -> str:
    return f"status IN ({', '.join(repr(value) for value in AUTOMATION_ATTEMPT_STATUSES)})"


def _trigger_receipt_status_clause() -> str:
    return f"status IN ({', '.join(repr(value) for value in AUTOMATION_TRIGGER_RECEIPT_STATUSES)})"


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
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=AUTOMATION_STATUS_DRAFT)
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
        ForeignKey(
            "automation_flows.id", name="fk_automation_flow_versions_flow", ondelete="CASCADE"
        ),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(int_id(), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    published_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    published_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class AutomationRun(IntPKMixin, UUIDMixin, Base):
    """One tenant-scoped test execution pinned to an immutable published version."""

    __tablename__ = "automation_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_automation_run_idempotency"
        ),
        Index("ix_automation_runs_flow_created", "flow_id", "created_at"),
        Index("ix_automation_runs_org_status_created", "organization_id", "status", "created_at"),
        CheckConstraint(_run_status_clause(), name="ck_automation_runs_status"),
        CheckConstraint("mode = 'test'", name="ck_automation_runs_mode"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    flow_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("automation_flows.id", name="fk_automation_runs_flow", ondelete="RESTRICT"),
        nullable=False,
    )
    version_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "automation_flow_versions.id",
            name="fk_automation_runs_version",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(12), nullable=False, default="test")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=AUTOMATION_RUN_QUEUED)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    trigger_input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    total_steps: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    completed_steps: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class AutomationStepAttempt(IntPKMixin, UUIDMixin, Base):
    """A durable, numbered attempt for one published node in an automation run."""

    __tablename__ = "automation_step_attempts"
    __table_args__ = (
        UniqueConstraint("run_id", "node_id", "attempt_no", name="uq_automation_step_attempt"),
        Index("ix_automation_step_attempts_run_started", "run_id", "started_at"),
        CheckConstraint(_attempt_status_clause(), name="ck_automation_step_attempts_status"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    run_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "automation_runs.id", name="fk_automation_step_attempts_run", ondelete="CASCADE"
        ),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    attempt_no: Mapped[int] = mapped_column(int_id(), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AUTOMATION_ATTEMPT_RUNNING
    )
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)


class AutomationTriggerReceipt(IntPKMixin, UUIDMixin, Base):
    """One real event matched to one active immutable automation version."""

    __tablename__ = "automation_trigger_receipts"
    __table_args__ = (
        UniqueConstraint(
            "flow_id", "version_id", "event_uuid", name="uq_automation_trigger_receipt"
        ),
        Index("ix_automation_trigger_receipts_flow_received", "flow_id", "received_at"),
        Index(
            "ix_automation_trigger_receipts_org_status_received",
            "organization_id",
            "status",
            "received_at",
        ),
        CheckConstraint(
            _trigger_receipt_status_clause(), name="ck_automation_trigger_receipts_status"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    flow_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "automation_flows.id", name="fk_automation_trigger_receipts_flow", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    version_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "automation_flow_versions.id",
            name="fk_automation_trigger_receipts_version",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    event_uuid: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_version: Mapped[int] = mapped_column(int_id(), nullable=False, default=1)
    event_occurred_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AUTOMATION_TRIGGER_RECEIPT_RECEIVED
    )
    received_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
