"""API contract for governed customer documents (Design Book 19)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.services.contact_document_service import (
    DocumentEventView,
    DocumentVersionView,
    DocumentView,
)

DocumentType = Literal["identity", "address", "income", "business", "consent", "other"]
DocumentStatus = Literal["submitted", "verified", "rejected", "expired", "archived"]
VerificationDecision = Literal["verified", "rejected"]


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


NaiveUTC = Annotated[datetime, AfterValidator(_to_naive_utc)]


class DocumentCreateRequest(BaseModel):
    document_type: DocumentType
    title: str = Field(min_length=1, max_length=160)
    media_asset_id: uuidlib.UUID
    expires_at: NaiveUTC | None = None
    note: str | None = Field(default=None, max_length=2000)


class DocumentVersionCreateRequest(BaseModel):
    media_asset_id: uuidlib.UUID
    note: str | None = Field(default=None, max_length=2000)
    expected_row_version: int | None = Field(default=None, ge=0)


class DocumentVerificationRequest(BaseModel):
    decision: VerificationDecision
    reason: str | None = Field(default=None, max_length=2000)
    expected_row_version: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def rejection_needs_reason(self) -> DocumentVerificationRequest:
        if self.decision == "rejected" and not (self.reason or "").strip():
            raise ValueError("reason is required when rejecting a document")
        return self


class DocumentTransitionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    expected_row_version: int | None = Field(default=None, ge=0)


class DocumentVersionResponse(BaseModel):
    id: str
    version_no: int
    media_asset_id: str
    file_name: str | None
    mime_type: str
    byte_size: int
    note: str | None
    uploaded_by: str | None
    uploaded_by_name: str | None
    created_at: datetime

    @classmethod
    def of(cls, view: DocumentVersionView) -> DocumentVersionResponse:
        return cls(
            id=view.id,
            version_no=view.version_no,
            media_asset_id=view.media_asset_id,
            file_name=view.file_name,
            mime_type=view.mime_type,
            byte_size=view.byte_size,
            note=view.note,
            uploaded_by=view.uploaded_by,
            uploaded_by_name=view.uploaded_by_name,
            created_at=view.created_at,
        )


class DocumentResponse(BaseModel):
    id: str
    contact_id: str
    document_type: DocumentType
    title: str
    status: DocumentStatus
    is_expired: bool
    expires_at: datetime | None
    verified_at: datetime | None
    verified_by: str | None
    verified_by_name: str | None
    rejection_reason: str | None
    archived_at: datetime | None
    current_version: DocumentVersionResponse
    versions: list[DocumentVersionResponse]
    version_count: int
    row_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, view: DocumentView) -> DocumentResponse:
        return cls(
            id=view.id,
            contact_id=view.contact_id,
            document_type=view.document_type,
            title=view.title,
            status=view.status,
            is_expired=view.is_expired,
            expires_at=view.expires_at,
            verified_at=view.verified_at,
            verified_by=view.verified_by,
            verified_by_name=view.verified_by_name,
            rejection_reason=view.rejection_reason,
            archived_at=view.archived_at,
            current_version=DocumentVersionResponse.of(view.current_version),
            versions=[DocumentVersionResponse.of(version) for version in view.versions],
            version_count=len(view.versions),
            row_version=view.row_version,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class DocumentListResponse(BaseModel):
    data: list[DocumentResponse]
    total: int


class DocumentEventResponse(BaseModel):
    id: int
    event_type: str
    actor_user_id: str | None
    actor_name: str | None
    from_value: dict[str, Any] | None
    to_value: dict[str, Any] | None
    reason: str | None
    created_at: datetime

    @classmethod
    def of(cls, view: DocumentEventView) -> DocumentEventResponse:
        return cls(
            id=view.id,
            event_type=view.event_type,
            actor_user_id=view.actor_user_id,
            actor_name=view.actor_name,
            from_value=view.from_value,
            to_value=view.to_value,
            reason=view.reason,
            created_at=view.created_at,
        )


class DocumentHistoryResponse(BaseModel):
    data: list[DocumentEventResponse]


class DocumentContentResponse(BaseModel):
    url: str
    expires_in: int
