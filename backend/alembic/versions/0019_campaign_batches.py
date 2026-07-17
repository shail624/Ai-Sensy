"""Campaign batches: dispatch checkpoints (Phase 6 Step 2 — Doc 03 §8.4).

**Expand** phase: creates ``campaign_batches``. Additive and reversible.

Small and fully constrained, unlike the roster it checkpoints: there are thousands of batches where
there are millions of recipients, so this one keeps its foreign key.

Revision ID: 0019_campaign_batches
Revises: 0018_campaigns
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id

revision = "0019_campaign_batches"
down_revision = "0018_campaigns"
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
        "campaign_batches",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", big_id(), nullable=False),
        sa.Column("batch_index", int_id(), nullable=False),
        sa.Column("size", int_id(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("dispatched_at", datetime6(), nullable=True),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], name="fk_cbatch_campaign", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_cbatch_campaign_idx", "campaign_batches", ["campaign_id", "batch_index"], unique=True
    )
    op.create_index("ix_cbatch_status", "campaign_batches", ["campaign_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_cbatch_status", table_name="campaign_batches")
    op.drop_index("uq_cbatch_campaign_idx", table_name="campaign_batches")
    op.drop_table("campaign_batches")
