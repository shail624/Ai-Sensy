"""Typed API contracts for the CORE-02 Vi domain foundation."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ReactivationStage = Literal[
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
]
EligibilityStatus = Literal["pending", "eligible", "not_eligible", "review_required"]
EligibilitySource = Literal["rules", "manual", "override"]
KycStatus = Literal["pending", "documents_pending", "under_review", "approved", "rejected"]
KycDecisionValue = Literal["approved", "rejected", "needs_information"]
KycDocumentPurpose = Literal["aadhaar", "pan"]
KycReasonCode = Literal[
    "holder_mismatch",
    "delhi_presence_unverified",
    "active_number_unverified",
    "aadhaar_missing",
    "pan_missing",
    "document_unreadable",
    "document_mismatch",
    "customer_unavailable",
    "other",
]
SimOrderStatus = Literal[
    "requested", "approved", "assigned", "dispatched", "delivered", "failed", "cancelled"
]
ActivationStatus = Literal["pending", "verification", "ready", "approved", "completed", "rejected"]
SlaDomain = Literal["reactivation", "kyc", "sim", "activation"]
SlaEventType = Literal["started", "breached", "resolved"]
SlaEntityType = Literal["reactivation_case", "kyc_case", "sim_order", "activation_record"]


class IdempotentRequest(BaseModel):
    idempotency_key: uuidlib.UUID


class VersionedRequest(BaseModel):
    expected_row_version: int = Field(ge=0)


class ReactivationCreateRequest(IdempotentRequest):
    owner_user_id: uuidlib.UUID | None = None
    previous_vi_number: str | None = Field(default=None, max_length=24)
    active_delhi_number: str | None = Field(default=None, max_length=24)
    source: str = Field(default="manual", min_length=1, max_length=40)


class ReactivationUpdateRequest(VersionedRequest):
    owner_user_id: uuidlib.UUID | None = None
    previous_vi_number: str | None = Field(default=None, max_length=24)
    active_delhi_number: str | None = Field(default=None, max_length=24)


class ReactivationTransitionRequest(IdempotentRequest, VersionedRequest):
    to_stage: ReactivationStage
    reason: str | None = Field(default=None, max_length=2000)


class ReactivationNoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4096)


class EligibilityCreateRequest(IdempotentRequest):
    status: EligibilityStatus
    source: EligibilitySource
    reason: str | None = Field(default=None, max_length=2000)
    approval_reference: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_approval(self) -> EligibilityCreateRequest:
        if self.source == "override" and not (self.approval_reference or "").strip():
            raise ValueError("approval_reference is required for an eligibility override")
        if self.status == "not_eligible" and not (self.reason or "").strip():
            raise ValueError("reason is required for a not-eligible decision")
        return self


class KycCreateRequest(IdempotentRequest):
    owner_user_id: uuidlib.UUID | None = None
    appointment_at: datetime | None = None


class KycUpdateRequest(VersionedRequest):
    status: Literal["pending", "documents_pending", "under_review"]
    owner_user_id: uuidlib.UUID | None = None
    holder_verified: bool
    delhi_presence_verified: bool
    active_delhi_number_verified: bool
    appointment_at: datetime | None = None


class KycDecisionRequest(IdempotentRequest, VersionedRequest):
    decision: KycDecisionValue
    reason_code: KycReasonCode | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_reason(self) -> KycDecisionRequest:
        if self.decision != "approved" and not (self.reason or "").strip():
            raise ValueError("reason is required unless approving")
        if self.decision != "approved" and self.reason_code is None:
            raise ValueError("reason_code is required unless approving")
        if self.decision == "approved" and self.reason_code is not None:
            raise ValueError("reason_code is only valid for a non-approval decision")
        return self


class KycDocumentReferenceRequest(VersionedRequest):
    purpose: KycDocumentPurpose
    document_id: uuidlib.UUID


class KycAppointmentCreateRequest(IdempotentRequest, VersionedRequest):
    due_at: datetime
    reminder_at: datetime | None = None
    assigned_agent_id: uuidlib.UUID | None = None
    description: str | None = Field(default=None, max_length=4096)


class SimOrderCreateRequest(IdempotentRequest):
    delivery_address: str = Field(min_length=1, max_length=2000)
    service_area: str = Field(default="Delhi NCR", min_length=1, max_length=80)
    delivery_owner_user_id: uuidlib.UUID | None = None


class SimOrderUpdateRequest(VersionedRequest):
    delivery_address: str = Field(min_length=1, max_length=2000)
    service_area: str = Field(min_length=1, max_length=80)
    delivery_owner_user_id: uuidlib.UUID | None = None
    sim_serial: str | None = Field(default=None, max_length=64)
    customer_confirmed: bool = False


class SimOrderTransitionRequest(IdempotentRequest, VersionedRequest):
    to_status: SimOrderStatus
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_reason(self) -> SimOrderTransitionRequest:
        if self.to_status in {"failed", "cancelled"} and not (self.reason or "").strip():
            raise ValueError("reason is required for failure or cancellation")
        return self


class ActivationCreateRequest(IdempotentRequest):
    sim_order_id: uuidlib.UUID | None = None
    owner_user_id: uuidlib.UUID | None = None


class ActivationUpdateRequest(VersionedRequest):
    owner_user_id: uuidlib.UUID | None = None
    sim_order_id: uuidlib.UUID | None = None


class ActivationTransitionRequest(IdempotentRequest, VersionedRequest):
    to_status: ActivationStatus
    approval_reference: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_boundary(self) -> ActivationTransitionRequest:
        if (
            self.to_status in {"approved", "completed"}
            and not (self.approval_reference or "").strip()
        ):
            raise ValueError("approval_reference is required for approval and completion")
        if self.to_status == "rejected" and not (self.reason or "").strip():
            raise ValueError("reason is required when rejecting activation")
        return self


class SlaPolicyCreateRequest(BaseModel):
    domain: SlaDomain
    trigger_name: str = Field(min_length=1, max_length=64)
    target_minutes: int = Field(gt=0)
    escalation_minutes: int = Field(gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_escalation(self) -> SlaPolicyCreateRequest:
        if self.escalation_minutes < self.target_minutes:
            raise ValueError("escalation_minutes must be at least target_minutes")
        return self


class SlaPolicyUpdateRequest(SlaPolicyCreateRequest, VersionedRequest):
    pass


class SlaEventCreateRequest(IdempotentRequest):
    policy_id: uuidlib.UUID
    contact_id: uuidlib.UUID
    entity_type: SlaEntityType
    entity_id: uuidlib.UUID
    event_type: SlaEventType
    due_at: datetime
    reason: str | None = Field(default=None, max_length=2000)


class ReactivationCaseResponse(BaseModel):
    id: uuidlib.UUID
    contact_id: uuidlib.UUID
    stage: ReactivationStage
    owner_user_id: uuidlib.UUID | None
    previous_vi_number: str | None
    active_delhi_number: str | None
    source: str
    closed_reason: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class ReactivationPipelineCardResponse(ReactivationCaseResponse):
    available_transitions: list[ReactivationStage]
    contact_name: str
    contact_phone: str
    contact_email: str | None
    contact_attributes: dict[str, Any]
    owner_name: str | None
    stage_entered_at: datetime
    latest_eligibility_status: EligibilityStatus | None
    latest_eligibility_reason: str | None
    open_task_count: int = Field(ge=0)
    overdue_task_count: int = Field(ge=0)
    next_task_due_at: datetime | None
    document_count: int = Field(ge=0)
    verified_document_count: int = Field(ge=0)
    sla_status: Literal["not_configured", "on_track", "breached", "resolved"]
    sla_due_at: datetime | None
    reservation_status: str | None
    family_plan_required: bool | None
    family_numbers: list[str]
    conversion_indicator: Literal["open", "converted", "lost"]


class ReactivationStageCountResponse(BaseModel):
    stage: ReactivationStage
    count: int = Field(ge=0)


class ReactivationPipelineResponse(BaseModel):
    data: list[ReactivationPipelineCardResponse]
    total: int = Field(ge=0)
    visible: int = Field(ge=0)
    stage_counts: list[ReactivationStageCountResponse]


class ReactivationNoteResponse(BaseModel):
    id: int
    case_id: uuidlib.UUID
    actor_user_id: uuidlib.UUID
    body: str
    created_at: datetime


class ReactivationNoteListResponse(BaseModel):
    data: list[ReactivationNoteResponse]


class ReactivationStageEventResponse(BaseModel):
    id: uuidlib.UUID
    case_id: uuidlib.UUID
    from_stage: ReactivationStage | None
    to_stage: ReactivationStage
    actor_user_id: uuidlib.UUID | None
    reason: str | None
    created_at: datetime


class EligibilityCheckResponse(BaseModel):
    id: uuidlib.UUID
    case_id: uuidlib.UUID
    status: EligibilityStatus
    source: EligibilitySource
    reason: str | None
    approval_reference: str | None
    checked_by: uuidlib.UUID | None
    checked_at: datetime


class KycCaseResponse(BaseModel):
    id: uuidlib.UUID
    reactivation_case_id: uuidlib.UUID
    contact_id: uuidlib.UUID
    status: KycStatus
    owner_user_id: uuidlib.UUID | None
    requester_user_id: uuidlib.UUID | None
    holder_verified: bool
    delhi_presence_verified: bool
    active_delhi_number_verified: bool
    appointment_at: datetime | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class KycDecisionResponse(BaseModel):
    id: uuidlib.UUID
    kyc_case_id: uuidlib.UUID
    decision_type: Literal["review", "manager_approval"]
    decision: KycDecisionValue
    reason_code: KycReasonCode | None
    reason: str | None
    decided_by: uuidlib.UUID | None
    decided_at: datetime


class KycDocumentReferenceResponse(BaseModel):
    id: uuidlib.UUID
    kyc_case_id: uuidlib.UUID
    purpose: KycDocumentPurpose
    document_id: uuidlib.UUID
    document_title: str
    document_type: str
    document_status: str
    row_version: int
    created_at: datetime
    updated_at: datetime


class KycAppointmentResponse(BaseModel):
    id: str
    title: str
    status: str
    due_at: datetime
    reminder_at: datetime | None
    assigned_agent_id: str
    assigned_agent_name: str | None
    row_version: int


class KycOperationsCardResponse(KycCaseResponse):
    contact_name: str
    contact_phone: str
    contact_email: str | None
    owner_name: str | None
    reactivation_stage: ReactivationStage
    checklist: list[KycDocumentReferenceResponse]
    checklist_complete: bool
    progress_percent: int = Field(ge=0, le=100)
    latest_review: KycDecisionResponse | None
    latest_manager_decision: KycDecisionResponse | None
    appointments: list[KycAppointmentResponse]
    sla_status: Literal["not_configured", "on_track", "breached", "resolved"]
    sla_due_at: datetime | None


class SimOrderResponse(BaseModel):
    id: uuidlib.UUID
    reactivation_case_id: uuidlib.UUID
    contact_id: uuidlib.UUID
    status: SimOrderStatus
    delivery_address: str
    service_area: str
    delivery_owner_user_id: uuidlib.UUID | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    sim_serial: str | None
    customer_confirmed: bool
    row_version: int
    created_at: datetime
    updated_at: datetime


class SimOrderEventResponse(BaseModel):
    id: uuidlib.UUID
    sim_order_id: uuidlib.UUID
    from_status: SimOrderStatus | None
    to_status: SimOrderStatus
    actor_user_id: uuidlib.UUID | None
    reason: str | None
    created_at: datetime


class ActivationRecordResponse(BaseModel):
    id: uuidlib.UUID
    reactivation_case_id: uuidlib.UUID
    sim_order_id: uuidlib.UUID | None
    contact_id: uuidlib.UUID
    status: ActivationStatus
    owner_user_id: uuidlib.UUID | None
    approval_reference: str | None
    approved_by: uuidlib.UUID | None
    approved_at: datetime | None
    completed_at: datetime | None
    rejection_reason: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class SlaPolicyResponse(BaseModel):
    id: uuidlib.UUID
    domain: SlaDomain
    trigger_name: str
    target_minutes: int
    escalation_minutes: int
    is_active: bool
    row_version: int
    created_at: datetime
    updated_at: datetime


class SlaEventResponse(BaseModel):
    id: uuidlib.UUID
    policy_id: uuidlib.UUID
    contact_id: uuidlib.UUID
    entity_type: SlaEntityType
    entity_id: uuidlib.UUID
    event_type: SlaEventType
    due_at: datetime
    actor_user_id: uuidlib.UUID | None
    reason: str | None
    created_at: datetime


class ReactivationCaseListResponse(BaseModel):
    data: list[ReactivationCaseResponse]
    total: int


class StageEventListResponse(BaseModel):
    data: list[ReactivationStageEventResponse]


class EligibilityListResponse(BaseModel):
    data: list[EligibilityCheckResponse]


class KycCaseListResponse(BaseModel):
    data: list[KycCaseResponse]
    total: int


class KycDecisionListResponse(BaseModel):
    data: list[KycDecisionResponse]


class KycDocumentReferenceListResponse(BaseModel):
    data: list[KycDocumentReferenceResponse]


class KycAppointmentListResponse(BaseModel):
    data: list[KycAppointmentResponse]


class KycOperationsResponse(BaseModel):
    data: list[KycOperationsCardResponse]
    total: int


class SimOrderListResponse(BaseModel):
    data: list[SimOrderResponse]
    total: int


class SimOrderEventListResponse(BaseModel):
    data: list[SimOrderEventResponse]


class ActivationRecordListResponse(BaseModel):
    data: list[ActivationRecordResponse]
    total: int


class SlaPolicyListResponse(BaseModel):
    data: list[SlaPolicyResponse]
    total: int


class SlaEventListResponse(BaseModel):
    data: list[SlaEventResponse]
    total: int
