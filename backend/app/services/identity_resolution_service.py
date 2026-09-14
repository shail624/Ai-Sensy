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
    conflict_id: str
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
                reasons=(
                    "Exact evidence resolves to multiple Contacts; operator review is required.",
                ),
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
                        reasons=(
                            "Identity ownership changed during resolution; no alias was moved.",
                        ),
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
            conflict_id=conflict.public_id,
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
        recommendation = await self._recommendations.get_scoped(organization_id, recommendation_id)
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
            conflict_id=conflict.public_id,
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
        evidence = [
            identity.evidence() for identity in sorted(normalized, key=lambda item: item.key)
        ]
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
            primary = await self._active_contact(organization_id, recommendation.primary_contact_id)
            duplicate = await self._active_contact(
                organization_id, recommendation.duplicate_contact_id
            )
            if primary is None or duplicate is None:
                continue
            views.append(
                IdentityRecommendationView(
                    recommendation=recommendation,
                    conflict_id=conflict.public_id,
                    primary_contact_id=primary.public_id,
                    duplicate_contact_id=duplicate.public_id,
                )
            )
        return IdentityConflictView(conflict=conflict, recommendations=views)
