"""Provider-neutral history-sync control-plane permission.

Revision ID: 0041_channel_sync_control_plane
Revises: 0040_channel_sync_media_foundation
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0041_channel_sync_control_plane"
down_revision = "0040_channel_sync_media_foundation"
branch_labels = None
depends_on = None

_PERMISSION = {
    "code": "channels:history_sync",
    "resource": "channels",
    "action": "history_sync",
    "description": "Manage provider-neutral history synchronization checkpoints",
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
    op.execute(
        _permissions.delete().where(_permissions.c.code == _PERMISSION["code"])
    )
