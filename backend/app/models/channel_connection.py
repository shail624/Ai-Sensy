"""Provider-neutral persistent channel connection, endpoint, and credential records.

M13-03 is the durable control-plane storage foundation only. These records contain configuration,
lifecycle, health, metadata, and encrypted credential facts; they do not implement a provider
adapter, session runtime, QR pairing, message synchronization, webhooks, or routing behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.orm.state import InstanceState

from app.channels.foundation import (
    ProviderDesiredState,
    ProviderHealthState,
    ProviderObservedState,
)
from app.channels.secrets import assert_no_secret_material
from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id, small_uint, varbinary

CHANNEL_SECRET_ACTIVE = "active"
CHANNEL_SECRET_REVOKED = "revoked"
CHANNEL_SECRET_STATUSES = (CHANNEL_SECRET_ACTIVE, CHANNEL_SECRET_REVOKED)

_DESIRED_STATES = tuple(state.value for state in ProviderDesiredState)
_OBSERVED_STATES = tuple(state.value for state in ProviderObservedState)
_HEALTH_STATES = tuple(state.value for state in ProviderHealthState)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _immutable_when_persisted(instance: object, key: str, value: str | None) -> str | None:
    state = cast(InstanceState[Any], inspect(instance))
    loaded = getattr(instance, key, None)
    if state.persistent and loaded is not None and loaded != value:
        raise ValueError(f"{key} is immutable after persistence")
    return value


class ChannelConnection(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """One organization-owned provider account or configured provider connection."""

    __tablename__ = "channel_connections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "connector_type",
            "provider_connection_id",
            name="uq_channel_connection_provider_identity",
        ),
        Index(
            "ix_channel_connections_org_active",
            "organization_id",
            "deleted_at",
            "channel_family",
        ),
        Index(
            "ix_channel_connections_org_state",
            "organization_id",
            "observed_state",
            "health_state",
        ),
        CheckConstraint(
            _in_clause("desired_state", _DESIRED_STATES),
            name="ck_channel_connection_desired_state",
        ),
        CheckConstraint(
            _in_clause("observed_state", _OBSERVED_STATES),
            name="ck_channel_connection_observed_state",
        ),
        CheckConstraint(
            _in_clause("health_state", _HEALTH_STATES),
            name="ck_channel_connection_health_state",
        ),
        CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_connection_health_score",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    channel_family: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_connection_id: Mapped[str | None] = mapped_column(String(190), nullable=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    desired_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProviderDesiredState.DISABLED.value
    )
    observed_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProviderObservedState.UNCONFIGURED.value
    )
    lifecycle_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lifecycle_changed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    health_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ProviderHealthState.UNKNOWN.value
    )
    health_score: Mapped[int | None] = mapped_column(small_uint(), nullable=True)
    health_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    health_observed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capability_snapshot_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    provider_configuration_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    endpoints: Mapped[list[ChannelEndpoint]] = relationship(
        "ChannelEndpoint", back_populates="connection", lazy="selectin", viewonly=True
    )
    secrets: Mapped[list[ChannelSecret]] = relationship(
        "ChannelSecret", back_populates="connection", lazy="raise", viewonly=True
    )

    @validates("connector_type", "provider_connection_id")
    def _validate_immutable_provider_identity(self, key: str, value: str | None) -> str | None:
        return _immutable_when_persisted(self, key, value)

    @validates("provider_configuration_json", "provider_metadata_json")
    def _validate_non_secret_json(
        self, key: str, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            assert_no_secret_material(value, field_name=key)
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ChannelConnection id={self.id} connector_type={self.connector_type!r} "
            f"provider_connection_id={self.provider_connection_id!r}>"
        )


class ChannelEndpoint(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """One addressable business identity belonging to a channel connection."""

    __tablename__ = "channel_endpoints"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "provider_endpoint_id",
            name="uq_channel_endpoint_provider_identity",
        ),
        UniqueConstraint(
            "connection_id",
            "endpoint_type",
            "normalized_address",
            name="uq_channel_endpoint_normalized_address",
        ),
        Index(
            "ix_channel_endpoints_org_active",
            "organization_id",
            "deleted_at",
            "enabled",
        ),
        Index(
            "ix_channel_endpoints_connection_default",
            "connection_id",
            "is_default",
            "deleted_at",
        ),
        CheckConstraint(
            _in_clause("observed_state", _OBSERVED_STATES),
            name="ck_channel_endpoint_observed_state",
        ),
        CheckConstraint(
            _in_clause("health_state", _HEALTH_STATES),
            name="ck_channel_endpoint_health_state",
        ),
        CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_endpoint_health_score",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_connections.id", ondelete="RESTRICT"), nullable=False
    )
    endpoint_type: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_address: Mapped[str] = mapped_column(String(190), nullable=False)
    display_address: Mapped[str | None] = mapped_column(String(190), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_endpoint_id: Mapped[str] = mapped_column(String(190), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observed_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProviderObservedState.UNCONFIGURED.value
    )
    health_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ProviderHealthState.UNKNOWN.value
    )
    health_score: Mapped[int | None] = mapped_column(small_uint(), nullable=True)
    health_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    health_observed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    endpoint_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    provider_limits_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    connection: Mapped[ChannelConnection] = relationship(
        "ChannelConnection", back_populates="endpoints"
    )

    @validates("provider_endpoint_id")
    def _validate_immutable_provider_endpoint(self, key: str, value: str) -> str:
        result = _immutable_when_persisted(self, key, value)
        assert result is not None
        return result

    @validates("endpoint_metadata_json", "provider_metadata_json", "provider_limits_json")
    def _validate_non_secret_json(
        self, key: str, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            assert_no_secret_material(value, field_name=key)
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ChannelEndpoint id={self.id} endpoint_type={self.endpoint_type!r} "
            f"provider_endpoint_id={self.provider_endpoint_id!r}>"
        )


class ChannelSecret(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """Encrypted, versioned, and revocable provider credential.

    No API schema is defined for this model. ``encrypted_payload`` is intentionally absent from all
    generated contracts and the representation is redacted.
    """

    __tablename__ = "channel_secrets"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "secret_type",
            "secret_version",
            name="uq_channel_secret_version",
        ),
        Index(
            "ix_channel_secrets_org_connection_status",
            "organization_id",
            "connection_id",
            "status",
        ),
        CheckConstraint(
            _in_clause("status", CHANNEL_SECRET_STATUSES),
            name="ck_channel_secret_status",
        ),
        CheckConstraint("secret_version > 0", name="ck_channel_secret_version_positive"),
        CheckConstraint("key_version > 0", name="ck_channel_secret_key_version_positive"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_connections.id", ondelete="RESTRICT"), nullable=False
    )
    secret_type: Mapped[str] = mapped_column(String(64), nullable=False)
    secret_version: Mapped[int] = mapped_column(int_id(), nullable=False)
    encrypted_payload: Mapped[bytes] = mapped_column(varbinary(4096), nullable=False)
    key_version: Mapped[int] = mapped_column(small_uint(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CHANNEL_SECRET_ACTIVE)
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    rotated_from_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("channel_secrets.id", ondelete="SET NULL"), nullable=True
    )
    rotated_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    revoked_by: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    connection: Mapped[ChannelConnection] = relationship(
        "ChannelConnection", back_populates="secrets"
    )

    @property
    def is_active(self) -> bool:
        return (
            self.status == CHANNEL_SECRET_ACTIVE
            and self.revoked_at is None
            and self.deleted_at is None
        )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ChannelSecret id={self.id} secret_type={self.secret_type!r} "
            f"secret_version={self.secret_version} status={self.status!r} payload=<redacted>>"
        )
