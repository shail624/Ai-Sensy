"""CORE-04 KYC operations: prerequisites, authority boundaries and projections."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.contact_document import ContactDocument
from app.models.contact_event import ContactEvent
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.models.vi_domain import KycDecision, KycDocumentReference, ReactivationCase
from app.schemas.vi_domain import KycDecisionRequest
from app.services.task_service import TaskService
from app.services.vi_domain_service import DomainTransitionError, ViDomainService


async def _contact(session, organization_id: int, suffix: str) -> Contact:
    contact = Contact(
        organization_id=organization_id,
        wa_id=f"9198111100{suffix}",
        phone_e164=f"+9198111100{suffix}",
        full_name=f"KYC Customer {suffix}",
    )
    session.add(contact)
    await session.commit()
    return contact


@pytest.mark.asyncio
async def test_governed_kyc_workflow_reuses_documents_tasks_and_stage_authority(
    db_session, organization, make_user
) -> None:
    requester = (await make_user(email="kyc-requester@vi.test", is_superuser=True)).user
    reviewer = (await make_user(email="kyc-reviewer@vi.test", is_superuser=True)).user
    manager = (await make_user(email="kyc-manager@vi.test", is_superuser=True)).user
    contact = await _contact(db_session, organization.id, "1")
    unrelated_contact = await _contact(db_session, organization.id, "2")
    contact_id = contact.id
    unrelated_contact_id = unrelated_contact.id
    service = ViDomainService(db_session)
    case_view = await service.create_reactivation(
        organization_id=organization.id,
        actor=requester,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(requester.public_id),
            "previous_vi_number": "9811111001",
            "active_delhi_number": "9811111002",
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
    case_id = case.id

    with pytest.raises(DomainTransitionError, match="documents are received"):
        await service.create_kyc(
            organization_id=organization.id,
            actor=requester,
            reactivation_id=uuid.UUID(case.public_id),
            payload={
                "idempotency_key": uuid.uuid4(),
                "owner_user_id": uuid.UUID(requester.public_id),
                "appointment_at": None,
            },
        )
    await db_session.rollback()
    case = (await db_session.scalars(select(ReactivationCase).where(ReactivationCase.id == case_id))).one()
    case.stage = "documents_received"
    await db_session.commit()

    kyc = await service.create_kyc(
        organization_id=organization.id,
        actor=requester,
        reactivation_id=uuid.UUID(case.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(requester.public_id),
            "appointment_at": None,
        },
    )
    await db_session.refresh(case)
    assert case.stage == "kyc_pending"
    kyc = await service.update_kyc(
        organization_id=organization.id,
        actor=requester,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "expected_row_version": 0,
            "status": "under_review",
            "owner_user_id": uuid.UUID(requester.public_id),
            "holder_verified": True,
            "delhi_presence_verified": True,
            "active_delhi_number_verified": True,
            "appointment_at": None,
        },
    )

    aadhaar = ContactDocument(
        organization_id=organization.id,
        contact_id=contact_id,
        document_type="identity",
        title="Aadhaar protected proof",
        status="verified",
        created_by=requester.id,
        updated_by=requester.id,
    )
    pan = ContactDocument(
        organization_id=organization.id,
        contact_id=contact_id,
        document_type="identity",
        title="PAN protected proof",
        status="verified",
        created_by=requester.id,
        updated_by=requester.id,
    )
    foreign_document = ContactDocument(
        organization_id=organization.id,
        contact_id=unrelated_contact_id,
        document_type="identity",
        title="Another customer's proof",
        status="verified",
        created_by=requester.id,
        updated_by=requester.id,
    )
    db_session.add_all([aadhaar, pan, foreign_document])
    await db_session.commit()
    aadhaar_public_id = aadhaar.public_id
    pan_public_id = pan.public_id
    foreign_document_public_id = foreign_document.public_id
    with pytest.raises(NotFoundError):
        await service.set_kyc_document_reference(
            organization_id=organization.id,
            actor=requester,
            public_id=uuid.UUID(kyc["id"]),
            payload={
                "expected_row_version": 1,
                "purpose": "aadhaar",
                "document_id": uuid.UUID(foreign_document_public_id),
            },
        )
    await db_session.rollback()
    await service.set_kyc_document_reference(
        organization_id=organization.id,
        actor=requester,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "expected_row_version": 1,
            "purpose": "aadhaar",
            "document_id": uuid.UUID(aadhaar_public_id),
        },
    )
    await service.set_kyc_document_reference(
        organization_id=organization.id,
        actor=requester,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "expected_row_version": 2,
            "purpose": "pan",
            "document_id": uuid.UUID(pan_public_id),
        },
    )
    assert await db_session.scalar(select(func.count()).select_from(KycDocumentReference)) == 2

    appointment_key = uuid.uuid4()
    appointment_payload = {
        "idempotency_key": appointment_key,
        "expected_row_version": 3,
        "due_at": utcnow() + timedelta(days=1),
        "reminder_at": utcnow() + timedelta(hours=20),
        "assigned_agent_id": uuid.UUID(reviewer.public_id),
        "description": "Bring governed originals; do not record identity numbers.",
    }
    appointment = await service.create_kyc_appointment(
        organization_id=organization.id,
        actor=requester,
        public_id=uuid.UUID(kyc["id"]),
        payload=appointment_payload,
    )
    retried = await service.create_kyc_appointment(
        organization_id=organization.id,
        actor=requester,
        public_id=uuid.UUID(kyc["id"]),
        payload=appointment_payload,
    )
    assert retried["id"] == appointment["id"]
    task = (
        await db_session.scalars(select(Task).where(Task.uuid == uuid.UUID(appointment["id"]).bytes))
    ).one()
    assert task.reference_type == "kyc_case" and task.reference_id is not None
    completed = await TaskService(db_session).complete(
        organization_id=organization.id,
        actor=reviewer,
        public_id=uuid.UUID(appointment["id"]),
        expected_row_version=0,
        completion_notes="Identity appointment completed",
        create_timeline_note=True,
    )
    assert completed.status == "completed"
    assert await db_session.scalar(select(func.count()).select_from(TaskEvent)) >= 2

    with pytest.raises(DomainTransitionError, match="requester cannot review"):
        await service.decide_kyc(
            organization_id=organization.id,
            actor=requester,
            public_id=uuid.UUID(kyc["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": 4,
                "decision": "approved",
                "reason_code": None,
                "reason": None,
            },
            manager_approval=False,
        )
    await db_session.rollback()
    review = await service.decide_kyc(
        organization_id=organization.id,
        actor=reviewer,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "idempotency_key": uuid.uuid4(),
            "expected_row_version": 4,
            "decision": "approved",
            "reason_code": None,
            "reason": None,
        },
        manager_approval=False,
    )
    with pytest.raises(DomainTransitionError, match="must be different users"):
        await service.decide_kyc(
            organization_id=organization.id,
            actor=reviewer,
            public_id=uuid.UUID(kyc["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": 5,
                "decision": "approved",
                "reason_code": None,
                "reason": None,
            },
            manager_approval=True,
        )
    await db_session.rollback()
    approved = await service.decide_kyc(
        organization_id=organization.id,
        actor=manager,
        public_id=uuid.UUID(kyc["id"]),
        payload={
            "idempotency_key": uuid.uuid4(),
            "expected_row_version": 5,
            "decision": "approved",
            "reason_code": None,
            "reason": None,
        },
        manager_approval=True,
    )
    assert review["decision_type"] == "review"
    assert approved["decision_type"] == "manager_approval"
    await db_session.refresh(case)
    assert case.stage == "verification"
    assert await db_session.scalar(select(func.count()).select_from(KycDecision)) == 2

    operations = await service.kyc_operations(
        organization.id, q="KYC Customer 1", statuses=["approved"], limit=20
    )
    assert operations["total"] == 1
    card = operations["data"][0]
    assert card["progress_percent"] == 100
    assert card["checklist_complete"] is True
    assert card["appointments"][0]["status"] == "completed"
    assert card["latest_review"]["decided_by"] == reviewer.public_id
    assert card["latest_manager_decision"]["decided_by"] == manager.public_id
    assert await db_session.scalar(select(func.count()).select_from(AuditLog)) >= 8
    assert await db_session.scalar(select(func.count()).select_from(ContactEvent)) >= 8
    with pytest.raises(DomainTransitionError, match="immutable"):
        await service.decide_kyc(
            organization_id=organization.id,
            actor=manager,
            public_id=uuid.UUID(kyc["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": 6,
                "decision": "approved",
                "reason_code": None,
                "reason": None,
            },
            manager_approval=True,
        )
    with pytest.raises(NotFoundError):
        await service.get_kyc(organization.id + 999, uuid.UUID(kyc["id"]))


def test_non_approval_decision_requires_structured_reason() -> None:
    with pytest.raises(ValidationError):
        KycDecisionRequest.model_validate(
            {
                "idempotency_key": str(uuid.uuid4()),
                "expected_row_version": 0,
                "decision": "rejected",
                "reason": "Evidence does not match.",
            }
        )
