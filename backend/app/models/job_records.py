"""Import & export job records (Doc 03 §11.6).

The durable, user-facing records of bulk work. Distinct from ``job_metadata`` (Doc 03 §11.7,
which mirrors *Celery* state): these hold the **business** outcome an operator sees — rows
processed/succeeded/failed and the downloadable error report (FR-CON-05), or the generated
artifact and its expiry (FR-CON-15). Both link to their Celery job via
``job_metadata.ref_type``/``ref_id``.
"""

from __future__ import annotations

from datetime import datetime

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
    mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
