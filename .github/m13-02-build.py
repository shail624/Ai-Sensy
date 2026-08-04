from __future__ import annotations

import sys
import textwrap
from pathlib import Path

root = Path(sys.argv[1]).resolve()

files: dict[str, str] = {}

files["backend/app/identity/__init__.py"] = '''
"""Provider-independent Customer identity resolution layer (M13-02)."""

from app.identity.domain import (
    APPROVED_IDENTITY_NAMESPACES,
    PHONE_IDENTITY_NAMESPACES,
    IdentityAssertion,
    IdentityConfidence,
    IdentityConflictStatus,
    IdentityKind,
    IdentityMergeRecommendationStatus,
    IdentityNormalizerRegistry,
    IdentityResolutionStatus,
    IdentitySource,
    NormalizedIdentity,
    default_identity_normalizers,
)

__all__ = [
    "APPROVED_IDENTITY_NAMESPACES",
    "PHONE_IDENTITY_NAMESPACES",
    "IdentityAssertion",
    "IdentityConfidence",
    "IdentityConflictStatus",
    "IdentityKind",
    "IdentityMergeRecommendationStatus",
    "IdentityNormalizerRegistry",
    "IdentityResolutionStatus",
    "IdentitySource",
    "NormalizedIdentity",
    "default_identity_normalizers",
]
'''

files["backend/app/identity/domain.py"] = '''
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
        return self.normalized_value if self.identity_namespace in PHONE_IDENTITY_NAMESPACES else None

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
                raise ValueError(f"identity namespace {normalized_namespace!r} is already registered")
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


def _build_default_registry() -> IdentityNormalizerRegistry:
    registry = IdentityNormalizerRegistry()
    registry.register("whatsapp_phone", _normalize_phone, global_scope=True)
    registry.register("sms_phone", _normalize_phone, global_scope=True)
    registry.register("whatsapp_lid", _normalize_opaque, global_scope=False)
    registry.register("instagram_user", _normalize_opaque, global_scope=False)
    registry.register("messenger_psid", _normalize_opaque, global_scope=False)
    registry.register("telegram_user", _normalize_opaque, global_scope=False)
    return registry


default_identity_normalizers = _build_default_registry()
'''

files["backend/app/identity/flags.py"] = '''
"""M13-02 feature flag resolved through the existing server-owned FeatureFlag authority."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.settings import FeatureFlag

IDENTITY_RESOLUTION_FLAG = "omnichannel_identity_resolution"


class IdentityResolutionFeatureFlag:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_enabled(self, organization_id: int) -> bool:
        rows = list(
            (
                await self._session.scalars(
                    select(FeatureFlag).where(
                        FeatureFlag.key_name == IDENTITY_RESOLUTION_FLAG,
                        or_(
                            FeatureFlag.organization_id.is_(None),
                            FeatureFlag.organization_id == organization_id,
                        ),
                    )
                )
            ).all()
        )
        enabled = False
        for row in rows:
            if row.organization_id is None:
                enabled = row.is_enabled
        for row in rows:
            if row.organization_id == organization_id:
                enabled = row.is_enabled
        return enabled

    async def require_enabled(self, organization_id: int) -> None:
        if not await self.is_enabled(organization_id):
            raise NotFoundError("Customer identity resolution is not enabled.")
'''

files["backend/app/models/contact_identity.py"] = '''
"""Immutable Contact aliases and restricted identity-conflict review records (M13-02)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import AuditMixin, IntPKMixin, TimestampMixin, UUIDMixin, VersionMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6
from app.identity.domain import (
    IdentityConfidence,
    IdentityConflictStatus,
    IdentityKind,
    IdentityMergeRecommendationStatus,
    IdentitySource,
)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


IDENTITY_KINDS = tuple(value.value for value in IdentityKind)
IDENTITY_CONFIDENCES = tuple(value.value for value in IdentityConfidence)
IDENTITY_SOURCES = tuple(value.value for value in IdentitySource)
IDENTITY_CONFLICT_STATUSES = tuple(value.value for value in IdentityConflictStatus)
IDENTITY_RECOMMENDATION_STATUSES = tuple(
    value.value for value in IdentityMergeRecommendationStatus
)


class ContactIdentity(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, Base):
    """One immutable exact identity key owned by one canonical Contact for its full history."""

    __tablename__ = "contact_identities"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "identity_namespace",
            "identity_scope",
            "normalized_value",
            name="uq_contact_identity_exact_key",
        ),
        Index(
            "ix_contact_identities_org_contact_created",
            "organization_id",
            "contact_id",
            "created_at",
        ),
        Index(
            "ix_contact_identities_org_endpoint",
            "organization_id",
            "connection_ref",
            "endpoint_ref",
        ),
        CheckConstraint(_in_clause("identity_kind", IDENTITY_KINDS), name="ck_identity_kind"),
        CheckConstraint(
            _in_clause("confidence", IDENTITY_CONFIDENCES), name="ck_identity_confidence"
        ),
        CheckConstraint(_in_clause("source", IDENTITY_SOURCES), name="ck_identity_source"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    identity_namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_scope: Mapped[str] = mapped_column(String(190), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(190), nullable=False)
    identity_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    connector_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    connection_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    endpoint_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[str] = mapped_column(String(24), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class IdentityConflict(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    """Restricted, non-destructive review item for conflicting or insufficient exact evidence."""

    __tablename__ = "identity_conflicts"
    __table_args__ = (
        UniqueConstraint("organization_id", "fingerprint", name="uq_identity_conflict_fingerprint"),
        Index(
            "ix_identity_conflicts_org_status_created",
            "organization_id",
            "status",
            "created_at",
        ),
        CheckConstraint(
            _in_clause("status", IDENTITY_CONFLICT_STATUSES), name="ck_identity_conflict_status"
        ),
        CheckConstraint(
            _in_clause("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_conflict_confidence",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(24), nullable=False)
    assertion_keys_json: Mapped[list[dict[str, str | None]]] = mapped_column(JSON, nullable=False)
    candidate_contact_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    decision_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    decision_by: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IdentityMergeRecommendation(
    IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base
):
    """An operator-authored recommendation. Approval records a decision but never merges Contacts."""

    __tablename__ = "identity_merge_recommendations"
    __table_args__ = (
        Index(
            "ix_identity_recommendations_org_conflict_status",
            "organization_id",
            "conflict_id",
            "status",
        ),
        CheckConstraint(
            _in_clause("status", IDENTITY_RECOMMENDATION_STATUSES),
            name="ck_identity_recommendation_status",
        ),
        CheckConstraint(
            _in_clause("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_recommendation_confidence",
        ),
        CheckConstraint(
            "primary_contact_id <> duplicate_contact_id",
            name="ck_identity_recommendation_distinct_contacts",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    conflict_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("identity_conflicts.id", ondelete="CASCADE"), nullable=False
    )
    primary_contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    duplicate_contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
'''

files["backend/app/repositories/contact_identity.py"] = '''
"""Tenant-scoped persistence queries for M13-02 identity records."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact_identity import (
    ContactIdentity,
    IdentityConflict,
    IdentityMergeRecommendation,
)
from app.repositories.base import BaseRepository


class ContactIdentityRepository(BaseRepository[ContactIdentity]):
    model = ContactIdentity

    async def get_exact(
        self,
        organization_id: int,
        identity_namespace: str,
        identity_scope: str,
        normalized_value: str,
    ) -> ContactIdentity | None:
        stmt = select(ContactIdentity).where(
            ContactIdentity.organization_id == organization_id,
            ContactIdentity.identity_namespace == identity_namespace,
            ContactIdentity.identity_scope == identity_scope,
            ContactIdentity.normalized_value == normalized_value,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_contact(
        self, organization_id: int, contact_id: int
    ) -> list[ContactIdentity]:
        stmt = (
            select(ContactIdentity)
            .where(
                ContactIdentity.organization_id == organization_id,
                ContactIdentity.contact_id == contact_id,
            )
            .order_by(ContactIdentity.created_at.asc(), ContactIdentity.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())


class IdentityConflictRepository(BaseRepository[IdentityConflict]):
    model = IdentityConflict

    async def get_scoped(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> IdentityConflict | None:
        stmt = select(IdentityConflict).where(
            IdentityConflict.organization_id == organization_id,
            IdentityConflict.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_fingerprint(
        self, organization_id: int, fingerprint: str
    ) -> IdentityConflict | None:
        stmt = select(IdentityConflict).where(
            IdentityConflict.organization_id == organization_id,
            IdentityConflict.fingerprint == fingerprint,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_scoped(
        self,
        organization_id: int,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[IdentityConflict]:
        stmt = select(IdentityConflict).where(IdentityConflict.organization_id == organization_id)
        if status is not None:
            stmt = stmt.where(IdentityConflict.status == status)
        stmt = stmt.order_by(IdentityConflict.created_at.desc(), IdentityConflict.id.desc())
        return list((await self.session.scalars(stmt.limit(limit).offset(offset))).all())

    async def count_scoped(self, organization_id: int, *, status: str | None) -> int:
        stmt = select(func.count()).select_from(IdentityConflict).where(
            IdentityConflict.organization_id == organization_id
        )
        if status is not None:
            stmt = stmt.where(IdentityConflict.status == status)
        return int((await self.session.scalar(stmt)) or 0)


class IdentityRecommendationRepository(BaseRepository[IdentityMergeRecommendation]):
    model = IdentityMergeRecommendation

    async def get_scoped(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> IdentityMergeRecommendation | None:
        stmt = select(IdentityMergeRecommendation).where(
            IdentityMergeRecommendation.organization_id == organization_id,
            IdentityMergeRecommendation.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_conflict(
        self, organization_id: int, conflict_id: int
    ) -> list[IdentityMergeRecommendation]:
        stmt = (
            select(IdentityMergeRecommendation)
            .where(
                IdentityMergeRecommendation.organization_id == organization_id,
                IdentityMergeRecommendation.conflict_id == conflict_id,
            )
            .order_by(
                IdentityMergeRecommendation.created_at.asc(),
                IdentityMergeRecommendation.id.asc(),
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def pending_for_conflict(
        self, organization_id: int, conflict_id: int
    ) -> IdentityMergeRecommendation | None:
        stmt = select(IdentityMergeRecommendation).where(
            IdentityMergeRecommendation.organization_id == organization_id,
            IdentityMergeRecommendation.conflict_id == conflict_id,
            IdentityMergeRecommendation.status == "pending",
        )
        return (await self.session.scalars(stmt)).first()
'''

files["backend/app/services/identity_resolution_service.py"] = '''
"""Exact, tenant-scoped Customer identity resolution without destructive merge behavior."""

from __future__ import annotations

import hashlib
import json
import uuid as uuidlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.identity.domain import (
    IdentityAssertion,
    IdentityConfidence,
    IdentityConflictStatus,
    IdentityMergeRecommendationStatus,
    IdentityNormalizerRegistry,
    IdentityResolutionStatus,
    NormalizedIdentity,
    default_identity_normalizers,
)
from app.identity.flags import IdentityResolutionFeatureFlag
from app.models.contact import OPT_IN_UNKNOWN, Contact
from app.models.contact_event import (
    EVENT_IDENTITY_CONFLICT_DETECTED,
    EVENT_IDENTITY_LINKED,
    EVENT_IDENTITY_RECOMMENDATION_APPROVED,
    EVENT_IDENTITY_RECOMMENDATION_CREATED,
    EVENT_IDENTITY_RECOMMENDATION_REJECTED,
    REF_TYPE_CONTACT_IDENTITY,
    REF_TYPE_IDENTITY_CONFLICT,
    REF_TYPE_IDENTITY_RECOMMENDATION,
)
from app.models.contact_identity import (
    ContactIdentity,
    IdentityConflict,
    IdentityMergeRecommendation,
)
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.contact_identity import (
    ContactIdentityRepository,
    IdentityConflictRepository,
    IdentityRecommendationRepository,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService
from app.services.contact_service import ContactService


@dataclass(slots=True)
class IdentityResolutionResult:
    status: IdentityResolutionStatus
    contact: Contact | None
    identities: list[ContactIdentity]
    conflict: IdentityConflict | None
    created_contact: bool
    reasons: tuple[str, ...]


@dataclass(slots=True)
class IdentityRecommendationView:
    recommendation: IdentityMergeRecommendation
    primary_contact_id: str
    duplicate_contact_id: str


@dataclass(slots=True)
class IdentityConflictView:
    conflict: IdentityConflict
    recommendations: list[IdentityRecommendationView]


class IdentityResolutionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        normalizers: IdentityNormalizerRegistry = default_identity_normalizers,
    ) -> None:
        self._session = session
        self._normalizers = normalizers
        self._identities = ContactIdentityRepository(session)
        self._conflicts = IdentityConflictRepository(session)
        self._recommendations = IdentityRecommendationRepository(session)
        self._contacts = ContactRepository(session)
        self._contact_service = ContactService(session)
        self._events = ContactEventService(session)
        self._audit = AuditService(session)
        self._flag = IdentityResolutionFeatureFlag(session)

    async def resolve(
        self,
        *,
        organization_id: int,
        actor: User,
        assertions: list[IdentityAssertion],
        contact_hint: uuidlib.UUID | None,
        new_contact_fields: dict[str, Any] | None,
    ) -> IdentityResolutionResult:
        await self._flag.require_enabled(organization_id)
        if not assertions:
            raise BadRequestError("At least one identity assertion is required.")
        normalized = self._normalize_unique(assertions)

        existing: dict[tuple[str, str, str], ContactIdentity] = {}
        candidates: dict[int, Contact] = {}
        for identity in normalized:
            row = await self._identities.get_exact(organization_id, *identity.key)
            if row is not None:
                existing[identity.key] = row
                contact = await self._active_contact(organization_id, row.contact_id)
                if contact is None:
                    raise ConflictError("Identity ownership points to an unavailable Contact.")
                candidates[contact.id] = contact
            if identity.wa_id is not None:
                phone_contact = await self._contacts.get_active_by_wa_id(
                    organization_id, identity.wa_id
                )
                if phone_contact is not None:
                    candidates[phone_contact.id] = phone_contact

        if contact_hint is not None:
            hinted = await self._contact_service.get_contact(organization_id, contact_hint)
            candidates[hinted.id] = hinted

        if len(candidates) > 1:
            conflict = await self._record_conflict(
                organization_id=organization_id,
                actor=actor,
                normalized=normalized,
                candidates=list(candidates.values()),
                reason_code="multiple_authoritative_contacts",
            )
            await self._session.commit()
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.CONFLICT,
                contact=None,
                identities=list(existing.values()),
                conflict=conflict,
                created_contact=False,
                reasons=("Exact evidence resolves to multiple Contacts; operator review is required.",),
            )

        created_contact = False
        contact = next(iter(candidates.values()), None)
        if contact is None:
            phones = {identity.phone_e164 for identity in normalized if identity.phone_e164}
            if len(phones) != 1:
                reason = (
                    "multiple_unlinked_phone_identities"
                    if len(phones) > 1
                    else "no_authoritative_contact"
                )
                conflict = await self._record_conflict(
                    organization_id=organization_id,
                    actor=actor,
                    normalized=normalized,
                    candidates=[],
                    reason_code=reason,
                )
                await self._session.commit()
                return IdentityResolutionResult(
                    status=IdentityResolutionStatus.REVIEW_REQUIRED,
                    contact=None,
                    identities=[],
                    conflict=conflict,
                    created_contact=False,
                    reasons=(
                        "No exact canonical Contact can be established without operator evidence.",
                    ),
                )

            phone_e164 = next(iter(phones))
            try:
                contact = await self._contact_service.create_contact(
                    organization_id=organization_id,
                    actor=actor,
                    phone_e164=phone_e164,
                    opt_in_status=OPT_IN_UNKNOWN,
                    source="identity_resolution",
                    fields=new_contact_fields or {},
                )
                created_contact = True
            except ConflictError:
                wa_id = phone_e164[1:]
                contact = await self._contacts.get_active_by_wa_id(organization_id, wa_id)
                if contact is None:
                    raise

        linked: list[ContactIdentity] = []
        for identity in normalized:
            current = await self._identities.get_exact(organization_id, *identity.key)
            if current is not None:
                if current.contact_id != contact.id:
                    other = await self._active_contact(organization_id, current.contact_id)
                    conflict_candidates = [contact]
                    if other is not None:
                        conflict_candidates.append(other)
                    conflict = await self._record_conflict(
                        organization_id=organization_id,
                        actor=actor,
                        normalized=normalized,
                        candidates=conflict_candidates,
                        reason_code="identity_ownership_changed",
                    )
                    await self._session.commit()
                    return IdentityResolutionResult(
                        status=IdentityResolutionStatus.CONFLICT,
                        contact=None,
                        identities=[current],
                        conflict=conflict,
                        created_contact=created_contact,
                        reasons=("Identity ownership changed during resolution; no alias was moved.",),
                    )
                linked.append(current)
                continue
            linked.append(
                await self._link_identity(
                    organization_id=organization_id,
                    actor=actor,
                    contact=contact,
                    identity=identity,
                )
            )

        await self._session.commit()
        return IdentityResolutionResult(
            status=(
                IdentityResolutionStatus.CREATED
                if created_contact
                else IdentityResolutionStatus.RESOLVED
            ),
            contact=contact,
            identities=linked,
            conflict=None,
            created_contact=created_contact,
            reasons=(),
        )

    async def list_contact_identities(
        self, organization_id: int, contact_id: uuidlib.UUID
    ) -> tuple[Contact, list[ContactIdentity]]:
        await self._flag.require_enabled(organization_id)
        contact = await self._contact_service.get_contact(organization_id, contact_id)
        return contact, await self._identities.list_for_contact(organization_id, contact.id)

    async def list_conflicts(
        self,
        organization_id: int,
        *,
        status: IdentityConflictStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[IdentityConflictView], int]:
        await self._flag.require_enabled(organization_id)
        rows = await self._conflicts.list_scoped(
            organization_id,
            status=status.value if status is not None else None,
            limit=limit,
            offset=offset,
        )
        views = [await self._conflict_view(organization_id, row) for row in rows]
        total = await self._conflicts.count_scoped(
            organization_id, status=status.value if status is not None else None
        )
        return views, total

    async def get_conflict(
        self, organization_id: int, conflict_id: uuidlib.UUID
    ) -> IdentityConflictView:
        await self._flag.require_enabled(organization_id)
        conflict = await self._conflicts.get_scoped(organization_id, conflict_id)
        if conflict is None:
            raise NotFoundError("Identity conflict not found.")
        return await self._conflict_view(organization_id, conflict)

    async def recommend_merge(
        self,
        *,
        organization_id: int,
        actor: User,
        conflict_id: uuidlib.UUID,
        primary_contact_id: uuidlib.UUID,
        duplicate_contact_id: uuidlib.UUID,
        confidence: IdentityConfidence,
        reason: str,
    ) -> IdentityRecommendationView:
        await self._flag.require_enabled(organization_id)
        conflict = await self._conflicts.get_scoped(organization_id, conflict_id)
        if conflict is None:
            raise NotFoundError("Identity conflict not found.")
        if await self._recommendations.pending_for_conflict(organization_id, conflict.id):
            raise ConflictError("This conflict already has a pending recommendation.")

        primary = await self._contact_service.get_contact(organization_id, primary_contact_id)
        duplicate = await self._contact_service.get_contact(organization_id, duplicate_contact_id)
        if primary.id == duplicate.id:
            raise BadRequestError("Primary and duplicate Contacts must be different.")
        allowed = set(conflict.candidate_contact_ids_json)
        if primary.public_id not in allowed or duplicate.public_id not in allowed:
            raise BadRequestError("Recommendation Contacts must belong to the conflict evidence.")
        if confidence in {IdentityConfidence.CONFLICTED, IdentityConfidence.AUTHORITATIVE}:
            raise BadRequestError("Recommendation confidence must be verified or candidate.")

        recommendation = IdentityMergeRecommendation(
            organization_id=organization_id,
            conflict_id=conflict.id,
            primary_contact_id=primary.id,
            duplicate_contact_id=duplicate.id,
            confidence=confidence.value,
            reason=reason,
            status=IdentityMergeRecommendationStatus.PENDING.value,
            created_by=actor.id,
        )
        await self._recommendations.add(recommendation)
        conflict.status = IdentityConflictStatus.RECOMMENDED.value
        conflict.updated_by = actor.id
        conflict.row_version += 1
        await self._audit.record(
            AuditAction.IDENTITY_MERGE_RECOMMENDATION_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="identity_merge_recommendation",
            entity_id=recommendation.id,
            after={
                "conflict_id": conflict.public_id,
                "primary_contact_id": primary.public_id,
                "duplicate_contact_id": duplicate.public_id,
                "confidence": confidence.value,
                "merge_executed": False,
            },
        )
        for contact in (primary, duplicate):
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_IDENTITY_RECOMMENDATION_CREATED,
                ref_type=REF_TYPE_IDENTITY_RECOMMENDATION,
                ref_id=recommendation.id,
                payload={"conflict_id": conflict.public_id, "merge_executed": False},
            )
        await self._session.commit()
        return IdentityRecommendationView(
            recommendation=recommendation,
            primary_contact_id=primary.public_id,
            duplicate_contact_id=duplicate.public_id,
        )

    async def decide_recommendation(
        self,
        *,
        organization_id: int,
        actor: User,
        recommendation_id: uuidlib.UUID,
        approve: bool,
        expected_version: int,
        note: str | None,
    ) -> IdentityRecommendationView:
        await self._flag.require_enabled(organization_id)
        recommendation = await self._recommendations.get_scoped(
            organization_id, recommendation_id
        )
        if recommendation is None:
            raise NotFoundError("Identity merge recommendation not found.")
        if recommendation.row_version != expected_version:
            raise VersionConflictError("The recommendation changed; reload and retry.")
        if recommendation.status != IdentityMergeRecommendationStatus.PENDING.value:
            raise ConflictError("This recommendation already has an operator decision.")
        conflict = await self._conflicts.get_by_id(recommendation.conflict_id)
        if conflict is None or conflict.organization_id != organization_id:
            raise NotFoundError("Identity conflict not found.")
        primary = await self._active_contact(organization_id, recommendation.primary_contact_id)
        duplicate = await self._active_contact(organization_id, recommendation.duplicate_contact_id)
        if primary is None or duplicate is None:
            raise ConflictError("Recommendation Contact evidence is no longer available.")

        now = utcnow()
        status = (
            IdentityMergeRecommendationStatus.APPROVED
            if approve
            else IdentityMergeRecommendationStatus.REJECTED
        )
        recommendation.status = status.value
        recommendation.decided_at = now
        recommendation.decided_by = actor.id
        recommendation.decision_note = note
        recommendation.updated_by = actor.id
        recommendation.row_version += 1
        conflict.status = (
            IdentityConflictStatus.RECOMMENDATION_APPROVED.value
            if approve
            else IdentityConflictStatus.RECOMMENDATION_REJECTED.value
        )
        conflict.decision_at = now
        conflict.decision_by = actor.id
        conflict.review_note = note
        conflict.updated_by = actor.id
        conflict.row_version += 1

        action = (
            AuditAction.IDENTITY_MERGE_RECOMMENDATION_APPROVED
            if approve
            else AuditAction.IDENTITY_MERGE_RECOMMENDATION_REJECTED
        )
        event_type = (
            EVENT_IDENTITY_RECOMMENDATION_APPROVED
            if approve
            else EVENT_IDENTITY_RECOMMENDATION_REJECTED
        )
        await self._audit.record(
            action,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="identity_merge_recommendation",
            entity_id=recommendation.id,
            after={
                "status": status.value,
                "primary_contact_id": primary.public_id,
                "duplicate_contact_id": duplicate.public_id,
                "merge_executed": False,
            },
            metadata={"operator_note": note},
        )
        for contact in (primary, duplicate):
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=event_type,
                ref_type=REF_TYPE_IDENTITY_RECOMMENDATION,
                ref_id=recommendation.id,
                payload={"status": status.value, "merge_executed": False},
            )
        await self._session.commit()
        return IdentityRecommendationView(
            recommendation=recommendation,
            primary_contact_id=primary.public_id,
            duplicate_contact_id=duplicate.public_id,
        )

    def _normalize_unique(self, assertions: list[IdentityAssertion]) -> list[NormalizedIdentity]:
        normalized: list[NormalizedIdentity] = []
        seen: set[tuple[str, str, str]] = set()
        for assertion in assertions:
            try:
                identity = self._normalizers.normalize(assertion)
            except ValueError as exc:
                raise BadRequestError(str(exc)) from exc
            if identity.key in seen:
                continue
            seen.add(identity.key)
            normalized.append(identity)
        return normalized

    async def _active_contact(self, organization_id: int, contact_id: int) -> Contact | None:
        contact = await self._session.get(Contact, contact_id)
        if (
            contact is None
            or contact.organization_id != organization_id
            or contact.deleted_at is not None
        ):
            return None
        return contact

    async def _link_identity(
        self,
        *,
        organization_id: int,
        actor: User,
        contact: Contact,
        identity: NormalizedIdentity,
    ) -> ContactIdentity:
        verified_at = (
            utcnow()
            if identity.confidence
            in {IdentityConfidence.AUTHORITATIVE, IdentityConfidence.VERIFIED}
            else None
        )
        row = ContactIdentity(
            organization_id=organization_id,
            contact_id=contact.id,
            identity_namespace=identity.identity_namespace,
            identity_scope=identity.identity_scope,
            normalized_value=identity.normalized_value,
            identity_kind=identity.identity_kind.value,
            connector_type=identity.connector_type,
            connection_ref=identity.connection_ref,
            endpoint_ref=identity.endpoint_ref,
            source=identity.source.value,
            confidence=identity.confidence.value,
            verified_at=verified_at,
            evidence_json={
                "normalization": "exact",
                "provider_record_immutable": True,
            },
            created_by=actor.id,
        )
        await self._identities.add(row)
        await self._events.record(
            organization_id=organization_id,
            contact_id=contact.id,
            event_type=EVENT_IDENTITY_LINKED,
            ref_type=REF_TYPE_CONTACT_IDENTITY,
            ref_id=row.id,
            payload={
                "identity_namespace": identity.identity_namespace,
                "identity_scope": identity.identity_scope,
                "source": identity.source.value,
                "confidence": identity.confidence.value,
            },
        )
        await self._audit.record(
            AuditAction.CONTACT_IDENTITY_LINKED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact_identity",
            entity_id=row.id,
            after={
                "contact_id": contact.public_id,
                "identity_namespace": identity.identity_namespace,
                "identity_scope": identity.identity_scope,
                "normalized_value": identity.normalized_value,
                "confidence": identity.confidence.value,
            },
        )
        return row

    async def _record_conflict(
        self,
        *,
        organization_id: int,
        actor: User,
        normalized: list[NormalizedIdentity],
        candidates: list[Contact],
        reason_code: str,
    ) -> IdentityConflict:
        candidate_ids = sorted({contact.public_id for contact in candidates})
        evidence = [identity.evidence() for identity in sorted(normalized, key=lambda item: item.key)]
        canonical = json.dumps(
            {
                "organization_id": organization_id,
                "reason_code": reason_code,
                "assertions": evidence,
                "candidate_contact_ids": candidate_ids,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = await self._conflicts.get_by_fingerprint(organization_id, fingerprint)
        if existing is not None:
            return existing

        conflict = IdentityConflict(
            organization_id=organization_id,
            fingerprint=fingerprint,
            status=IdentityConflictStatus.OPEN.value,
            reason_code=reason_code,
            confidence=IdentityConfidence.CONFLICTED.value,
            assertion_keys_json=evidence,
            candidate_contact_ids_json=candidate_ids,
            detected_at=utcnow(),
            created_by=actor.id,
        )
        await self._conflicts.add(conflict)
        await self._audit.record(
            AuditAction.IDENTITY_CONFLICT_DETECTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="identity_conflict",
            entity_id=conflict.id,
            after={
                "reason_code": reason_code,
                "candidate_contact_ids": candidate_ids,
                "automatic_merge": False,
            },
        )
        for contact in candidates:
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_IDENTITY_CONFLICT_DETECTED,
                ref_type=REF_TYPE_IDENTITY_CONFLICT,
                ref_id=conflict.id,
                payload={"reason_code": reason_code, "automatic_merge": False},
            )
        return conflict

    async def _conflict_view(
        self, organization_id: int, conflict: IdentityConflict
    ) -> IdentityConflictView:
        recommendations = await self._recommendations.list_for_conflict(
            organization_id, conflict.id
        )
        views: list[IdentityRecommendationView] = []
        for recommendation in recommendations:
            primary = await self._active_contact(
                organization_id, recommendation.primary_contact_id
            )
            duplicate = await self._active_contact(
                organization_id, recommendation.duplicate_contact_id
            )
            if primary is None or duplicate is None:
                continue
            views.append(
                IdentityRecommendationView(
                    recommendation=recommendation,
                    primary_contact_id=primary.public_id,
                    duplicate_contact_id=duplicate.public_id,
                )
            )
        return IdentityConflictView(conflict=conflict, recommendations=views)
'''

files["backend/app/schemas/contact_identity.py"] = '''
"""API schemas for exact Customer identity resolution and restricted manual review."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.identity.domain import (
    IdentityAssertion,
    IdentityConfidence,
    IdentityConflictStatus,
    IdentityKind,
    IdentitySource,
)
from app.models.contact_identity import ContactIdentity
from app.services.identity_resolution_service import (
    IdentityConflictView,
    IdentityRecommendationView,
    IdentityResolutionResult,
)


class IdentityAssertionRequest(BaseModel):
    identity_namespace: str = Field(min_length=2, max_length=64)
    identity_scope: str = Field(min_length=1, max_length=190)
    value: str = Field(min_length=1, max_length=190)
    identity_kind: IdentityKind = IdentityKind.PROVIDER
    connector_type: str | None = Field(default=None, max_length=64)
    connection_ref: str | None = Field(default=None, max_length=120)
    endpoint_ref: str | None = Field(default=None, max_length=120)
    source: IdentitySource = IdentitySource.PROVIDER
    confidence: IdentityConfidence = IdentityConfidence.AUTHORITATIVE

    def to_domain(self) -> IdentityAssertion:
        return IdentityAssertion(**self.model_dump())


class IdentityNewContactProfile(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    locale: str | None = Field(default=None, max_length=10)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class IdentityResolutionRequest(BaseModel):
    assertions: list[IdentityAssertionRequest] = Field(min_length=1, max_length=20)
    contact_id: uuidlib.UUID | None = None
    new_contact: IdentityNewContactProfile | None = None


class ContactIdentityResponse(BaseModel):
    id: str
    contact_id: str
    identity_namespace: str
    identity_scope: str
    normalized_value: str
    identity_kind: str
    connector_type: str | None
    connection_ref: str | None
    endpoint_ref: str | None
    source: str
    confidence: str
    verified_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, row: ContactIdentity, contact_id: str) -> ContactIdentityResponse:
        return cls(
            id=row.public_id,
            contact_id=contact_id,
            identity_namespace=row.identity_namespace,
            identity_scope=row.identity_scope,
            normalized_value=row.normalized_value,
            identity_kind=row.identity_kind,
            connector_type=row.connector_type,
            connection_ref=row.connection_ref,
            endpoint_ref=row.endpoint_ref,
            source=row.source,
            confidence=row.confidence,
            verified_at=row.verified_at,
            created_at=row.created_at,
        )


class IdentityResolutionResponse(BaseModel):
    status: str
    canonical_contact_id: str | None
    identities: list[ContactIdentityResponse]
    conflict_id: str | None
    created_contact: bool
    reasons: list[str]
    automatic_merge: bool = False

    @classmethod
    def from_result(cls, result: IdentityResolutionResult) -> IdentityResolutionResponse:
        contact_id = result.contact.public_id if result.contact is not None else None
        return cls(
            status=result.status.value,
            canonical_contact_id=contact_id,
            identities=(
                [ContactIdentityResponse.from_model(row, contact_id) for row in result.identities]
                if contact_id is not None
                else []
            ),
            conflict_id=result.conflict.public_id if result.conflict is not None else None,
            created_contact=result.created_contact,
            reasons=list(result.reasons),
        )


class IdentityMergeRecommendationResponse(BaseModel):
    id: str
    conflict_id: str
    primary_contact_id: str
    duplicate_contact_id: str
    confidence: str
    reason: str
    status: str
    decided_at: datetime | None
    decided_by: int | None
    decision_note: str | None
    created_at: datetime
    row_version: int
    merge_executed: bool = False

    @classmethod
    def from_view(
        cls, view: IdentityRecommendationView, conflict_public_id: str
    ) -> IdentityMergeRecommendationResponse:
        row = view.recommendation
        return cls(
            id=row.public_id,
            conflict_id=conflict_public_id,
            primary_contact_id=view.primary_contact_id,
            duplicate_contact_id=view.duplicate_contact_id,
            confidence=row.confidence,
            reason=row.reason,
            status=row.status,
            decided_at=row.decided_at,
            decided_by=row.decided_by,
            decision_note=row.decision_note,
            created_at=row.created_at,
            row_version=row.row_version,
        )


class IdentityConflictResponse(BaseModel):
    id: str
    status: str
    reason_code: str
    confidence: str
    assertion_keys: list[dict[str, Any]]
    candidate_contact_ids: list[str]
    review_note: str | None
    detected_at: datetime
    decision_at: datetime | None
    decision_by: int | None
    created_at: datetime
    updated_at: datetime
    row_version: int
    recommendations: list[IdentityMergeRecommendationResponse]
    automatic_merge: bool = False

    @classmethod
    def from_view(cls, view: IdentityConflictView) -> IdentityConflictResponse:
        row = view.conflict
        return cls(
            id=row.public_id,
            status=row.status,
            reason_code=row.reason_code,
            confidence=row.confidence,
            assertion_keys=row.assertion_keys_json,
            candidate_contact_ids=row.candidate_contact_ids_json,
            review_note=row.review_note,
            detected_at=row.detected_at,
            decision_at=row.decision_at,
            decision_by=row.decision_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            row_version=row.row_version,
            recommendations=[
                IdentityMergeRecommendationResponse.from_view(item, row.public_id)
                for item in view.recommendations
            ],
        )


class IdentityConflictPage(BaseModel):
    data: list[IdentityConflictResponse]
    total: int
    limit: int
    offset: int


class IdentityMergeRecommendationCreateRequest(BaseModel):
    primary_contact_id: uuidlib.UUID
    duplicate_contact_id: uuidlib.UUID
    confidence: IdentityConfidence
    reason: str = Field(min_length=3, max_length=2000)


class IdentityRecommendationDecisionRequest(BaseModel):
    row_version: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=2000)
'''

files["backend/app/api/v1/endpoints/contact_identity.py"] = '''
"""M13-02 identity resolution and restricted manual-review endpoints."""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.identity.domain import IdentityConflictStatus
from app.models.user import User
from app.schemas.contact_identity import (
    ContactIdentityResponse,
    IdentityConflictPage,
    IdentityConflictResponse,
    IdentityMergeRecommendationCreateRequest,
    IdentityMergeRecommendationResponse,
    IdentityRecommendationDecisionRequest,
    IdentityResolutionRequest,
    IdentityResolutionResponse,
)
from app.services.identity_resolution_service import IdentityResolutionService

router = APIRouter()

IdentityReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
IdentityWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]


@router.post(
    "/identity-resolution/resolve",
    response_model=IdentityResolutionResponse,
    summary="Resolve exact provider/endpoint identities to one canonical Contact",
)
async def resolve_identity(
    payload: IdentityResolutionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityResolutionResponse:
    result = await IdentityResolutionService(session).resolve(
        organization_id=actor.organization_id,
        actor=actor,
        assertions=[assertion.to_domain() for assertion in payload.assertions],
        contact_hint=payload.contact_id,
        new_contact_fields=(
            payload.new_contact.model_dump(exclude_none=True) if payload.new_contact else None
        ),
    )
    return IdentityResolutionResponse.from_result(result)


@router.get(
    "/contacts/{contact_id}/identities",
    response_model=list[ContactIdentityResponse],
    summary="List immutable exact identities linked to a canonical Contact",
)
async def list_contact_identities(
    contact_id: uuidlib.UUID,
    session: SessionDep,
    actor: IdentityReadActor,
) -> list[ContactIdentityResponse]:
    contact, rows = await IdentityResolutionService(session).list_contact_identities(
        actor.organization_id, contact_id
    )
    return [ContactIdentityResponse.from_model(row, contact.public_id) for row in rows]


@router.get(
    "/identity-conflicts",
    response_model=IdentityConflictPage,
    summary="List the tenant-scoped manual identity review queue",
)
async def list_identity_conflicts(
    session: SessionDep,
    actor: IdentityReadActor,
    conflict_status: IdentityConflictStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> IdentityConflictPage:
    views, total = await IdentityResolutionService(session).list_conflicts(
        actor.organization_id,
        status=conflict_status,
        limit=limit,
        offset=offset,
    )
    return IdentityConflictPage(
        data=[IdentityConflictResponse.from_view(view) for view in views],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/identity-conflicts/{conflict_id}",
    response_model=IdentityConflictResponse,
    summary="Get one identity conflict and its recommendation history",
)
async def get_identity_conflict(
    conflict_id: uuidlib.UUID,
    session: SessionDep,
    actor: IdentityReadActor,
) -> IdentityConflictResponse:
    view = await IdentityResolutionService(session).get_conflict(
        actor.organization_id, conflict_id
    )
    return IdentityConflictResponse.from_view(view)


@router.post(
    "/identity-conflicts/{conflict_id}/recommendations",
    response_model=IdentityMergeRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a non-destructive operator merge recommendation",
)
async def create_identity_recommendation(
    conflict_id: uuidlib.UUID,
    payload: IdentityMergeRecommendationCreateRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    view = await IdentityResolutionService(session).recommend_merge(
        organization_id=actor.organization_id,
        actor=actor,
        conflict_id=conflict_id,
        primary_contact_id=payload.primary_contact_id,
        duplicate_contact_id=payload.duplicate_contact_id,
        confidence=payload.confidence,
        reason=payload.reason,
    )
    return IdentityMergeRecommendationResponse.from_view(view, str(conflict_id))


@router.post(
    "/identity-merge-recommendations/{recommendation_id}/approve",
    response_model=IdentityMergeRecommendationResponse,
    summary="Approve a recommendation without merging or moving identities",
)
async def approve_identity_recommendation(
    recommendation_id: uuidlib.UUID,
    payload: IdentityRecommendationDecisionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    service = IdentityResolutionService(session)
    view = await service.decide_recommendation(
        organization_id=actor.organization_id,
        actor=actor,
        recommendation_id=recommendation_id,
        approve=True,
        expected_version=payload.row_version,
        note=payload.note,
    )
    conflict = await service.get_conflict(actor.organization_id, uuidlib.UUID(int=0))
    return IdentityMergeRecommendationResponse.from_view(view, conflict.conflict.public_id)


@router.post(
    "/identity-merge-recommendations/{recommendation_id}/reject",
    response_model=IdentityMergeRecommendationResponse,
    summary="Reject a recommendation without merging or moving identities",
)
async def reject_identity_recommendation(
    recommendation_id: uuidlib.UUID,
    payload: IdentityRecommendationDecisionRequest,
    session: SessionDep,
    actor: IdentityWriteActor,
) -> IdentityMergeRecommendationResponse:
    service = IdentityResolutionService(session)
    view = await service.decide_recommendation(
        organization_id=actor.organization_id,
        actor=actor,
        recommendation_id=recommendation_id,
        approve=False,
        expected_version=payload.row_version,
        note=payload.note,
    )
    conflict = await service.get_conflict(actor.organization_id, uuidlib.UUID(int=0))
    return IdentityMergeRecommendationResponse.from_view(view, conflict.conflict.public_id)
'''

files["backend/alembic/versions/0036_customer_identity_resolution.py"] = '''
"""Provider-independent Customer identity resolution records.

Revision ID: 0036_customer_identity_resolution
Revises: 0035_notification_center
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.contact_identity import (
    IDENTITY_CONFIDENCES,
    IDENTITY_CONFLICT_STATUSES,
    IDENTITY_KINDS,
    IDENTITY_RECOMMENDATION_STATUSES,
    IDENTITY_SOURCES,
)

revision = "0036_customer_identity_resolution"
down_revision = "0035_notification_center"
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

    op.create_table(
        "contact_identities",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("identity_namespace", sa.String(64), nullable=False),
        sa.Column("identity_scope", sa.String(190), nullable=False),
        sa.Column("normalized_value", sa.String(190), nullable=False),
        sa.Column("identity_kind", sa.String(16), nullable=False),
        sa.Column("connector_type", sa.String(64), nullable=True),
        sa.Column("connection_ref", sa.String(120), nullable=True),
        sa.Column("endpoint_ref", sa.String(120), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("verified_at", datetime6(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_contact_identities_uuid"),
        sa.UniqueConstraint(
            "organization_id",
            "identity_namespace",
            "identity_scope",
            "normalized_value",
            name="uq_contact_identity_exact_key",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("identity_kind", IDENTITY_KINDS), name="ck_identity_kind"),
        sa.CheckConstraint(
            _in("confidence", IDENTITY_CONFIDENCES), name="ck_identity_confidence"
        ),
        sa.CheckConstraint(_in("source", IDENTITY_SOURCES), name="ck_identity_source"),
        **args,
    )
    op.create_index(
        "ix_contact_identities_org_contact_created",
        "contact_identities",
        ["organization_id", "contact_id", "created_at"],
    )
    op.create_index(
        "ix_contact_identities_org_endpoint",
        "contact_identities",
        ["organization_id", "connection_ref", "endpoint_ref"],
    )

    op.create_table(
        "identity_conflicts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("assertion_keys_json", sa.JSON(), nullable=False),
        sa.Column("candidate_contact_ids_json", sa.JSON(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("detected_at", datetime6(), nullable=False, server_default=now),
        sa.Column("decision_at", datetime6(), nullable=True),
        sa.Column("decision_by", big_id(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_identity_conflicts_uuid"),
        sa.UniqueConstraint(
            "organization_id", "fingerprint", name="uq_identity_conflict_fingerprint"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("status", IDENTITY_CONFLICT_STATUSES), name="ck_identity_conflict_status"
        ),
        sa.CheckConstraint(
            _in("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_conflict_confidence",
        ),
        **args,
    )
    op.create_index(
        "ix_identity_conflicts_org_status_created",
        "identity_conflicts",
        ["organization_id", "status", "created_at"],
    )

    op.create_table(
        "identity_merge_recommendations",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("conflict_id", big_id(), nullable=False),
        sa.Column("primary_contact_id", big_id(), nullable=False),
        sa.Column("duplicate_contact_id", big_id(), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decided_at", datetime6(), nullable=True),
        sa.Column("decided_by", big_id(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_identity_merge_recommendations_uuid"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conflict_id"], ["identity_conflicts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["duplicate_contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("status", IDENTITY_RECOMMENDATION_STATUSES),
            name="ck_identity_recommendation_status",
        ),
        sa.CheckConstraint(
            _in("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_recommendation_confidence",
        ),
        sa.CheckConstraint(
            "primary_contact_id <> duplicate_contact_id",
            name="ck_identity_recommendation_distinct_contacts",
        ),
        **args,
    )
    op.create_index(
        "ix_identity_recommendations_org_conflict_status",
        "identity_merge_recommendations",
        ["organization_id", "conflict_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_recommendations_org_conflict_status",
        table_name="identity_merge_recommendations",
    )
    op.drop_table("identity_merge_recommendations")
    op.drop_index("ix_identity_conflicts_org_status_created", table_name="identity_conflicts")
    op.drop_table("identity_conflicts")
    op.drop_index("ix_contact_identities_org_endpoint", table_name="contact_identities")
    op.drop_index("ix_contact_identities_org_contact_created", table_name="contact_identities")
    op.drop_table("contact_identities")
'''

files["backend/tests/test_identity_resolution.py"] = '''
"""M13-02 exact identity, tenant, conflict, recommendation and no-merge acceptance tests."""

from __future__ import annotations

from sqlalchemy import select

from app.core.security import hash_password
from app.identity.domain import IdentityAssertion, IdentityNormalizerRegistry
from app.identity.flags import IDENTITY_RESOLUTION_FLAG
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.contact_event import ContactEvent
from app.models.contact_identity import ContactIdentity
from app.models.organization import Organization
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.identity_resolution_service import IdentityResolutionService

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _set_flag(session_factory, organization_id: int, enabled: bool = True) -> None:
    async with session_factory() as session:
        session.add(
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=organization_id,
                is_enabled=enabled,
            )
        )
        await session.commit()


def _phone_assertion(phone: str) -> dict[str, str]:
    return {
        "identity_namespace": "whatsapp_phone",
        "identity_scope": "global",
        "value": phone,
        "identity_kind": "provider",
        "source": "provider",
        "confidence": "authoritative",
    }


async def _create_contact(client, headers: dict[str, str], phone: str, name: str) -> dict:
    response = await client.post(
        "/api/v1/contacts",
        headers=headers,
        json={"phone_e164": phone, "full_name": name},
    )
    assert response.status_code == 201
    return response.json()


async def test_exact_phone_creates_one_canonical_contact_and_links_endpoint_aliases(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "assertions": [_phone_assertion("+14155552671")],
            "new_contact": {"full_name": "Canonical Customer"},
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "created"
    assert body["canonical_contact_id"]
    assert body["automatic_merge"] is False
    canonical_id = body["canonical_contact_id"]

    alias = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": canonical_id,
            "assertions": [
                {
                    "identity_namespace": "messenger_psid",
                    "identity_scope": "endpoint:page-1",
                    "value": "PSID-001",
                    "identity_kind": "endpoint",
                    "connector_type": "future-provider",
                    "connection_ref": "connection-1",
                    "endpoint_ref": "page-1",
                    "source": "provider",
                    "confidence": "verified",
                },
                {
                    "identity_namespace": "messenger_psid",
                    "identity_scope": "endpoint:page-2",
                    "value": "PSID-002",
                    "identity_kind": "endpoint",
                    "connector_type": "future-provider",
                    "connection_ref": "connection-1",
                    "endpoint_ref": "page-2",
                    "source": "provider",
                    "confidence": "verified",
                },
            ],
        },
    )
    assert alias.status_code == 200
    assert alias.json()["canonical_contact_id"] == canonical_id

    identities = await client.get(
        f"/api/v1/contacts/{canonical_id}/identities", headers=headers
    )
    assert identities.status_code == 200
    rows = identities.json()
    assert len(rows) == 3
    assert {row["contact_id"] for row in rows} == {canonical_id}
    assert {row["endpoint_ref"] for row in rows if row["endpoint_ref"]} == {
        "page-1",
        "page-2",
    }

    repeated = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "resolved"
    assert repeated.json()["canonical_contact_id"] == canonical_id
    assert len(repeated.json()["identities"]) == 1


async def test_conflict_queue_recommendation_approval_never_merges_or_moves_identity(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")
    primary = await _create_contact(client, headers, "+14155550001", "Primary")
    duplicate = await _create_contact(client, headers, "+14155550002", "Duplicate")

    linked = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": primary["id"],
            "assertions": [
                {
                    "identity_namespace": "instagram_user",
                    "identity_scope": "business:ig-1",
                    "value": "IG-USER-9",
                    "connector_type": "future-provider",
                }
            ],
        },
    )
    assert linked.status_code == 200
    identity_id = linked.json()["identities"][0]["id"]

    detected = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": duplicate["id"],
            "assertions": [
                {
                    "identity_namespace": "instagram_user",
                    "identity_scope": "business:ig-1",
                    "value": "IG-USER-9",
                    "connector_type": "future-provider",
                }
            ],
        },
    )
    assert detected.status_code == 200
    conflict = detected.json()
    assert conflict["status"] == "conflict"
    assert conflict["canonical_contact_id"] is None
    conflict_id = conflict["conflict_id"]

    queue = await client.get("/api/v1/identity-conflicts?status=open", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    assert set(queue.json()["data"][0]["candidate_contact_ids"]) == {
        primary["id"],
        duplicate["id"],
    }

    recommendation = await client.post(
        f"/api/v1/identity-conflicts/{conflict_id}/recommendations",
        headers=headers,
        json={
            "primary_contact_id": primary["id"],
            "duplicate_contact_id": duplicate["id"],
            "confidence": "verified",
            "reason": "Operator reviewed exact provider evidence.",
        },
    )
    assert recommendation.status_code == 201
    rec = recommendation.json()
    assert rec["status"] == "pending" and rec["merge_executed"] is False

    approved = await client.post(
        f"/api/v1/identity-merge-recommendations/{rec['id']}/approve",
        headers=headers,
        json={"row_version": rec["row_version"], "note": "Approved for later merge workflow."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["merge_executed"] is False

    assert (await client.get(f"/api/v1/contacts/{primary['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/v1/contacts/{duplicate['id']}", headers=headers)).status_code == 200
    primary_identities = (
        await client.get(f"/api/v1/contacts/{primary['id']}/identities", headers=headers)
    ).json()
    duplicate_identities = (
        await client.get(f"/api/v1/contacts/{duplicate['id']}/identities", headers=headers)
    ).json()
    assert {row["id"] for row in primary_identities} == {identity_id}
    assert duplicate_identities == []

    async with session_factory() as session:
        identity = (await session.scalars(select(ContactIdentity))).one()
        assert identity.contact_id == primary["row_version"] + 1
        actions = set((await session.scalars(select(AuditLog.action))).all())
        assert AuditAction.IDENTITY_CONFLICT_DETECTED in actions
        assert AuditAction.IDENTITY_MERGE_RECOMMENDATION_CREATED in actions
        assert AuditAction.IDENTITY_MERGE_RECOMMENDATION_APPROVED in actions
        events = set((await session.scalars(select(ContactEvent.event_type))).all())
        assert "identity_conflict_detected" in events
        assert "identity_recommendation_approved" in events


async def test_non_phone_identity_without_authoritative_contact_requires_review_not_fuzzy_merge(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")
    await _create_contact(client, headers, "+14155550011", "Same Name")
    await _create_contact(client, headers, "+14155550012", "Same Name")

    result = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "new_contact": {"full_name": "Same Name"},
            "assertions": [
                {
                    "identity_namespace": "telegram_user",
                    "identity_scope": "provider:telegram",
                    "value": "tg-opaque-1",
                    "connector_type": "future-provider",
                }
            ],
        },
    )
    assert result.status_code == 200
    assert result.json()["status"] == "review_required"
    assert result.json()["canonical_contact_id"] is None
    listing = await client.get("/api/v1/contacts", headers=headers)
    assert listing.json()["page"]["total"] == 2


async def test_flag_and_rbac_fail_closed(client, make_user, session_factory, organization) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    owner_headers = await _headers(client, "owner@vi.co")
    disabled = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=owner_headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert disabled.status_code == 404

    await _set_flag(session_factory, organization.id)
    await make_user(email="restricted@vi.co", password=PASSWORD)
    restricted_headers = await _headers(client, "restricted@vi.co")
    denied = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=restricted_headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert denied.status_code == 403


async def test_tenant_isolation_allows_same_exact_key_without_cross_tenant_resolution(
    db_session, session_factory, organization
) -> None:
    actor_one = User(
        organization_id=organization.id,
        email="one@vi.test",
        password_hash=hash_password(PASSWORD),
        full_name="One",
        is_superuser=True,
    )
    second_org = Organization(name="Second Org", slug="second-org")
    db_session.add_all([actor_one, second_org])
    await db_session.flush()
    actor_two = User(
        organization_id=second_org.id,
        email="two@vi.test",
        password_hash=hash_password(PASSWORD),
        full_name="Two",
        is_superuser=True,
    )
    db_session.add(actor_two)
    db_session.add_all(
        [
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=organization.id,
                is_enabled=True,
            ),
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=second_org.id,
                is_enabled=True,
            ),
        ]
    )
    await db_session.commit()

    assertion = IdentityAssertion(
        identity_namespace="whatsapp_phone",
        identity_scope="global",
        value="+14155552671",
    )
    first = await IdentityResolutionService(db_session).resolve(
        organization_id=organization.id,
        actor=actor_one,
        assertions=[assertion],
        contact_hint=None,
        new_contact_fields={"full_name": "One"},
    )
    second = await IdentityResolutionService(db_session).resolve(
        organization_id=second_org.id,
        actor=actor_two,
        assertions=[assertion],
        contact_hint=None,
        new_contact_fields={"full_name": "Two"},
    )
    assert first.contact is not None and second.contact is not None
    assert first.contact.public_id != second.contact.public_id
    identities = list((await db_session.scalars(select(ContactIdentity))).all())
    assert len(identities) == 2
    assert {row.organization_id for row in identities} == {organization.id, second_org.id}


async def test_future_namespace_registration_requires_no_resolver_architecture_change() -> None:
    registry = IdentityNormalizerRegistry()
    registry.register("future_network_user", lambda value: value.strip(), global_scope=False)
    normalized = registry.normalize(
        IdentityAssertion(
            identity_namespace="future_network_user",
            identity_scope="provider:future",
            value=" user-42 ",
            connector_type="future-provider",
        )
    )
    assert normalized.normalized_value == "user-42"
    assert normalized.key == ("future_network_user", "provider:future", "user-42")
'''

for relative_path, content in files.items():
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def replace_once(relative_path: str, old: str, new: str) -> None:
    path = root / relative_path
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(f"expected one marker in {relative_path}: {old!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_once(
    "backend/app/models/__init__.py",
    "from app.models.contact import Contact\n",
    "from app.models.contact import Contact\n"
    "from app.models.contact_identity import (\n"
    "    ContactIdentity,\n"
    "    IdentityConflict,\n"
    "    IdentityMergeRecommendation,\n"
    ")\n",
)
replace_once(
    "backend/app/models/__init__.py",
    '    "Contact",\n',
    '    "Contact",\n'
    '    "ContactIdentity",\n'
    '    "IdentityConflict",\n'
    '    "IdentityMergeRecommendation",\n',
)
replace_once(
    "backend/app/api/v1/router.py",
    "    contact_documents,\n    contacts,\n",
    "    contact_documents,\n    contact_identity,\n    contacts,\n",
)
replace_once(
    "backend/app/api/v1/router.py",
    'api_router.include_router(contacts.router, tags=["Contacts"])\n',
    'api_router.include_router(contacts.router, tags=["Contacts"])\n'
    'api_router.include_router(contact_identity.router, tags=["Customer Identity"])\n',
)
replace_once(
    "backend/app/models/contact_event.py",
    'EVENT_CONTACT_MERGED = "contact_merged"\n',
    'EVENT_CONTACT_MERGED = "contact_merged"\n'
    'EVENT_IDENTITY_LINKED = "identity_linked"\n'
    'EVENT_IDENTITY_CONFLICT_DETECTED = "identity_conflict_detected"\n'
    'EVENT_IDENTITY_RECOMMENDATION_CREATED = "identity_recommendation_created"\n'
    'EVENT_IDENTITY_RECOMMENDATION_APPROVED = "identity_recommendation_approved"\n'
    'EVENT_IDENTITY_RECOMMENDATION_REJECTED = "identity_recommendation_rejected"\n',
)
replace_once(
    "backend/app/models/contact_event.py",
    'REF_TYPE_CONTACT_DOCUMENT = "contact_document"\n',
    'REF_TYPE_CONTACT_DOCUMENT = "contact_document"\n'
    'REF_TYPE_CONTACT_IDENTITY = "contact_identity"\n'
    'REF_TYPE_IDENTITY_CONFLICT = "identity_conflict"\n'
    'REF_TYPE_IDENTITY_RECOMMENDATION = "identity_merge_recommendation"\n',
)
replace_once(
    "backend/app/services/audit_service.py",
    '    CONTACT_MERGED = "contact.merged"\n',
    '    CONTACT_MERGED = "contact.merged"\n'
    '    CONTACT_IDENTITY_LINKED = "contact_identity.linked"\n'
    '    IDENTITY_CONFLICT_DETECTED = "identity_conflict.detected"\n'
    '    IDENTITY_MERGE_RECOMMENDATION_CREATED = "identity_merge_recommendation.created"\n'
    '    IDENTITY_MERGE_RECOMMENDATION_APPROVED = "identity_merge_recommendation.approved"\n'
    '    IDENTITY_MERGE_RECOMMENDATION_REJECTED = "identity_merge_recommendation.rejected"\n',
)
