"""Media schemas (Doc 04 §16)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.media import MediaAsset


class MediaResponse(BaseModel):
    id: str
    type: str = "media_asset"
    media_type: str
    mime_type: str
    file_name: str | None
    byte_size: int
    sha256: str
    storage_backend: str
    width: int | None
    height: int | None
    duration_sec: int | None
    usage_count: int
    created_at: datetime

    @classmethod
    def from_asset(cls, asset: MediaAsset) -> MediaResponse:
        return cls(
            id=asset.public_id,
            media_type=asset.media_type,
            mime_type=asset.mime_type,
            file_name=asset.file_name,
            byte_size=asset.byte_size,
            sha256=asset.sha256,
            storage_backend=asset.storage_backend,
            width=asset.width,
            height=asset.height,
            duration_sec=asset.duration_sec,
            usage_count=asset.usage_count,
            created_at=asset.created_at,
        )


class MediaListResponse(BaseModel):
    data: list[MediaResponse]
    total: int


class MediaContentResponse(BaseModel):
    """A signed, expiring URL for the asset (Doc 04 §16, FR-MED-09)."""

    url: str
    expires_in: int
