"""Extend governed workspace views to Reports.

Revision ID: 0061_reports_workspace_views
Revises: 0060_kyc_workspace_views
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0061_reports_workspace_views"
down_revision = "0060_kyc_workspace_views"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "analytics:views_manage",
    "resource": "analytics",
    "action": "views_manage",
    "description": "Manage organization-shared Report views",
}

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def _replace_workspace_constraint(allowed: str) -> None:
    with op.batch_alter_table("reactivation_views") as batch_op:
        batch_op.drop_constraint("ck_reactivation_views_workspace", type_="check")
        batch_op.create_check_constraint(
            "ck_reactivation_views_workspace",
            f"workspace IN ({allowed})",
        )


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE code = :code"),
        {"code": _PERMISSION["code"]},
    ).first()
    if exists is None:
        op.bulk_insert(_permissions, [_PERMISSION])
    _replace_workspace_constraint("'reactivation', 'contacts', 'campaigns', 'kyc', 'reports'")


def downgrade() -> None:
    _replace_workspace_constraint("'reactivation', 'contacts', 'campaigns', 'kyc'")
    op.execute(_permissions.delete().where(_permissions.c.code == _PERMISSION["code"]))
