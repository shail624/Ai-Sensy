"""Durable next-fire projection for live Automation schedules.

Revision ID: 0047_automation_schedule_due
Revises: 0046_automation_notifications
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047_automation_schedule_due"
down_revision = "0046_automation_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("automation_flows") as batch:
        batch.add_column(sa.Column("next_run_at", sa.DateTime(), nullable=True))
        batch.create_index(
            "ix_automation_flows_schedule_due",
            ["status", "next_run_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("automation_flows") as batch:
        batch.drop_index("ix_automation_flows_schedule_due")
        batch.drop_column("next_run_at")
