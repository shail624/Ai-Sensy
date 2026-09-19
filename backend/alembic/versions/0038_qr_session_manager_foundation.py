"""Provider-neutral QR Session Manager durable control-plane foundation.

Revision ID: 0038_qr_session_manager_foundation
Revises: 0037_persistent_channel_connections
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.channels.foundation import ProviderHealthState
from app.channels.session import SessionRestartPolicy, SessionState
from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary

revision = "0038_qr_session_manager_foundation"
down_revision = "0037_persistent_channel_connections"
branch_labels = None
depends_on = None

_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "channels:read",
        "resource": "channels",
        "action": "read",
        "description": "View provider-neutral channel connections and sessions",
    },
    {
        "code": "channels:manage",
        "resource": "channels",
        "action": "manage",
        "description": "Register and manage provider-neutral channel sessions",
    },
    {
        "code": "channels:diagnose",
        "resource": "channels",
        "action": "diagnose",
        "description": "Operate session leases, heartbeats and health observations",
    },
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


def _table_args(dialect: str) -> dict[str, Any]:
    if dialect != "mysql":
        return {}
    return {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    args = _table_args(dialect)
    session_states = tuple(state.value for state in SessionState)
    restart_policies = tuple(policy.value for policy in SessionRestartPolicy)
    health_states = tuple(state.value for state in ProviderHealthState)

    op.create_table(
        "channel_sessions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("connection_id", big_id(), nullable=False),
        sa.Column("owner_user_id", big_id(), nullable=False),
        sa.Column("secret_id", big_id(), nullable=True),
        sa.Column("session_revision", int_id(), nullable=False),
        sa.Column(
            "state",
            sa.String(32),
            nullable=False,
            server_default=SessionState.REGISTERED.value,
        ),
        sa.Column("state_changed_at", datetime6(), nullable=False, server_default=now),
        sa.Column("state_detail", sa.String(500), nullable=True),
        sa.Column(
            "health_state",
            sa.String(24),
            nullable=False,
            server_default=ProviderHealthState.UNKNOWN.value,
        ),
        sa.Column("health_score", small_uint(), nullable=True),
        sa.Column("health_detail", sa.String(500), nullable=True),
        sa.Column("health_observed_at", datetime6(), nullable=True),
        sa.Column(
            "restart_policy",
            sa.String(24),
            nullable=False,
            server_default=SessionRestartPolicy.NEVER.value,
        ),
        sa.Column("reconnect_attempts", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_reconnect_attempts", int_id(), nullable=False, server_default=sa.text("3")),
        sa.Column("next_restart_at", datetime6(), nullable=True),
        sa.Column("holder_runtime_id", sa.String(160), nullable=True),
        sa.Column("lease_expires_at", datetime6(), nullable=True),
        sa.Column("fencing_token", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_heartbeat_at", datetime6(), nullable=True),
        sa.Column("last_activity_at", datetime6(), nullable=True),
        sa.Column("expires_at", datetime6(), nullable=True),
        sa.Column("terminated_at", datetime6(), nullable=True),
        sa.Column("capability_references_json", sa.JSON(), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=True),
        sa.Column("recovery_metadata_json", sa.JSON(), nullable=True),
        sa.Column("last_error_code", sa.String(120), nullable=True),
        sa.Column("last_error_summary", sa.String(500), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_channel_sessions_uuid"),
        sa.UniqueConstraint(
            "connection_id", "session_revision", name="uq_channel_session_revision"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["connection_id"], ["channel_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["secret_id"], ["channel_secrets.id"], ondelete="SET NULL"),
        sa.CheckConstraint(_in("state", session_states), name="ck_channel_session_state"),
        sa.CheckConstraint(
            _in("restart_policy", restart_policies),
            name="ck_channel_session_restart_policy",
        ),
        sa.CheckConstraint(
            _in("health_state", health_states), name="ck_channel_session_health_state"
        ),
        sa.CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_session_health_score",
        ),
        sa.CheckConstraint("session_revision > 0", name="ck_channel_session_revision_positive"),
        sa.CheckConstraint("fencing_token >= 0", name="ck_channel_session_fencing_non_negative"),
        sa.CheckConstraint(
            "reconnect_attempts >= 0", name="ck_channel_session_reconnect_non_negative"
        ),
        sa.CheckConstraint(
            "max_reconnect_attempts >= 0",
            name="ck_channel_session_max_reconnect_non_negative",
        ),
        **args,
    )
    op.create_index(
        "ix_channel_sessions_org_state",
        "channel_sessions",
        ["organization_id", "state", "deleted_at"],
    )
    op.create_index(
        "ix_channel_sessions_connection_current",
        "channel_sessions",
        ["connection_id", "session_revision", "deleted_at"],
    )
    op.create_index(
        "ix_channel_sessions_lease",
        "channel_sessions",
        ["lease_expires_at", "holder_runtime_id"],
    )

    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
    op.drop_index("ix_channel_sessions_lease", table_name="channel_sessions")
    op.drop_index("ix_channel_sessions_connection_current", table_name="channel_sessions")
    op.drop_index("ix_channel_sessions_org_state", table_name="channel_sessions")
    op.drop_table("channel_sessions")
