"""Import, export & bulk job records (Doc 03 §11.6).

The durable, user-facing records of bulk work. Distinct from ``job_metadata`` (Doc 03 §11.7,
which mirrors *Celery* state): these hold the **business** outcome an operator sees — rows
processed/succeeded/failed and the downloadable error report (FR-CON-05), or the generated
artifact and its expiry (FR-CON-15). Each links to its Celery job via
``job_metadata.ref_type``/``ref_id``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
STATUS_EXPIRED = "expired"

#: Duplicate handling on import (FR-CON-06).
DEDUP_SKIP = "skip"
DEDUP_MERGE = "merge"
DEDUP_OVERWRITE = "overwrite"
DEDUP_STRATEGIES = (DEDUP_SKIP, DEDUP_MERGE, DEDUP_OVERWRITE)

EXPORT_FORMATS = ("csv", "xlsx", "json")

# --- Bulk operations (Doc 04 §30; FR-CON-06/07/08) --------------------------
OP_BULK_UPDATE = "bulk_update"
OP_BULK_DELETE = "bulk_delete"
OP_DEDUPLICATE = "deduplicate"
BULK_OPERATIONS = (OP_BULK_UPDATE, OP_BULK_DELETE, OP_DEDUPLICATE)

#: ``bulk_update`` actions — the edits FR-CON-07 scopes to a selection or filter.
ACTION_ADD_TAGS = "add_tags"
ACTION_REMOVE_TAGS = "remove_tags"
ACTION_SET_ATTRIBUTES = "set_attributes"
BULK_ACTIONS = (ACTION_ADD_TAGS, ACTION_REMOVE_TAGS, ACTION_SET_ATTRIBUTES)

#: ``deduplicate`` modes (Doc 04 §14.1 — "report or merge").
MODE_REPORT = "report"
MODE_MERGE = "merge"
DEDUP_MODES = (MODE_REPORT, MODE_MERGE)

#: Keys a dedup scan may group on (FR-CON-06 "normalized phone and configurable keys").
DEDUP_KEYS = ("wa_id", "phone_e164", "email", "full_name")

#: Per §29 the inline error list is capped; the full set goes to the error report.
ERROR_CAP = 100


class ImportJob(IntPKMixin, UUIDMixin, Base):
    """A chunked contact import (Doc 03 §11.6; FR-CON-03/05/06)."""

    __tablename__ = "imports"
    __table_args__ = (
        Index("ix_imports_org", "organization_id", "status", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_imports_org", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    entity: Mapped[str] = mapped_column(String(40), nullable=False, default="contacts")
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    #: Storage key of the uploaded source file (never the bytes — Doc 08 §14).
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mapping_json: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    dedup_strategy: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_PENDING)
    total_rows: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    processed_rows: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    error_report_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ImportJob id={self.id} {self.status}>"


class ExportJob(IntPKMixin, UUIDMixin, Base):
    """A generated export artifact (Doc 03 §11.6; FR-CON-15).

    ``storage_key`` references the artifact in the storage backend (never the bytes) and
    ``expires_at`` bounds how long it stays downloadable.
    """

    __tablename__ = "exports"
    __table_args__ = (
        Index("ix_exports_org", "organization_id", "status", "created_at"),
        CheckConstraint("format IN ('csv','xlsx','json')", name="ck_exports_format"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_exports_org", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    entity: Mapped[str] = mapped_column(String(40), nullable=False, default="contacts")
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    #: The filter set the export was resolved from (Doc 03 §11.6).
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_PENDING)
    row_count: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= utcnow()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ExportJob id={self.id} {self.status}>"


class BulkJob(IntPKMixin, UUIDMixin, Base):
    """A bulk contact operation — update / delete / deduplicate (Doc 04 §30; FR-CON-06/07/08).

    Sits beside ``imports``/``exports`` in the Doc 03 §11.6 job-record family and exists for the
    same reason they do: ``job_metadata`` mirrors *Celery* state and is organization-blind, so it
    can neither be scoped to a tenant nor carry the per-item outcome the operator polls. This row
    is the durable **business** record — the resolved request, live progress, and the capped
    ``errors_json`` + downloadable report that make up the §29 partial-success envelope.
    """

    __tablename__ = "bulk_jobs"
    __table_args__ = (
        Index("ix_bulk_jobs_org", "organization_id", "status", "created_at"),
        CheckConstraint(
            "operation IN ('bulk_update','bulk_delete','deduplicate')", name="ck_bulk_jobs_operation"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_bulk_jobs_org", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    entity: Mapped[str] = mapped_column(String(40), nullable=False, default="contacts")
    operation: Mapped[str] = mapped_column(String(24), nullable=False)
    #: ``bulk_update`` only: which edit to apply (``add_tags``/``remove_tags``/``set_attributes``).
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: The validated request: addressing (ids or filter) + action payload (Doc 04 §30).
    request_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_PENDING)
    total_items: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    processed_items: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    succeeded_items: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    skipped_items: Mapped[int] = mapped_column(big_id(), nullable=False, default=0)
    #: First ``ERROR_CAP`` per-item failures, inline for the UI (§29); the rest are in the report.
    errors_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    error_report_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    @property
    def result_status(self) -> str:
        """``success`` | ``partial_success`` | ``failed`` — the §29 envelope's source of truth."""
        if self.status == STATUS_FAILED:
            return "failed"
        if self.failed_items:
            return "failed" if not self.succeeded_items else "partial_success"
        return "success"

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<BulkJob id={self.id} {self.operation} {self.status}>"
