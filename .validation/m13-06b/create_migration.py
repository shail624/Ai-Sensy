#!/usr/bin/env python3
"""Write the bounded M13-06B permission-only migration into a product checkout."""

from __future__ import annotations

import sys
from pathlib import Path

CONTENT = '''"""Provider-neutral history synchronization control-plane authorization.

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

_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "channels:history_sync",
        "resource": "channels",
        "action": "history_sync",
        "description": "Manage provider-neutral history synchronization checkpoints",
    }
]

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: create_migration.py PRODUCT_ROOT")
    root = Path(sys.argv[1]).resolve()
    target = root / "backend/alembic/versions/0041_channel_sync_control_plane.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CONTENT, encoding="utf-8")


if __name__ == "__main__":
    main()
