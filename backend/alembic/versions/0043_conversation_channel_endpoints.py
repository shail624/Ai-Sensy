"""Link the message ledger to provider-neutral channel endpoints (QR-08).

**Expand** stage of the additive evolution ADR-0020 names explicitly: "Existing WABA,
phone-number, conversation, message, webhook/event and media records are linked and backfilled
additively." A WAHA-originated conversation has no Meta ``phone_numbers`` row to own it — it is
owned by a ``channel_endpoints`` row instead (M13-03, migration ``0037``) — so
``conversations.phone_number_id`` can no longer be the *only* way a thread is owned.

Purely additive, no data touched:

* ``conversations`` gains a nullable ``channel_endpoint_id`` (real FK — this table is not
  partitioned) and ``phone_number_id`` widens to nullable. A new check constraint requires
  **exactly one** of the two to be set — a conversation is owned by a Meta number or a channel
  endpoint, never both, never neither. Every existing row already has ``phone_number_id`` set, so
  the constraint holds for all of them without a backfill.
* ``messages`` and ``webhook_events`` gain a nullable ``channel_endpoint_id`` alongside the
  existing nullable ``phone_number_id``. Both tables are partitioned on MySQL, so — exactly like
  ``phone_number_id`` already does — the new column is app-enforced, not an FK
  (``ix_msg_endpoint_wamid``/0042 is the precedent: a partitioned table cannot hold a unique key
  that omits its partition column, so scoped uniqueness stays a read-plus-persist-first
  discipline, not a database constraint).
* New indexes mirror the existing Meta-scoped ones: ``uq_conv_endpoint_contact`` (the WAHA-side
  analogue of ``uq_conv_number_contact``) and ``ix_msg_channel_endpoint_wamid`` (the WAHA-side
  analogue of ``ix_msg_endpoint_wamid``), so endpoint-scoped provider-message-identity lookups get
  the same query plan Meta's already have.

No column is dropped, renamed, or narrowed. No existing row's ``phone_number_id`` changes.

Revision ID: 0043_conversation_channel_endpoints
Revises: 0042_scope_provider_message_identity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id

revision = "0043_conversation_channel_endpoints"
down_revision = "0042_scope_provider_message_identity"
branch_labels = None
depends_on = None

_CONV_OWNER_CHECK = (
    "(phone_number_id IS NOT NULL AND channel_endpoint_id IS NULL) OR "
    "(phone_number_id IS NULL AND channel_endpoint_id IS NOT NULL)"
)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    # --- conversations: real table, real FK, exactly-one-owner check --------
    with op.batch_alter_table("conversations") as batch:
        batch.alter_column("phone_number_id", existing_type=big_id(), nullable=True)
        batch.add_column(sa.Column("channel_endpoint_id", big_id(), nullable=True))
        batch.create_foreign_key(
            "fk_conv_channel_endpoint",
            "channel_endpoints",
            ["channel_endpoint_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_check_constraint("ck_conv_endpoint_owner", _CONV_OWNER_CHECK)
    op.create_index(
        "uq_conv_endpoint_contact",
        "conversations",
        ["channel_endpoint_id", "contact_id"],
        unique=True,
    )

    # --- messages: partitioned on MySQL, app-enforced (no FK), like phone_number_id already is
    if dialect == "mysql":
        op.alter_column("messages", "phone_number_id", existing_type=big_id(), nullable=True)
        op.add_column("messages", sa.Column("channel_endpoint_id", big_id(), nullable=True))
    else:
        with op.batch_alter_table("messages") as batch:
            batch.alter_column("phone_number_id", existing_type=big_id(), nullable=True)
            batch.add_column(sa.Column("channel_endpoint_id", big_id(), nullable=True))
    op.create_index(
        "ix_msg_channel_endpoint_wamid", "messages", ["channel_endpoint_id", "wamid"], unique=False
    )

    # --- webhook_events: partitioned on MySQL, app-enforced (no FK); already nullable
    if dialect == "mysql":
        op.add_column("webhook_events", sa.Column("channel_endpoint_id", big_id(), nullable=True))
    else:
        with op.batch_alter_table("webhook_events") as batch:
            batch.add_column(sa.Column("channel_endpoint_id", big_id(), nullable=True))
    op.create_index(
        "ix_whe_endpoint", "webhook_events", ["channel_endpoint_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_whe_endpoint", table_name="webhook_events")
    with op.batch_alter_table("webhook_events") as batch:
        batch.drop_column("channel_endpoint_id")

    op.drop_index("ix_msg_channel_endpoint_wamid", table_name="messages")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("channel_endpoint_id")
        batch.alter_column("phone_number_id", existing_type=big_id(), nullable=False)

    op.drop_index("uq_conv_endpoint_contact", table_name="conversations")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_constraint("ck_conv_endpoint_owner", type_="check")
        batch.drop_constraint("fk_conv_channel_endpoint", type_="foreignkey")
        batch.drop_column("channel_endpoint_id")
        batch.alter_column("phone_number_id", existing_type=big_id(), nullable=False)
