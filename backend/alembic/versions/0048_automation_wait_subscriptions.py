"""Durable, contact-scoped Automation wait subscriptions.

Revision ID: 0048_automation_wait_subscriptions
Revises: 0047_automation_schedule_due
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary
from app.models.automation import AUTOMATION_WAIT_STATUSES

revision = "0048_automation_wait_subscriptions"
down_revision = "0047_automation_schedule_due"
branch_labels = None
depends_on = None


def _in_clause(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, Any] = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        }
        if dialect == "mysql"
        else {}
    )
    op.create_table(
        "automation_wait_subscriptions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("run_id", big_id(), nullable=False),
        sa.Column("receipt_id", big_id(), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'waiting'")),
        sa.Column("started_at", datetime6(), nullable=False, server_default=now),
        sa.Column("timeout_at", datetime6(), nullable=False),
        sa.Column("matched_event_uuid", uuid_binary(), nullable=True),
        sa.Column("resolved_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_wait_subscriptions_uuid"),
        sa.UniqueConstraint(
            "run_id", "node_id", name="uq_automation_wait_subscription_run_node"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["automation_runs.id"],
            name="fk_automation_wait_subscriptions_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["automation_trigger_receipts.id"],
            name="fk_automation_wait_subscriptions_receipt",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in_clause(AUTOMATION_WAIT_STATUSES),
            name="ck_automation_wait_subscriptions_status",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_automation_wait_subscriptions_match",
        "automation_wait_subscriptions",
        ["organization_id", "status", "event_type", "contact_id", "started_at"],
    )
    op.create_index(
        "ix_automation_wait_subscriptions_timeout",
        "automation_wait_subscriptions",
        ["status", "timeout_at"],
    )
    op.create_index(
        "ix_automation_wait_subscriptions_matched_event",
        "automation_wait_subscriptions",
        ["matched_event_uuid"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_wait_subscriptions_matched_event",
        table_name="automation_wait_subscriptions",
    )
    op.drop_index(
        "ix_automation_wait_subscriptions_timeout",
        table_name="automation_wait_subscriptions",
    )
    op.drop_index(
        "ix_automation_wait_subscriptions_match",
        table_name="automation_wait_subscriptions",
    )
    op.drop_table("automation_wait_subscriptions")
