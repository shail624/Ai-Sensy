"""Rebuildable Vi CRM domain-outcome analytics rollups.

Revision ID: 0051_domain_outcome_analytics
Revises: 0050_scheduled_analytics_reports
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id

revision = "0051_domain_outcome_analytics"
down_revision = "0050_scheduled_analytics_reports"
branch_labels = None
depends_on = None

_LEGACY_REPORTS = (
    "messages",
    "failures",
    "campaigns",
    "conversations",
    "tasks",
    "customers",
    "costs",
)
_REPORTS = (*_LEGACY_REPORTS, "reactivation", "kyc", "service_levels")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _counter(name: str) -> sa.Column:
    return sa.Column(name, int_id(), nullable=False, server_default=sa.text("0"))


def _accumulator(name: str) -> sa.Column:
    return sa.Column(name, big_id(), nullable=False, server_default=sa.text("0"))


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
        "analytics_domain_outcome_rollups",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("grain", sa.String(8), nullable=False, server_default=sa.text("'hour'")),
        sa.Column("bucket_start", datetime6(), nullable=False),
        sa.Column("domain", sa.String(24), nullable=False),
        sa.Column("outcome", sa.String(64), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        _counter("reactivation_case_created_count"),
        _counter("reactivation_transition_count"),
        _counter("reactivation_completed_count"),
        _counter("reactivation_not_required_count"),
        _accumulator("reactivation_turnaround_seconds_sum"),
        _counter("reactivation_turnaround_count"),
        _counter("eligibility_decision_count"),
        _counter("eligibility_eligible_count"),
        _counter("eligibility_not_eligible_count"),
        _counter("eligibility_review_required_count"),
        _counter("kyc_decision_count"),
        _counter("kyc_approved_count"),
        _counter("kyc_rejected_count"),
        _counter("kyc_needs_information_count"),
        _accumulator("kyc_turnaround_seconds_sum"),
        _counter("kyc_turnaround_count"),
        _counter("sim_transition_count"),
        _counter("sim_delivered_count"),
        _counter("sim_failed_count"),
        _counter("activation_transition_count"),
        _counter("activation_completed_count"),
        _counter("activation_rejected_count"),
        _counter("sla_started_count"),
        _counter("sla_breached_count"),
        _counter("sla_resolved_count"),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "domain",
            "outcome",
            "source",
            "actor_user_id",
            name="uq_ador_grain",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ador_organization_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "domain != '' AND outcome != '' AND source != ''", name="ck_ador_dimensions"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_ador_org_bucket_domain",
        "analytics_domain_outcome_rollups",
        ["organization_id", "grain", "bucket_start", "domain"],
    )

    with op.batch_alter_table("report_schedules") as batch:
        batch.drop_constraint("ck_rs_report", type_="check")
        batch.create_check_constraint("ck_rs_report", _in("report", _REPORTS))


def downgrade() -> None:
    schedules = sa.table("report_schedules", sa.column("report", sa.String))
    op.execute(schedules.delete().where(schedules.c.report.in_(_REPORTS[7:])))
    with op.batch_alter_table("report_schedules") as batch:
        batch.drop_constraint("ck_rs_report", type_="check")
        batch.create_check_constraint("ck_rs_report", _in("report", _LEGACY_REPORTS))
    op.drop_index(
        "ix_ador_org_bucket_domain", table_name="analytics_domain_outcome_rollups"
    )
    op.drop_table("analytics_domain_outcome_rollups")
