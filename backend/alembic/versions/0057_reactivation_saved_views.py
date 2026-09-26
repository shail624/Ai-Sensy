"""Add governed personal and team-shared Reactivation views.

Revision ID: 0057_reactivation_saved_views
Revises: 0056_campaign_recipient_operations
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, uuid_binary

revision = "0057_reactivation_saved_views"
down_revision = "0056_campaign_recipient_operations"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "reactivation:views_manage",
    "resource": "reactivation",
    "action": "views_manage",
    "description": "Manage organization-shared Reactivation views",
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

    op.create_table(
        "reactivation_views",
        sa.Column("id", big_id(), primary_key=True, autoincrement=True),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column(
            "organization_id",
            big_id(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            big_id(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False),
        sa.Column("display", sa.String(16), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "visibility IN ('private', 'shared')",
            name="ck_reactivation_views_visibility",
        ),
        sa.CheckConstraint(
            "display IN ('board', 'list')",
            name="ck_reactivation_views_display",
        ),
        sa.UniqueConstraint("uuid", name="uq_reactivation_views_uuid"),
        sa.UniqueConstraint(
            "organization_id",
            "visibility",
            "created_by_user_id",
            "name",
            name="uq_reactivation_views_scope_creator_name",
        ),
        **MYSQL_TABLE_ARGS,
    )
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


def downgrade() -> None:
    op.drop_index("ix_reactivation_views_org_creator", table_name="reactivation_views")
    op.drop_index(
        "ix_reactivation_views_org_visibility_created",
        table_name="reactivation_views",
    )
    op.drop_table("reactivation_views")
    op.execute(_permissions.delete().where(_permissions.c.code == _PERMISSION["code"]))
