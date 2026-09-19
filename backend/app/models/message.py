"""The message ledger & delivery log (Doc 03 §9.2/§9.3) — FR-WA-06/07.

``messages`` is deliberately **one** table, not "messages" plus a separate ledger (Doc 03 §9.2): a
campaign send *is* a message, and a second table would duplicate `wamid`, direction, status and
cost. The pricing columns make it the billing ledger too.

``message_status_history`` is separate for the opposite reason: status is append-only and the
highest-volume thing in the system (100M+), so keeping it out of `messages` keeps the ledger row
small and the hot-path update cheap. The *current* status is denormalized onto `messages.status`;
the full transition history lives here.

Both are partitioned monthly on MySQL and therefore carry the composite ``(id, created_at)``
primary key that requires — and, because a partitioned table cannot be an FK target, hold **no**
foreign keys: `conversation_id`/`message_id` are app-enforced (Doc 03 §9.2/§9.3).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CHAR, JSON, Boolean, CheckConstraint, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

# messages.direction (Doc 03 §9.2)
DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"

# messages.status (Doc 03 §9.2) — also the canonical vocabulary an adapter normalizes a channel's
# native status names into, so this is the single definition of what a delivery state can be.
MSG_ACCEPTED = "accepted"
MSG_SENT = "sent"
MSG_DELIVERED = "delivered"
MSG_READ = "read"
MSG_FAILED = "failed"
MSG_STATUSES = (MSG_ACCEPTED, MSG_SENT, MSG_DELIVERED, MSG_READ, MSG_FAILED)

#: Delivery is a one-way street (Doc 06 §11.3, decision D16): status only moves **forward**, so a
#: reordered webhook — a late `delivered` arriving after `read` — is a no-op rather than a
#: regression. This ordering is what makes out-of-order delivery safe without global ordering.
STATUS_RANK: dict[str, int] = {MSG_ACCEPTED: 0, MSG_SENT: 1, MSG_DELIVERED: 2, MSG_READ: 3}

#: `failed` is terminal (D16): nothing follows it, and it can arrive from any live state.
TERMINAL_STATUSES = (MSG_FAILED,)

#: When a status carries a timestamp, it also stamps this column on `messages`.
STATUS_TIMESTAMP_COLUMN = {
    MSG_SENT: "sent_at",
    MSG_DELIVERED: "delivered_at",
    MSG_READ: "read_at",
}


def advances(current: str, incoming: str) -> bool:
    """Is ``incoming`` a forward transition from ``current``? (Doc 06 §11.3 / D16.)"""
    if current in TERMINAL_STATUSES:
        return False
    if incoming in TERMINAL_STATUSES:
        return True
    return STATUS_RANK.get(incoming, -1) > STATUS_RANK.get(current, -1)


class Message(IntPKMixin, UUIDMixin, Base):
    """One message in the ledger (Doc 03 §9.2)."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_msg_conversation", "conversation_id", "created_at"),
        # Webhook status lookup by wamid; also the inbound idempotency key (Doc 06 §2.3).
        Index("ix_msg_wamid", "wamid"),
        # The channel-endpoint-scoped analogue of ``ix_msg_endpoint_wamid`` (0042) — WAHA's
        # provider message identity lookup (QR-08).
        Index("ix_msg_channel_endpoint_wamid", "channel_endpoint_id", "wamid"),
        Index("ix_msg_org_created", "organization_id", "created_at"),
        Index("ix_msg_campaign", "campaign_id"),
        Index("ix_msg_contact", "contact_id", "created_at"),
        Index("ix_msg_status", "status", "created_at"),
        CheckConstraint("direction IN ('inbound','outbound')", name="ck_msg_direction"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    #: App-enforced FK to ``conversations.id`` (this table is partitioned).
    conversation_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    #: Set for a Meta-owned message; ``NULL`` for a channel-endpoint-owned one (QR-08). App-enforced
    #: like ``channel_endpoint_id`` below — this table is partitioned and cannot hold either as a
    #: real FK.
    phone_number_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: Set for a provider-neutral (WAHA) message; ``NULL`` for a Meta-owned one (QR-08). Scopes
    #: provider message identity the same way ``phone_number_id`` already does for Meta
    #: (ADR-0020, ``ix_msg_channel_endpoint_wamid``).
    channel_endpoint_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    #: The channel's own message id (Meta's ``wamid``).
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    template_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: Canonical content produced by the adapter — never a provider's payload shape.
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    media_asset_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MSG_ACCEPTED)
    error_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    pricing_model: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Message id={self.id} {self.direction} {self.status}>"


class MessageStatusHistory(IntPKMixin, Base):
    """One delivery-status transition, append-only (Doc 03 §9.3)."""

    __tablename__ = "message_status_history"
    __table_args__ = (
        Index("ix_msh_message", "message_id", "created_at"),
        Index("ix_msh_wamid", "wamid"),
        Index("ix_msh_status", "status", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    #: App-enforced FK to ``messages.id`` (both tables are partitioned).
    message_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recipient_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    #: The channel's timestamp for the transition, not ours (Doc 03 §9.3).
    occurred_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<MessageStatusHistory message_id={self.message_id} {self.status}>"
