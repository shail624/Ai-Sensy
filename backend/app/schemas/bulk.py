"""Bulk contact operation schemas (Doc 04 §29 partial success, §30 bulk operations).

Addressing follows §30's two mutually-exclusive modes: an explicit ``ids`` selection, or a
``filter`` the server resolves. The filter reuses the segment/search rule shape, so a saved
segment, an ad-hoc search, an export and a bulk edit all describe an audience the same way.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.job_records import (
    BULK_ACTIONS,
    DEDUP_KEYS,
    DEDUP_MODES,
    MODE_REPORT,
    BulkJob,
)
from app.models.segment import MATCH_ALL, MATCH_TYPES
from app.schemas.segment import SegmentRuleModel


class BulkFilter(BaseModel):
    """A filter that resolves to an audience (Doc 04 §30 addressing mode (b))."""

    match_type: str = MATCH_ALL
    rules: list[SegmentRuleModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> BulkFilter:
        if self.match_type not in MATCH_TYPES:
            raise ValueError(f"match_type must be one of {list(MATCH_TYPES)}")
        return self


class _Addressed(BaseModel):
    """Shared addressing: exactly one of ``ids`` / ``filter``, plus the §30 safety guard."""

    ids: list[uuidlib.UUID] | None = None
    filter: BulkFilter | None = None
    #: Optional guard — if the resolved count differs, the server returns 409 rather than
    #: acting on a surprise set (Doc 04 §30).
    expected_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _exclusive(self) -> _Addressed:
        if (self.ids is None) == (self.filter is None):
            raise ValueError("provide exactly one of 'ids' or 'filter'")
        if self.ids is not None and not self.ids:
            raise ValueError("'ids' must not be empty")
        return self


class BulkUpdateRequest(_Addressed):
    """``POST /contacts/bulk-update`` — add/remove tags or set attributes (FR-CON-07)."""

    action: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _action(self) -> BulkUpdateRequest:
        if self.action not in BULK_ACTIONS:
            raise ValueError(f"action must be one of {list(BULK_ACTIONS)}")
        return self


class BulkDeleteRequest(_Addressed):
    """``POST /contacts/bulk-delete`` — soft-delete over a selection or filter (FR-CON-08)."""


class DeduplicateRequest(BaseModel):
    """``POST /contacts/deduplicate`` — dedup scan, report or merge (FR-CON-06)."""

    keys: list[str] = Field(default_factory=lambda: ["email"])
    mode: str = MODE_REPORT

    @model_validator(mode="after")
    def _check(self) -> DeduplicateRequest:
        if self.mode not in DEDUP_MODES:
            raise ValueError(f"mode must be one of {list(DEDUP_MODES)}")
        if not self.keys:
            raise ValueError("'keys' must not be empty")
        unknown = [k for k in self.keys if k not in DEDUP_KEYS]
        if unknown:
            raise ValueError(f"unknown dedup keys {unknown}; supported: {list(DEDUP_KEYS)}")
        return self


class BulkSummary(BaseModel):
    """The §29 summary block; ``processed`` drives the live progress bar (§30)."""

    total: int | None
    processed: int
    succeeded: int
    failed: int
    skipped: int


class BulkItemError(BaseModel):
    """One per-item failure (§29 ``errors[]``)."""

    id: str | None = None
    code: str
    message: str


class BulkProgressResponse(BaseModel):
    """``GET /contacts/bulk/{uuid}`` — the §29 ``PartialSuccessResult`` for an async job."""

    id: str
    type: str
    operation: str
    action: str | None
    job_status: str
    status: str
    summary: BulkSummary
    errors: list[BulkItemError]
    error_report_url: str | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: BulkJob, error_report_url: str | None) -> BulkProgressResponse:
        return cls(
            id=job.public_id,
            type=job.operation,
            operation=job.operation,
            action=job.action,
            job_status=job.status,
            status=job.result_status,
            summary=BulkSummary(
                total=job.total_items,
                processed=job.processed_items,
                succeeded=job.succeeded_items,
                failed=job.failed_items,
                skipped=job.skipped_items,
            ),
            errors=[BulkItemError(**item) for item in (job.errors_json or [])],
            error_report_url=error_report_url,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
