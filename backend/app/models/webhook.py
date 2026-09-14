"""Inbound webhook models (Doc 03 §9.4; Doc 06 §11) — FR-WA-05/07/08.

``webhook_events`` is the **durability record of the ingest path**: a delivery is verified,
written here, and acked with ``200`` before anything is interpreted, so a crash between ack and
processing costs latency rather than an event (Doc 06 §11.2). One row per canonical event, because
`event_id` is what makes processing idempotent (FR-WA-07) — Meta retries a delivery for up to 7
days and every retry must be recognisable as the same event.

``webhook_dead_letter`` is where an event that cannot be processed is **isolated** (§11.6): kept
with its payload for inspection and replay rather than blocking the stream or being dropped.
Distinct from ``dead_letter`` (Doc 06 §7), which parks *tasks* — this parks *events*, and the two
have different owners, retention (180 days, Doc 04 §23.1) and replay paths.

On MySQL ``webhook_events`` carries the composite ``(id, created_at)`` primary key its monthly
range partitioning requires (applied in the migration); the ORM maps the surrogate ``id``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, small_uint

# webhook_events.status (Doc 03 §9.4)
WH_RECEIVED = "received"
WH_PROCESSED = "processed"
WH_FAILED = "failed"
WH_DUPLICATE = "duplicate"
WH_STATUSES = (WH_RECEIVED, WH_PROCESSED, WH_FAILED, WH_DUPLICATE)
#: Terminal states — a task redelivery for one of these is a no-op (Doc 06 §8).
WH_SETTLED = (WH_PROCESSED, WH_DUPLICATE)

# webhook_dead_letter.status (Doc 03 §9.4)
WHDL_PENDING = "pending"
WHDL_REPLAYED = "replayed"
WHDL_DISCARDED = "discarded"


class WebhookEvent(IntPKMixin, Base):
    """One inbound event, persisted before it is processed (Doc 03 §9.4; FR-WA-05)."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_whe_status", "status", "created_at"),
        # Non-unique on purpose: a duplicate delivery is *recorded* and marked ``duplicate``
        # (Doc 03 §9.4), not rejected by the database — the evidence of a retry has value.
        Index("ix_whe_event", "event_id"),
        Index("ix_whe_number", "phone_number_id", "created_at"),
        # The channel-endpoint-scoped analogue, for a WAHA delivery (QR-08).
        Index("ix_whe_endpoint", "channel_endpoint_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    #: Dedup key (FR-WA-07): Meta's message id, or message id + state for a status callback.
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    #: FK to ``phone_numbers.id`` — resolved at ingest from the channel's own number id. NULL means
    #: the event is for a number we do not own, or is routed by ``channel_endpoint_id`` instead;
    #: app-enforced (the table is partitioned, no FKs).
    phone_number_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: FK to ``channel_endpoints.id`` — resolved at ingest from the WAHA session name (QR-08).
    #: ``NULL`` for a Meta event, which routes by ``phone_number_id`` instead. App-enforced, same
    #: as ``phone_number_id``.
    channel_endpoint_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: Canonical event type (``InboundEventType``) — what the processor routes on.
    object_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    #: Always true for stored rows: an unverified body is rejected and never reaches this table.
    signature_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=WH_RECEIVED)
    processed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    attempts: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    @property
    def is_settled(self) -> bool:
        return self.status in WH_SETTLED

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<WebhookEvent id={self.id} {self.object_type} {self.status}>"


class WebhookDeadLetter(IntPKMixin, UUIDMixin, Base):
    """An event that could not be processed, kept for replay (Doc 03 §9.4; FR-WA-08)."""

    __tablename__ = "webhook_dead_letter"
    __table_args__ = (
        Index("ix_whdl_status", "status", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    #: ``webhook_events.id`` this came from; app-enforced (the source table is partitioned).
    source_event_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: Copied, not referenced: the source row ages out on its own retention (90 days vs 180,
    #: Doc 04 §23.1), and a dead letter without its payload could not be replayed.
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    attempts: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=WHDL_PENDING)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    replayed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<WebhookDeadLetter id={self.id} {self.status}>"
