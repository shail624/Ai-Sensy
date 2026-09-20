"""Add exact-match first-message rules to organization tags.

Revision ID: 0070_tag_first_message_rules
Revises: 0069_google_sheet_export_format
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070_tag_first_message_rules"
down_revision = "0069_google_sheet_export_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.add_column(
            sa.Column(
                "first_message_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(sa.Column("first_message_keywords_json", sa.JSON(), nullable=True))
    tags = sa.table("tags", sa.column("first_message_keywords_json", sa.JSON()))
    op.execute(tags.update().values(first_message_keywords_json=[]))
    with op.batch_alter_table("tags") as batch:
        batch.alter_column("first_message_keywords_json", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.drop_column("first_message_keywords_json")
        batch.drop_column("first_message_enabled")
