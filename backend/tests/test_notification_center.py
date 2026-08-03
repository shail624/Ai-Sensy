"""CORE-09 durable delivery, RBAC, tenant and task-lifecycle regression tests."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.notification import Notification
from app.models.task import Task
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService
from app.services.vi_domain_service import ViDomainService

PASSWORD = "Sup3r-Secret-Pass!"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_notification_projection_is_idempotent_and_task_lifecycle_resolves_it(
    db_session, organization, make_user
) -> None:
    owner = (await make_user(email="notify-owner@vi.test", is_superuser=True)).user
    contact = Contact(
        organization_id=organization.id,
        wa_id="919900001111",
        phone_e164="+919900001111",
        full_name="Notification Customer",
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
        await db_session.scalars(select(Task).where(Task.reference_type == "reactivation_case"))
    ).one()
    task_service = TaskService(db_session)
    assert await task_service.dispatch_due_notifications(now=utcnow()) == {"notified": 1}
    assert await task_service.dispatch_due_notifications(now=utcnow()) == {"notified": 0}

    await vi.transition_reactivation(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(case["id"]),
        payload={
            "idempotency_key": uuid.uuid4(),
            "expected_row_version": 1,
            "to_stage": "lead_confirmed",
            "reason": None,
        },
    )

    notifications = list((await db_session.scalars(select(Notification))).all())
    assert {row.notification_type for row in notifications} == {
        "case_assigned",
        "case_status_changed",
        "follow_up_due",
    }
    due = next(row for row in notifications if row.notification_type == "follow_up_due")
    assert due.recipient_user_id == owner.id
    assert due.task_id == task.id

    await task_service.complete(
        organization_id=organization.id,
        actor=owner,
        public_id=uuid.UUID(task.public_id),
        expected_row_version=task.row_version,
        completion_notes=None,
        create_timeline_note=False,
    )
    await db_session.refresh(due)
    assert due.resolved_at is not None

    projection = NotificationService(db_session)
    duplicate = await projection.emit(
        organization_id=organization.id,
        recipient_user_id=owner.id,
        notification_type="case_assigned",
        title="Ignored duplicate",
        body="Ignored duplicate",
        dedup_key="stable-delivery-key",
    )
    again = await projection.emit(
        organization_id=organization.id,
        recipient_user_id=owner.id,
        notification_type="case_assigned",
        title="Ignored duplicate",
        body="Ignored duplicate",
        dedup_key="stable-delivery-key",
    )
    assert duplicate.id == again.id
    assert await db_session.scalar(
        select(func.count()).select_from(Notification).where(Notification.dedup_key == "stable-delivery-key")
    ) == 1


@pytest.mark.asyncio
async def test_notification_api_read_state_filters_deep_links_and_team_scope(
    client, session_factory, organization, make_user
) -> None:
    owner = await make_user(email="notify-api-owner@vi.co", is_superuser=True)
    agent = await make_user(email="notify-api-agent@vi.co", roles=("agent",))
    other = await make_user(email="notify-api-other@vi.co", roles=("agent",))
    async with session_factory() as session:
        contact = Contact(
            organization_id=organization.id,
            wa_id="919900002222",
            phone_e164="+919900002222",
            full_name="Deep Link Customer",
        )
        session.add(contact)
        await session.flush()
        case = await ViDomainService(session).create_reactivation(
            organization_id=organization.id,
            actor=owner.user,
            contact_id=uuid.UUID(contact.public_id),
            payload={
                "idempotency_key": uuid.uuid4(),
                "owner_user_id": uuid.UUID(agent.user.public_id),
                "source": "manual",
            },
        )

    agent_headers = await _headers(client, agent.user.email)
    page = await client.get("/api/v1/notifications?status=unread", headers=agent_headers)
    assert page.status_code == 200, page.text
    assert len(page.json()["data"]) == 1
    item = page.json()["data"][0]
    assert item["reactivation_case"]["id"] == case["id"]
    assert item["contact"]["name"] == "Deep Link Customer"

    marked = await client.post(f"/api/v1/notifications/{item['id']}/read", headers=agent_headers)
    assert marked.status_code == 200
    assert marked.json()["read_status"] == "read"
    assert (await client.get("/api/v1/notifications/unread-count", headers=agent_headers)).json() == {
        "unread": 0
    }
    # Read is idempotent and never creates duplicate audit evidence.
    assert (await client.post(f"/api/v1/notifications/{item['id']}/read", headers=agent_headers)).status_code == 200
    async with session_factory() as session:
        assert await session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "notification.read")
        ) == 1

    forbidden = await client.get(
        f"/api/v1/notifications?assignee_id={other.user.public_id}", headers=agent_headers
    )
    assert forbidden.status_code == 403
    owner_headers = await _headers(client, owner.user.email)
    assert (
        await client.get(
            f"/api/v1/notifications?assignee_id={agent.user.public_id}", headers=owner_headers
        )
    ).status_code == 200

    all_read = await client.post("/api/v1/notifications/read-all", headers=agent_headers)
    assert all_read.status_code == 200
    assert all_read.json() == {"updated": 0}
