"""Provider-neutral runtime and pairing contracts for M13-05.

The durable runtime authority remains :class:`ChannelSession`: leases, fencing, heartbeat,
health, lifecycle, restart and recovery facts are not duplicated here. Runtime registration is
process metadata validated against the existing provider/capability registries. Pairing persistence
records state, expiry and a constrained reason code only; no QR representation or provider secret is
modelled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError
from app.channels.validation import (
    normalize_capabilities,
    validate_connector_type,
    validate_text,
)

_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{1,119}$")


class PairingState(StrEnum):
    """Provider-neutral pairing attempt lifecycle without a QR payload representation."""

    UNPAIRED = "unpaired"
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_AVAILABLE = "pairing_available"
    PAIRING_EXPIRED = "pairing_expired"
    PAIRING_CANCELLED = "pairing_cancelled"
    PAIRED = "paired"


LEGAL_PAIRING_TRANSITIONS: dict[PairingState, frozenset[PairingState]] = {
    PairingState.UNPAIRED: frozenset({PairingState.PAIRING_REQUESTED}),
    PairingState.PAIRING_REQUESTED: frozenset(
        {
            PairingState.PAIRING_AVAILABLE,
            PairingState.PAIRING_CANCELLED,
        }
    ),
    PairingState.PAIRING_AVAILABLE: frozenset(
        {
            PairingState.PAIRING_EXPIRED,
            PairingState.PAIRING_CANCELLED,
            PairingState.PAIRED,
        }
    ),
    PairingState.PAIRING_EXPIRED: frozenset({PairingState.PAIRING_REQUESTED}),
    PairingState.PAIRING_CANCELLED: frozenset({PairingState.PAIRING_REQUESTED}),
    PairingState.PAIRED: frozenset(),
}


def can_transition_pairing(current: PairingState, target: PairingState) -> bool:
    """Return whether the provider-neutral pairing state machine permits the transition."""

    return target in LEGAL_PAIRING_TRANSITIONS[current]


def validate_reason_code(value: str, *, field_name: str = "reason_code") -> str:
    """Validate a redaction-safe machine reason instead of accepting arbitrary provider text."""

    normalized = value.strip().lower()
    if not _REASON_CODE.fullmatch(normalized):
        raise ChannelConfigError(
            f"{field_name} must be 2-120 lowercase letters, digits or underscores"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """Static runtime-host facts registered for one existing connector type.

    A registration does not create a provider adapter or durable runtime row. The connector must
    already exist in :class:`ProviderRegistry`, and runtime capabilities must be a subset of the
    provider's declared capabilities.
    """

    connector_type: str
    display_name: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    pairing_managed: bool = False
    pairing_ttl_seconds: int = 60
    heartbeat_interval_seconds: int = 30
    lease_seconds: int = 60

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_type", validate_connector_type(self.connector_type))
        object.__setattr__(
            self,
            "display_name",
            validate_text(self.display_name, field_name="display_name", max_length=120),
        )
        object.__setattr__(self, "capabilities", normalize_capabilities(self.capabilities))
        if self.pairing_ttl_seconds < 15 or self.pairing_ttl_seconds > 300:
            raise ChannelConfigError("pairing_ttl_seconds must be between 15 and 300")
        if self.heartbeat_interval_seconds < 5 or self.heartbeat_interval_seconds > 300:
            raise ChannelConfigError("heartbeat_interval_seconds must be between 5 and 300")
        if self.lease_seconds < self.heartbeat_interval_seconds or self.lease_seconds > 300:
            raise ChannelConfigError(
                "lease_seconds must be between heartbeat_interval_seconds and 300"
            )
        if self.pairing_managed and Capability.QR_AUTH not in self.capabilities:
            raise ChannelConfigError("pairing_managed runtimes must declare qr_auth")


class RuntimeEventType(StrEnum):
    """Safe control-plane event vocabulary introduced by the runtime foundation."""

    CAPABILITIES_PUBLISHED = "runtime.capabilities_published"
    PAIRING_STATE_CHANGED = "runtime.pairing_state_changed"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """Redacted runtime event suitable for Audit and a future internal event publisher."""

    event_type: RuntimeEventType
    organization_id: int
    session_public_id: str
    runtime_id: str
    occurred_at: datetime
    state: str | None = None
    capabilities: tuple[str, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.organization_id <= 0:
            raise ChannelConfigError("organization_id must be a positive integer")
        object.__setattr__(
            self,
            "session_public_id",
            validate_text(
                self.session_public_id,
                field_name="session_public_id",
                max_length=64,
            ),
        )
        object.__setattr__(
            self,
            "runtime_id",
            validate_text(self.runtime_id, field_name="runtime_id", max_length=160),
        )
        if self.reason_code is not None:
            object.__setattr__(self, "reason_code", validate_reason_code(self.reason_code))
        object.__setattr__(self, "capabilities", tuple(sorted(set(self.capabilities))))

    def audit_payload(self) -> dict[str, object]:
        """Return a fixed, secret-free payload; arbitrary provider metadata is not accepted."""

        return {
            "event_type": self.event_type.value,
            "session_public_id": self.session_public_id,
            "runtime_id": self.runtime_id,
            "occurred_at": self.occurred_at.isoformat(),
            "state": self.state,
            "capabilities": list(self.capabilities),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    """Permission-restricted, secret-free factual session diagnostics."""

    connector_type: str
    session_public_id: str
    session_revision: int
    session_state: str
    pairing_state: str
    pairing_revision: int
    runtime_id: str | None
    fencing_token: int
    lease_expires_at: datetime | None
    last_heartbeat_at: datetime | None
    health_state: str
    health_score: int | None
    reconnect_attempts: int
    max_reconnect_attempts: int
    restart_policy: str
    runtime_capabilities: tuple[str, ...]
    last_error_code: str | None
