"""Sale status and number release date set from Live Chat (UI-AIS-06)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.task import TASK_STATUS_CANCELLED, TASK_STATUS_OPEN, Task
from app.services.inbox_query_service import InboxQueryService
from app.services.sale_status_service import SaleStatusService
from tests.test_qr08_inbox_integration import _meta_endpoint


async def _thread(db_session, organization_id: int, wa_id: str, suffix: str) -> Conversation:
    number = await _meta_endpoint(db_session, organization_id, suffix=suffix)
    contact = Contact(organization_id=organization_id, wa_id=wa_id, phone_e164=f"+{wa_id}")
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization_id, phone_number_id=number.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()
    return conversation


async def _list(db_session, organization_id: int, sale_status: str) -> list[int]:
    page = await InboxQueryService(db_session).list_conversations(
        organization_id=organization_id,
        limit=10,
        cursor=None,
        contact=None,
        status=None,
        assignee=None,
        number=None,
        tag=None,
        q=None,
        sale_status=sale_status,
    )
    return [c.id for c in page.conversations]


@pytest.mark.anyio
async def test_status_is_set_filtered_and_cleared(db_session, organization, make_user) -> None:
    actor = (await make_user(email="sale-status@vi.co", is_superuser=True)).user
    marked = await _thread(db_session, organization.id, "919990004444", "S1")
    unmarked = await _thread(db_session, organization.id, "919990005555", "S2")
    service = SaleStatusService(db_session)

    details = await service.update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(bytes=marked.uuid),
        sale_status="sale_in_field",
    )
    assert details.sale_status == "sale_in_field"
    assert details.release_date is None

    assert await _list(db_session, organization.id, "sale_in_field") == [marked.id]
    assert await _list(db_session, organization.id, "none") == [unmarked.id]
    with pytest.raises(BadRequestError):
        await _list(db_session, organization.id, "maybe")

    cleared = await service.update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(bytes=marked.uuid),
        sale_status=None,
    )
    assert cleared.sale_status is None


@pytest.mark.anyio
async def test_release_date_keeps_exactly_one_reminder(db_session, organization, make_user) -> None:
    actor = (await make_user(email="release-date@vi.co", is_superuser=True)).user
    thread = await _thread(db_session, organization.id, "919990006666", "R1")
    public = uuidlib.UUID(bytes=thread.uuid)
    service = SaleStatusService(db_session)

    first = await service.update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=public,
        release_date=date(2026, 10, 5),
    )
    assert first.release_task_id is not None
    task = await db_session.scalar(select(Task).where(Task.conversation_id == thread.id))
    assert task.status == TASK_STATUS_OPEN
    assert task.due_at == datetime(2026, 10, 5, 4, 30)

    # A new date moves the same reminder instead of adding a second one.
    moved = await service.update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=public,
        release_date=date(2026, 10, 9),
    )
    assert moved.release_task_id == first.release_task_id
    tasks = (await db_session.scalars(select(Task).where(Task.conversation_id == thread.id))).all()
    assert len(tasks) == 1
    await db_session.refresh(tasks[0])
    assert tasks[0].due_at == datetime(2026, 10, 9, 4, 30)

    # Clearing the date cancels the reminder.
    removed = await service.update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=public,
        release_date=None,
    )
    assert removed.release_date is None
    assert removed.release_task_id is None
    await db_session.refresh(tasks[0])
    assert tasks[0].status == TASK_STATUS_CANCELLED


@pytest.mark.anyio
async def test_other_organizations_chat_is_not_found(db_session, organization, make_user) -> None:
    actor = (await make_user(email="sale-cross@vi.co", is_superuser=True)).user
    with pytest.raises(NotFoundError):
        await SaleStatusService(db_session).update(
            organization_id=organization.id,
            actor=actor,
            conversation_public_id=uuidlib.uuid4(),
            sale_status="sale_done",
        )


@pytest.mark.anyio
async def test_due_release_date_notifies_the_agent(db_session, organization, make_user) -> None:
    from app.models.notification import Notification
    from app.services.task_service import TaskService

    actor = (await make_user(email="release-due@vi.co", is_superuser=True)).user
    thread = await _thread(db_session, organization.id, "919990007777", "N1")
    await SaleStatusService(db_session).update(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(bytes=thread.uuid),
        release_date=date(2026, 10, 5),
    )

    early = await TaskService(db_session).dispatch_due_notifications(now=datetime(2026, 10, 5, 4))
    assert early == {"notified": 0}
    due = await TaskService(db_session).dispatch_due_notifications(now=datetime(2026, 10, 5, 5))
    assert due == {"notified": 1}
    notice = await db_session.scalar(
        select(Notification).where(Notification.recipient_user_id == actor.id)
    )
    assert notice.notification_type == "release_date_due"
    assert notice.title == "Release date today: +919990007777"
    # Scans converge: the same due date never notifies twice.
    again = await TaskService(db_session).dispatch_due_notifications(now=datetime(2026, 10, 5, 6))
    assert again == {"notified": 0}
