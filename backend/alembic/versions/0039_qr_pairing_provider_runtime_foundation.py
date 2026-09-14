"""Provider-neutral QR pairing and runtime control-plane foundation.

Revision ID: 0039_qr_pairing_provider_runtime_foundation
Revises: 0038_qr_session_manager_foundation
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.channels.runtime import PairingState
from app.db.types import datetime6, int_id

revision = "0039_qr_pairing_provider_runtime_foundation"
down_revision = "0038_qr_session_manager_foundation"
branch_labels = None
depends_on = None

_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "channels:authenticate",
        "resource": "channels",
        "action": "authenticate",
        "description": "Manage provider-neutral pairing lifecycle",
    }
]

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    states = tuple(state.value for state in PairingState)

    with op.batch_alter_table("channel_sessions") as batch:
        batch.add_column(
            sa.Column(
                "pairing_state",
                sa.String(32),
                nullable=False,
                server_default=PairingState.UNPAIRED.value,
            )
        )
        batch.add_column(
            sa.Column("pairing_revision", int_id(), nullable=False, server_default=sa.text("0"))
        )
        batch.add_column(
            sa.Column("pairing_changed_at", datetime6(), nullable=False, server_default=now)
        )
        batch.add_column(sa.Column("pairing_expires_at", datetime6(), nullable=True))
        batch.add_column(sa.Column("pairing_reason_code", sa.String(120), nullable=True))
        batch.add_column(sa.Column("runtime_capabilities_json", sa.JSON(), nullable=True))
        batch.create_check_constraint(
            "ck_channel_session_pairing_state", _in("pairing_state", states)
        )
        batch.create_check_constraint(
            "ck_channel_session_pairing_non_negative", "pairing_revision >= 0"
        )

    op.create_index(
        "ix_channel_sessions_pairing",
        "channel_sessions",
        ["organization_id", "pairing_state", "pairing_expires_at"],
    )

    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
    op.drop_index("ix_channel_sessions_pairing", table_name="channel_sessions")
    with op.batch_alter_table("channel_sessions") as batch:
        batch.drop_constraint("ck_channel_session_pairing_non_negative", type_="check")
        batch.drop_constraint("ck_channel_session_pairing_state", type_="check")
        batch.drop_column("runtime_capabilities_json")
        batch.drop_column("pairing_reason_code")
        batch.drop_column("pairing_expires_at")
        batch.drop_column("pairing_changed_at")
        batch.drop_column("pairing_revision")
        batch.drop_column("pairing_state")
