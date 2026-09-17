"""Let a segment rule ask what WhatsApp said about the number.

Revision ID: 0065_segment_scan_source
Revises: 0064_recipient_replied_at

SCAN-01 made reachability visible and scope §13's "Create segment" makes it actionable, which is
where the value is: every campaign send costs money, so a roster that keeps including numbers Meta
has already refused pays for the same refusal every month. Until now an operator could read that
list and not exclude it.

The new source is ``scan``, with the single field ``reachability``. It is compiled from the Scan
screen's own predicate rather than a second copy, so a segment of "not on WhatsApp" is exactly the
set that screen shows.

Only the CHECK constraint moves; the rule row's shape is unchanged. The constraint is widened the
way ``0062`` widened it, through ``batch_alter_table`` so SQLite rebuilds the table and MySQL
alters it in place.
"""

from __future__ import annotations

from alembic import op

revision = "0065_segment_scan_source"
down_revision = "0064_recipient_replied_at"
branch_labels = None
depends_on = None

_BEFORE = "'contact', 'attribute', 'tag', 'engagement', 'reactivation', 'kyc', 'document', 'activation'"
_AFTER = _BEFORE + ", 'scan'"


def _replace_source_constraint(allowed: str) -> None:
    with op.batch_alter_table("segment_rules") as batch_op:
        batch_op.drop_constraint("ck_segrules_source", type_="check")
        batch_op.create_check_constraint("ck_segrules_source", f"field_source IN ({allowed})")


def upgrade() -> None:
    _replace_source_constraint(_AFTER)


def downgrade() -> None:
    _replace_source_constraint(_BEFORE)
