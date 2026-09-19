"""Durable skipped evidence for live automation conditions.

Revision ID: 0045_automation_live_conditions
Revises: 0044_automation_live_handoff_runtime
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.automation import (
    AUTOMATION_ATTEMPT_INTERRUPTED,
    AUTOMATION_ATTEMPT_SKIPPED,
    AUTOMATION_ATTEMPT_STATUSES,
)

revision = "0045_automation_live_conditions"
down_revision = "0044_automation_live_handoff_runtime"
branch_labels = None
depends_on = None


def _in_clause(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    with op.batch_alter_table("automation_step_attempts") as batch:
        batch.drop_constraint("ck_automation_step_attempts_status", type_="check")
        batch.create_check_constraint(
            "ck_automation_step_attempts_status", _in_clause(AUTOMATION_ATTEMPT_STATUSES)
        )


def downgrade() -> None:
    legacy_statuses = tuple(
        status for status in AUTOMATION_ATTEMPT_STATUSES if status != AUTOMATION_ATTEMPT_SKIPPED
    )
    attempts = sa.table("automation_step_attempts", sa.column("status", sa.String))
    with op.batch_alter_table("automation_step_attempts") as batch:
        batch.drop_constraint("ck_automation_step_attempts_status", type_="check")
    op.execute(
        attempts.update()
        .where(attempts.c.status == AUTOMATION_ATTEMPT_SKIPPED)
        .values(status=AUTOMATION_ATTEMPT_INTERRUPTED)
    )
    with op.batch_alter_table("automation_step_attempts") as batch:
        batch.create_check_constraint(
            "ck_automation_step_attempts_status", _in_clause(legacy_statuses)
        )
