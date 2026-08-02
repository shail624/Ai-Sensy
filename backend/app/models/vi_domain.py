"""Tenant-scoped Vi reactivation domain foundation (CORE-02).

Mutable aggregates carry optimistic row versions. Decisions and lifecycle events are
append-only records; no update or delete service is exposed for those tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
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
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, uuid_binary

REACTIVATION_STAGES: tuple[str, ...] = (
    "new_lead",
    "follow_up",
    "interested",
    "eligibility_check",
    "eligible",
    "documents_pending",
    "documents_received",
    "kyc_pending",
    "verification",
    "confirmed",
    "sim_order",
    "activation_pending",
    "completed",
    "not_eligible",
    "not_interested",
)
REACTIVATION_TERMINAL_STAGES = frozenset({"completed", "not_eligible", "not_interested"})
REACTIVATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "new_lead": frozenset({"follow_up", "not_interested"}),
    "follow_up": frozenset({"interested", "not_interested"}),
    "interested": frozenset({"eligibility_check", "not_interested"}),
    "eligibility_check": frozenset({"eligible", "not_eligible"}),
    "eligible": frozenset({"documents_pending"}),
    "documents_pending": frozenset({"documents_received"}),
    "documents_received": frozenset({"kyc_pending"}),
    "kyc_pending": frozenset({"verification"}),
    "verification": frozenset({"confirmed", "documents_pending", "not_eligible"}),
    "confirmed": frozenset({"sim_order"}),
    "sim_order": frozenset({"activation_pending"}),
    "activation_pending": frozenset({"completed"}),
    "completed": frozenset(),
    "not_eligible": frozenset(),
    "not_interested": frozenset(),
}

ELIGIBILITY_STATUSES = ("pending", "eligible", "not_eligible", "review_required")
ELIGIBILITY_SOURCES = ("rules", "manual", "override")
KYC_STATUSES = ("pending", "documents_pending", "under_review", "approved", "rejected")
KYC_PREPARATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"documents_pending", "under_review"}),
    "documents_pending": frozenset({"pending", "under_review"}),
    "under_review": frozenset({"documents_pending"}),
}
KYC_DECISIONS = ("approved", "rejected", "needs_information")
KYC_DECISION_TYPES = ("review", "manager_approval")
SIM_ORDER_STATUSES = (
    "requested",
    "approved",
    "assigned",
    "dispatched",
    "delivered",
    "failed",
    "cancelled",
)
SIM_ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "requested": frozenset({"approved", "cancelled"}),
    "approved": frozenset({"assigned", "cancelled"}),
    "assigned": frozenset({"dispatched", "failed", "cancelled"}),
    "dispatched": frozenset({"delivered", "failed"}),
    "failed": frozenset({"assigned", "cancelled"}),
    "delivered": frozenset(),
    "cancelled": frozenset(),
}
ACTIVATION_STATUSES = ("pending", "verification", "ready", "approved", "completed", "rejected")
ACTIVATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"verification", "rejected"}),
    "verification": frozenset({"ready", "rejected"}),
    "ready": frozenset({"approved", "rejected"}),
    "approved": frozenset({"completed"}),
    "completed": frozenset(),
    "rejected": frozenset(),
}
SLA_DOMAINS = ("reactivation", "kyc", "sim", "activation")
SLA_EVENT_TYPES = ("started", "breached", "resolved")
SLA_ENTITY_TYPES = ("reactivation_case", "kyc_case", "sim_order", "activation_record")


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ReactivationCase(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    __tablename__ = "reactivation_cases"
    __table_args__ = (
        UniqueConstraint("organization_id", "contact_id", name="uq_reactivation_org_contact"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_reactivation_idem"),
        Index("ix_reactivation_org_stage_updated", "organization_id", "stage", "updated_at"),
        CheckConstraint(_in_clause("stage", REACTIVATION_STAGES), name="ck_reactivation_stage"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="new_lead")
    owner_user_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_vi_number: Mapped[str | None] = mapped_column(String(24), nullable=True)
    active_delhi_number: Mapped[str | None] = mapped_column(String(24), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    closed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ReactivationStageEvent(IntPKMixin, UUIDMixin, Base):
    __tablename__ = "reactivation_stage_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_reactivation_stage_idem"),
        Index("ix_reactivation_stage_case_created", "case_id", "created_at"),
        CheckConstraint(
            _in_clause("to_stage", REACTIVATION_STAGES), name="ck_reactivation_event_to"
        ),
        CheckConstraint(
            f"from_stage IS NULL OR {_in_clause('from_stage', REACTIVATION_STAGES)}",
            name="ck_reactivation_event_from",
        ),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class EligibilityCheck(IntPKMixin, UUIDMixin, Base):
    __tablename__ = "eligibility_checks"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_eligibility_idem"),
        Index("ix_eligibility_case_created", "case_id", "created_at"),
        CheckConstraint(_in_clause("status", ELIGIBILITY_STATUSES), name="ck_eligibility_status"),
        CheckConstraint(_in_clause("source", ELIGIBILITY_SOURCES), name="ck_eligibility_source"),
        CheckConstraint(
            "source != 'override' OR approval_reference IS NOT NULL",
            name="ck_eligibility_override_approval",
        ),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    checked_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class KycCase(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    __tablename__ = "kyc_cases"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_kyc_reactivation_case"
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_kyc_idem"),
        Index("ix_kyc_org_status_updated", "organization_id", "status", "updated_at"),
        CheckConstraint(_in_clause("status", KYC_STATUSES), name="ck_kyc_status"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reactivation_case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    owner_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    holder_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delhi_presence_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active_delhi_number_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    appointment_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class KycDecision(IntPKMixin, UUIDMixin, Base):
    __tablename__ = "kyc_decisions"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_kyc_decision_idem"),
        Index("ix_kyc_decision_case_created", "kyc_case_id", "created_at"),
        CheckConstraint(
            _in_clause("decision_type", KYC_DECISION_TYPES), name="ck_kyc_decision_type"
        ),
        CheckConstraint(_in_clause("decision", KYC_DECISIONS), name="ck_kyc_decision_value"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    kyc_case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(24), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class SimOrder(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    __tablename__ = "sim_orders"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_sim_reactivation_case"
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_sim_order_idem"),
        UniqueConstraint("organization_id", "sim_serial", name="uq_sim_order_serial"),
        Index("ix_sim_order_org_status_updated", "organization_id", "status", "updated_at"),
        CheckConstraint(_in_clause("status", SIM_ORDER_STATUSES), name="ck_sim_order_status"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reactivation_case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="requested")
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    service_area: Mapped[str] = mapped_column(String(80), nullable=False, default="Delhi NCR")
    delivery_owner_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sim_serial: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class SimOrderEvent(IntPKMixin, UUIDMixin, Base):
    __tablename__ = "sim_order_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_sim_order_event_idem"),
        Index("ix_sim_order_event_order_created", "sim_order_id", "created_at"),
        CheckConstraint(_in_clause("to_status", SIM_ORDER_STATUSES), name="ck_sim_event_status"),
        CheckConstraint(
            f"from_status IS NULL OR {_in_clause('from_status', SIM_ORDER_STATUSES)}",
            name="ck_sim_event_from",
        ),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    sim_order_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("sim_orders.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)


class ActivationRecord(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    __tablename__ = "activation_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_activation_reactivation_case"
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_activation_idem"),
        Index("ix_activation_org_status_updated", "organization_id", "status", "updated_at"),
        CheckConstraint(_in_clause("status", ACTIVATION_STATUSES), name="ck_activation_status"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reactivation_case_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("reactivation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    sim_order_id: Mapped[int | None] = mapped_column(
        big_id(), ForeignKey("sim_orders.id", ondelete="RESTRICT"), nullable=True
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    owner_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(uuid_binary(), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class SlaPolicy(IntPKMixin, UUIDMixin, TimestampMixin, AuditMixin, VersionMixin, Base):
    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint("organization_id", "domain", "trigger_name", name="uq_sla_policy_scope"),
        Index("ix_sla_policy_org_active", "organization_id", "is_active"),
        CheckConstraint(_in_clause("domain", SLA_DOMAINS), name="ck_sla_policy_domain"),
        CheckConstraint("target_minutes > 0", name="ck_sla_target_positive"),
        CheckConstraint("escalation_minutes >= target_minutes", name="ck_sla_escalation_order"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(24), nullable=False)
    trigger_name: Mapped[str] = mapped_column(String(64), nullable=False)
    target_minutes: Mapped[int] = mapped_column(nullable=False)
    escalation_minutes: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SlaEvent(IntPKMixin, UUIDMixin, Base):
    __tablename__ = "sla_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_sla_event_idem"),
        Index("ix_sla_event_entity_created", "entity_type", "entity_id", "created_at"),
        Index("ix_sla_event_org_type_due", "organization_id", "event_type", "due_at"),
        CheckConstraint(_in_clause("event_type", SLA_EVENT_TYPES), name="ck_sla_event_type"),
        CheckConstraint(_in_clause("entity_type", SLA_ENTITY_TYPES), name="ck_sla_entity_type"),
        MYSQL_TABLE_ARGS,
    )
    organization_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    policy_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("sla_policies.id", ondelete="RESTRICT"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    due_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[bytes] = mapped_column(nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
