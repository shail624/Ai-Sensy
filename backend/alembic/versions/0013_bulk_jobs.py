"""Bulk contact operation job records (Module 2 Step 5C — Doc 03 §11.6 family).

**Expand** phase: creates ``bulk_jobs``. Additive and reversible.

Revision ID: 0013_bulk_jobs
Revises: 0012_exports
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0013_bulk_jobs"
down_revision = "0012_exports"
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
        "bulk_jobs",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("requested_by", big_id(), nullable=True),
        sa.Column("entity", sa.String(40), nullable=False, server_default=sa.text("'contacts'")),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("action", sa.String(32), nullable=True),
        sa.Column("request_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_items", big_id(), nullable=True),
        sa.Column("processed_items", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("succeeded_items", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_items", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("skipped_items", big_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("errors_json", sa.JSON(), nullable=True),
        sa.Column("error_report_key", sa.String(512), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_bulk_jobs_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_bulk_jobs_org", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "operation IN ('bulk_update','bulk_delete','deduplicate')", name="ck_bulk_jobs_operation"
        ),
        **mysql_args,
    )
    op.create_index("ix_bulk_jobs_org", "bulk_jobs", ["organization_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_bulk_jobs_org", table_name="bulk_jobs")
    op.drop_table("bulk_jobs")
