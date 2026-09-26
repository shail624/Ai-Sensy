"""Add exact-match first-message rules to organization tags.

Revision ID: 0071_tag_first_message_rules
Revises: 0070_phone_quality_unknown
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0071_tag_first_message_rules"
down_revision = "0070_phone_quality_unknown"
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
        # MySQL renders ALTER COLUMN as MODIFY and therefore requires the current type. Omitting
        # it works on SQLite but makes a clean MySQL upgrade fail after the preceding ADD COLUMN
        # statements have already committed.
        batch.alter_column(
            "first_message_keywords_json",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.drop_column("first_message_keywords_json")
        batch.drop_column("first_message_enabled")
