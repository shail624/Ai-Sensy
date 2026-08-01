"""Durable business events and automation trigger receipts (Design Book 24).

Revision ID: 0031_automation_trigger_receipts
Revises: 0030_automation_test_runtime
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.automation import AUTOMATION_TRIGGER_RECEIPT_STATUSES
from app.models.business_event import BUSINESS_EVENT_ACTORS

revision = "0031_automation_trigger_receipts"
down_revision = "0030_automation_test_runtime"
branch_labels = None
depends_on = None


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{value}'" for value in values) + ")"


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

    event_types = op.create_table(
        "business_event_types",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_version", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("schema_ref", sa.String(160), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type", "event_version", name="uq_bet_type_version"),
        sa.CheckConstraint(
            "category IN ('lead','kyc','payment','sim','campaign','ai','template',"
            "'connector','user','audit')",
            name="ck_bet_category",
        ),
        **mysql_args,
    )
    op.create_index("ix_bet_category", "business_event_types", ["category"])
    op.bulk_insert(
        event_types,
        [
            {
                "event_type": "contact.created",
                "event_version": 1,
                "category": "lead",
                "subject_type": "contact",
                "description": "A tenant contact was created.",
                "schema_ref": "internal://events/contact.created/v1",
                "is_active": True,
            }
        ],
    )

    event_columns: list[Any] = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_version", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("occurred_at", datetime6(), nullable=False),
        sa.Column("recorded_at", datetime6(), nullable=False, server_default=now),
        sa.Column("actor_type", sa.String(12), nullable=False),
        sa.Column("actor_id", big_id(), nullable=True),
        sa.Column("subject_type", sa.String(32), nullable=True),
        sa.Column("subject_id", big_id(), nullable=True),
        sa.Column("channel_type", sa.String(24), nullable=True),
        sa.Column("connector_id", big_id(), nullable=True),
        sa.Column("campaign_id", big_id(), nullable=True),
        sa.Column("contact_id", big_id(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column("schema_ref", sa.String(160), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
    ]
    event_constraints: list[Any] = [
        sa.CheckConstraint(
            _in_clause("actor_type", BUSINESS_EVENT_ACTORS),
            name="ck_business_events_actor_type",
        )
    ]
    if dialect == "mysql":
        op.create_table(
            "business_events",
            *event_columns,
            *event_constraints,
            sa.PrimaryKeyConstraint("id", "occurred_at"),
            sa.UniqueConstraint("uuid", "occurred_at", name="uq_business_events_uuid_time"),
            **mysql_args,
        )
    else:
        op.create_table(
            "business_events",
            *event_columns,
            *event_constraints,
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid", name="uq_business_events_uuid"),
        )
    op.create_index("ix_be_type_time", "business_events", ["event_type", "occurred_at"])
    op.create_index(
        "ix_be_subject", "business_events", ["subject_type", "subject_id", "occurred_at"]
    )
    op.create_index("ix_be_campaign", "business_events", ["campaign_id", "occurred_at"])
    op.create_index("ix_be_contact", "business_events", ["contact_id", "occurred_at"])
    op.create_index("ix_be_channel", "business_events", ["channel_type", "occurred_at"])
    op.create_index("ix_be_correlation", "business_events", ["correlation_id"])
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE business_events PARTITION BY RANGE COLUMNS (occurred_at) ("
            "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
            "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
            "PARTITION p2026_09 VALUES LESS THAN ('2026-10-01'), "
            "PARTITION pmax VALUES LESS THAN (MAXVALUE))"
        )

    op.create_table(
        "automation_trigger_receipts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("flow_id", big_id(), nullable=False),
        sa.Column("version_id", big_id(), nullable=False),
        sa.Column("event_uuid", uuid_binary(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_version", int_id(), nullable=False, server_default=sa.text("1")),
        sa.Column("event_occurred_at", datetime6(), nullable=False),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'received'")),
        sa.Column("received_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_trigger_receipts_uuid"),
        sa.UniqueConstraint(
            "flow_id", "version_id", "event_uuid", name="uq_automation_trigger_receipt"
        ),
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["automation_flows.id"],
            name="fk_automation_trigger_receipts_flow",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["automation_flow_versions.id"],
            name="fk_automation_trigger_receipts_version",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in_clause("status", AUTOMATION_TRIGGER_RECEIPT_STATUSES),
            name="ck_automation_trigger_receipts_status",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_automation_trigger_receipts_flow_received",
        "automation_trigger_receipts",
        ["flow_id", "received_at"],
    )
    op.create_index(
        "ix_automation_trigger_receipts_org_status_received",
        "automation_trigger_receipts",
        ["organization_id", "status", "received_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_trigger_receipts_org_status_received",
        table_name="automation_trigger_receipts",
    )
    op.drop_index(
        "ix_automation_trigger_receipts_flow_received",
        table_name="automation_trigger_receipts",
    )
    op.drop_table("automation_trigger_receipts")
    op.drop_index("ix_be_correlation", table_name="business_events")
    op.drop_index("ix_be_channel", table_name="business_events")
    op.drop_index("ix_be_contact", table_name="business_events")
    op.drop_index("ix_be_campaign", table_name="business_events")
    op.drop_index("ix_be_subject", table_name="business_events")
    op.drop_index("ix_be_type_time", table_name="business_events")
    op.drop_table("business_events")
    op.drop_index("ix_bet_category", table_name="business_event_types")
    op.drop_table("business_event_types")
