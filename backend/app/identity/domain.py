"""Immutable identity vocabulary, normalization and exact-key validation for M13-02.

Resolution is intentionally exact. Display names, profile names, avatars and email similarity are
never identity evidence. Provider namespaces are registered in a small provider-independent
normalizer registry so future providers add vocabulary without changing the resolver architecture.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock

from app.channels.validation import validate_connector_type, validate_text

_NAMESPACE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,189}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

PHONE_IDENTITY_NAMESPACES = frozenset({"whatsapp_phone", "sms_phone"})
APPROVED_IDENTITY_NAMESPACES = frozenset(
    {
        "whatsapp_phone",
        "whatsapp_lid",
        "whatsapp_jid",
        "instagram_user",
        "messenger_psid",
        "telegram_user",
        "sms_phone",
    }
)


class IdentityKind(StrEnum):
    PROVIDER = "provider"
    ENDPOINT = "endpoint"


class IdentityConfidence(StrEnum):
    """Factual confidence categories; no fuzzy or synthetic score is inferred."""

    AUTHORITATIVE = "authoritative"
    VERIFIED = "verified"
    CANDIDATE = "candidate"
    CONFLICTED = "conflicted"


class IdentitySource(StrEnum):
    PROVIDER = "provider"
    OPERATOR = "operator"
    CANONICAL_PHONE = "canonical_phone"


class IdentityResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    CREATED = "created"
    CONFLICT = "conflict"
    REVIEW_REQUIRED = "review_required"


class IdentityConflictStatus(StrEnum):
    OPEN = "open"
    RECOMMENDED = "recommended"
    RECOMMENDATION_APPROVED = "recommendation_approved"
    RECOMMENDATION_REJECTED = "recommendation_rejected"


class IdentityMergeRecommendationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class _NamespaceSpec:
    normalizer: Callable[[str], str]
    global_scope: bool


@dataclass(frozen=True, slots=True)
class NormalizedIdentity:
    identity_namespace: str
    identity_scope: str
    normalized_value: str
    identity_kind: IdentityKind
    connector_type: str | None
    connection_ref: str | None
    endpoint_ref: str | None
    source: IdentitySource
    confidence: IdentityConfidence

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.identity_namespace, self.identity_scope, self.normalized_value)

    @property
    def phone_e164(self) -> str | None:
        return (
            self.normalized_value if self.identity_namespace in PHONE_IDENTITY_NAMESPACES else None
        )

    @property
    def wa_id(self) -> str | None:
        return self.normalized_value[1:] if self.identity_namespace == "whatsapp_phone" else None

    def evidence(self) -> dict[str, str | None]:
        return {
            "identity_namespace": self.identity_namespace,
            "identity_scope": self.identity_scope,
            "normalized_value": self.normalized_value,
            "identity_kind": self.identity_kind.value,
            "connector_type": self.connector_type,
            "connection_ref": self.connection_ref,
            "endpoint_ref": self.endpoint_ref,
            "source": self.source.value,
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True, slots=True)
class IdentityAssertion:
    identity_namespace: str
    identity_scope: str
    value: str
    identity_kind: IdentityKind = IdentityKind.PROVIDER
    connector_type: str | None = None
    connection_ref: str | None = None
    endpoint_ref: str | None = None
    source: IdentitySource = IdentitySource.PROVIDER
    confidence: IdentityConfidence = IdentityConfidence.AUTHORITATIVE


class IdentityNormalizerRegistry:
    """Thread-safe namespace registry used by every provider-neutral resolution request."""

    def __init__(self) -> None:
        self._specs: dict[str, _NamespaceSpec] = {}
        self._lock = RLock()

    def register(
        self,
        namespace: str,
        normalizer: Callable[[str], str],
        *,
        global_scope: bool,
        replace: bool = False,
    ) -> None:
        normalized_namespace = _validate_namespace(namespace)
        with self._lock:
            if normalized_namespace in self._specs and not replace:
                raise ValueError(
                    f"identity namespace {normalized_namespace!r} is already registered"
                )
            self._specs[normalized_namespace] = _NamespaceSpec(normalizer, global_scope)

    def namespaces(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._specs))

    def normalize(self, assertion: IdentityAssertion) -> NormalizedIdentity:
        namespace = _validate_namespace(assertion.identity_namespace)
        with self._lock:
            spec = self._specs.get(namespace)
        if spec is None:
            raise ValueError(f"identity namespace {namespace!r} is not approved")

        scope = _validate_scope(assertion.identity_scope)
        if spec.global_scope and scope != "global":
            raise ValueError(f"{namespace} identities must use the global scope")
        if not spec.global_scope and scope == "global":
            raise ValueError(f"{namespace} identities require an explicit provider scope")

        connection_ref = _optional_reference(assertion.connection_ref, "connection_ref")
        endpoint_ref = _optional_reference(assertion.endpoint_ref, "endpoint_ref")
        if endpoint_ref is not None and connection_ref is None:
            raise ValueError("endpoint_ref requires connection_ref")
        if assertion.identity_kind is IdentityKind.ENDPOINT and (
            connection_ref is None or endpoint_ref is None
        ):
            raise ValueError("endpoint identities require connection_ref and endpoint_ref")

        connector_type = (
            validate_connector_type(assertion.connector_type)
            if assertion.connector_type is not None
            else None
        )
        normalized_value = spec.normalizer(assertion.value)
        return NormalizedIdentity(
            identity_namespace=namespace,
            identity_scope=scope,
            normalized_value=normalized_value,
            identity_kind=IdentityKind(assertion.identity_kind),
            connector_type=connector_type,
            connection_ref=connection_ref,
            endpoint_ref=endpoint_ref,
            source=IdentitySource(assertion.source),
            confidence=IdentityConfidence(assertion.confidence),
        )


def _validate_namespace(value: str) -> str:
    normalized = value.strip().lower()
    if not _NAMESPACE.fullmatch(normalized):
        raise ValueError("identity_namespace must be lowercase snake_case")
    return normalized


def _validate_scope(value: str) -> str:
    normalized = value.strip()
    if not _SCOPE.fullmatch(normalized):
        raise ValueError("identity_scope contains unsupported characters")
    return normalized


def _optional_reference(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return validate_text(value, field_name=field_name, max_length=120)


def _normalize_phone(value: str) -> str:
    normalized = re.sub(r"[\s().-]", "", value.strip())
    if not _E164.fullmatch(normalized):
        raise ValueError("telephone identity must be E.164, e.g. +14155552671")
    return normalized


def _normalize_opaque(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip())
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("identity value contains control characters")
    return validate_text(normalized, field_name="identity value", max_length=190)


def _normalize_whatsapp_jid(value: str) -> str:
    """Preserve a provider-native WhatsApp phone JID without treating it as E.164.

    ``@c.us`` and ``@s.whatsapp.net`` are distinct provider routing representations even when
    their digit component is the same.  LIDs intentionally use the separately governed
    ``whatsapp_lid`` namespace.
    """

    normalized = _normalize_opaque(value)
    if not re.fullmatch(r"[1-9]\d{7,18}@(c\.us|s\.whatsapp\.net)", normalized):
        raise ValueError("WhatsApp JID must be a direct @c.us or @s.whatsapp.net address")
    return normalized


def _build_default_registry() -> IdentityNormalizerRegistry:
    registry = IdentityNormalizerRegistry()
    registry.register("whatsapp_phone", _normalize_phone, global_scope=True)
    registry.register("sms_phone", _normalize_phone, global_scope=True)
    registry.register("whatsapp_lid", _normalize_opaque, global_scope=False)
    registry.register("whatsapp_jid", _normalize_whatsapp_jid, global_scope=False)
    registry.register("instagram_user", _normalize_opaque, global_scope=False)
    registry.register("messenger_psid", _normalize_opaque, global_scope=False)
    registry.register("telegram_user", _normalize_opaque, global_scope=False)
    return registry


default_identity_normalizers = _build_default_registry()
