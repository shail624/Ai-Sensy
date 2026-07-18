"""Conversation tags (Phase 7 Step 5 — Doc 03 §9.7, v1.3).

**Expand** phase: creates ``conversation_tags``. Additive and reversible.

The M:N junction between conversations and the existing ``tags`` taxonomy — a mirror of
``contact_tags`` (composite PK, reverse index, both FKs ``ON DELETE CASCADE``). No new tag entity and
no change to ``tags``/``contact_tags``.

Revision ID: 0025_conversation_tags
Revises: 0024_quick_replies
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6

revision = "0025_conversation_tags"
down_revision = "0024_quick_replies"
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
        "conversation_tags",
        sa.Column("conversation_id", big_id(), nullable=False),
        sa.Column("tag_id", big_id(), nullable=False),
        sa.Column("tagged_at", datetime6(), nullable=False, server_default=now),
        sa.Column("tagged_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("conversation_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], name="fk_convtag_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="fk_convtag_tag", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_convtag_tag", "conversation_tags", ["tag_id", "conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_convtag_tag", table_name="conversation_tags")
    op.drop_table("conversation_tags")
