"""Record where an audited action came from, not only who did it.

Revision ID: 0066_audit_request_origin
Revises: 0065_segment_scan_source

``audit_logs`` has carried ``ip_address`` since the schema was written, and only the sign-in path
ever filled it: ``AuthService`` passes one, every other caller passes nothing. So the trail answers
*who* and *what* for every action and *where* for almost none — which is a weaker record than the
column list suggests, and the gap is invisible until somebody has to investigate.

This adds ``user_agent`` beside it and a request-scoped context both are read from, so an action
audited anywhere in the application carries its origin without every service signature growing two
parameters it has no way to fill.

**Deliberately outside the row hash.** ``_row_hash`` already excludes ``ip_address``; excluding the
device with it keeps that decision consistent and keeps the canonical form unchanged across this
migration. Widening it would invalidate the digest of every row ever written — and a
tamper-evidence scheme that cannot verify yesterday is worth less than one covering slightly fewer
fields.

Writing this migration's test is what surfaced a separate defect, fixed in the same change: the
digest was taken before ``created_at`` was assigned, so every historical row stored a real
timestamp under a hash computed over ``null`` and could never be recomputed from its own persisted
content. Those rows are reported as ``verified_legacy`` rather than as tampered — their content is
intact, their timestamp was simply never covered.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0066_audit_request_origin"
down_revision = "0065_segment_scan_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(length=400), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "user_agent")
