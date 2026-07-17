"""WhatsApp infrastructure: WABAs & phone numbers (Module 4 Step 2 — Doc 03 §5.1/§5.2).

**Expand** phase: creates ``whatsapp_business_accounts`` and ``phone_numbers``. Additive and
reversible. Tokens are stored as AES-GCM ciphertext in ``VARBINARY`` columns (FR-WA-03).

Revision ID: 0014_waba_phone_numbers
Revises: 0013_bulk_jobs
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, small_uint, uuid_binary, varbinary

revision = "0014_waba_phone_numbers"
down_revision = "0013_bulk_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "whatsapp_business_accounts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("waba_id", sa.String(32), nullable=False),
        sa.Column("business_name", sa.String(160), nullable=False),
        sa.Column("meta_business_id", sa.String(32), nullable=True),
        sa.Column("access_token_enc", varbinary(1024), nullable=False),
        sa.Column("token_expires_at", datetime6(), nullable=True),
        sa.Column("webhook_verify_token_enc", varbinary(255), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_waba_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_waba_org", ondelete="RESTRICT"
        ),
        sa.CheckConstraint("status IN ('active','suspended','disabled')", name="ck_waba_status"),
        **mysql_args,
    )
    op.create_index("uq_waba_metaid", "whatsapp_business_accounts", ["waba_id"], unique=True)
    op.create_index("ix_waba_org", "whatsapp_business_accounts", ["organization_id"])

    op.create_table(
        "phone_numbers",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("waba_id", big_id(), nullable=False),
        sa.Column(
            "channel_type", sa.String(24), nullable=False, server_default=sa.text("'whatsapp'")
        ),
        sa.Column("phone_number_id", sa.String(32), nullable=False),
        sa.Column("display_number", sa.String(24), nullable=False),
        sa.Column("verified_name", sa.String(160), nullable=True),
        sa.Column("quality_rating", sa.String(8), nullable=True),
        sa.Column("messaging_tier", sa.String(16), nullable=True),
        sa.Column("mps_limit", small_uint(), nullable=False, server_default=sa.text("80")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'connected'")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("throughput_level", sa.String(16), nullable=True),
        sa.Column("last_synced_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_phone_uuid"),
        sa.ForeignKeyConstraint(
            ["waba_id"],
            ["whatsapp_business_accounts.id"],
            name="fk_phone_waba",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_phone_org", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "quality_rating IN ('GREEN','YELLOW','RED') OR quality_rating IS NULL",
            name="ck_phone_quality",
        ),
        **mysql_args,
    )
    op.create_index("uq_phone_metaid", "phone_numbers", ["phone_number_id"], unique=True)
    op.create_index("ix_phone_waba", "phone_numbers", ["waba_id"])
    op.create_index("ix_phone_org", "phone_numbers", ["organization_id", "channel_type"])


def downgrade() -> None:
    op.drop_index("ix_phone_org", table_name="phone_numbers")
    op.drop_index("ix_phone_waba", table_name="phone_numbers")
    op.drop_index("uq_phone_metaid", table_name="phone_numbers")
    op.drop_table("phone_numbers")
    op.drop_index("ix_waba_org", table_name="whatsapp_business_accounts")
    op.drop_index("uq_waba_metaid", table_name="whatsapp_business_accounts")
    op.drop_table("whatsapp_business_accounts")
