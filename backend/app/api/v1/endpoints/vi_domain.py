"""Permission-scoped CORE-02 Vi domain APIs."""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.vi_domain import (
    ActivationCreateRequest,
    ActivationRecordListResponse,
    ActivationRecordResponse,
    ActivationTransitionRequest,
    ActivationUpdateRequest,
    EligibilityCheckResponse,
    EligibilityCreateRequest,
    EligibilityListResponse,
    KycCaseListResponse,
    KycCaseResponse,
    KycCreateRequest,
    KycDecisionListResponse,
    KycDecisionRequest,
    KycDecisionResponse,
    KycUpdateRequest,
    ReactivationCaseListResponse,
    ReactivationCaseResponse,
    ReactivationCreateRequest,
    ReactivationStageEventResponse,
    ReactivationTransitionRequest,
    ReactivationUpdateRequest,
    SimOrderCreateRequest,
    SimOrderEventListResponse,
    SimOrderEventResponse,
    SimOrderListResponse,
    SimOrderResponse,
    SimOrderTransitionRequest,
    SimOrderUpdateRequest,
    SlaEventCreateRequest,
    SlaEventListResponse,
    SlaEventResponse,
    SlaPolicyCreateRequest,
    SlaPolicyListResponse,
    SlaPolicyResponse,
    SlaPolicyUpdateRequest,
    StageEventListResponse,
)
from app.services.vi_domain_service import ViDomainService

router = APIRouter()

ReactivationReader = Annotated[User, Depends(require_permissions("reactivation:read"))]
ReactivationWriter = Annotated[User, Depends(require_permissions("reactivation:write"))]
ReactivationTransitioner = Annotated[User, Depends(require_permissions("reactivation:transition"))]
KycReader = Annotated[User, Depends(require_permissions("kyc:read"))]
KycWriter = Annotated[User, Depends(require_permissions("kyc:write"))]
KycReviewer = Annotated[User, Depends(require_permissions("kyc:decide"))]
KycApprover = Annotated[User, Depends(require_permissions("kyc:approve"))]
SimReader = Annotated[User, Depends(require_permissions("sim:read"))]
SimWriter = Annotated[User, Depends(require_permissions("sim:write"))]
SimManager = Annotated[User, Depends(require_permissions("sim:manage"))]
ActivationReader = Annotated[User, Depends(require_permissions("activation:read"))]
ActivationWriter = Annotated[User, Depends(require_permissions("activation:write"))]
ActivationApprover = Annotated[User, Depends(require_permissions("activation:approve"))]
SlaReader = Annotated[User, Depends(require_permissions("sla:read"))]
SlaManager = Annotated[User, Depends(require_permissions("sla:manage"))]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/reactivation-cases", response_model=ReactivationCaseListResponse)
async def list_reactivation_cases(
    session: SessionDep,
    actor: ReactivationReader,
    contact_id: uuidlib.UUID | None = None,
    limit: Limit = 100,
) -> ReactivationCaseListResponse:
    rows, total = await ViDomainService(session).list_reactivation(
        actor.organization_id, contact_id=contact_id, limit=limit
    )
    return ReactivationCaseListResponse(
        data=[ReactivationCaseResponse(**row) for row in rows], total=total
    )


@router.get(
    "/contacts/{contact_id}/reactivation-cases", response_model=ReactivationCaseListResponse
)
async def list_contact_reactivation_cases(
    contact_id: uuidlib.UUID, session: SessionDep, actor: ReactivationReader
) -> ReactivationCaseListResponse:
    rows, total = await ViDomainService(session).list_reactivation(
        actor.organization_id, contact_id=contact_id, limit=100
    )
    return ReactivationCaseListResponse(
        data=[ReactivationCaseResponse(**row) for row in rows], total=total
    )


@router.post(
    "/contacts/{contact_id}/reactivation-cases",
    response_model=ReactivationCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reactivation_case(
    contact_id: uuidlib.UUID,
    payload: ReactivationCreateRequest,
    session: SessionDep,
    actor: ReactivationWriter,
) -> ReactivationCaseResponse:
    row = await ViDomainService(session).create_reactivation(
        organization_id=actor.organization_id,
        actor=actor,
        contact_id=contact_id,
        payload=payload.model_dump(),
    )
    return ReactivationCaseResponse(**row)


@router.get("/reactivation-cases/{case_id}", response_model=ReactivationCaseResponse)
async def get_reactivation_case(
    case_id: uuidlib.UUID, session: SessionDep, actor: ReactivationReader
) -> ReactivationCaseResponse:
    return ReactivationCaseResponse(
        **await ViDomainService(session).get_reactivation(actor.organization_id, case_id)
    )


@router.patch("/reactivation-cases/{case_id}", response_model=ReactivationCaseResponse)
async def update_reactivation_case(
    case_id: uuidlib.UUID,
    payload: ReactivationUpdateRequest,
    session: SessionDep,
    actor: ReactivationWriter,
) -> ReactivationCaseResponse:
    return ReactivationCaseResponse(
        **await ViDomainService(session).update_reactivation(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.post("/reactivation-cases/{case_id}/transition", response_model=ReactivationCaseResponse)
async def transition_reactivation_case(
    case_id: uuidlib.UUID,
    payload: ReactivationTransitionRequest,
    session: SessionDep,
    actor: ReactivationTransitioner,
) -> ReactivationCaseResponse:
    return ReactivationCaseResponse(
        **await ViDomainService(session).transition_reactivation(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/reactivation-cases/{case_id}/stage-events", response_model=StageEventListResponse)
async def list_reactivation_stage_events(
    case_id: uuidlib.UUID, session: SessionDep, actor: ReactivationReader
) -> StageEventListResponse:
    rows = await ViDomainService(session).stage_events(actor.organization_id, case_id)
    return StageEventListResponse(data=[ReactivationStageEventResponse(**row) for row in rows])


@router.get(
    "/reactivation-cases/{case_id}/eligibility-checks", response_model=EligibilityListResponse
)
async def list_eligibility_checks(
    case_id: uuidlib.UUID, session: SessionDep, actor: ReactivationReader
) -> EligibilityListResponse:
    rows = await ViDomainService(session).list_eligibility(actor.organization_id, case_id)
    return EligibilityListResponse(data=[EligibilityCheckResponse(**row) for row in rows])


@router.post(
    "/reactivation-cases/{case_id}/eligibility-checks",
    response_model=EligibilityCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_eligibility_check(
    case_id: uuidlib.UUID,
    payload: EligibilityCreateRequest,
    session: SessionDep,
    actor: ReactivationTransitioner,
) -> EligibilityCheckResponse:
    return EligibilityCheckResponse(
        **await ViDomainService(session).create_eligibility(
            organization_id=actor.organization_id,
            actor=actor,
            case_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/eligibility-checks/{check_id}", response_model=EligibilityCheckResponse)
async def get_eligibility_check(
    check_id: uuidlib.UUID, session: SessionDep, actor: ReactivationReader
) -> EligibilityCheckResponse:
    return EligibilityCheckResponse(
        **await ViDomainService(session).get_eligibility(actor.organization_id, check_id)
    )


@router.get("/kyc-cases", response_model=KycCaseListResponse)
async def list_kyc_cases(
    session: SessionDep,
    actor: KycReader,
    contact_id: uuidlib.UUID | None = None,
    limit: Limit = 100,
) -> KycCaseListResponse:
    rows, total = await ViDomainService(session).list_kyc(
        actor.organization_id, contact_id=contact_id, limit=limit
    )
    return KycCaseListResponse(data=[KycCaseResponse(**row) for row in rows], total=total)


@router.get("/contacts/{contact_id}/kyc-cases", response_model=KycCaseListResponse)
async def list_contact_kyc_cases(
    contact_id: uuidlib.UUID, session: SessionDep, actor: KycReader
) -> KycCaseListResponse:
    rows, total = await ViDomainService(session).list_kyc(
        actor.organization_id, contact_id=contact_id, limit=100
    )
    return KycCaseListResponse(data=[KycCaseResponse(**row) for row in rows], total=total)


@router.post(
    "/reactivation-cases/{case_id}/kyc-cases",
    response_model=KycCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kyc_case(
    case_id: uuidlib.UUID, payload: KycCreateRequest, session: SessionDep, actor: KycWriter
) -> KycCaseResponse:
    return KycCaseResponse(
        **await ViDomainService(session).create_kyc(
            organization_id=actor.organization_id,
            actor=actor,
            reactivation_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/kyc-cases/{kyc_id}", response_model=KycCaseResponse)
async def get_kyc_case(
    kyc_id: uuidlib.UUID, session: SessionDep, actor: KycReader
) -> KycCaseResponse:
    return KycCaseResponse(**await ViDomainService(session).get_kyc(actor.organization_id, kyc_id))


@router.patch("/kyc-cases/{kyc_id}", response_model=KycCaseResponse)
async def update_kyc_case(
    kyc_id: uuidlib.UUID, payload: KycUpdateRequest, session: SessionDep, actor: KycWriter
) -> KycCaseResponse:
    return KycCaseResponse(
        **await ViDomainService(session).update_kyc(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=kyc_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/kyc-cases/{kyc_id}/decisions", response_model=KycDecisionListResponse)
async def list_kyc_decisions(
    kyc_id: uuidlib.UUID, session: SessionDep, actor: KycReader
) -> KycDecisionListResponse:
    rows = await ViDomainService(session).list_kyc_decisions(actor.organization_id, kyc_id)
    return KycDecisionListResponse(data=[KycDecisionResponse(**row) for row in rows])


@router.post(
    "/kyc-cases/{kyc_id}/decisions",
    response_model=KycDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_kyc_review(
    kyc_id: uuidlib.UUID, payload: KycDecisionRequest, session: SessionDep, actor: KycReviewer
) -> KycDecisionResponse:
    return KycDecisionResponse(
        **await ViDomainService(session).decide_kyc(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=kyc_id,
            payload=payload.model_dump(),
            manager_approval=False,
        )
    )


@router.post(
    "/kyc-cases/{kyc_id}/approvals",
    response_model=KycDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_kyc_approval(
    kyc_id: uuidlib.UUID, payload: KycDecisionRequest, session: SessionDep, actor: KycApprover
) -> KycDecisionResponse:
    return KycDecisionResponse(
        **await ViDomainService(session).decide_kyc(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=kyc_id,
            payload=payload.model_dump(),
            manager_approval=True,
        )
    )


@router.get("/kyc-decisions/{decision_id}", response_model=KycDecisionResponse)
async def get_kyc_decision(
    decision_id: uuidlib.UUID, session: SessionDep, actor: KycReader
) -> KycDecisionResponse:
    return KycDecisionResponse(
        **await ViDomainService(session).get_kyc_decision(actor.organization_id, decision_id)
    )


@router.get("/sim-orders", response_model=SimOrderListResponse)
async def list_sim_orders(
    session: SessionDep, actor: SimReader, case_id: uuidlib.UUID | None = None, limit: Limit = 100
) -> SimOrderListResponse:
    rows, total = await ViDomainService(session).list_sim_orders(
        actor.organization_id, case_id=case_id, limit=limit
    )
    return SimOrderListResponse(data=[SimOrderResponse(**row) for row in rows], total=total)


@router.get("/reactivation-cases/{case_id}/sim-orders", response_model=SimOrderListResponse)
async def list_case_sim_orders(
    case_id: uuidlib.UUID, session: SessionDep, actor: SimReader
) -> SimOrderListResponse:
    rows, total = await ViDomainService(session).list_sim_orders(
        actor.organization_id, case_id=case_id, limit=100
    )
    return SimOrderListResponse(data=[SimOrderResponse(**row) for row in rows], total=total)


@router.post(
    "/reactivation-cases/{case_id}/sim-orders",
    response_model=SimOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sim_order(
    case_id: uuidlib.UUID, payload: SimOrderCreateRequest, session: SessionDep, actor: SimWriter
) -> SimOrderResponse:
    return SimOrderResponse(
        **await ViDomainService(session).create_sim_order(
            organization_id=actor.organization_id,
            actor=actor,
            reactivation_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/sim-orders/{order_id}", response_model=SimOrderResponse)
async def get_sim_order(
    order_id: uuidlib.UUID, session: SessionDep, actor: SimReader
) -> SimOrderResponse:
    return SimOrderResponse(
        **await ViDomainService(session).get_sim_order(actor.organization_id, order_id)
    )


@router.patch("/sim-orders/{order_id}", response_model=SimOrderResponse)
async def update_sim_order(
    order_id: uuidlib.UUID, payload: SimOrderUpdateRequest, session: SessionDep, actor: SimWriter
) -> SimOrderResponse:
    return SimOrderResponse(
        **await ViDomainService(session).update_sim_order(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=order_id,
            payload=payload.model_dump(),
        )
    )


@router.post("/sim-orders/{order_id}/transition", response_model=SimOrderResponse)
async def transition_sim_order(
    order_id: uuidlib.UUID,
    payload: SimOrderTransitionRequest,
    session: SessionDep,
    actor: SimManager,
) -> SimOrderResponse:
    return SimOrderResponse(
        **await ViDomainService(session).transition_sim_order(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=order_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/sim-orders/{order_id}/events", response_model=SimOrderEventListResponse)
async def list_sim_order_events(
    order_id: uuidlib.UUID, session: SessionDep, actor: SimReader
) -> SimOrderEventListResponse:
    rows = await ViDomainService(session).sim_events(actor.organization_id, order_id)
    return SimOrderEventListResponse(data=[SimOrderEventResponse(**row) for row in rows])


@router.get("/sim-order-events/{event_id}", response_model=SimOrderEventResponse)
async def get_sim_order_event(
    event_id: uuidlib.UUID, session: SessionDep, actor: SimReader
) -> SimOrderEventResponse:
    return SimOrderEventResponse(
        **await ViDomainService(session).get_sim_event(actor.organization_id, event_id)
    )


@router.get("/activation-records", response_model=ActivationRecordListResponse)
async def list_activation_records(
    session: SessionDep,
    actor: ActivationReader,
    case_id: uuidlib.UUID | None = None,
    limit: Limit = 100,
) -> ActivationRecordListResponse:
    rows, total = await ViDomainService(session).list_activations(
        actor.organization_id, case_id=case_id, limit=limit
    )
    return ActivationRecordListResponse(
        data=[ActivationRecordResponse(**row) for row in rows], total=total
    )


@router.get(
    "/reactivation-cases/{case_id}/activation-records", response_model=ActivationRecordListResponse
)
async def list_case_activation_records(
    case_id: uuidlib.UUID, session: SessionDep, actor: ActivationReader
) -> ActivationRecordListResponse:
    rows, total = await ViDomainService(session).list_activations(
        actor.organization_id, case_id=case_id, limit=100
    )
    return ActivationRecordListResponse(
        data=[ActivationRecordResponse(**row) for row in rows], total=total
    )


@router.post(
    "/reactivation-cases/{case_id}/activation-records",
    response_model=ActivationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_activation_record(
    case_id: uuidlib.UUID,
    payload: ActivationCreateRequest,
    session: SessionDep,
    actor: ActivationWriter,
) -> ActivationRecordResponse:
    return ActivationRecordResponse(
        **await ViDomainService(session).create_activation(
            organization_id=actor.organization_id,
            actor=actor,
            reactivation_id=case_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/activation-records/{activation_id}", response_model=ActivationRecordResponse)
async def get_activation_record(
    activation_id: uuidlib.UUID, session: SessionDep, actor: ActivationReader
) -> ActivationRecordResponse:
    return ActivationRecordResponse(
        **await ViDomainService(session).get_activation(actor.organization_id, activation_id)
    )


@router.patch("/activation-records/{activation_id}", response_model=ActivationRecordResponse)
async def update_activation_record(
    activation_id: uuidlib.UUID,
    payload: ActivationUpdateRequest,
    session: SessionDep,
    actor: ActivationWriter,
) -> ActivationRecordResponse:
    return ActivationRecordResponse(
        **await ViDomainService(session).update_activation(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=activation_id,
            payload=payload.model_dump(),
        )
    )


@router.post(
    "/activation-records/{activation_id}/transition", response_model=ActivationRecordResponse
)
async def transition_activation_record(
    activation_id: uuidlib.UUID,
    payload: ActivationTransitionRequest,
    session: SessionDep,
    actor: ActivationWriter,
) -> ActivationRecordResponse:
    return ActivationRecordResponse(
        **await ViDomainService(session).transition_activation(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=activation_id,
            payload=payload.model_dump(),
            approval_command=False,
        )
    )


@router.post(
    "/activation-records/{activation_id}/approval", response_model=ActivationRecordResponse
)
async def approve_activation_record(
    activation_id: uuidlib.UUID,
    payload: ActivationTransitionRequest,
    session: SessionDep,
    actor: ActivationApprover,
) -> ActivationRecordResponse:
    return ActivationRecordResponse(
        **await ViDomainService(session).transition_activation(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=activation_id,
            payload=payload.model_dump(),
            approval_command=True,
        )
    )


@router.get("/sla/policies", response_model=SlaPolicyListResponse)
async def list_sla_policies(
    session: SessionDep, actor: SlaReader, limit: Limit = 100
) -> SlaPolicyListResponse:
    rows, total = await ViDomainService(session).list_sla_policies(actor.organization_id, limit)
    return SlaPolicyListResponse(data=[SlaPolicyResponse(**row) for row in rows], total=total)


@router.post("/sla/policies", response_model=SlaPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_sla_policy(
    payload: SlaPolicyCreateRequest, session: SessionDep, actor: SlaManager
) -> SlaPolicyResponse:
    return SlaPolicyResponse(
        **await ViDomainService(session).create_sla_policy(
            organization_id=actor.organization_id, actor=actor, payload=payload.model_dump()
        )
    )


@router.get("/sla/policies/{policy_id}", response_model=SlaPolicyResponse)
async def get_sla_policy(
    policy_id: uuidlib.UUID, session: SessionDep, actor: SlaReader
) -> SlaPolicyResponse:
    return SlaPolicyResponse(
        **await ViDomainService(session).get_sla_policy(actor.organization_id, policy_id)
    )


@router.patch("/sla/policies/{policy_id}", response_model=SlaPolicyResponse)
async def update_sla_policy(
    policy_id: uuidlib.UUID, payload: SlaPolicyUpdateRequest, session: SessionDep, actor: SlaManager
) -> SlaPolicyResponse:
    return SlaPolicyResponse(
        **await ViDomainService(session).update_sla_policy(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=policy_id,
            payload=payload.model_dump(),
        )
    )


@router.get("/sla/events", response_model=SlaEventListResponse)
async def list_sla_events(
    session: SessionDep, actor: SlaReader, limit: Limit = 100
) -> SlaEventListResponse:
    rows, total = await ViDomainService(session).list_sla_events(actor.organization_id, limit)
    return SlaEventListResponse(data=[SlaEventResponse(**row) for row in rows], total=total)


@router.post("/sla/events", response_model=SlaEventResponse, status_code=status.HTTP_201_CREATED)
async def create_sla_event(
    payload: SlaEventCreateRequest, session: SessionDep, actor: SlaManager
) -> SlaEventResponse:
    return SlaEventResponse(
        **await ViDomainService(session).create_sla_event(
            organization_id=actor.organization_id, actor=actor, payload=payload.model_dump()
        )
    )


@router.get("/sla/events/{event_id}", response_model=SlaEventResponse)
async def get_sla_event(
    event_id: uuidlib.UUID, session: SessionDep, actor: SlaReader
) -> SlaEventResponse:
    return SlaEventResponse(
        **await ViDomainService(session).get_sla_event(actor.organization_id, event_id)
    )
