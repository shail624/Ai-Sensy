"""System settings & feature flags (Module 1 — Doc 03 §11.5, §11.7).

**Expand** phase: creates the ``settings`` and ``feature_flags`` tables. Additive and
reversible (downgrade drops them). No data seeded — settings/flags are created on demand.

Revision ID: 0003_settings_feature_flags
Revises: 0002_seed_permissions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6

revision = "0003_settings_feature_flags"
down_revision = "0002_seed_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    updated = (
        sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)")
        if dialect == "mysql"
        else sa.text("CURRENT_TIMESTAMP")
    )
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "settings",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=True),
        sa.Column("scope", sa.String(24), nullable=False, server_default=sa.text("'organization'")),
        sa.Column("scope_id", big_id(), nullable=True),
        sa.Column("key_name", sa.String(120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("value_type", sa.String(16), nullable=False, server_default=sa.text("'json'")),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "scope_id", "key_name", name="uq_settings_scope_key"),
        **mysql_args,
    )
    op.create_index("ix_settings_org", "settings", ["organization_id"])

    op.create_table(
        "feature_flags",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("key_name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("rollout_json", sa.JSON(), nullable=True),
        sa.Column("organization_id", big_id(), nullable=True),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_name", "organization_id", name="uq_ff_key_org"),
        **mysql_args,
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
    op.drop_index("ix_settings_org", table_name="settings")
    op.drop_table("settings")
