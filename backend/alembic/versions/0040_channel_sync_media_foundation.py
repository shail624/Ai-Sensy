"""Provider-neutral synchronization checkpoint and media-reference persistence.

Revision ID: 0040_channel_sync_media_foundation
Revises: 0039_qr_pairing_provider_runtime_foundation
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.channels.sync import ChannelSyncStatus, ChannelSyncType, MediaTransferState
from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0040_channel_sync_media_foundation"
down_revision = "0039_qr_pairing_provider_runtime_foundation"
branch_labels = None
depends_on = None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _table_args(dialect: str) -> dict[str, Any]:
    if dialect != "mysql":
        return {}
    return {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    args = _table_args(dialect)
    sync_types = tuple(item.value for item in ChannelSyncType)
    sync_statuses = tuple(item.value for item in ChannelSyncStatus)
    media_states = tuple(item.value for item in MediaTransferState)

    op.create_table(
        "channel_sync_checkpoints",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("connection_id", big_id(), nullable=False),
        sa.Column("endpoint_id", big_id(), nullable=False),
        sa.Column("job_id", big_id(), nullable=True),
        sa.Column(
            "sync_type",
            sa.String(32),
            nullable=False,
            server_default=ChannelSyncType.HISTORY.value,
        ),
        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default=ChannelSyncStatus.PENDING.value,
        ),
        sa.Column("cursor_json", sa.JSON(), nullable=True),
        sa.Column("watermark_at", datetime6(), nullable=True),
        sa.Column("cutover_at", datetime6(), nullable=True),
        sa.Column("processed_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_count", int_id(), nullable=True),
        sa.Column("started_at", datetime6(), nullable=True),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.Column("last_progress_at", datetime6(), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_channel_sync_checkpoints_uuid"),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "endpoint_id",
            "sync_type",
            name="uq_channel_sync_checkpoint_scope",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["connection_id"], ["channel_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["channel_endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["job_metadata.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("sync_type", sync_types),
            name="ck_channel_sync_checkpoint_type",
        ),
        sa.CheckConstraint(
            _in("status", sync_statuses),
            name="ck_channel_sync_checkpoint_status",
        ),
        sa.CheckConstraint(
            "processed_count >= 0",
            name="ck_channel_sync_checkpoint_processed_non_negative",
        ),
        sa.CheckConstraint(
            "failed_count >= 0",
            name="ck_channel_sync_checkpoint_failed_non_negative",
        ),
        sa.CheckConstraint(
            "total_count IS NULL OR total_count >= 0",
            name="ck_channel_sync_checkpoint_total_non_negative",
        ),
        sa.CheckConstraint(
            "failed_count <= processed_count",
            name="ck_channel_sync_checkpoint_failed_within_processed",
        ),
        sa.CheckConstraint(
            "total_count IS NULL OR processed_count <= total_count",
            name="ck_channel_sync_checkpoint_processed_within_total",
        ),
        **args,
    )
    op.create_index(
        "ix_channel_sync_checkpoints_org_status",
        "channel_sync_checkpoints",
        ["organization_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_channel_sync_checkpoints_connection_endpoint",
        "channel_sync_checkpoints",
        ["connection_id", "endpoint_id", "sync_type"],
    )

    op.create_table(
        "media_channel_references",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("media_asset_id", big_id(), nullable=False),
        sa.Column("endpoint_id", big_id(), nullable=False),
        sa.Column("provider_media_id", sa.String(190), nullable=False),
        sa.Column(
            "upload_state",
            sa.String(24),
            nullable=False,
            server_default=MediaTransferState.NOT_REQUESTED.value,
        ),
        sa.Column(
            "download_state",
            sa.String(24),
            nullable=False,
            server_default=MediaTransferState.NOT_REQUESTED.value,
        ),
        sa.Column("expires_at", datetime6(), nullable=True),
        sa.Column("last_verified_at", datetime6(), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=True),
        sa.Column("last_error_code", sa.String(120), nullable=True),
        sa.Column("last_error_summary", sa.String(500), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_media_channel_references_uuid"),
        sa.UniqueConstraint(
            "endpoint_id",
            "provider_media_id",
            name="uq_media_channel_reference_provider_identity",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["channel_endpoints.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            _in("upload_state", media_states),
            name="ck_media_channel_reference_upload_state",
        ),
        sa.CheckConstraint(
            _in("download_state", media_states),
            name="ck_media_channel_reference_download_state",
        ),
        **args,
    )
    op.create_index(
        "ix_media_channel_references_org_asset",
        "media_channel_references",
        ["organization_id", "media_asset_id", "updated_at"],
    )
    op.create_index(
        "ix_media_channel_references_org_endpoint",
        "media_channel_references",
        ["organization_id", "endpoint_id", "updated_at"],
    )
    op.create_index(
        "ix_media_channel_references_expiry",
        "media_channel_references",
        ["expires_at", "download_state", "upload_state"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_channel_references_expiry",
        table_name="media_channel_references",
    )
    op.drop_index(
        "ix_media_channel_references_org_endpoint",
        table_name="media_channel_references",
    )
    op.drop_index(
        "ix_media_channel_references_org_asset",
        table_name="media_channel_references",
    )
    op.drop_table("media_channel_references")
    op.drop_index(
        "ix_channel_sync_checkpoints_connection_endpoint",
        table_name="channel_sync_checkpoints",
    )
    op.drop_index(
        "ix_channel_sync_checkpoints_org_status",
        table_name="channel_sync_checkpoints",
    )
    op.drop_table("channel_sync_checkpoints")
