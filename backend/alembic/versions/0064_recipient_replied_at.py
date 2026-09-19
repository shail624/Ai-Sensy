"""Record when a campaign recipient wrote back.

Revision ID: 0064_recipient_replied_at
Revises: 0063_reachability_contact_index

``campaigns.replied_count`` has existed since the schema was written, is returned by the API, and
is printed on every campaign screen as "Replies: N (X% of delivered)". Nothing ever wrote it. Every
campaign has therefore reported zero replies for its whole life -- a confident, specific number
that was never measured, on the one metric a *reactivation* campaign exists to produce.

It could not be recomputed from anything, either: ``refresh_progress`` derives every other counter
from the roster, and the roster had no reply to derive from. So the fact is recorded where the rest
of the recipient's history already lives, and the counter joins the others in being derived rather
than incremented.

Nullable and unindexed on purpose. The count is always scoped to one campaign, which
``uq_crecip_campaign_contact`` already leads with, so a second index would be paid for on every
insert into a 200,000-row ledger to serve a query that is already selective. The table is
range-partitioned, so a *unique* key would have had to include ``created_at`` -- nothing here
needs one.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import datetime6

revision = "0064_recipient_replied_at"
down_revision = "0063_reachability_contact_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_recipients",
        sa.Column("replied_at", datetime6(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_recipients", "replied_at")
