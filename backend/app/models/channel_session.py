"""Provider-neutral persistent channel session control-plane record.

The record stores lifecycle, ownership, lease/fencing, heartbeat, recovery and capability facts.
Provider credentials are referenced by foreign key only and are never copied into session metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.channels.foundation import ProviderHealthState
from app.channels.runtime import PairingState
from app.channels.secrets import assert_no_secret_material
from app.channels.session import SessionRestartPolicy, SessionState
from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id, small_uint

_SESSION_STATES = tuple(state.value for state in SessionState)
_RESTART_POLICIES = tuple(policy.value for policy in SessionRestartPolicy)
_HEALTH_STATES = tuple(state.value for state in ProviderHealthState)
_PAIRING_STATES = tuple(state.value for state in PairingState)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ChannelSession(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """One durable provider-neutral session revision for a channel connection."""

    __tablename__ = "channel_sessions"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "session_revision",
            name="uq_channel_session_revision",
        ),
        Index(
            "ix_channel_sessions_org_state",
            "organization_id",
            "state",
            "deleted_at",
        ),
        Index(
            "ix_channel_sessions_connection_current",
            "connection_id",
            "session_revision",
            "deleted_at",
        ),
        Index(
            "ix_channel_sessions_lease",
            "lease_expires_at",
            "holder_runtime_id",
        ),
        Index(
            "ix_channel_sessions_pairing",
            "organization_id",
            "pairing_state",
            "pairing_expires_at",
        ),
        CheckConstraint(_in_clause("state", _SESSION_STATES), name="ck_channel_session_state"),
        CheckConstraint(
            _in_clause("pairing_state", _PAIRING_STATES),
            name="ck_channel_session_pairing_state",
        ),
        CheckConstraint(
            _in_clause("restart_policy", _RESTART_POLICIES),
            name="ck_channel_session_restart_policy",
        ),
        CheckConstraint(
            _in_clause("health_state", _HEALTH_STATES),
            name="ck_channel_session_health_state",
        ),
        CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_channel_session_health_score",
        ),
        CheckConstraint("session_revision > 0", name="ck_channel_session_revision_positive"),
        CheckConstraint("pairing_revision >= 0", name="ck_channel_session_pairing_non_negative"),
        CheckConstraint("fencing_token >= 0", name="ck_channel_session_fencing_non_negative"),
        CheckConstraint(
            "reconnect_attempts >= 0", name="ck_channel_session_reconnect_non_negative"
        ),
        CheckConstraint(
            "max_reconnect_attempts >= 0", name="ck_channel_session_max_reconnect_non_negative"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("channel_connections.id", ondelete="RESTRICT"), nullable=False
    )
    owner_user_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    secret_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("channel_secrets.id", ondelete="SET NULL"), nullable=True
    )
    session_revision: Mapped[int] = mapped_column(int_id(), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SessionState.REGISTERED.value
    )
    state_changed_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    state_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pairing_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PairingState.UNPAIRED.value
    )
    pairing_revision: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    pairing_changed_at: Mapped[datetime] = mapped_column(
        datetime6(), nullable=False
    )
    pairing_expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    pairing_reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    health_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ProviderHealthState.UNKNOWN.value
    )
    health_score: Mapped[int | None] = mapped_column(small_uint(), nullable=True)
    health_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    health_observed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    restart_policy: Mapped[str] = mapped_column(
        String(24), nullable=False, default=SessionRestartPolicy.NEVER.value
    )
    reconnect_attempts: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    max_reconnect_attempts: Mapped[int] = mapped_column(int_id(), nullable=False, default=3)
    next_restart_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    holder_runtime_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    fencing_token: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    capability_references_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    runtime_capabilities_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    recovery_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @validates("provider_metadata_json", "recovery_metadata_json")
    def _validate_non_secret_json(
        self, key: str, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            assert_no_secret_material(value, field_name=key)
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ChannelSession id={self.id} connection_id={self.connection_id} "
            f"revision={self.session_revision} state={self.state!r} secret=<reference-only>>"
        )
