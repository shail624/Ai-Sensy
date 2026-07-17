"""WhatsApp infrastructure models (Doc 03 §5.1/§5.2) — FR-WA-01/02/03/04/13.

The platform's Channel-1 provisioning records: which WABAs are connected and which numbers they
own. Multi-WABA is first-class (FR-WA-01), and ``phone_numbers`` carries ``channel_type`` so a
future Instagram/Messenger number is data rather than a schema change (Doc 03 §5.2, NFR-EXT-02).

Tokens live in ``access_token_enc`` as AES-GCM ciphertext (:mod:`app.core.crypto`, FR-WA-03) and
are **write-only** at the API edge (Doc 04 §13.2) — nothing here ever renders one.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
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
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, small_uint, varbinary

# whatsapp_business_accounts.status (Doc 03 §5.1)
WABA_ACTIVE = "active"
WABA_SUSPENDED = "suspended"
WABA_DISABLED = "disabled"
WABA_STATUSES = (WABA_ACTIVE, WABA_SUSPENDED, WABA_DISABLED)

# phone_numbers.quality_rating (Doc 03 §5.2, FR-WA-04)
QUALITY_RATINGS = ("GREEN", "YELLOW", "RED")

#: Default per-number send pacing target (Doc 03 §5.2); the rate gate consumes it (Doc 06 §5).
DEFAULT_MPS_LIMIT = 80


class WhatsAppBusinessAccount(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A connected WABA (Doc 03 §5.1; FR-WA-01/03)."""

    __tablename__ = "whatsapp_business_accounts"
    __table_args__ = (
        Index("uq_waba_metaid", "waba_id", unique=True),
        Index("ix_waba_org", "organization_id"),
        CheckConstraint("status IN ('active','suspended','disabled')", name="ck_waba_status"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_waba_org", ondelete="RESTRICT"),
        nullable=False,
    )
    #: Meta's WABA id — globally unique, so a WABA cannot be connected twice (409).
    waba_id: Mapped[str] = mapped_column(String(32), nullable=False)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    meta_business_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: AES-GCM ciphertext of the system-user token — never selected into a response (FR-WA-03).
    access_token_enc: Mapped[bytes] = mapped_column(varbinary(1024), nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    webhook_verify_token_enc: Mapped[bytes | None] = mapped_column(varbinary(255), nullable=True)
    #: Billing currency + timezone feed the cost engine and scheduling in later modules.
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=WABA_ACTIVE)

    phone_numbers: Mapped[list[PhoneNumber]] = relationship(
        "PhoneNumber", back_populates="waba", lazy="selectin", viewonly=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<WhatsAppBusinessAccount id={self.id} waba_id={self.waba_id!r}>"


class PhoneNumber(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A phone number owned by a WABA (Doc 03 §5.2; FR-WA-02/04/13)."""

    __tablename__ = "phone_numbers"
    __table_args__ = (
        Index("uq_phone_metaid", "phone_number_id", unique=True),
        Index("ix_phone_waba", "waba_id"),
        Index("ix_phone_org", "organization_id", "channel_type"),
        CheckConstraint(
            "quality_rating IN ('GREEN','YELLOW','RED') OR quality_rating IS NULL",
            name="ck_phone_quality",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_phone_org", ondelete="RESTRICT"),
        nullable=False,
    )
    #: FK to the owning WABA row (not Meta's string id).
    waba_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("whatsapp_business_accounts.id", name="fk_phone_waba", ondelete="CASCADE"),
        nullable=False,
    )
    #: Omnichannel readiness (Doc 03 §5.2, NFR-EXT-02) — matches ChannelType.
    channel_type: Mapped[str] = mapped_column(String(24), nullable=False, default="whatsapp")
    #: Meta's phone_number_id — the key inbound webhook routing looks numbers up by.
    phone_number_id: Mapped[str] = mapped_column(String(32), nullable=False)
    display_number: Mapped[str] = mapped_column(String(24), nullable=False)
    verified_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    quality_rating: Mapped[str | None] = mapped_column(String(8), nullable=True)
    messaging_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mps_limit: Mapped[int] = mapped_column(
        small_uint(), nullable=False, default=DEFAULT_MPS_LIMIT
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="connected")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    throughput_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    waba: Mapped[WhatsAppBusinessAccount] = relationship(
        "WhatsAppBusinessAccount", back_populates="phone_numbers"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<PhoneNumber id={self.id} display_number={self.display_number!r}>"
