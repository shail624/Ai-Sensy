"""Permit queued contact exports whose destination is a Google Sheet tab.

Revision ID: 0069_google_sheet_export_format
Revises: 0068_attribute_required_and_active
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0069_google_sheet_export_format"
down_revision = "0068_attribute_required_and_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exports") as batch:
        batch.drop_constraint("ck_exports_format", type_="check")
        batch.create_check_constraint(
            "ck_exports_format", "format IN ('csv','xlsx','json','pdf','google_sheet')"
        )


def downgrade() -> None:
    exports = sa.table("exports", sa.column("format", sa.String))
    op.execute(exports.delete().where(exports.c.format == "google_sheet"))
    with op.batch_alter_table("exports") as batch:
        batch.drop_constraint("ck_exports_format", type_="check")
        batch.create_check_constraint(
            "ck_exports_format", "format IN ('csv','xlsx','json','pdf')"
        )
