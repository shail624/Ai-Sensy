"""Durable personal schedules for Analytics report exports.

Revision ID: 0050_scheduled_analytics_reports
Revises: 0049_report_pdf_exports
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary

revision = "0050_scheduled_analytics_reports"
down_revision = "0049_report_pdf_exports"
branch_labels = None
depends_on = None

_LEGACY_NOTIFICATION_TYPES = (
    "follow_up_due",
    "release_date_due",
    "case_assigned",
    "case_status_changed",
    "automation_attention",
)
_NOTIFICATION_TYPES = (*_LEGACY_NOTIFICATION_TYPES, "report_ready")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


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
        "report_schedules",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("owner_user_id", big_id(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("report", sa.String(32), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("preset", sa.String(24), nullable=False),
        sa.Column("granularity", sa.String(8), nullable=False),
        sa.Column("cadence", sa.String(12), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("local_time", sa.String(5), nullable=False),
        sa.Column("weekday", sa.String(9), nullable=True),
        sa.Column("month_day", small_uint(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", datetime6(), nullable=True),
        sa.Column("last_run_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_report_schedules_uuid"),
        sa.UniqueConstraint(
            "organization_id", "owner_user_id", "name", name="uq_report_schedules_owner_name"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_report_schedules_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_report_schedules_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            _in(
                "report",
                ("messages", "failures", "campaigns", "conversations", "tasks", "customers", "costs"),
            ),
            name="ck_rs_report",
        ),
        sa.CheckConstraint(_in("format", ("pdf", "xlsx", "csv")), name="ck_rs_format"),
        sa.CheckConstraint(
            _in(
                "preset",
                ("yesterday", "last_7d", "last_30d", "this_month", "last_month", "this_quarter"),
            ),
            name="ck_rs_preset",
        ),
        sa.CheckConstraint(_in("granularity", ("day", "week", "month")), name="ck_rs_granularity"),
        sa.CheckConstraint(_in("cadence", ("daily", "weekly", "monthly")), name="ck_rs_cadence"),
        sa.CheckConstraint(
            "(cadence = 'daily' AND weekday IS NULL AND month_day IS NULL) OR "
            "(cadence = 'weekly' AND weekday IS NOT NULL AND month_day IS NULL) OR "
            "(cadence = 'monthly' AND weekday IS NULL AND month_day IS NOT NULL)",
            name="ck_rs_cadence_shape",
        ),
        sa.CheckConstraint(
            "weekday IS NULL OR "
            + _in(
                "weekday",
                ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
            ),
            name="ck_rs_weekday",
        ),
        sa.CheckConstraint(
            "month_day IS NULL OR (month_day >= 1 AND month_day <= 28)", name="ck_rs_month_day"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_report_schedules_due", "report_schedules", ["is_active", "next_run_at"]
    )
    op.create_index(
        "ix_report_schedules_owner_created",
        "report_schedules",
        ["organization_id", "owner_user_id", "created_at"],
    )

    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notification_type", type_="check")
        batch.create_check_constraint(
            "ck_notification_type", _in("notification_type", _NOTIFICATION_TYPES)
        )


def downgrade() -> None:
    notifications = sa.table("notifications", sa.column("notification_type", sa.String))
    op.execute(notifications.delete().where(notifications.c.notification_type == "report_ready"))
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notification_type", type_="check")
        batch.create_check_constraint(
            "ck_notification_type", _in("notification_type", _LEGACY_NOTIFICATION_TYPES)
        )
    op.drop_index("ix_report_schedules_owner_created", table_name="report_schedules")
    op.drop_index("ix_report_schedules_due", table_name="report_schedules")
    op.drop_table("report_schedules")
