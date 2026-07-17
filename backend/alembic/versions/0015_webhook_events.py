"""Inbound webhook storage: events & dead letter (Module 4 Step 3 — Doc 03 §9.4).

**Expand** phase: creates ``webhook_events`` and ``webhook_dead_letter``. Additive and reversible.

``webhook_events`` is a 10M+ table, so on MySQL it takes the composite ``(id, created_at)`` primary
key its monthly RANGE partitioning requires (Doc 03 §9.4) — the same shape ``audit_logs`` uses; on
SQLite (test suite, Doc 10 §8) it is a plain surrogate-key table. Neither table carries a foreign
key: a partitioned table cannot be an FK target, so ``phone_number_id``/``source_event_id`` are
app-enforced (Doc 03 §9.2/§9.4).

Revision ID: 0015_webhook_events
Revises: 0014_waba_phone_numbers
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, small_uint, uuid_binary

revision = "0015_webhook_events"
down_revision = "0014_waba_phone_numbers"
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

    # --- webhook_events (Doc 03 §9.4) — partitioned on MySQL -----------------
    event_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("phone_number_id", big_id(), nullable=True),
        sa.Column("object_type", sa.String(40), nullable=True),
        sa.Column("signature_ok", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'received'")),
        sa.Column("processed_at", datetime6(), nullable=True),
        sa.Column("attempts", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
    ]
    if dialect == "mysql":
        # The partition column must be part of every unique key, hence the composite PK.
        op.create_table(
            "webhook_events",
            *event_columns,
            sa.PrimaryKeyConstraint("id", "created_at"),
            **mysql_args,
        )
    else:
        op.create_table("webhook_events", *event_columns, sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_whe_status", "webhook_events", ["status", "created_at"])
    op.create_index("ix_whe_event", "webhook_events", ["event_id"])
    op.create_index("ix_whe_number", "webhook_events", ["phone_number_id", "created_at"])
    if dialect == "mysql":
        # Monthly RANGE partitioning with a catch-all (Doc 03 §9.4). New monthly partitions are
        # provisioned by the maintenance job (Doc 06 §10 / Doc 11), as for `audit_logs`.
        op.execute(
            "ALTER TABLE webhook_events PARTITION BY RANGE COLUMNS (created_at) ("
            "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
            "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
            "PARTITION pmax VALUES LESS THAN (MAXVALUE))"
        )

    # --- webhook_dead_letter (Doc 03 §9.4) -----------------------------------
    op.create_table(
        "webhook_dead_letter",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("source_event_id", big_id(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error_detail", sa.String(1024), nullable=True),
        sa.Column("attempts", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("replayed_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_whdl_uuid"),
        **mysql_args,
    )
    op.create_index("ix_whdl_status", "webhook_dead_letter", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_whdl_status", table_name="webhook_dead_letter")
    op.drop_table("webhook_dead_letter")
    op.drop_index("ix_whe_number", table_name="webhook_events")
    op.drop_index("ix_whe_event", table_name="webhook_events")
    op.drop_index("ix_whe_status", table_name="webhook_events")
    op.drop_table("webhook_events")
