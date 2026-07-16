"""Job metadata & dead-letter models (Doc 03 §11.7; Doc 06 §7).

``job_metadata`` is the **durable mirror of Celery job state** — Redis is transient, so job
status/progress and the ``/jobs`` monitoring surface read from MySQL (Doc 03 §11.7, FR-MON-01/02).

``dead_letter`` is the general parked-task store (Doc 06 §7.3): work that exhausted retries or
is unclassifiable/poison, kept durably with its original payload so it can be inspected,
grouped by ``fingerprint`` (§7.4), replayed through the same idempotent processor, or discarded
— never silently lost. (``webhook_dead_letter`` in Doc 03 §9.4 is the webhook-specific store
and belongs to the Messaging module.)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, small_uint

# job_metadata.status (Doc 03 §11.7)
JOB_QUEUED = "queued"
JOB_STARTED = "started"
JOB_SUCCESS = "success"
JOB_FAILURE = "failure"
JOB_RETRY = "retry"
JOB_REVOKED = "revoked"
JOB_STATUSES = (JOB_QUEUED, JOB_STARTED, JOB_SUCCESS, JOB_FAILURE, JOB_RETRY, JOB_REVOKED)
JOB_TERMINAL_STATUSES = (JOB_SUCCESS, JOB_FAILURE, JOB_REVOKED)

# dead_letter.status (Doc 06 §7.4)
DL_PARKED = "parked"
DL_REPLAYED = "replayed"
DL_DISCARDED = "discarded"


class JobMetadata(IntPKMixin, UUIDMixin, Base):
    """Durable mirror of a Celery job (Doc 03 §11.7)."""

    __tablename__ = "job_metadata"
    __table_args__ = (
        Index("ix_job_status", "status", "created_at"),
        Index("ix_job_ref", "ref_type", "ref_id"),
        MYSQL_TABLE_ARGS,
    )

    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    task_name: Mapped[str] = mapped_column(String(160), nullable=False)
    queue: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JOB_QUEUED)
    ref_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    args_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    attempts: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    @property
    def is_terminal(self) -> bool:
        return self.status in JOB_TERMINAL_STATUSES

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<JobMetadata {self.task_name} {self.status}>"


class DeadLetter(IntPKMixin, UUIDMixin, Base):
    """A parked task that could not be processed (Doc 06 §7)."""

    __tablename__ = "dead_letter"
    __table_args__ = (
        Index("ix_dl_status", "status", "created_at"),
        Index("ix_dl_fingerprint", "fingerprint", "created_at"),
        Index("ix_dl_queue", "source_queue", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    source_queue: Mapped[str] = mapped_column(String(60), nullable=False)
    task_name: Mapped[str] = mapped_column(String(160), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stack_trace: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    attempts: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    #: Groups identical root causes so a spike shows one cause, not thousands of rows (§7.4).
    fingerprint: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    request_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=DL_PARKED)
    resolved_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<DeadLetter {self.task_name} {self.status}>"
