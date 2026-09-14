"""Index the campaign recipient ledger for operational paging.

Revision ID: 0056_campaign_recipient_operations
Revises: 0055_campaign_results_exports
"""

from __future__ import annotations

from alembic import op

revision = "0056_campaign_recipient_operations"
down_revision = "0055_campaign_results_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_crecip_campaign_created",
        "campaign_recipients",
        ["campaign_id", "created_at", "id"],
    )
    op.create_index(
        "ix_crecip_campaign_status_created",
        "campaign_recipients",
        ["campaign_id", "status", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crecip_campaign_status_created",
        table_name="campaign_recipients",
    )
    op.drop_index("ix_crecip_campaign_created", table_name="campaign_recipients")
