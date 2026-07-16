"""API keys (Module 1 — Doc 03 §4.4).

**Expand** phase: creates the ``api_keys`` table. Additive and reversible.

Revision ID: 0004_api_keys
Revises: 0003_settings_feature_flags
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0004_api_keys"
down_revision = "0003_settings_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    created = (
        sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    )
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "api_keys",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("key_prefix", sa.CHAR(12), nullable=False),
        sa.Column("key_hash", sa.CHAR(64), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("last_used_at", datetime6(), nullable=True),
        sa.Column("expires_at", datetime6(), nullable=True),
        sa.Column("revoked_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_apikeys_uuid"),
        sa.UniqueConstraint("key_hash", name="uq_apikeys_hash"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_apikeys_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_apikeys_org", "api_keys", ["organization_id", "revoked_at"])


def downgrade() -> None:
    op.drop_index("ix_apikeys_org", table_name="api_keys")
    op.drop_table("api_keys")
