"""Widen Alembic's own version-tracking column for MySQL.

MySQL enforces ``VARCHAR`` length; Alembic's own ``alembic_version.version_num`` column defaults
to ``VARCHAR(32)`` (see ``alembic.ddl.impl.DefaultImpl.version_table_impl``), which the very next
revision's identifier — ``0036_customer_identity_resolution``, 33 characters — already exceeds.
``alembic upgrade head`` therefore fails on a real MySQL 8 database while stamping that revision,
even though the revision's own schema changes apply cleanly first (MySQL DDL auto-commits, so the
new tables land regardless; only the bookkeeping ``UPDATE alembic_version ...`` fails).

Widened to 255 characters here — comfortable headroom over the current longest identifier
(``0039_qr_pairing_provider_runtime_foundation``, 43 characters) for reasonably longer future
revision names, without unbounded growth. SQLite has no ``VARCHAR`` length enforcement (type
affinity only) and is unaffected; this repository targets MySQL exclusively (no PostgreSQL dialect
exists anywhere under ``app/db``), so no other dialect branch is needed.

This is the one deliberate exception to the "additive only, no altered columns" discipline every
other migration in this history follows: it repairs Alembic's own internal bookkeeping table, not
an application/domain table, and no real MySQL deployment has ever advanced past
``0035_notification_center`` (this is the observed failure), so nothing here alters state any live
environment has actually reached.

Revision ID: 0035a_widen_version_table
Revises: 0035_notification_center
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0035a_widen_version_table"
down_revision = "0035_notification_center"
branch_labels = None
depends_on = None

_NARROW = 32
_WIDE = 255


def upgrade() -> None:
    if op.get_bind().dialect.name == "mysql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(_NARROW),
            type_=sa.String(_WIDE),
            existing_nullable=False,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "mysql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(_WIDE),
            type_=sa.String(_NARROW),
            existing_nullable=False,
        )
