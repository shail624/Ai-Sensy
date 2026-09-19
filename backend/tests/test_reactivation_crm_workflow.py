"""Owner-approved Reactivation CRM status, label and reminder regression coverage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.exceptions import BadRequestError, VersionConflictError
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.contact_event import ContactEvent
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.models.vi_domain import REACTIVATION_STAGES, REACTIVATION_TRANSITIONS
from app.schemas.vi_domain import ReactivationUpdateRequest
from app.services.task_service import TaskService
from app.services.vi_domain_service import ViDomainService


@pytest.mark.asyncio
async def test_status_labels_and_task_backed_dates_are_one_governed_workflow(
    db_session, organization, make_user
) -> None:
    owner = (await make_user(email="crm-owner@vi.test", is_superuser=True)).user
    contact = Contact(
        organization_id=organization.id,
        wa_id="919988776655",
        phone_e164="+919988776655",
        full_name="Scheduled Customer",
    )
    db_session.add(contact)
    await db_session.commit()
    service = ViDomainService(db_session)
    case = await service.create_reactivation(
        organization_id=organization.id,
        actor=owner,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(owner.public_id),
            "previous_vi_number": None,
            "active_delhi_number": None,
            "source": "manual",
        },
    )
    follow_up_at = utcnow() - timedelta(days=1)
    release_at = utcnow() + timedelta(days=2)
    updated = await service.update_reactivation(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(case["id"]),
        payload={
            "expected_row_version": 0,
            "labels": ["follow_up", "name_change", "priority"],
            "follow_up_at": follow_up_at,
            "release_at": release_at,
        },
    )
    assert updated["labels"] == ["follow_up", "name_change", "priority"]

    projection = await service.reactivation_pipeline(
        organization.id,
        q=None,
        stages=None,
        labels=["follow_up"],
        reminder_view="overdue",
    )
    assert projection["total"] == 1
    assert projection["reminder_counts"] == {"overdue": 1, "due_today": 0, "upcoming": 1}
    assert {task["task_type"] for task in projection["data"][0]["reminders"]} == {
        "reminder",
        "custom",
    }

    tasks = list(
        (
            await db_session.scalars(
                select(Task).where(Task.reference_type == "reactivation_case").order_by(Task.due_at)
            )
        ).all()
    )
    assert {task.assigned_agent_id for task in tasks} == {owner.id}
    assert await TaskService(db_session).dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    await TaskService(db_session).snooze(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(tasks[0].public_id),
        expected_row_version=tasks[0].row_version,
        minutes=60,
    )
    events = list((await db_session.scalars(select(TaskEvent))).all())
    assert {event.event_type for event in events} >= {"created", "due_notified", "snoozed"}
    actions = {row.action for row in (await db_session.scalars(select(AuditLog))).all()}
    assert {"task.created", "task.due_notified", "task.snoozed"} <= actions
    timeline = {row.event_type for row in (await db_session.scalars(select(ContactEvent))).all()}
    assert {"task_created", "task_due_notified", "task_snoozed"} <= timeline

    replacement = (await make_user(email="crm-replacement@vi.test")).user
    reassigned = await service.update_reactivation(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(case["id"]),
        payload={
            "expected_row_version": 1,
            "owner_user_id": uuid.UUID(replacement.public_id),
        },
    )
    assert reassigned["owner_user_id"] == replacement.public_id
    current_tasks = await service._repo.case_reminders(organization.id, int(tasks[0].reference_id))
    assert {task.assigned_agent_id for task in current_tasks} == {replacement.id}

    with pytest.raises(VersionConflictError):
        await service.update_reactivation(
            organization_id=organization.id,
            actor=owner,
            public_id=uuid.UUID(case["id"]),
            payload={"expected_row_version": 0, "labels": []},
        )
    with pytest.raises(BadRequestError, match="closing reason"):
        await service.transition_reactivation(
            organization_id=organization.id,
            actor=owner,
            public_id=uuid.UUID(case["id"]),
            payload={
                "idempotency_key": uuid.uuid4(),
                "expected_row_version": 2,
                "to_stage": "not_required",
                "reason": "   ",
            },
        )


@pytest.mark.asyncio
async def test_pipeline_offset_pagination_is_stable_bounded_and_tenant_scoped(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="crm-pagination@vi.test", is_superuser=True)).user
    service = ViDomainService(db_session)
    case_ids: set[str] = set()

    for index in range(3):
        contact = Contact(
            organization_id=organization.id,
            wa_id=f"9199002200{index}",
            phone_e164=f"+9199002200{index}",
            full_name=f"Paged Customer {index}",
        )
        db_session.add(contact)
        await db_session.commit()
        created = await service.create_reactivation(
            organization_id=organization.id,
            actor=actor,
            contact_id=uuid.UUID(contact.public_id),
            payload={
                "idempotency_key": uuid.uuid4(),
                "owner_user_id": uuid.UUID(actor.public_id),
                "previous_vi_number": None,
                "active_delhi_number": None,
                "source": "manual",
            },
        )
        case_ids.add(created["id"])

    first = await service.reactivation_pipeline(
        organization.id,
        q=None,
        stages=None,
        offset=0,
        limit=2,
    )
    second = await service.reactivation_pipeline(
        organization.id,
        q=None,
        stages=None,
        offset=2,
        limit=2,
    )

    first_ids = {row["id"] for row in first["data"]}
    second_ids = {row["id"] for row in second["data"]}
    assert first["total"] == second["total"] == 3
    assert first["visible"] == 2
    assert second["visible"] == 1
    assert not first_ids.intersection(second_ids)
    assert first_ids | second_ids == case_ids


def test_label_date_contract_and_status_vocabulary() -> None:
    assert REACTIVATION_STAGES == (
        "new_lead",
        "lead_confirmed",
        "documents_pending",
        "documents_received",
        "kyc_verification",
        "sim_required",
        "activation_pending",
        "completed",
        "not_required",
    )
    assert not REACTIVATION_TRANSITIONS["completed"]
    assert not REACTIVATION_TRANSITIONS["not_required"]
    with pytest.raises(ValidationError, match="follow_up_at"):
        ReactivationUpdateRequest(expected_row_version=1, labels=["follow_up"])
    with pytest.raises(ValidationError, match="release_at"):
        ReactivationUpdateRequest(expected_row_version=1, labels=["name_change"])
    with pytest.raises(ValidationError, match="requires the Follow-up label"):
        ReactivationUpdateRequest(
            expected_row_version=1,
            labels=[],
            follow_up_at=datetime.now(UTC),
        )
    normalized = ReactivationUpdateRequest(
        expected_row_version=1,
        labels=["follow_up"],
        follow_up_at=datetime.now(UTC),
    )
    assert normalized.follow_up_at is not None
    assert normalized.follow_up_at.tzinfo is None


@pytest.mark.asyncio
async def test_reminders_require_an_assigned_case_owner(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="crm-agent@vi.test", is_superuser=True)).user
    contact = Contact(
        organization_id=organization.id,
        wa_id="919900112233",
        phone_e164="+919900112233",
        full_name="Unassigned Customer",
    )
    db_session.add(contact)
    await db_session.commit()
    service = ViDomainService(db_session)
    case = await service.create_reactivation(
        organization_id=organization.id,
        actor=actor,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": None,
            "previous_vi_number": None,
            "active_delhi_number": None,
            "source": "manual",
        },
    )
    with pytest.raises(BadRequestError, match="Assign a staff member"):
        await service.update_reactivation(
            organization_id=organization.id,
            actor=actor,
            public_id=uuid.UUID(case["id"]),
            payload={
                "expected_row_version": 0,
                "labels": ["follow_up"],
                "follow_up_at": utcnow() + timedelta(days=1),
                "release_at": None,
            },
        )
