"""API schemas for exact Customer identity resolution and restricted manual review."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.identity.domain import (
    IdentityAssertion,
    IdentityConfidence,
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
    def from_view(cls, view: IdentityRecommendationView) -> IdentityMergeRecommendationResponse:
        row = view.recommendation
        return cls(
            id=row.public_id,
            conflict_id=view.conflict_id,
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
                IdentityMergeRecommendationResponse.from_view(item) for item in view.recommendations
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
