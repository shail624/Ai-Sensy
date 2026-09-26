"""Add the governed conversation-transcript export permission.

Revision ID: 0053_conversation_transcript_exports
Revises: 0052_team_productivity_reports
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0053_conversation_transcript_exports"
down_revision = "0052_team_productivity_reports"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "inbox:export",
    "resource": "inbox",
    "action": "export",
    "description": "Export governed conversation transcripts",
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
