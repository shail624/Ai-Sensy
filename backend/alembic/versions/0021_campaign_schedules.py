"""Campaign schedules (Phase 6 Step 4 — Doc 03 §8.2).

**Expand** phase: creates ``campaign_schedules``. Additive and reversible.

"The DB is the schedule, Beat is the heartbeat" (Doc 06 §10.2, D14): this table is what makes
schedules editable at runtime and durable across restarts. ``ix_csched_next`` is the tick's index —
the scan is O(due rows), never a full table scan (Doc 06 §10.2).

Revision ID: 0021_campaign_schedules
Revises: 0020_campaign_retry_queue
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0021_campaign_schedules"
down_revision = "0020_campaign_retry_queue"
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
        "campaign_schedules",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("campaign_id", big_id(), nullable=False),
        sa.Column("schedule_type", sa.String(16), nullable=False),
        sa.Column("run_at", datetime6(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("cron_expr", sa.String(120), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("next_run_at", datetime6(), nullable=True),
        sa.Column("last_run_at", datetime6(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_csched_uuid"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], name="fk_csched_campaign", ondelete="CASCADE"
        ),
        # Only the two the frozen schema permits: a drip sequence is expanded into `one_time`
        # rows, not stored as a third type (Doc 06 §10.3).
        sa.CheckConstraint("schedule_type IN ('one_time','recurring')", name="ck_csched_type"),
        **mysql_args,
    )
    op.create_index("ix_csched_next", "campaign_schedules", ["is_active", "next_run_at"])
    op.create_index("ix_csched_campaign", "campaign_schedules", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_csched_campaign", table_name="campaign_schedules")
    op.drop_index("ix_csched_next", table_name="campaign_schedules")
    op.drop_table("campaign_schedules")
