"""Import job record (Doc 03 §11.6).

The durable, user-facing record of a bulk import. Distinct from ``job_metadata`` (Doc 03 §11.7,
which mirrors *Celery* state): this holds the **business** progress an operator sees — rows
processed/succeeded/failed, the dedup strategy, and the downloadable error report (FR-CON-05).
The two are linked via ``job_metadata.ref_type='import'`` / ``ref_id``.

``exports`` (also Doc 03 §11.6) lands with the Export step.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

#: Duplicate handling on import (FR-CON-06).
DEDUP_SKIP = "skip"
DEDUP_MERGE = "merge"
DEDUP_OVERWRITE = "overwrite"
DEDUP_STRATEGIES = (DEDUP_SKIP, DEDUP_MERGE, DEDUP_OVERWRITE)


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
