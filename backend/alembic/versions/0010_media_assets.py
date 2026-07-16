"""Media assets (Storage foundation — Doc 03 §7.2).

**Expand** phase: creates ``media_assets`` (file metadata + storage reference; blobs live in the
storage backend, never the database — FR-MED-06). Additive and reversible.

Revision ID: 0010_media_assets
Revises: 0009_queue_engine
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0010_media_assets"
down_revision = "0009_queue_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    created = (
        sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    )
    updated = (
        sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)")
        if dialect == "mysql"
        else sa.text("CURRENT_TIMESTAMP")
    )
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "media_assets",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("byte_size", big_id(), nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False),
        sa.Column(
            "storage_backend", sa.String(16), nullable=False, server_default=sa.text("'local'")
        ),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("width", int_id(), nullable=True),
        sa.Column("height", int_id(), nullable=True),
        sa.Column("duration_sec", int_id(), nullable=True),
        sa.Column("meta_media_id", sa.String(64), nullable=True),
        sa.Column("meta_media_expires_at", datetime6(), nullable=True),
        sa.Column("usage_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_media_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_media_org", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "media_type IN ('image','video','document','audio','sticker')", name="ck_media_type"
        ),
        **mysql_args,
    )
    op.create_index("uq_media_org_sha", "media_assets", ["organization_id", "sha256"], unique=True)
    op.create_index("ix_media_type", "media_assets", ["organization_id", "media_type"])


def downgrade() -> None:
    op.drop_index("ix_media_type", table_name="media_assets")
    op.drop_index("uq_media_org_sha", table_name="media_assets")
    op.drop_table("media_assets")
