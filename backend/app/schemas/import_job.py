"""Contact import schemas (Doc 04 §3 async envelope, §14.1)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.job_records import DEDUP_SKIP, ImportJob


class ImportCreateRequest(BaseModel):
    """``POST /contacts/import`` (Doc 04 §14.1 sample)."""

    upload_id: uuidlib.UUID
    format: str = "csv"
    mapping: dict[str, str] = Field(min_length=1)
    dedup_strategy: str = DEDUP_SKIP


class ImportInspectRequest(BaseModel):
    """``POST /contacts/import/inspect`` — read an uploaded file's shape, import nothing."""

    upload_id: uuidlib.UUID
    format: str = "csv"


class ImportInspectResponse(BaseModel):
    """Just enough for the wizard's mapping step (Doc 05 B3.3 step 2)."""

    type: str = "import_inspection"
    headers: list[str]
    sample_row: list[str]
    #: Worksheet the headers came from; ``None`` for CSV, which has no sheets.
    sheet_name: str | None
    #: From the workbook's stored dimension, so a generator may omit or overstate it. The import
    #: itself always reports the true count.
    estimated_rows: int | None
    errors: list[dict[str, str]]


class JobEnvelope(BaseModel):
    """The ``job`` object of a 202 response (Doc 04 §3)."""

    id: str
    type: str
    status: str
    poll_url: str


class JobAcceptedResponse(BaseModel):
    """``202 Accepted`` — the only response a long-running operation returns (Doc 04 §3)."""

    job: JobEnvelope


class ImportProgressResponse(BaseModel):
    """``GET /contacts/import/{uuid}`` — progress + error report link (FR-CON-05)."""

    id: str
    type: str = "import"
    status: str
    format: str
    dedup_strategy: str | None
    total_rows: int | None
    processed_rows: int
    success_rows: int
    error_rows: int
    error_report_url: str | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: ImportJob, error_report_url: str | None) -> ImportProgressResponse:
        return cls(
            id=job.public_id,
            status=job.status,
            format=job.format,
            dedup_strategy=job.dedup_strategy,
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            success_rows=job.success_rows,
            error_rows=job.error_rows,
            error_report_url=error_report_url,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
