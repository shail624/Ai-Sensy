"""Extend governed workspace views to Contacts.

Revision ID: 0058_contacts_workspace_views
Revises: 0057_reactivation_saved_views
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0058_contacts_workspace_views"
down_revision = "0057_reactivation_saved_views"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "contacts:views_manage",
    "resource": "contacts",
    "action": "views_manage",
    "description": "Manage organization-shared Contacts views",
}

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE code = :code"),
        {"code": _PERMISSION["code"]},
    ).first()
    if exists is None:
        op.bulk_insert(_permissions, [_PERMISSION])

    with op.batch_alter_table("reactivation_views") as batch_op:
        batch_op.add_column(
            sa.Column(
                "workspace",
                sa.String(24),
                nullable=False,
                server_default="reactivation",
            )
        )
        batch_op.create_check_constraint(
            "ck_reactivation_views_workspace",
            "workspace IN ('reactivation', 'contacts')",
        )
        batch_op.drop_constraint(
            "uq_reactivation_views_scope_creator_name",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_reactivation_views_scope_creator_name",
            [
                "organization_id",
                "workspace",
                "visibility",
                "created_by_user_id",
                "name",
            ],
        )

    op.drop_index(
        "ix_reactivation_views_org_visibility_created",
        table_name="reactivation_views",
    )
    op.drop_index("ix_reactivation_views_org_creator", table_name="reactivation_views")
    op.create_index(
        "ix_reactivation_views_org_visibility_created",
        "reactivation_views",
        ["organization_id", "workspace", "visibility", "created_at"],
    )
    op.create_index(
        "ix_reactivation_views_org_creator",
        "reactivation_views",
        ["organization_id", "workspace", "created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_reactivation_views_org_creator", table_name="reactivation_views")
    op.drop_index(
        "ix_reactivation_views_org_visibility_created",
        table_name="reactivation_views",
    )
    # Keep an explicit organization-leading index in place while replacing the
    # workspace-aware unique constraint. MySQL may otherwise treat that unique
    # constraint as the supporting index for the organization foreign key and
    # reject its removal with error 1553.
    op.create_index(
        "ix_reactivation_views_org_visibility_created",
        "reactivation_views",
        ["organization_id", "visibility", "created_at"],
    )
    op.create_index(
        "ix_reactivation_views_org_creator",
        "reactivation_views",
        ["organization_id", "created_by_user_id"],
    )
    with op.batch_alter_table("reactivation_views") as batch_op:
        batch_op.drop_constraint(
            "uq_reactivation_views_scope_creator_name",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_reactivation_views_scope_creator_name",
            ["organization_id", "visibility", "created_by_user_id", "name"],
        )
        batch_op.drop_constraint("ck_reactivation_views_workspace", type_="check")
        batch_op.drop_column("workspace")

    op.execute(_permissions.delete().where(_permissions.c.code == _PERMISSION["code"]))
