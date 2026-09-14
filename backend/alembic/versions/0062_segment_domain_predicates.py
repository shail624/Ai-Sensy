"""Add governed Vi-domain sources to segment rules.

Revision ID: 0062_segment_domain_predicates
Revises: 0061_reports_workspace_views
"""

from __future__ import annotations

from alembic import op

revision = "0062_segment_domain_predicates"
down_revision = "0061_reports_workspace_views"
branch_labels = None
depends_on = None


def _replace_source_constraint(allowed: str) -> None:
    with op.batch_alter_table("segment_rules") as batch_op:
        batch_op.drop_constraint("ck_segrules_source", type_="check")
        batch_op.create_check_constraint(
            "ck_segrules_source",
            f"field_source IN ({allowed})",
        )


def upgrade() -> None:
    _replace_source_constraint(
        "'contact', 'attribute', 'tag', 'engagement', "
        "'reactivation', 'kyc', 'document', 'activation'"
    )


def downgrade() -> None:
    _replace_source_constraint("'contact', 'attribute', 'tag', 'engagement'")
