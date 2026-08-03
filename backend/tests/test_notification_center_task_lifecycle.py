# CORE-09 regression for notification revisions across Task lifecycle changes.

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.notification import NOTIFICATION_FOLLOW_UP_DUE, Notification
from app.models.task import Task
from app.services.task_service import TaskService
from app.services.vi_domain_service import ViDomainService


@pytest.mark.asyncio
async def test_due_notification_revision_follows_reassign_reopen_bulk_and_delete(
    db_session, organization, make_user
) -> None:
    owner = (await make_user(email="notify-revision-owner@vi.co", is_superuser=True)).user
    agent = (await make_user(email="notify-revision-agent@vi.co", roles=("agent",))).user
    contact = Contact(
        organization_id=organization.id,
        wa_id="919900003333",
        phone_e164="+919900003333",
        full_name="Notification Revision Customer",
    )
    db_session.add(contact)
    await db_session.commit()

    vi = ViDomainService(db_session)
    case = await vi.create_reactivation(
        organization_id=organization.id,
        actor=owner,
        contact_id=uuid.UUID(contact.public_id),
        payload={
            "idempotency_key": uuid.uuid4(),
            "owner_user_id": uuid.UUID(owner.public_id),
            "source": "manual",
        },
    )
    await vi.update_reactivation(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(case["id"]),
        payload={
            "expected_row_version": 0,
            "labels": ["follow_up"],
            "follow_up_at": utcnow() - timedelta(days=1),
        },
    )

    task = (
        await db_session.scalars(
            select(Task).where(
                Task.organization_id == organization.id,
                Task.reference_type == "reactivation_case",
            )
        )
    ).one()
    tasks = TaskService(db_session)

    assert await tasks.dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    due_rows = list(
        (
            await db_session.scalars(
                select(Notification)
                .where(Notification.notification_type == NOTIFICATION_FOLLOW_UP_DUE)
                .order_by(Notification.id)
            )
        ).all()
    )
    assert len(due_rows) == 1
    assert due_rows[-1].recipient_user_id == owner.id

    await tasks.reassign(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(task.public_id),
        expected_row_version=task.row_version,
        assigned_agent_id=uuid.UUID(agent.public_id),
    )
    await db_session.refresh(task)
    await db_session.refresh(due_rows[-1])
    assert due_rows[-1].resolved_at is not None
    assert task.due_notified_at is None

    assert await tasks.dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    due_rows = list(
        (
            await db_session.scalars(
                select(Notification)
                .where(Notification.notification_type == NOTIFICATION_FOLLOW_UP_DUE)
                .order_by(Notification.id)
            )
        ).all()
    )
    assert len(due_rows) == 2
    assert due_rows[-1].recipient_user_id == agent.id
    assert due_rows[-1].resolved_at is None

    await tasks.complete(
        organization_id=organization.id,
        actor=agent,
        public_id=uuid.UUID(task.public_id),
        expected_row_version=task.row_version,
        completion_notes=None,
        create_timeline_note=False,
    )
    await db_session.refresh(task)
    await db_session.refresh(due_rows[-1])
    assert due_rows[-1].resolved_at is not None

    await tasks.reopen(
        organization_id=organization.id,
        actor=agent,
        public_id=uuid.UUID(task.public_id),
        expected_row_version=task.row_version,
    )
    await db_session.refresh(task)
    assert task.due_notified_at is None

    assert await tasks.dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    due_rows = list(
        (
            await db_session.scalars(
                select(Notification)
                .where(Notification.notification_type == NOTIFICATION_FOLLOW_UP_DUE)
                .order_by(Notification.id)
            )
        ).all()
    )
    assert len(due_rows) == 3
    assert due_rows[-1].recipient_user_id == agent.id
    assert due_rows[-1].resolved_at is None

    outcome = await tasks.bulk_update(
        organization_id=organization.id,
        actor=owner,
        public_ids=[uuid.UUID(task.public_id)],
        status=None,
        priority=None,
        due_at=None,
        assigned_agent_id=uuid.UUID(owner.public_id),
    )
    assert outcome.succeeded == 1
    await db_session.refresh(task)
    await db_session.refresh(due_rows[-1])
    assert due_rows[-1].resolved_at is not None
    assert task.due_notified_at is None

    assert await tasks.dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    due_rows = list(
        (
            await db_session.scalars(
                select(Notification)
                .where(Notification.notification_type == NOTIFICATION_FOLLOW_UP_DUE)
                .order_by(Notification.id)
            )
        ).all()
    )
    assert len(due_rows) == 4
    assert due_rows[-1].recipient_user_id == owner.id
    assert due_rows[-1].resolved_at is None

    await tasks.delete(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(task.public_id),
    )
    await db_session.refresh(due_rows[-1])
    assert due_rows[-1].resolved_at is not None
