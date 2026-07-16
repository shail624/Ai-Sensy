"""Contact export schemas (Doc 04 §3 async envelope, §14.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.job_records import ExportJob
from app.models.segment import MATCH_ALL
from app.schemas.segment import SegmentRuleModel


class ExportCreateRequest(BaseModel):
    """``POST /contacts/export`` — filters reuse the segment/search rule shape."""

    format: str = "csv"
    match_type: str = MATCH_ALL
    rules: list[SegmentRuleModel] = Field(default_factory=list)


class ExportProgressResponse(BaseModel):
    """``GET /contacts/export/{uuid}`` — progress + signed download link."""

    id: str
    type: str = "export"
    status: str
    format: str
    row_count: int | None
    download_url: str | None
    expires_at: datetime | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: ExportJob, download_url: str | None) -> ExportProgressResponse:
        return cls(
            id=job.public_id,
            status=job.status,
            format=job.format,
            row_count=job.row_count,
            download_url=download_url,
            expires_at=job.expires_at,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
