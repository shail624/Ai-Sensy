"""Conversations & the message ledger (Module 4 Step 4 — Doc 03 §9.1/§9.2/§9.3).

**Expand** phase: creates ``conversations``, ``messages`` and ``message_status_history``. Additive
and reversible.

``messages`` (10M+) and ``message_status_history`` (100M+) are partitioned monthly on MySQL and so
take the composite ``(id, created_at)`` primary key that requires — and carry **no** foreign keys,
because a partitioned table cannot be an FK target (Doc 03 §9.2/§9.3); those references are
app-enforced. ``conversations`` is small and fully constrained. On SQLite (test suite, Doc 10 §8)
the partitioned tables are plain surrogate-key tables.

Revision ID: 0016_conversations_messages
Revises: 0015_webhook_events
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0016_conversations_messages"
down_revision = "0015_webhook_events"
branch_labels = None
depends_on = None

_PARTITIONS = (
    "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
    "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
    "PARTITION pmax VALUES LESS THAN (MAXVALUE)"
)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    # --- conversations (Doc 03 §9.1) -----------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("phone_number_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column(
            "channel_type", sa.String(24), nullable=False, server_default=sa.text("'whatsapp'")
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("assigned_user_id", big_id(), nullable=True),
        sa.Column("last_message_at", datetime6(), nullable=True),
        sa.Column("last_inbound_at", datetime6(), nullable=True),
        sa.Column("window_expires_at", datetime6(), nullable=True),
        sa.Column("unread_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_message_preview", sa.String(255), nullable=True),
        sa.Column("is_window_open", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_conv_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_conv_org", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["phone_number_id"], ["phone_numbers.id"], name="fk_conv_number", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name="fk_conv_contact", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["users.id"], name="fk_conv_assignee", ondelete="SET NULL"
        ),
        sa.CheckConstraint("status IN ('open','pending','resolved','snoozed')", name="ck_conv_status"),
        **mysql_args,
    )
    op.create_index(
        "uq_conv_number_contact", "conversations", ["phone_number_id", "contact_id"], unique=True
    )
    op.create_index(
        "ix_conv_org_status", "conversations", ["organization_id", "status", "last_message_at"]
    )
    op.create_index("ix_conv_assignee", "conversations", ["assigned_user_id", "status"])
    op.create_index("ix_conv_window", "conversations", ["is_window_open", "window_expires_at"])

    # --- messages (Doc 03 §9.2) — the ledger, partitioned on MySQL -----------
    message_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("conversation_id", big_id(), nullable=False),
        sa.Column("phone_number_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("campaign_id", big_id(), nullable=True),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("message_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(16), nullable=True),
        sa.Column("template_id", big_id(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("media_asset_id", big_id(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'accepted'")),
        sa.Column("error_code", sa.String(24), nullable=True),
        sa.Column("pricing_model", sa.String(16), nullable=True),
        sa.Column("is_billable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_amount", sa.Numeric(12, 6), nullable=True),
        sa.Column("cost_currency", sa.CHAR(3), nullable=True),
        sa.Column("sent_at", datetime6(), nullable=True),
        sa.Column("delivered_at", datetime6(), nullable=True),
        sa.Column("read_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.CheckConstraint("direction IN ('inbound','outbound')", name="ck_msg_direction"),
    ]
    if dialect == "mysql":
        # No key on `uuid`: every unique key on a partitioned table must contain the partition
        # column, which is why Doc 03 §9.2 lists none — the public id is carried, not indexed.
        op.create_table(
            "messages",
            *message_columns,
            sa.PrimaryKeyConstraint("id", "created_at"),
            **mysql_args,
        )
    else:
        op.create_table(
            "messages",
            *message_columns,
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid", name="uq_msg_uuid"),
        )
    op.create_index("ix_msg_conversation", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_msg_wamid", "messages", ["wamid"])
    op.create_index("ix_msg_org_created", "messages", ["organization_id", "created_at"])
    op.create_index("ix_msg_campaign", "messages", ["campaign_id"])
    op.create_index("ix_msg_contact", "messages", ["contact_id", "created_at"])
    op.create_index("ix_msg_status", "messages", ["status", "created_at"])
    if dialect == "mysql":
        op.execute(f"ALTER TABLE messages PARTITION BY RANGE COLUMNS (created_at) ({_PARTITIONS})")

    # --- message_status_history (Doc 03 §9.3) — partitioned on MySQL ---------
    history_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("message_id", big_id(), nullable=False),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(24), nullable=True),
        sa.Column("error_title", sa.String(160), nullable=True),
        sa.Column("error_detail", sa.String(512), nullable=True),
        sa.Column("recipient_id", sa.String(24), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", datetime6(), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
    ]
    if dialect == "mysql":
        op.create_table(
            "message_status_history",
            *history_columns,
            sa.PrimaryKeyConstraint("id", "created_at"),
            **mysql_args,
        )
    else:
        op.create_table(
            "message_status_history", *history_columns, sa.PrimaryKeyConstraint("id")
        )
    op.create_index("ix_msh_message", "message_status_history", ["message_id", "created_at"])
    op.create_index("ix_msh_wamid", "message_status_history", ["wamid"])
    op.create_index("ix_msh_status", "message_status_history", ["status", "created_at"])
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE message_status_history "
            f"PARTITION BY RANGE COLUMNS (created_at) ({_PARTITIONS})"
        )


def downgrade() -> None:
    op.drop_index("ix_msh_status", table_name="message_status_history")
    op.drop_index("ix_msh_wamid", table_name="message_status_history")
    op.drop_index("ix_msh_message", table_name="message_status_history")
    op.drop_table("message_status_history")

    for index in (
        "ix_msg_status",
        "ix_msg_contact",
        "ix_msg_campaign",
        "ix_msg_org_created",
        "ix_msg_wamid",
        "ix_msg_conversation",
    ):
        op.drop_index(index, table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conv_window", table_name="conversations")
    op.drop_index("ix_conv_assignee", table_name="conversations")
    op.drop_index("ix_conv_org_status", table_name="conversations")
    op.drop_index("uq_conv_number_contact", table_name="conversations")
    op.drop_table("conversations")
