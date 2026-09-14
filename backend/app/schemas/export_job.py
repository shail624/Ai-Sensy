"""Contact export schemas (Doc 04 §3 async envelope, §14.1)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.pagination import Page
from app.models.job_records import ExportJob
from app.models.segment import MATCH_ALL
from app.schemas.segment import SegmentRuleModel


class ExportCreateRequest(BaseModel):
    """``POST /contacts/export`` — filters reuse the segment/search rule shape."""

    format: str = "csv"
    match_type: str = MATCH_ALL
    rules: list[SegmentRuleModel] = Field(default_factory=list)


def _naive_utc(value: datetime | None) -> datetime | None:
    """Store one unambiguous UTC instant in the platform's naive-UTC database convention."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


class ConversationTranscriptExportRequest(BaseModel):
    """Queue a transcript for one tenant-scoped conversation.

    ``from`` is inclusive and ``to`` is exclusive. Both are optional so an operator can export the
    complete factual thread; when supplied they are normalized to the platform's UTC convention.
    """

    model_config = ConfigDict(populate_by_name=True)

    conversation_id: uuidlib.UUID
    format: Literal["pdf", "csv", "xlsx", "json"] = "pdf"
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

    @model_validator(mode="after")
    def _valid_range(self) -> ConversationTranscriptExportRequest:
        self.from_ = _naive_utc(self.from_)
        self.to = _naive_utc(self.to)
        if self.from_ is not None and self.to is not None and self.from_ >= self.to:
            raise ValueError("from must be earlier than to")
        return self


class CampaignResultsExportRequest(BaseModel):
    """Queue one campaign's factual per-recipient result ledger."""

    format: Literal["pdf", "csv", "xlsx", "json"] = "xlsx"
    status: Literal[
        "pending",
        "queued",
        "sent",
        "delivered",
        "read",
        "failed",
        "skipped",
        "cancelled",
    ] | None = None


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


class DownloadItemResponse(BaseModel):
    """One permission-filtered artifact in the user's Download Center."""

    id: str
    type: str = "download"
    category: str
    name: str
    format: str
    status: str
    row_count: int | None
    download_url: str | None
    expires_at: datetime | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: ExportJob, download_url: str | None) -> DownloadItemResponse:
        is_report = job.entity.startswith("report:")
        is_transcript = job.entity == "conversation_transcript"
        is_campaign = job.entity == "campaign_results"
        report_name = job.entity.removeprefix("report:").replace("_", " ")
        campaign_name = str((job.filters_json or {}).get("campaign_name") or "Campaign")
        return cls(
            id=job.public_id,
            category=(
                "analytics"
                if is_report
                else "chat_history"
                if is_transcript
                else "campaigns"
                if is_campaign
                else "contacts"
            ),
            name=(
                f"{report_name.title()} report"
                if is_report
                else "Chat transcript"
                if is_transcript
                else f"{campaign_name} results"
                if is_campaign
                else "Contacts export"
            ),
            format=job.format,
            status="expired" if job.is_expired else job.status,
            row_count=job.row_count,
            download_url=None if job.is_expired else download_url,
            expires_at=job.expires_at,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )


class DownloadsPage(BaseModel):
    data: list[DownloadItemResponse]
    page: Page
