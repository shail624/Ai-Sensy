"""Owner-approved lightweight Reactivation CRM workflow.

Revision ID: 0034_reactivation_crm
Revises: 0033_kyc_operations
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6
from app.models.vi_domain import (
    REACTIVATION_EVENT_STAGES,
    REACTIVATION_LABELS,
    REACTIVATION_LEGACY_STAGES,
    REACTIVATION_STAGES,
)

revision = "0034_reactivation_crm"
down_revision = "0033_kyc_operations"
branch_labels = None
depends_on = None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    args: dict[str, Any] = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        }
        if dialect == "mysql"
        else {}
    )

    # Preserve immutable historical event values while allowing the corrected vocabulary forward.
    with op.batch_alter_table("reactivation_stage_events") as batch:
        batch.drop_constraint("ck_reactivation_event_from", type_="check")
        batch.drop_constraint("ck_reactivation_event_to", type_="check")
        batch.create_check_constraint(
            "ck_reactivation_event_to", _in("to_stage", REACTIVATION_EVENT_STAGES)
        )
        batch.create_check_constraint(
            "ck_reactivation_event_from",
            f"from_stage IS NULL OR {_in('from_stage', REACTIVATION_EVENT_STAGES)}",
        )

    with op.batch_alter_table("reactivation_cases") as batch:
        batch.drop_constraint("ck_reactivation_stage", type_="check")
    mapping = {
        "follow_up": "lead_confirmed",
        "interested": "lead_confirmed",
        "eligibility_check": "lead_confirmed",
        "eligible": "lead_confirmed",
        "kyc_pending": "kyc_verification",
        "verification": "kyc_verification",
        "confirmed": "lead_confirmed",
        "sim_order": "sim_required",
        "not_eligible": "not_required",
        "not_interested": "not_required",
    }
    cases = sa.table("reactivation_cases", sa.column("stage", sa.String(32)))
    for old, new in mapping.items():
        op.execute(cases.update().where(cases.c.stage == old).values(stage=new))
    with op.batch_alter_table("reactivation_cases") as batch:
        batch.create_check_constraint("ck_reactivation_stage", _in("stage", REACTIVATION_STAGES))

    op.create_table(
        "reactivation_case_labels",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("case_id", big_id(), nullable=False),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "label", name="uq_reactivation_case_label"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["reactivation_cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("label", REACTIVATION_LABELS), name="ck_reactivation_label"),
        **args,
    )
    op.create_index(
        "ix_reactivation_label_org_label_case",
        "reactivation_case_labels",
        ["organization_id", "label", "case_id"],
    )

    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("ck_tasks_reference_pair", type_="check")
        batch.add_column(sa.Column("due_notified_at", datetime6(), nullable=True))
        batch.create_check_constraint(
            "ck_tasks_reference_pair",
            "(reference_type IS NULL AND reference_id IS NULL) OR "
            "(reference_type IN ('kyc_case', 'reactivation_case') AND reference_id IS NOT NULL)",
        )
        batch.create_index(
            "ix_tasks_due_notification",
            ["status", "due_at", "due_notified_at", "reference_type"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_due_notification")
        batch.drop_constraint("ck_tasks_reference_pair", type_="check")
        batch.drop_column("due_notified_at")
        batch.create_check_constraint(
            "ck_tasks_reference_pair",
            "(reference_type IS NULL AND reference_id IS NULL) OR "
            "(reference_type = 'kyc_case' AND reference_id IS NOT NULL)",
        )

    op.drop_index("ix_reactivation_label_org_label_case", table_name="reactivation_case_labels")
    op.drop_table("reactivation_case_labels")

    with op.batch_alter_table("reactivation_cases") as batch:
        batch.drop_constraint("ck_reactivation_stage", type_="check")
    mapping = {
        "lead_confirmed": "interested",
        "kyc_verification": "verification",
        "sim_required": "sim_order",
        "not_required": "not_interested",
    }
    cases = sa.table("reactivation_cases", sa.column("stage", sa.String(32)))
    for new, old in mapping.items():
        op.execute(cases.update().where(cases.c.stage == new).values(stage=old))
    legacy_current = tuple(
        dict.fromkeys(
            (
                *REACTIVATION_LEGACY_STAGES,
                "new_lead",
                "documents_pending",
                "documents_received",
                "activation_pending",
                "completed",
            )
        )
    )
    with op.batch_alter_table("reactivation_cases") as batch:
        batch.create_check_constraint("ck_reactivation_stage", _in("stage", legacy_current))

    with op.batch_alter_table("reactivation_stage_events") as batch:
        batch.drop_constraint("ck_reactivation_event_from", type_="check")
        batch.drop_constraint("ck_reactivation_event_to", type_="check")
    events = sa.table(
        "reactivation_stage_events",
        sa.column("from_stage", sa.String(32)),
        sa.column("to_stage", sa.String(32)),
    )
    for new, old in mapping.items():
        op.execute(events.update().where(events.c.from_stage == new).values(from_stage=old))
        op.execute(events.update().where(events.c.to_stage == new).values(to_stage=old))
    with op.batch_alter_table("reactivation_stage_events") as batch:
        batch.create_check_constraint("ck_reactivation_event_to", _in("to_stage", legacy_current))
        batch.create_check_constraint(
            "ck_reactivation_event_from",
            f"from_stage IS NULL OR {_in('from_stage', legacy_current)}",
        )
