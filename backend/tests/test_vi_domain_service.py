"""Focused CORE-02 domain, transition, concurrency and projection tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.exceptions import VersionConflictError
from app.models.audit import AuditLog
from app.models.business_event import BusinessEvent
from app.models.contact import Contact
from app.models.contact_document import ContactDocument
from app.models.contact_event import ContactEvent
from app.models.vi_domain import (
    REACTIVATION_STAGES,
    REACTIVATION_TRANSITIONS,
    KycCase,
    KycDecision,
    ReactivationCase,
    ReactivationStageEvent,
    SimOrder,
)
from app.services.vi_domain_service import IdempotencyConflictError, ViDomainService


async def _contact(session, organization_id: int, suffix: str = "1") -> Contact:
    row = Contact(
        organization_id=organization_id,
        wa_id=f"9199000000{suffix}",
        phone_e164=f"+9199000000{suffix}",
        full_name=f"Vi Customer {suffix}",
    )
    session.add(row)
    await session.commit()
    return row


@pytest.mark.asyncio
async def test_reactivation_is_idempotent_versioned_and_projected(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="core02-owner@vi.test", is_superuser=True)).user
    contact = await _contact(db_session, organization.id)
    service = ViDomainService(db_session)
    create_key = uuid.uuid4()
    create = {
        "idempotency_key": create_key,
        "owner_user_id": uuid.UUID(actor.public_id),
        "previous_vi_number": "9811111111",
        "active_delhi_number": "9822222222",
        "source": "manual",
    }

    first = await service.create_reactivation(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuid.UUID(contact.public_id),
        payload=create,
    )
    retried = await service.create_reactivation(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuid.UUID(contact.public_id),
        payload=create,
    )
    assert retried["id"] == first["id"]
    assert first["stage"] == "new_lead"

    transition_key = uuid.uuid4()
    command = {
        "idempotency_key": transition_key,
        "expected_row_version": 0,
        "to_stage": "follow_up",
        "reason": "Initial callback scheduled",
    }
    transitioned = await service.transition_reactivation(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(first["id"]),
        payload=command,
    )
    retried_transition = await service.transition_reactivation(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(first["id"]),
        payload=command,
    )
    assert transitioned["row_version"] == 1
    assert retried_transition["row_version"] == 1

    with pytest.raises(IdempotencyConflictError):
        await service.transition_reactivation(
            organization_id=organization.id,
            actor=actor,
            public_id=uuid.UUID(first["id"]),
            payload={**command, "to_stage": "not_interested"},
        )
    with pytest.raises(VersionConflictError):
        await service.transition_reactivation(
            organization_id=organization.id,
            actor=actor,
            public_id=uuid.UUID(first["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": 0,
                "to_stage": "interested",
                "reason": None,
            },
        )

    assert await db_session.scalar(select(func.count()).select_from(ReactivationCase)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ReactivationStageEvent)) == 2
    assert await db_session.scalar(select(func.count()).select_from(ContactEvent)) == 2
    assert await db_session.scalar(select(func.count()).select_from(BusinessEvent)) == 2
    assert await db_session.scalar(select(func.count()).select_from(AuditLog)) == 2


def test_reactivation_transition_matrix_is_closed_and_complete() -> None:
    expected = {
        "new_lead": {"follow_up", "not_interested"},
        "follow_up": {"interested", "not_interested"},
        "interested": {"eligibility_check", "not_interested"},
        "eligibility_check": {"eligible", "not_eligible"},
        "eligible": {"documents_pending"},
        "documents_pending": {"documents_received"},
        "documents_received": {"kyc_pending"},
        "kyc_pending": {"verification"},
        "verification": {"confirmed", "documents_pending", "not_eligible"},
        "confirmed": {"sim_order"},
        "sim_order": {"activation_pending"},
        "activation_pending": {"completed"},
        "completed": set(),
        "not_eligible": set(),
        "not_interested": set(),
    }
    assert tuple(expected) == REACTIVATION_STAGES
    assert {stage: set(targets) for stage, targets in REACTIVATION_TRANSITIONS.items()} == expected
    for source in REACTIVATION_STAGES:
        rejected = set(REACTIVATION_STAGES) - expected[source]
        assert source in rejected
        assert not (set(REACTIVATION_TRANSITIONS[source]) & rejected)


@pytest.mark.asyncio
async def test_pipeline_projection_assignment_and_immutable_notes(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="core03-owner@vi.test", is_superuser=True)).user
    assignee = (await make_user(email="core03-agent@vi.test")).user
    contact = await _contact(db_session, organization.id, "3")
    service = ViDomainService(db_session)
    created = await service.create_reactivation(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": None,
            "previous_vi_number": "9811111113",
            "active_delhi_number": None,
            "source": "manual",
        },
    )
    assigned = await service.update_reactivation(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(created["id"]),
        payload={
            "expected_row_version": 0,
            "owner_user_id": uuid.UUID(assignee.public_id),
            "previous_vi_number": "9811111113",
            "active_delhi_number": "9822222223",
        },
    )
    assert assigned["row_version"] == 1

    projection = await service.reactivation_pipeline(
        organization.id,
        q="Customer 3",
        stages=["new_lead"],
        owner_user_id=uuid.UUID(assignee.public_id),
        limit=20,
    )
    assert projection["total"] == 1
    card = projection["data"][0]
    assert card["contact_name"] == "Vi Customer 3"
    assert card["owner_name"] == assignee.full_name
    assert card["available_transitions"] == ["follow_up", "not_interested"]
    assert card["open_task_count"] == 0
    assert card["document_count"] == 0
    assert card["sla_status"] == "not_configured"
    assert card["conversion_indicator"] == "open"
    assert len(projection["stage_counts"]) == 15

    note = await service.add_reactivation_note(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(created["id"]),
        body="  Customer requested a weekday callback.  ",
    )
    notes = await service.list_reactivation_notes(organization.id, uuid.UUID(created["id"]))
    assert notes == [note]
    assert note["body"] == "Customer requested a weekday callback."
    timeline = (
        await db_session.scalars(
            select(ContactEvent).where(ContactEvent.event_type == "reactivation_note_added")
        )
    ).one()
    assert timeline.ref_id is not None
    audit = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.action == "reactivation_case.note_added")
        )
    ).one()
    assert audit.entity_id == timeline.ref_id


@pytest.mark.asyncio
async def test_kyc_sim_activation_and_sla_boundaries(db_session, organization, make_user) -> None:
    actor = (await make_user(email="core02-manager@vi.test", is_superuser=True)).user
    reviewer = (await make_user(email="core04-reviewer@vi.test", is_superuser=True)).user
    approver = (await make_user(email="core04-approver@vi.test", is_superuser=True)).user
    contact = await _contact(db_session, organization.id, "2")
    service = ViDomainService(db_session)
    case_view = await service.create_reactivation(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(actor.public_id),
            "previous_vi_number": None,
            "active_delhi_number": "9898989898",
            "source": "manual",
        },
    )
    case = (
        await db_session.scalars(
            select(ReactivationCase).where(
                ReactivationCase.uuid == uuid.UUID(case_view["id"]).bytes
            )
        )
    ).one()
    case.stage = "documents_received"
    await db_session.commit()

    kyc = await service.create_kyc(
        organization_id=organization.id,
        actor=actor,
        reactivation_id=uuid.UUID(case.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(actor.public_id),
            "appointment_at": None,
        },
    )
    kyc = await service.update_kyc(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "expected_row_version": 0,
            "status": "under_review",
            "owner_user_id": uuid.UUID(actor.public_id),
            "holder_verified": True,
            "delhi_presence_verified": True,
            "active_delhi_number_verified": True,
            "appointment_at": None,
        },
    )
    aadhaar = ContactDocument(
            organization_id=organization.id,
            contact_id=contact.id,
            document_type="identity",
            title="Governed Aadhaar proof",
            status="verified",
            created_by=actor.id,
            updated_by=actor.id,
        )
    pan = ContactDocument(
            organization_id=organization.id,
            contact_id=contact.id,
            document_type="identity",
            title="Governed PAN proof",
            status="verified",
            created_by=actor.id,
            updated_by=actor.id,
    )
    db_session.add_all([aadhaar, pan])
    await db_session.commit()
    await service.set_kyc_document_reference(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(kyc["id"]),
        payload={"expected_row_version": 1, "purpose": "aadhaar", "document_id": uuid.UUID(aadhaar.public_id)},
    )
    await service.set_kyc_document_reference(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(kyc["id"]),
        payload={"expected_row_version": 2, "purpose": "pan", "document_id": uuid.UUID(pan.public_id)},
    )
    review = await service.decide_kyc(
        organization_id=organization.id,
        actor=reviewer,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "idempotency_key": uuid.uuid4(),
            "expected_row_version": 3,
            "decision": "approved",
            "reason_code": None,
            "reason": None,
        },
        manager_approval=False,
    )
    approval = await service.decide_kyc(
        organization_id=organization.id,
        actor=approver,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "idempotency_key": uuid.uuid4(),
            "expected_row_version": 4,
            "decision": "approved",
            "reason_code": None,
            "reason": None,
        },
        manager_approval=True,
    )
    assert review["decision_type"] == "review"
    assert approval["decision_type"] == "manager_approval"
    stored_kyc = (
        await db_session.scalars(select(KycCase).where(KycCase.uuid == uuid.UUID(kyc["id"]).bytes))
    ).one()
    assert stored_kyc.status == "approved"
    assert case.stage == "verification"
    assert await db_session.scalar(select(func.count()).select_from(KycDecision)) == 2

    case.stage = "confirmed"
    await db_session.commit()
    order = await service.create_sim_order(
        organization_id=organization.id,
        actor=actor,
        reactivation_id=uuid.UUID(case.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "delivery_address": "New Delhi",
            "service_area": "Delhi NCR",
            "delivery_owner_user_id": uuid.UUID(actor.public_id),
        },
    )
    order = await service.update_sim_order(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(order["id"]),
        payload={
            "expected_row_version": 0,
            "delivery_address": "New Delhi",
            "service_area": "Delhi NCR",
            "delivery_owner_user_id": uuid.UUID(actor.public_id),
            "sim_serial": "SIM-CORE02-001",
            "customer_confirmed": False,
        },
    )
    for expected, target in ((1, "approved"), (2, "assigned"), (3, "dispatched"), (4, "delivered")):
        order = await service.transition_sim_order(
            organization_id=organization.id,
            actor=actor,
            public_id=uuid.UUID(order["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": expected,
                "to_status": target,
                "reason": None,
            },
        )
    order = await service.update_sim_order(
        organization_id=organization.id,
        actor=actor,
        public_id=uuid.UUID(order["id"]),
        payload={
            "expected_row_version": 5,
            "delivery_address": "New Delhi",
            "service_area": "Delhi NCR",
            "delivery_owner_user_id": uuid.UUID(actor.public_id),
            "sim_serial": "SIM-CORE02-001",
            "customer_confirmed": True,
        },
    )
    assert order["status"] == "delivered" and order["customer_confirmed"] is True

    case.stage = "sim_order"
    await db_session.commit()
    activation = await service.create_activation(
        organization_id=organization.id,
        actor=actor,
        reactivation_id=uuid.UUID(case.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "sim_order_id": uuid.UUID(order["id"]),
            "owner_user_id": uuid.UUID(actor.public_id),
        },
    )
    for expected, target, approval_command in (
        (0, "verification", False),
        (1, "ready", False),
        (2, "approved", True),
        (3, "completed", True),
    ):
        activation = await service.transition_activation(
            organization_id=organization.id,
            actor=actor,
            public_id=uuid.UUID(activation["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": expected,
                "to_status": target,
                "approval_reference": "MGR-CORE02" if approval_command else None,
                "reason": None,
            },
            approval_command=approval_command,
        )
    assert activation["status"] == "completed"

    policy = await service.create_sla_policy(
        organization_id=organization.id,
        actor=actor,
        payload={
            "domain": "activation",
            "trigger_name": "activation_pending",
            "target_minutes": 120,
            "escalation_minutes": 180,
            "is_active": True,
        },
    )
    event = await service.create_sla_event(
        organization_id=organization.id,
        actor=actor,
        payload={
            "idempotency_key": uuid.uuid4(),
            "policy_id": uuid.UUID(policy["id"]),
            "contact_id": uuid.UUID(contact.public_id),
            "entity_type": "activation_record",
            "entity_id": uuid.UUID(activation["id"]),
            "event_type": "resolved",
            "due_at": activation["completed_at"],
            "reason": "Activated within SLA",
        },
    )
    assert event["entity_id"] == activation["id"]
    assert event["event_type"] == "resolved"
    assert await db_session.scalar(select(func.count()).select_from(SimOrder)) == 1
