"""Contact import job records (Module 2 async — Doc 03 §11.6).

**Expand** phase: creates ``imports``. Additive and reversible. (``exports`` lands with the
Export step.)

Revision ID: 0011_imports
Revises: 0010_media_assets
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0011_imports"
down_revision = "0010_media_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    created = (
        sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    )
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )
    op.create_table(
        "imports",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("requested_by", big_id(), nullable=True),
        sa.Column("entity", sa.String(40), nullable=False, server_default=sa.text("'contacts'")),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("source_key", sa.String(512), nullable=True),
        sa.Column("mapping_json", sa.JSON(), nullable=True),
        sa.Column("dedup_strategy", sa.String(16), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_rows", big_id(), nullable=True),
        sa.Column("processed_rows", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_rows", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_rows", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_report_key", sa.String(512), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_imports_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_imports_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_imports_org", "imports", ["organization_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_imports_org", table_name="imports")
    op.drop_table("imports")
