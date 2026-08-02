"""Immutable enterprise business-event ledger (Design Book 03 §21)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

BUSINESS_EVENT_ACTOR_USER = "user"
BUSINESS_EVENT_ACTOR_SYSTEM = "system"
BUSINESS_EVENT_ACTOR_AI = "ai"
BUSINESS_EVENT_ACTOR_CONNECTOR = "connector"
BUSINESS_EVENT_ACTORS = (
    BUSINESS_EVENT_ACTOR_USER,
    BUSINESS_EVENT_ACTOR_SYSTEM,
    BUSINESS_EVENT_ACTOR_AI,
    BUSINESS_EVENT_ACTOR_CONNECTOR,
)

BUSINESS_EVENT_CONTACT_CREATED = "contact.created"
BUSINESS_EVENT_REACTIVATION_CREATED = "reactivation.case.created"
BUSINESS_EVENT_REACTIVATION_TRANSITIONED = "reactivation.stage.transitioned"
BUSINESS_EVENT_ELIGIBILITY_DECIDED = "reactivation.eligibility.decided"
BUSINESS_EVENT_KYC_DECIDED = "kyc.decision.recorded"
BUSINESS_EVENT_SIM_TRANSITIONED = "sim.order.transitioned"
BUSINESS_EVENT_ACTIVATION_TRANSITIONED = "sim.activation.transitioned"
BUSINESS_EVENT_SLA_RECORDED = "audit.sla.recorded"


class BusinessEventType(IntPKMixin, Base):
    """One governed type/version in the additive event taxonomy."""

    __tablename__ = "business_event_types"
    __table_args__ = (
        UniqueConstraint("event_type", "event_version", name="uq_bet_type_version"),
        Index("ix_bet_category", "category"),
        CheckConstraint(
            "category IN ('lead','kyc','payment','sim','campaign','ai','template',"
            "'connector','user','audit')",
            name="ck_bet_category",
        ),
        MYSQL_TABLE_ARGS,
    )

    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class BusinessEvent(IntPKMixin, UUIDMixin, Base):
    """One append-only business fact; no ORM update or delete service exists."""

    __tablename__ = "business_events"
    __table_args__ = (
        Index("ix_be_type_time", "event_type", "occurred_at"),
        Index("ix_be_subject", "subject_type", "subject_id", "occurred_at"),
        Index("ix_be_campaign", "campaign_id", "occurred_at"),
        Index("ix_be_contact", "contact_id", "occurred_at"),
        Index("ix_be_channel", "channel_type", "occurred_at"),
        Index("ix_be_correlation", "correlation_id"),
        CheckConstraint(
            "actor_type IN ('user','system','ai','connector')",
            name="ck_business_events_actor_type",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    occurred_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    actor_type: Mapped[str] = mapped_column(String(12), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    channel_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    connector_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    campaign_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    contact_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    schema_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
