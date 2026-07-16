"""Media asset model (Doc 03 §7.2) — file metadata, never blobs (FR-MED-06).

The row holds metadata plus a **reference** (`storage_backend` + `storage_key`); the bytes live
in the storage backend. `(organization_id, sha256)` is unique so one stored blob is reused
across templates/campaigns/messages (FR-MED-05 content dedup).

`meta_media_id`/`meta_media_expires_at` and the dimension/duration columns are part of the
frozen schema; they are populated by the Meta integration and media-processing modules.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id


class MediaAsset(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A stored file (Doc 03 §7.2)."""

    __tablename__ = "media_assets"
    __table_args__ = (
        Index("uq_media_org_sha", "organization_id", "sha256", unique=True),
        Index("ix_media_type", "organization_id", "media_type"),
        CheckConstraint(
            "media_type IN ('image','video','document','audio','sticker')", name="ck_media_type"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_media_org", ondelete="CASCADE"),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    byte_size: Mapped[int] = mapped_column(big_id(), nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    height: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    meta_media_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_media_expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    usage_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<MediaAsset id={self.id} {self.media_type}/{self.mime_type}>"
