"""Allow governed Team Productivity report schedules.

Revision ID: 0052_team_productivity_reports
Revises: 0051_domain_outcome_analytics
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052_team_productivity_reports"
down_revision = "0051_domain_outcome_analytics"
branch_labels = None
depends_on = None

_PREVIOUS_REPORTS = (
    "messages",
    "failures",
    "campaigns",
    "conversations",
    "tasks",
    "customers",
    "costs",
    "reactivation",
    "kyc",
    "service_levels",
)
_REPORTS = (*_PREVIOUS_REPORTS, "team_productivity")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    with op.batch_alter_table("report_schedules") as batch:
        batch.drop_constraint("ck_rs_report", type_="check")
        batch.create_check_constraint("ck_rs_report", _in("report", _REPORTS))


def downgrade() -> None:
    schedules = sa.table("report_schedules", sa.column("report", sa.String))
    op.execute(schedules.delete().where(schedules.c.report == "team_productivity"))
    with op.batch_alter_table("report_schedules") as batch:
        batch.drop_constraint("ck_rs_report", type_="check")
        batch.create_check_constraint("ck_rs_report", _in("report", _PREVIOUS_REPORTS))
