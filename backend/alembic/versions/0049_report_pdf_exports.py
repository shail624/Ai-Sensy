"""Allow PDF artifacts for governed analytics report exports.

Revision ID: 0049_report_pdf_exports
Revises: 0048_automation_wait_subscriptions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049_report_pdf_exports"
down_revision = "0048_automation_wait_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exports") as batch:
        batch.drop_constraint("ck_exports_format", type_="check")
        batch.create_check_constraint(
            "ck_exports_format", "format IN ('csv','xlsx','json','pdf')"
        )


def downgrade() -> None:
    exports = sa.table("exports", sa.column("format", sa.String))
    # A legacy schema cannot represent PDF truthfully; remove those expiring job records before
    # restoring its narrower constraint. Stored artifacts remain subject to normal retention.
    op.execute(exports.delete().where(exports.c.format == "pdf"))
    with op.batch_alter_table("exports") as batch:
        batch.drop_constraint("ck_exports_format", type_="check")
        batch.create_check_constraint(
            "ck_exports_format", "format IN ('csv','xlsx','json')"
        )
