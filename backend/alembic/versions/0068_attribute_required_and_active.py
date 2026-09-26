"""Give a custom attribute a required flag and a retirement flag.

Revision ID: 0068_attribute_required_and_active
Revises: 0067_reachability_covering_index

`custom_attribute_definitions` could say a field was indexed and that it held PII, and could not say
the two things an operations team actually asks of a field definition: *this one must not be left
blank*, and *we have stopped using this one*.

Both defaults preserve every existing row's behaviour exactly — nothing becomes required, nothing
becomes retired — so this migration changes no observable behaviour on its own.

``is_required`` is deliberately narrow. ``POST /contacts/{id}/attributes`` is a **partial** update:
it writes the keys it is given and deletes the ones passed as ``null``. "Required" therefore cannot
mean "every write must carry it" — that would break every partial update and every import in the
product. It means **it may not be cleared**: once the field has a value, passing ``null`` for it is
refused.

``is_active`` retires a definition without destroying its data. A retired attribute accepts no new
value, and its existing values stay readable and stay deletable, so a field can be wound down
instead of deleted out from under the history that references it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0068_attribute_required_and_active"
down_revision = "0067_reachability_covering_index"
branch_labels = None
depends_on = None

_TABLE = "custom_attribute_definitions"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        _TABLE,
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "is_active")
    op.drop_column(_TABLE, "is_required")
