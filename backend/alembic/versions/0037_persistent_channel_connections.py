"""Provider-neutral channel connection, endpoint, and encrypted credential persistence.

Revision ID: 0037_persistent_channel_connections
Revises: 0036_customer_identity_resolution
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.channels.foundation import (
    ProviderDesiredState,
    ProviderHealthState,
    ProviderObservedState,
)
from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary, varbinary
from app.models.channel_connection import CHANNEL_SECRET_STATUSES

revision = "0037_persistent_channel_connections"
down_revision = "0036_customer_identity_resolution"
branch_labels = None
depends_on = None


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
    desired_states = tuple(state.value for state in ProviderDesiredState)
    observed_states = tuple(state.value for state in ProviderObservedState)
    health_states = tuple(state.value for state in ProviderHealthState)

    op.create_table(
        "channel_connections",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("channel_family", sa.String(64), nullable=False),
        sa.Column("connector_type", sa.String(64), nullable=False),
        sa.Column("provider_connection_id", sa.String(190), nullable=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column(
            "desired_state",
            sa.String(32),
            nullable=False,
            server_default=ProviderDesiredState.DISABLED.value,
        ),
        sa.Column(
            "observed_state",
            sa.String(32),
            nullable=False,
            server_default=ProviderObservedState.UNCONFIGURED.value,
        ),
        sa.Column("lifecycle_detail", sa.String(500), nullable=True),
        sa.Column("lifecycle_changed_at", datetime6(), nullable=True),
        sa.Column(
            "health_state",
            sa.String(24),
            nullable=False,
            server_default=ProviderHealthState.UNKNOWN.value,
        ),
        sa.Column("health_score", small_uint(), nullable=True),
        sa.Column("health_detail", sa.String(500), nullable=True),
        sa.Column("health_observed_at", datetime6(), nullable=True),
        sa.Column("last_activity_at", datetime6(), nullable=True),
        sa.Column("last_error_code", sa.String(120), nullable=True),
        sa.Column("last_error_summary", sa.String(500), nullable=True),
        sa.Column("capability_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("provider_configuration_json", sa.JSON(), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_channel_connections_uuid"),
        sa.UniqueConstraint(
            "organization_id",
            "connector_type",
            "provider_connection_id",
            name="uq_channel_connection_provider_identity",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            _in("desired_state", desired_states),
            name="ck_channel_connection_desired_state",
        ),
        sa.CheckConstraint(
            _in("observed_state", observed_states),
            name="ck_channel_connection_observed_state",
        ),
        sa.CheckConstraint(
            _in("health_state", health_states),
            name="ck_channel_connection_health_state",
        ),
        sa.CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_connection_health_score",
        ),
        **args,
    )
    op.create_index(
        "ix_channel_connections_org_active",
        "channel_connections",
        ["organization_id", "deleted_at", "channel_family"],
    )
    op.create_index(
        "ix_channel_connections_org_state",
        "channel_connections",
        ["organization_id", "observed_state", "health_state"],
    )

    op.create_table(
        "channel_endpoints",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("connection_id", big_id(), nullable=False),
        sa.Column("endpoint_type", sa.String(64), nullable=False),
        sa.Column("normalized_address", sa.String(190), nullable=False),
        sa.Column("display_address", sa.String(190), nullable=True),
        sa.Column("display_name", sa.String(160), nullable=True),
        sa.Column("provider_endpoint_id", sa.String(190), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "observed_state",
            sa.String(32),
            nullable=False,
            server_default=ProviderObservedState.UNCONFIGURED.value,
        ),
        sa.Column(
            "health_state",
            sa.String(24),
            nullable=False,
            server_default=ProviderHealthState.UNKNOWN.value,
        ),
        sa.Column("health_score", small_uint(), nullable=True),
        sa.Column("health_detail", sa.String(500), nullable=True),
        sa.Column("health_observed_at", datetime6(), nullable=True),
        sa.Column("endpoint_metadata_json", sa.JSON(), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=True),
        sa.Column("provider_limits_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_channel_endpoints_uuid"),
        sa.UniqueConstraint(
            "connection_id",
            "provider_endpoint_id",
            name="uq_channel_endpoint_provider_identity",
        ),
        sa.UniqueConstraint(
            "connection_id",
            "endpoint_type",
            "normalized_address",
            name="uq_channel_endpoint_normalized_address",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["connection_id"], ["channel_connections.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            _in("observed_state", observed_states),
            name="ck_channel_endpoint_observed_state",
        ),
        sa.CheckConstraint(
            _in("health_state", health_states),
            name="ck_channel_endpoint_health_state",
        ),
        sa.CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_endpoint_health_score",
        ),
        **args,
    )
    op.create_index(
        "ix_channel_endpoints_org_active",
        "channel_endpoints",
        ["organization_id", "deleted_at", "enabled"],
    )
    op.create_index(
        "ix_channel_endpoints_connection_default",
        "channel_endpoints",
        ["connection_id", "is_default", "deleted_at"],
    )

    op.create_table(
        "channel_secrets",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("connection_id", big_id(), nullable=False),
        sa.Column("secret_type", sa.String(64), nullable=False),
        sa.Column("secret_version", int_id(), nullable=False),
        sa.Column("encrypted_payload", varbinary(4096), nullable=False),
        sa.Column("key_version", small_uint(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("expires_at", datetime6(), nullable=True),
        sa.Column("rotated_from_id", big_id(), nullable=True),
        sa.Column("rotated_at", datetime6(), nullable=True),
        sa.Column("revoked_at", datetime6(), nullable=True),
        sa.Column("revoked_by", big_id(), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("last_accessed_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_channel_secrets_uuid"),
        sa.UniqueConstraint(
            "connection_id",
            "secret_type",
            "secret_version",
            name="uq_channel_secret_version",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["connection_id"], ["channel_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rotated_from_id"], ["channel_secrets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(_in("status", CHANNEL_SECRET_STATUSES), name="ck_channel_secret_status"),
        sa.CheckConstraint("secret_version > 0", name="ck_channel_secret_version_positive"),
        sa.CheckConstraint("key_version > 0", name="ck_channel_secret_key_version_positive"),
        **args,
    )
    op.create_index(
        "ix_channel_secrets_org_connection_status",
        "channel_secrets",
        ["organization_id", "connection_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_channel_secrets_org_connection_status", table_name="channel_secrets")
    op.drop_table("channel_secrets")
    op.drop_index("ix_channel_endpoints_connection_default", table_name="channel_endpoints")
    op.drop_index("ix_channel_endpoints_org_active", table_name="channel_endpoints")
    op.drop_table("channel_endpoints")
    op.drop_index("ix_channel_connections_org_state", table_name="channel_connections")
    op.drop_index("ix_channel_connections_org_active", table_name="channel_connections")
    op.drop_table("channel_connections")
