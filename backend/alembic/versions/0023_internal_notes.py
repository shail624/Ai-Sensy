"""Internal notes (Phase 7 Step 1 — Doc 03 §9.5).

**Expand** phase: creates ``internal_notes``. Additive and reversible.

The conversation collaboration layer's only new table: ``conversations`` (status, assignee) already
exists from Module 4 (0016). Staff-only notes hang off a conversation and are attributed to their
author — the two foreign keys the frozen schema declares.

Revision ID: 0023_internal_notes
Revises: 0022_rate_cards
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0023_internal_notes"
down_revision = "0022_rate_cards"
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
        "internal_notes",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("conversation_id", big_id(), nullable=False),
        sa.Column("author_user_id", big_id(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_note_uuid"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], name="fk_note_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"], name="fk_note_author", ondelete="RESTRICT"
        ),
        **mysql_args,
    )
    op.create_index("ix_note_conversation", "internal_notes", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_note_conversation", table_name="internal_notes")
    op.drop_table("internal_notes")
