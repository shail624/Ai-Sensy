"""Add a sale status and a number release date (with its reminder task) to contacts.

Revision ID: 0072_contact_sale_status
Revises: 0071_tag_first_message_rules
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id

revision = "0072_contact_sale_status"
down_revision = "0071_tag_first_message_rules"
branch_labels = None
depends_on = None

_SALE_STATUSES = (
    "follow_up",
    "sale_reminder",
    "sale_in_field",
    "sale_confirmed",
    "sale_done",
    "activated_elsewhere",
    "not_interested",
)


def upgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.add_column(sa.Column("sale_status", sa.String(32), nullable=True))
        batch.add_column(sa.Column("release_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("release_task_id", big_id(), nullable=True))
        batch.create_index("ix_contacts_org_sale_status", ["organization_id", "sale_status"])
        batch.create_check_constraint(
            "ck_contacts_sale_status",
            "sale_status IS NULL OR sale_status IN ("
            + ",".join(f"'{value}'" for value in _SALE_STATUSES)
            + ")",
        )


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.drop_constraint("ck_contacts_sale_status", type_="check")
        batch.drop_index("ix_contacts_org_sale_status")
        batch.drop_column("release_task_id")
        batch.drop_column("release_date")
        batch.drop_column("sale_status")
