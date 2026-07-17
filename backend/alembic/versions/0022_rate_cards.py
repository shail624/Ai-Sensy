"""Rate cards (Phase 6 Step 5 — Doc 03 §8.5).

**Expand** phase: creates ``rate_cards``. Additive and reversible.

The table is created **empty and stays empty**: this migration seeds no rates. Doc 12 §53 places
Meta's pricing outside the frozen set, so the platform restates none of it — an operator populates
the card, and until then estimation answers ``rate_card_not_configured`` (Doc 04 §17).

No ``organization_id``: the card is global (Doc 03 §8.5.1) — Doc 04 §17's "no reseller markup".

Revision ID: 0022_rate_cards
Revises: 0021_campaign_schedules
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0022_rate_cards"
down_revision = "0021_campaign_schedules"
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
        "rate_cards",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("country_code", sa.CHAR(2), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 6), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("effective_from", datetime6(), nullable=False),
        sa.Column("effective_to", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_ratecard_uuid"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_ratecard_author", ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "category IN ('marketing','utility','authentication')", name="ck_ratecard_category"
        ),
        sa.CheckConstraint("unit_price >= 0", name="ck_ratecard_price"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="ck_ratecard_window"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_ratecard_slot", "rate_cards", ["country_code", "category", "effective_from"], unique=True
    )
    op.create_index(
        "ix_ratecard_lookup",
        "rate_cards",
        ["country_code", "category", "effective_from", "effective_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_ratecard_lookup", table_name="rate_cards")
    op.drop_index("uq_ratecard_slot", table_name="rate_cards")
    op.drop_table("rate_cards")
