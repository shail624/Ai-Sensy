"""Make the reachability aggregate index-only.

Revision ID: 0067_reachability_covering_index
Revises: 0066_audit_request_origin

`/scan/reachability` filtered by a verdict, and `/scan/reachability/counts`, both aggregate every
recipient row the organization owns — they have to, because a verdict is only known once the whole
ledger for a contact has been read, so there is no page of fifty to narrow to first.

Access was already indexed by ``uq_crecip_campaign_contact``, but none of the columns the aggregate
*reads* were in any index, so each of the matched rows cost a row lookup. Measured against a real
MySQL 8 holding 200,000 recipients: the unfiltered page answered in 13ms and every verdict filter
in 400-460ms, which is the ordinary way that screen is used and over the project's 300ms budget.

Covering the aggregate brings the filtered page to 180ms, `unknown` to 227ms and the tallies to
215ms, with the plan reporting index-only access.

The cost is on the write side: ``delivered_at``, ``read_at`` and ``failed_at`` are all in the index
and all written as receipts arrive. Measured at +21% on a bulk update of 2,000 recipients — about
six microseconds per receipt. That is the right way round for a ledger written once per message and
read on every visit to the screen.

Non-unique, so MySQL's requirement that a unique index include the partitioning column does not
apply and ``created_at`` stays out of it.
"""

from __future__ import annotations

from alembic import op

revision = "0067_reachability_covering_index"
down_revision = "0066_audit_request_origin"
branch_labels = None
depends_on = None

_NAME = "ix_crecip_reachability"
_TABLE = "campaign_recipients"
_COLUMNS = [
    "campaign_id",
    "contact_id",
    "status",
    "error_code",
    "delivered_at",
    "read_at",
    "failed_at",
]


def upgrade() -> None:
    op.create_index(_NAME, _TABLE, _COLUMNS, unique=False)


def downgrade() -> None:
    op.drop_index(_NAME, table_name=_TABLE)
