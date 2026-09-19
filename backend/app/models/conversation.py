"""Conversation model (Doc 03 §9.1) — FR-WA-12 / INB-06.

One open thread per ``(phone_number, contact)``, and the home of the **24-hour customer-service
window**: WhatsApp only permits free-form replies within 24h of the customer's last inbound
message, so the window is not a display detail — it is the rule that decides whether a send is
allowed at all.

``window_expires_at``/``is_window_open`` are **denormalized** from ``last_inbound_at`` (Doc 03
§9.1). The stored flag is what ``ix_conv_window`` indexes so expiring threads can be swept in bulk;
:attr:`Conversation.window_is_open` is the truth at read time, because a window closes by time
passing rather than by anything writing a row.

``unread_count``/``last_message_preview`` are likewise denormalized so the inbox list renders
without touching the 10M+ ledger (Doc 03 §9.1).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import (
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
    utcnow,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

# conversations.status (Doc 03 §9.1)
CONV_OPEN = "open"
CONV_PENDING = "pending"
CONV_RESOLVED = "resolved"
CONV_SNOOZED = "snoozed"
CONV_STATUSES = (CONV_OPEN, CONV_PENDING, CONV_RESOLVED, CONV_SNOOZED)

#: The Meta customer-service window: 24h from the customer's last inbound message (FR-WA-12).
WINDOW = timedelta(hours=24)

#: ``last_message_preview`` is VARCHAR(255) (Doc 03 §9.1).
PREVIEW_LENGTH = 255


class Conversation(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A thread between one of our endpoints and one contact (Doc 03 §9.1; ADR-0020).

    Owned by exactly one of a Meta ``phone_numbers`` row or a provider-neutral
    ``channel_endpoints`` row (QR-08) — never both, never neither (``ck_conv_endpoint_owner``).
    Each provider keeps its own thread per contact rather than sharing one (ADR-0020 "Separate
    conversations, unified customer"): provider rules, sender identity and health differ, so a
    WAHA conversation and a Meta conversation with the same contact are two rows, not one.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        # One thread per (number, contact) — the constraint that makes upsert-on-inbound safe
        # under concurrent deliveries (Doc 06 §9.4: the data layer is the ultimate guard).
        Index("uq_conv_number_contact", "phone_number_id", "contact_id", unique=True),
        # The same guarantee for a channel-endpoint-owned (WAHA) thread (QR-08).
        Index("uq_conv_endpoint_contact", "channel_endpoint_id", "contact_id", unique=True),
        Index("ix_conv_org_status", "organization_id", "status", "last_message_at"),
        Index("ix_conv_assignee", "assigned_user_id", "status"),
        Index("ix_conv_window", "is_window_open", "window_expires_at"),
        CheckConstraint(
            "status IN ('open','pending','resolved','snoozed')", name="ck_conv_status"
        ),
        CheckConstraint(
            "(phone_number_id IS NOT NULL AND channel_endpoint_id IS NULL) OR "
            "(phone_number_id IS NULL AND channel_endpoint_id IS NOT NULL)",
            name="ck_conv_endpoint_owner",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_conv_org", ondelete="RESTRICT"),
        nullable=False,
    )
    #: Set for a Meta-owned thread; ``NULL`` for a channel-endpoint-owned one (QR-08).
    phone_number_id: Mapped[int | None] = mapped_column(
        big_id(),
        ForeignKey("phone_numbers.id", name="fk_conv_number", ondelete="CASCADE"),
        nullable=True,
    )
    #: Set for a provider-neutral (WAHA) thread; ``NULL`` for a Meta-owned one (QR-08).
    channel_endpoint_id: Mapped[int | None] = mapped_column(
        big_id(),
        ForeignKey("channel_endpoints.id", name="fk_conv_channel_endpoint", ondelete="RESTRICT"),
        nullable=True,
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("contacts.id", name="fk_conv_contact", ondelete="CASCADE"),
        nullable=False,
    )
    #: Omnichannel readiness (Doc 03 §9.1) — matches ChannelType, as on ``phone_numbers``.
    channel_type: Mapped[str] = mapped_column(String(24), nullable=False, default="whatsapp")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CONV_OPEN)
    assigned_user_id: Mapped[int | None] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_conv_assignee", ondelete="SET NULL"),
        nullable=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    #: Window start — the customer's last inbound message (Doc 03 §9.1).
    last_inbound_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    window_expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    unread_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    last_message_preview: Mapped[str | None] = mapped_column(
        String(PREVIEW_LENGTH), nullable=True
    )
    is_window_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @property
    def window_is_open(self) -> bool:
        """Whether a free-form reply is permitted **now** (FR-WA-12).

        Computed rather than read from ``is_window_open``: nothing writes to a thread when its
        window lapses, so the stored flag is only ever as fresh as the last message.
        """
        return self.window_expires_at is not None and self.window_expires_at > utcnow()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Conversation id={self.id} status={self.status!r}>"
