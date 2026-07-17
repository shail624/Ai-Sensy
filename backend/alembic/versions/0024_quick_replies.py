"""Quick replies (Phase 7 Step 4 — Doc 03 §9.5).

**Expand** phase: creates ``quick_replies``. Additive and reversible.

Personal/shared canned messages for the shared inbox. ``owner_user_id`` NULL means shared org-wide,
else the reply is personal to that user (FR-INB-04). The frozen schema declares only ``fk_qr_org``
(no FK on ``owner_user_id``/``created_by``) and no ``row_version`` — this migration matches it exactly.

Revision ID: 0024_quick_replies
Revises: 0023_internal_notes
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0024_quick_replies"
down_revision = "0023_internal_notes"
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
        "quick_replies",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("owner_user_id", big_id(), nullable=True),
        sa.Column("shortcut", sa.String(60), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("usage_count", int_id(), nullable=False, server_default="0"),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_qr_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_qr_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_qr_org_owner", "quick_replies", ["organization_id", "owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_qr_org_owner", table_name="quick_replies")
    op.drop_table("quick_replies")
