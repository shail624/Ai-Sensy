"""Governed customer-document records (Design Book 19, Phase 4A).

Document metadata and lifecycle state live here; file bytes remain in the existing media
storage boundary.  Versions and events are append-only so verification decisions retain a
complete, attributable history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
    utcnow,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

DOCUMENT_TYPE_IDENTITY = "identity"
DOCUMENT_TYPE_ADDRESS = "address"
DOCUMENT_TYPE_INCOME = "income"
DOCUMENT_TYPE_BUSINESS = "business"
DOCUMENT_TYPE_CONSENT = "consent"
DOCUMENT_TYPE_OTHER = "other"
DOCUMENT_TYPES: tuple[str, ...] = (
    DOCUMENT_TYPE_IDENTITY,
    DOCUMENT_TYPE_ADDRESS,
    DOCUMENT_TYPE_INCOME,
    DOCUMENT_TYPE_BUSINESS,
    DOCUMENT_TYPE_CONSENT,
    DOCUMENT_TYPE_OTHER,
)

DOCUMENT_STATUS_SUBMITTED = "submitted"
DOCUMENT_STATUS_VERIFIED = "verified"
DOCUMENT_STATUS_REJECTED = "rejected"
DOCUMENT_STATUS_EXPIRED = "expired"
DOCUMENT_STATUS_ARCHIVED = "archived"
DOCUMENT_STATUSES: tuple[str, ...] = (
    DOCUMENT_STATUS_SUBMITTED,
    DOCUMENT_STATUS_VERIFIED,
    DOCUMENT_STATUS_REJECTED,
    DOCUMENT_STATUS_EXPIRED,
    DOCUMENT_STATUS_ARCHIVED,
)

DOCUMENT_EVENT_CREATED = "created"
DOCUMENT_EVENT_VERSION_ADDED = "version_added"
DOCUMENT_EVENT_VERIFIED = "verified"
DOCUMENT_EVENT_REJECTED = "rejected"
DOCUMENT_EVENT_EXPIRED = "expired"
DOCUMENT_EVENT_ARCHIVED = "archived"


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ContactDocument(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A governed document attached to one customer."""

    __tablename__ = "contact_documents"
    __table_args__ = (
        Index(
            "ix_contact_documents_org_contact_updated",
            "organization_id",
            "contact_id",
            "updated_at",
        ),
        Index("ix_contact_documents_org_status_expiry", "organization_id", "status", "expires_at"),
        CheckConstraint(
            _in_clause("document_type", DOCUMENT_TYPES), name="ck_contact_documents_type"
        ),
        CheckConstraint(
            _in_clause("status", DOCUMENT_STATUSES), name="ck_contact_documents_status"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_contact_documents_org", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("contacts.id", name="fk_contact_documents_contact", ondelete="RESTRICT"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DOCUMENT_STATUS_SUBMITTED
    )
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    verified_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)


class ContactDocumentVersion(IntPKMixin, UUIDMixin, Base):
    """One immutable media-backed version of a customer document."""

    __tablename__ = "contact_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_contact_document_version_no"),
        Index("ix_contact_document_versions_document_created", "document_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    document_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "contact_documents.id", name="fk_contact_document_versions_doc", ondelete="CASCADE"
        ),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(int_id(), nullable=False)
    media_asset_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "media_assets.id", name="fk_contact_document_versions_media", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    uploaded_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class ContactDocumentEvent(IntPKMixin, Base):
    """Append-only document lifecycle history."""

    __tablename__ = "contact_document_events"
    __table_args__ = (
        Index("ix_contact_document_events_document_created", "document_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    document_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "contact_documents.id", name="fk_contact_document_events_doc", ondelete="CASCADE"
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    from_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    to_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
