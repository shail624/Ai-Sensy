"""Deterministic automation test-run ledger (Design Book 23, MD5 Phase 2B).

Revision ID: 0030_automation_test_runtime
Revises: 0029_automation_definitions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.automation import AUTOMATION_ATTEMPT_STATUSES, AUTOMATION_RUN_STATUSES

revision = "0030_automation_test_runtime"
down_revision = "0029_automation_definitions"
branch_labels = None
depends_on = None


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        }
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "automation_runs",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("flow_id", big_id(), nullable=False),
        sa.Column("version_id", big_id(), nullable=False),
        sa.Column("mode", sa.String(12), nullable=False, server_default=sa.text("'test'")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("trigger_input_json", sa.JSON(), nullable=False),
        sa.Column("total_steps", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_steps", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("started_at", datetime6(), nullable=True),
        sa.Column("finished_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_runs_uuid"),
        sa.UniqueConstraint("correlation_id", name="uq_automation_runs_correlation_id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_automation_run_idempotency"
        ),
        sa.ForeignKeyConstraint(
            ["flow_id"], ["automation_flows.id"], name="fk_automation_runs_flow", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["automation_flow_versions.id"],
            name="fk_automation_runs_version",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(_in_clause("status", AUTOMATION_RUN_STATUSES), name="ck_automation_runs_status"),
        sa.CheckConstraint("mode = 'test'", name="ck_automation_runs_mode"),
        **mysql_args,
    )
    op.create_index("ix_automation_runs_flow_created", "automation_runs", ["flow_id", "created_at"])
    op.create_index(
        "ix_automation_runs_org_status_created",
        "automation_runs",
        ["organization_id", "status", "created_at"],
    )

    op.create_table(
        "automation_step_attempts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("run_id", big_id(), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False),
        sa.Column("node_kind", sa.String(24), nullable=False),
        sa.Column("attempt_no", int_id(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'running'")),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("started_at", datetime6(), nullable=False, server_default=now),
        sa.Column("finished_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_step_attempts_uuid"),
        sa.UniqueConstraint("run_id", "node_id", "attempt_no", name="uq_automation_step_attempt"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["automation_runs.id"],
            name="fk_automation_step_attempts_run",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            _in_clause("status", AUTOMATION_ATTEMPT_STATUSES),
            name="ck_automation_step_attempts_status",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_automation_step_attempts_run_started",
        "automation_step_attempts",
        ["run_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_step_attempts_run_started", table_name="automation_step_attempts"
    )
    op.drop_table("automation_step_attempts")
    op.drop_index("ix_automation_runs_org_status_created", table_name="automation_runs")
    op.drop_index("ix_automation_runs_flow_created", table_name="automation_runs")
    op.drop_table("automation_runs")
