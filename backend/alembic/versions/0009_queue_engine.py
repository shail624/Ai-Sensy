"""Queue engine: job metadata & dead letter (Module 6 — Doc 03 §11.7, Doc 06 §7).

**Expand** phase: creates ``job_metadata`` (durable mirror of Celery job state) and
``dead_letter`` (the general parked-task store). Additive and reversible.

Revision ID: 0009_queue_engine
Revises: 0008_custom_attributes
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, small_uint, uuid_binary

revision = "0009_queue_engine"
down_revision = "0008_custom_attributes"
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
        "job_metadata",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=False),
        sa.Column("task_name", sa.String(160), nullable=False),
        sa.Column("queue", sa.String(60), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("ref_type", sa.String(24), nullable=True),
        sa.Column("ref_id", big_id(), nullable=True),
        sa.Column("args_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("attempts", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", datetime6(), nullable=True),
        sa.Column("finished_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_job_uuid"),
        sa.UniqueConstraint("task_id", name="uq_job_taskid"),
        **mysql_args,
    )
    op.create_index("ix_job_status", "job_metadata", ["status", "created_at"])
    op.create_index("ix_job_ref", "job_metadata", ["ref_type", "ref_id"])

    op.create_table(
        "dead_letter",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("source_queue", sa.String(60), nullable=False),
        sa.Column("task_name", sa.String(160), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("error_class", sa.String(32), nullable=True),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("stack_trace", sa.String(4096), nullable=True),
        sa.Column("attempts", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("fingerprint", sa.CHAR(40), nullable=True),
        sa.Column("request_id", sa.CHAR(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'parked'")),
        sa.Column("resolved_by", big_id(), nullable=True),
        sa.Column("resolved_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_dl_uuid"),
        **mysql_args,
    )
    op.create_index("ix_dl_status", "dead_letter", ["status", "created_at"])
    op.create_index("ix_dl_fingerprint", "dead_letter", ["fingerprint", "created_at"])
    op.create_index("ix_dl_queue", "dead_letter", ["source_queue", "created_at"])


def downgrade() -> None:
    for index in ("ix_dl_queue", "ix_dl_fingerprint", "ix_dl_status"):
        op.drop_index(index, table_name="dead_letter")
    op.drop_table("dead_letter")
    op.drop_index("ix_job_ref", table_name="job_metadata")
    op.drop_index("ix_job_status", table_name="job_metadata")
    op.drop_table("job_metadata")
