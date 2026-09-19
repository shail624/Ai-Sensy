"""Add the governed campaign-results export permission.

Revision ID: 0055_campaign_results_exports
Revises: 0054_chat_history_filters_views
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0055_campaign_results_exports"
down_revision = "0054_chat_history_filters_views"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "campaigns:export",
    "resource": "campaigns",
    "action": "export",
    "description": "Export governed campaign recipient results",
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


def downgrade() -> None:
    op.execute(_permissions.delete().where(_permissions.c.code == _PERMISSION["code"]))
