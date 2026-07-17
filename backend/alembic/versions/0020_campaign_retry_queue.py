"""Campaign retry queue (Phase 6 Step 3 — Doc 03 §8.4).

**Expand** phase: creates ``campaign_retry_queue``. Additive and reversible.

The durable half of smart retry: Celery/Redis carries the live attempt, this table carries the
schedule, so a campaign held at Meta's rate limit survives a Redis flush (NFR-DR-06).
``ix_cretry_due`` is the scanner's index.

Revision ID: 0020_campaign_retry_queue
Revises: 0019_campaign_batches
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, small_uint

revision = "0020_campaign_retry_queue"
down_revision = "0019_campaign_batches"
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
        "campaign_retry_queue",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", big_id(), nullable=False),
        sa.Column("recipient_id", big_id(), nullable=False),
        sa.Column("attempt", small_uint(), nullable=False, server_default=sa.text("1")),
        sa.Column("error_code", sa.String(24), nullable=True),
        sa.Column("next_attempt_at", datetime6(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        # No FK to campaign_recipients: it is partitioned, so `recipient_id` is app-enforced.
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], name="fk_cretry_campaign", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_cretry_due", "campaign_retry_queue", ["status", "next_attempt_at"])
    op.create_index("ix_cretry_campaign", "campaign_retry_queue", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_cretry_campaign", table_name="campaign_retry_queue")
    op.drop_index("ix_cretry_due", table_name="campaign_retry_queue")
    op.drop_table("campaign_retry_queue")
