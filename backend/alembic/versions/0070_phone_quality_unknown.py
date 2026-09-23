"""Permit Meta's ``UNKNOWN`` quality rating on a phone number.

Revision ID: 0070_phone_quality_unknown
Revises: 0069_google_sheet_export_format

Meta's WhatsApp Cloud API reports ``UNKNOWN`` for a number that has not sent enough messages yet
for a quality score to exist — the normal state for a number just added to a WABA, which is exactly
when an operator is most likely to sync. ``ck_phone_quality`` only permitted ``GREEN``/``YELLOW``/
``RED``/``NULL``, so ``WabaService.run_sync`` failed its one batched flush the moment Meta reported
any number this way, and — because every synced number in that WABA shares the one flush — took the
rest of that sync's already-good updates down with it. Reproduced against live MySQL before this
migration existed: ``(3819, "Check constraint 'ck_phone_numbers_ck_phone_quality' is violated.")``,
with a same-batch ``GREEN`` number's update lost alongside the rejected one.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070_phone_quality_unknown"
down_revision = "0069_google_sheet_export_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as batch:
        batch.drop_constraint("ck_phone_quality", type_="check")
        batch.create_check_constraint(
            "ck_phone_quality", "quality_rating IN ('GREEN','YELLOW','RED','UNKNOWN')"
        )


def downgrade() -> None:
    # The number itself is real and stays; only the newly-permitted rating value cannot. Null it
    # rather than deleting the row — the same distinction QR/WABA rows draw elsewhere between "not
    # rated" and "does not exist" (Doc 03 §5.2), and consistent with the column already being
    # nullable for exactly this "Meta has not rated it yet" case.
    phone_numbers = sa.table("phone_numbers", sa.column("quality_rating", sa.String))
    op.execute(
        phone_numbers.update()
        .where(phone_numbers.c.quality_rating == "UNKNOWN")
        .values(quality_rating=None)
    )
    with op.batch_alter_table("phone_numbers") as batch:
        batch.drop_constraint("ck_phone_quality", type_="check")
        batch.create_check_constraint(
            "ck_phone_quality", "quality_rating IN ('GREEN','YELLOW','RED')"
        )
