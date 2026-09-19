"""Provider-neutral omnichannel control-plane domain contracts.

M13-01 deliberately defines immutable in-process contracts only. Persistence remains with the
existing owning modules and provider execution remains behind :class:`ChannelAdapter`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.channels.capabilities import Capability, ChannelType
from app.channels.validation import (
    normalize_capabilities,
    validate_aware_datetime,
    validate_connector_type,
    validate_non_negative,
    validate_organization_id,
    validate_score,
    validate_text,
)


class CommunicationPurpose(StrEnum):
    """Business purpose of a provider-independent communication request."""

    SERVICE = "service"
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    AUTHENTICATION = "authentication"


class CommunicationOrigin(StrEnum):
    """Repository authority that created a communication intent."""

    MANUAL = "manual"
    API = "api"
    CAMPAIGN = "campaign"
    AUTOMATION = "automation"
    SYSTEM = "system"


class ProviderHealthState(StrEnum):
    """Provider-independent observed health state."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ProviderDesiredState(StrEnum):
    """Operator/configuration intent for a future channel connection."""

    ENABLED = "enabled"
    PAUSED = "paused"
    DISABLED = "disabled"


class ProviderObservedState(StrEnum):
    """Provider-independent state observed by the control plane."""

    UNKNOWN = "unknown"
    UNCONFIGURED = "unconfigured"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    AUTHENTICATION_REQUIRED = "authentication_required"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ChannelMetadata:
    """Static, factual metadata declared by a provider adapter."""

    connector_type: str
    channel_type: ChannelType
    display_name: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    lifecycle_managed: bool = False
    health_managed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_type", validate_connector_type(self.connector_type))
        object.__setattr__(
            self,
            "display_name",
            validate_text(self.display_name, field_name="display_name", max_length=100),
        )
        object.__setattr__(self, "capabilities", normalize_capabilities(self.capabilities))


@dataclass(frozen=True, slots=True)
class CommunicationIntent:
    """Provider-independent request description; it does not send a message."""

    organization_id: int
    intent_key: str
    channel_type: ChannelType
    purpose: CommunicationPurpose
    origin: CommunicationOrigin
    required_capabilities: frozenset[Capability] = field(default_factory=frozenset)
    bulk: bool = False

    def __post_init__(self) -> None:
        validate_organization_id(self.organization_id)
        object.__setattr__(
            self,
            "intent_key",
            validate_text(self.intent_key, field_name="intent_key", max_length=120),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            normalize_capabilities(self.required_capabilities),
        )


@dataclass(frozen=True, slots=True)
class CommunicationPolicy:
    """Organization-aware constraints evaluated before future provider selection."""

    policy_key: str
    organization_id: int | None = None
    allowed_channel_types: frozenset[ChannelType] = field(
        default_factory=lambda: frozenset(ChannelType)
    )
    allowed_purposes: frozenset[CommunicationPurpose] = field(
        default_factory=lambda: frozenset(CommunicationPurpose)
    )
    allowed_origins: frozenset[CommunicationOrigin] = field(
        default_factory=lambda: frozenset(CommunicationOrigin)
    )
    required_capabilities: frozenset[Capability] = field(default_factory=frozenset)
    allow_bulk: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_key",
            validate_text(self.policy_key, field_name="policy_key", max_length=120),
        )
        if self.organization_id is not None:
            validate_organization_id(self.organization_id)
        if not self.allowed_channel_types:
            raise ValueError("allowed_channel_types must not be empty")
        if not self.allowed_purposes:
            raise ValueError("allowed_purposes must not be empty")
        if not self.allowed_origins:
            raise ValueError("allowed_origins must not be empty")
        object.__setattr__(
            self,
            "allowed_channel_types",
            frozenset(ChannelType(value) for value in self.allowed_channel_types),
        )
        object.__setattr__(
            self,
            "allowed_purposes",
            frozenset(CommunicationPurpose(value) for value in self.allowed_purposes),
        )
        object.__setattr__(
            self,
            "allowed_origins",
            frozenset(CommunicationOrigin(value) for value in self.allowed_origins),
        )
        object.__setattr__(
            self, "required_capabilities", normalize_capabilities(self.required_capabilities)
        )


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """Factual policy result; callers decide how to present or enforce it."""

    allowed: bool
    reasons: tuple[str, ...] = ()
    missing_capabilities: frozenset[Capability] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Provider-neutral health snapshot; no synthetic score is inferred."""

    connector_type: str
    state: ProviderHealthState
    observed_at: datetime
    detail: str | None = None
    score: int | None = None
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_type", validate_connector_type(self.connector_type))
        validate_aware_datetime(self.observed_at, field_name="observed_at")
        if self.detail is not None:
            object.__setattr__(
                self,
                "detail",
                validate_text(self.detail, field_name="detail", max_length=500),
            )
        if self.score is not None:
            validate_score(self.score)
        if self.retry_after_seconds is not None:
            validate_non_negative(self.retry_after_seconds, field_name="retry_after_seconds")


@dataclass(frozen=True, slots=True)
class ProviderLifecycle:
    """Desired and observed provider lifecycle state without executing a runtime."""

    connector_type: str
    desired_state: ProviderDesiredState
    observed_state: ProviderObservedState
    observed_at: datetime
    detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_type", validate_connector_type(self.connector_type))
        validate_aware_datetime(self.observed_at, field_name="observed_at")
        if self.detail is not None:
            object.__setattr__(
                self,
                "detail",
                validate_text(self.detail, field_name="detail", max_length=500),
            )
