"""Provider-neutral history checkpoint and media-reference persistence.

The records are inert control-plane facts. They do not start provider work, fetch history, ingest
events, transfer media, or bypass provider certification. Opaque provider metadata is constrained
to non-secret JSON and all repository access remains organization-scoped.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.channels.secrets import assert_no_secret_material
from app.channels.sync import ChannelSyncStatus, ChannelSyncType, MediaTransferState
from app.db.base import Base
from app.db.mixins import AuditMixin, IntPKMixin, TimestampMixin, UUIDMixin, VersionMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

_SYNC_TYPES = tuple(item.value for item in ChannelSyncType)
_SYNC_STATUSES = tuple(item.value for item in ChannelSyncStatus)
_MEDIA_STATES = tuple(item.value for item in MediaTransferState)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ChannelSyncCheckpoint(
    IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base
):
    """One organization/connection/endpoint synchronization checkpoint."""

    __tablename__ = "channel_sync_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "connection_id",
            "endpoint_id",
            "sync_type",
            name="uq_channel_sync_checkpoint_scope",
        ),
        Index(
            "ix_channel_sync_checkpoints_org_status",
            "organization_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_channel_sync_checkpoints_connection_endpoint",
            "connection_id",
            "endpoint_id",
            "sync_type",
        ),
        CheckConstraint(
            _in_clause("sync_type", _SYNC_TYPES),
            name="ck_channel_sync_checkpoint_type",
        ),
        CheckConstraint(
            _in_clause("status", _SYNC_STATUSES),
            name="ck_channel_sync_checkpoint_status",
        ),
        CheckConstraint(
            "processed_count >= 0",
            name="ck_channel_sync_checkpoint_processed_non_negative",
        ),
        CheckConstraint(
            "failed_count >= 0",
            name="ck_channel_sync_checkpoint_failed_non_negative",
        ),
        CheckConstraint(
            "total_count IS NULL OR total_count >= 0",
            name="ck_channel_sync_checkpoint_total_non_negative",
        ),
        CheckConstraint(
            "failed_count <= processed_count",
            name="ck_channel_sync_checkpoint_failed_within_processed",
        ),
        CheckConstraint(
            "total_count IS NULL OR processed_count <= total_count",
            name="ck_channel_sync_checkpoint_processed_within_total",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_connections.id", ondelete="RESTRICT"), nullable=False
    )
    endpoint_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_endpoints.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("job_metadata.id", ondelete="SET NULL"), nullable=True
    )
    sync_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ChannelSyncType.HISTORY.value
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ChannelSyncStatus.PENDING.value
    )
    cursor_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    watermark_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    cutover_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    processed_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    total_count: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_progress_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @validates("cursor_json")
    def _validate_cursor(
        self, key: str, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            assert_no_secret_material(value, field_name=key)
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ChannelSyncCheckpoint id={self.id} connection_id={self.connection_id} "
            f"endpoint_id={self.endpoint_id} type={self.sync_type!r} status={self.status!r}>"
        )


class MediaChannelReference(
    IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base
):
    """One provider media identifier scoped to an existing endpoint and media asset."""

    __tablename__ = "media_channel_references"
    __table_args__ = (
        UniqueConstraint(
            "endpoint_id",
            "provider_media_id",
            name="uq_media_channel_reference_provider_identity",
        ),
        Index(
            "ix_media_channel_references_org_asset",
            "organization_id",
            "media_asset_id",
            "updated_at",
        ),
        Index(
            "ix_media_channel_references_org_endpoint",
            "organization_id",
            "endpoint_id",
            "updated_at",
        ),
        Index(
            "ix_media_channel_references_expiry",
            "expires_at",
            "download_state",
            "upload_state",
        ),
        CheckConstraint(
            _in_clause("upload_state", _MEDIA_STATES),
            name="ck_media_channel_reference_upload_state",
        ),
        CheckConstraint(
            _in_clause("download_state", _MEDIA_STATES),
            name="ck_media_channel_reference_download_state",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    media_asset_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False
    )
    endpoint_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_endpoints.id", ondelete="RESTRICT"), nullable=False
    )
    provider_media_id: Mapped[str] = mapped_column(String(190), nullable=False)
    upload_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=MediaTransferState.NOT_REQUESTED.value
    )
    download_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=MediaTransferState.NOT_REQUESTED.value
    )
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @validates("provider_metadata_json")
    def _validate_provider_metadata(
        self, key: str, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            assert_no_secret_material(value, field_name=key)
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<MediaChannelReference id={self.id} endpoint_id={self.endpoint_id} "
            f"media_asset_id={self.media_asset_id} provider_media_id={self.provider_media_id!r}>"
        )
