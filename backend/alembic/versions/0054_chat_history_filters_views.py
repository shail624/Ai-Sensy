"""Add advanced Chat History filters and organization-shared views.

Revision ID: 0054_chat_history_filters_views
Revises: 0053_conversation_transcript_exports
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, uuid_binary

revision = "0054_chat_history_filters_views"
down_revision = "0053_conversation_transcript_exports"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "inbox:views_manage",
    "resource": "inbox",
    "action": "views_manage",
    "description": "Manage organization-shared Chat History views",
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
        "conversation_history_views",
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
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("uuid", name="uq_conversation_history_views_uuid"),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_conversation_history_views_org_name"
        ),
        **MYSQL_TABLE_ARGS,
    )
    op.create_index(
        "ix_conversation_history_views_org_created",
        "conversation_history_views",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_history_views_org_created",
        table_name="conversation_history_views",
    )
    op.drop_table("conversation_history_views")
    op.execute(_permissions.delete().where(_permissions.c.code == _PERMISSION["code"]))
