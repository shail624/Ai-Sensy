"""Once-only live automation handoff consumption.

Revision ID: 0044_automation_live_handoff_runtime
Revises: 0043_conversation_channel_endpoints
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6
from app.models.automation import AUTOMATION_TRIGGER_RECEIPT_STATUSES

revision = "0044_automation_live_handoff_runtime"
down_revision = "0043_conversation_channel_endpoints"
branch_labels = None
depends_on = None


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    event_types = sa.table(
        "business_event_types",
        sa.column("event_type", sa.String),
        sa.column("event_version", sa.SmallInteger),
        sa.column("category", sa.String),
        sa.column("subject_type", sa.String),
        sa.column("description", sa.String),
        sa.column("schema_ref", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        event_types,
        [
            {
                "event_type": "message.received",
                "event_version": 1,
                "category": "connector",
                "subject_type": "message",
                "description": "An inbound customer message was durably accepted.",
                "schema_ref": "internal://events/message.received/v1",
                "is_active": True,
            }
        ],
    )

    with op.batch_alter_table("automation_runs") as batch:
        batch.drop_constraint("ck_automation_runs_mode", type_="check")
        batch.create_check_constraint(
            "ck_automation_runs_mode", "mode IN ('test','live')"
        )

    with op.batch_alter_table("automation_trigger_receipts") as batch:
        batch.drop_constraint("ck_automation_trigger_receipts_status", type_="check")
        batch.add_column(sa.Column("run_id", big_id(), nullable=True))
        batch.add_column(sa.Column("processing_started_at", datetime6(), nullable=True))
        batch.add_column(sa.Column("processed_at", datetime6(), nullable=True))
        batch.create_foreign_key(
            "fk_automation_trigger_receipts_run",
            "automation_runs",
            ["run_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint("uq_automation_trigger_receipts_run", ["run_id"])
        batch.create_check_constraint(
            "ck_automation_trigger_receipts_status",
            _in_clause("status", AUTOMATION_TRIGGER_RECEIPT_STATUSES),
        )


def downgrade() -> None:
    with op.batch_alter_table("automation_trigger_receipts") as batch:
        batch.drop_constraint("ck_automation_trigger_receipts_status", type_="check")
        batch.drop_constraint("uq_automation_trigger_receipts_run", type_="unique")
        batch.drop_constraint("fk_automation_trigger_receipts_run", type_="foreignkey")
        batch.drop_column("processed_at")
        batch.drop_column("processing_started_at")
        batch.drop_column("run_id")
        batch.create_check_constraint(
            "ck_automation_trigger_receipts_status", "status = 'received'"
        )

    with op.batch_alter_table("automation_runs") as batch:
        batch.drop_constraint("ck_automation_runs_mode", type_="check")
        batch.create_check_constraint("ck_automation_runs_mode", "mode = 'test'")

    event_types = sa.table("business_event_types", sa.column("event_type", sa.String))
    op.execute(event_types.delete().where(event_types.c.event_type == "message.received"))
