"""Contact model (Doc 03 §6.1) — Module 2 foundation.

The platform's first large table (1M+ rows): a WhatsApp contact keyed for dedup by
``(organization_id, wa_id)``. Not partitioned (Doc 03 §6.1). Soft-deleted with
optimistic-concurrency ``row_version``. Tags, custom attributes, and the activity timeline
are separate sub-resources added in later steps; this model is the core contact record.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, JSON, Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6
from app.models.tag import Tag, contact_tags

OPT_IN_UNKNOWN = "unknown"
OPT_IN_OPTED_IN = "opted_in"
OPT_IN_OPTED_OUT = "opted_out"
OPT_IN_STATUSES = (OPT_IN_UNKNOWN, OPT_IN_OPTED_IN, OPT_IN_OPTED_OUT)


class Contact(
    IntPKMixin,
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    Base,
):
    """A WhatsApp contact (Doc 03 §6.1)."""

    __tablename__ = "contacts"
    __table_args__ = (
        Index("uq_contacts_org_waid", "organization_id", "wa_id", unique=True),
        Index("ix_contacts_org_created", "organization_id", "created_at"),
        Index("ix_contacts_org_optin", "organization_id", "opt_in_status"),
        Index("ix_contacts_last_inbound", "organization_id", "last_inbound_at"),
        Index("ix_contacts_email", "email"),
        Index("ix_contacts_name", "organization_id", "full_name"),
        CheckConstraint(
            "opt_in_status IN ('unknown','opted_in','opted_out')", name="ck_contacts_optin"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_contacts_org", ondelete="RESTRICT"),
        nullable=False,
    )
    wa_id: Mapped[str] = mapped_column(String(24), nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(24), nullable=False)
    country_code: Mapped[str | None] = mapped_column(CHAR(2), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    profile_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    opt_in_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=OPT_IN_UNKNOWN
    )
    opt_in_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    opt_out_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    is_active_on_wa: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_contacted_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attributes_cache: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Eager-loaded so a fetched/listed contact always carries its tags (Doc 04 §14 schema);
    # selectin issues one extra query per page, avoiding N+1. Writes go through contact_tags.
    tags: Mapped[list[Tag]] = relationship(
        Tag,
        secondary=contact_tags,
        lazy="selectin",
        order_by=Tag.name,
        viewonly=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Contact id={self.id} wa_id={self.wa_id!r}>"
