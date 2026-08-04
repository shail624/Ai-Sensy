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
IDENTITY_RECOMMENDATION_STATUSES = tuple(value.value for value in IdentityMergeRecommendationStatus)


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
