"""Index the recipient ledger by contact, for the reachability page.

Revision ID: 0063_reachability_contact_index
Revises: 0062_segment_domain_predicates

Every existing index on ``campaign_recipients`` leads with ``campaign_id``, because every query
until now started from a campaign. SCAN-01 asks the opposite question -- what happened to *this
contact*, across every campaign -- and no index answers it, so the lookup for a page of fifty
contacts scanned the whole ledger.

Measured against a real MySQL 8 at 200,000 recipients: the page query falls from **41.6ms to
9.1ms**. Deliberately *not* added when the same idea was tried during PERF-01, where it changed
nothing: at that point the query still aggregated the entire ledger, and no index avoids reading
rows you have asked for. It pays off only now that PERF-01 made the read selective -- the index and
the query shape are worth something together and nothing apart.

Non-unique, which is what a range-partitioned table permits: MySQL requires every *unique* key to
contain the partitioning column (``created_at``), and a plain key has no such rule.
"""

from __future__ import annotations

from alembic import op

revision = "0063_reachability_contact_index"
down_revision = "0062_segment_domain_predicates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_crecip_contact", "campaign_recipients", ["contact_id"])


def downgrade() -> None:
    op.drop_index("ix_crecip_contact", table_name="campaign_recipients")
