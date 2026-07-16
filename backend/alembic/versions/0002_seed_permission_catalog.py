"""Seed the permission catalog (Module 1 — Doc 04 §4.3).

**Migrate** phase (data): populates the fixed ``permissions`` lookup with the seeded
catalog. Permissions are global (no ``organization_id``); the preset *roles* and the owner
user are created by the bootstrap routine (``python -m app.cli create-owner``), which needs
an organization to exist first. Adding permissions later is a new additive migration
(governance rule, Doc 12 §58) — this revision is the initial snapshot.

Revision ID: 0002_seed_permissions
Revises: 0001_identity_and_audit
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.rbac.catalog import permission_rows

revision = "0002_seed_permissions"
down_revision = "0001_identity_and_audit"
branch_labels = None
depends_on = None

# Lightweight, migration-local table handle (independent of the ORM model, so this
# revision keeps working even if the model evolves).
_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(_permissions, permission_rows())


def downgrade() -> None:
    codes = [row["code"] for row in permission_rows()]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
