"""Shared validation for provider-neutral channel contracts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError

if TYPE_CHECKING:
    from app.channels.foundation import (
        CommunicationIntent,
        CommunicationPolicy,
        PolicyEvaluation,
    )

_CONNECTOR_TYPE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def validate_connector_type(value: str) -> str:
    normalized = value.strip().lower()
    if not _CONNECTOR_TYPE.fullmatch(normalized):
        raise ChannelConfigError(
            "connector_type must be 2-64 lowercase letters, digits or underscores"
        )
    return normalized


def validate_text(value: str, *, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ChannelConfigError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ChannelConfigError(f"{field_name} must be at most {max_length} characters")
    return normalized


def validate_organization_id(value: int) -> None:
    if value <= 0:
        raise ChannelConfigError("organization_id must be a positive integer")


def validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ChannelConfigError(f"{field_name} must be timezone-aware")


def validate_score(value: int) -> None:
    if value < 0 or value > 100:
        raise ChannelConfigError("score must be between 0 and 100")


def validate_non_negative(value: int, *, field_name: str) -> None:
    if value < 0:
        raise ChannelConfigError(f"{field_name} must be zero or greater")


def normalize_capabilities(values: Iterable[Capability | str]) -> frozenset[Capability]:
    try:
        return frozenset(Capability(value) for value in values)
    except ValueError as exc:
        raise ChannelConfigError(f"Unknown channel capability: {exc}") from exc


def evaluate_communication_policy(
    intent: CommunicationIntent,
    policy: CommunicationPolicy,
    provider_capabilities: Iterable[Capability | str],
) -> PolicyEvaluation:
    """Evaluate intent and provider metadata without dispatching any communication."""
    from app.channels.foundation import PolicyEvaluation

    reasons: list[str] = []
    available = normalize_capabilities(provider_capabilities)
    required = intent.required_capabilities | policy.required_capabilities

    if not policy.enabled:
        reasons.append("policy_disabled")
    if policy.organization_id is not None and policy.organization_id != intent.organization_id:
        reasons.append("organization_scope_mismatch")
    if intent.channel_type not in policy.allowed_channel_types:
        reasons.append("channel_not_allowed")
    if intent.purpose not in policy.allowed_purposes:
        reasons.append("purpose_not_allowed")
    if intent.origin not in policy.allowed_origins:
        reasons.append("origin_not_allowed")
    if intent.bulk and not policy.allow_bulk:
        reasons.append("bulk_not_allowed")

    missing = required - available
    if missing:
        reasons.append("missing_capabilities")

    return PolicyEvaluation(
        allowed=not reasons,
        reasons=tuple(reasons),
        missing_capabilities=frozenset(missing),
    )
