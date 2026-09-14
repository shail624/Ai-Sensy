"""CORE-11C inactivity resolution over existing conversation/task/audit/event authorities."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM, AuditLog
from app.models.business_event import (
    BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
    BusinessEvent,
)
from app.models.contact import Contact
from app.models.conversation import (
    CONV_OPEN,
    CONV_PENDING,
    CONV_RESOLVED,
    CONV_SNOOZED,
    Conversation,
)
from app.models.task import TASK_TYPE_REMINDER, Task
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.schemas.settings import InboxOperationsSettings
from app.services.inbox_operations_service import InboxOperationsService


async def test_auto_resolve_is_opt_in_bounded_and_protects_active_work(
    make_user, session_factory, organization
) -> None:
    owner = await make_user(
        email="owner@vi.co", password="Sup3r-Secret-Pass1", is_superuser=True
    )
    now = utcnow()
    old = now - timedelta(hours=4)
    recent = now - timedelta(minutes=15)
    async with session_factory() as session:
        waba = WhatsAppBusinessAccount(
            organization_id=organization.id,
            waba_id="WABA-AUTO-RESOLVE",
            business_name="Vi",
            access_token_enc=b"ciphertext",
        )
        session.add(waba)
        await session.flush()
        number = PhoneNumber(
            organization_id=organization.id,
            waba_id=waba.id,
            phone_number_id="PN-AUTO-RESOLVE",
            display_number="+911111111111",
        )
        session.add(number)
        await session.flush()

        specs = {
            "eligible": (CONV_PENDING, 0, old),
            "unread": (CONV_OPEN, 1, old),
            "snoozed": (CONV_SNOOZED, 0, old),
            "resolved": (CONV_RESOLVED, 0, old),
            "recent": (CONV_OPEN, 0, recent),
            "task": (CONV_OPEN, 0, old),
        }
        ids: dict[str, int] = {}
        contacts: dict[str, Contact] = {}
        for index, (name, (status, unread, activity_at)) in enumerate(specs.items(), start=1):
            contact = Contact(
                organization_id=organization.id,
                phone_e164=f"+9199900000{index:02d}",
                wa_id=f"9199900000{index:02d}",
                source="test",
            )
            session.add(contact)
            await session.flush()
            conversation = Conversation(
                organization_id=organization.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                status=status,
                unread_count=unread,
                last_message_at=activity_at,
                updated_at=activity_at,
            )
            session.add(conversation)
            await session.flush()
            ids[name] = conversation.id
            contacts[name] = contact

        session.add(
            Task(
                organization_id=organization.id,
                contact_id=contacts["task"].id,
                conversation_id=ids["task"],
                assigned_agent_id=owner.user.id,
                created_by=owner.user.id,
                title="Call this customer",
                task_type=TASK_TYPE_REMINDER,
                due_at=now + timedelta(hours=1),
            )
        )
        await session.commit()

    # No persisted opt-in policy means the scanner is inert.
    async with session_factory() as session:
        disabled = await InboxOperationsService(session).auto_resolve_inactive(now=now)
    assert disabled == {
        "organizations": 0,
        "candidates": 0,
        "resolved": 0,
        "skipped": 0,
        "invalid_policies": 0,
    }

    async with session_factory() as session:
        await InboxOperationsService(session).update(
            organization_id=organization.id,
            actor=owner.user,
            policy=InboxOperationsSettings.model_validate(
                {"auto_resolve": {"enabled": True, "inactive_after_hours": 2}}
            ),
        )
    async with session_factory() as session:
        result = await InboxOperationsService(session).auto_resolve_inactive(now=now)
    assert result == {
        "organizations": 1,
        "candidates": 1,
        "resolved": 1,
        "skipped": 0,
        "invalid_policies": 0,
    }

    async with session_factory() as session:
        conversations = {
            row.id: row for row in (await session.scalars(select(Conversation))).all()
        }
        audits = list(
            (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "conversation.status_changed",
                        AuditLog.actor_type == ACTOR_SYSTEM,
                    )
                )
            ).all()
        )
        events = list(
            (
                await session.scalars(
                    select(BusinessEvent).where(
                        BusinessEvent.event_type == BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED
                    )
                )
            ).all()
        )
    assert conversations[ids["eligible"]].status == CONV_RESOLVED
    assert conversations[ids["unread"]].status == CONV_OPEN
    assert conversations[ids["snoozed"]].status == CONV_SNOOZED
    assert conversations[ids["resolved"]].status == CONV_RESOLVED
    assert conversations[ids["recent"]].status == CONV_OPEN
    assert conversations[ids["task"]].status == CONV_OPEN
    assert len(audits) == 1
    assert audits[0].metadata_json["policy"] == "auto_resolve"
    assert len(events) == 1
    assert events[0].payload_json["inactive_after_hours"] == 2

    # Re-running the same tick converges: no second mutation, audit row, or business event.
    async with session_factory() as session:
        repeated = await InboxOperationsService(session).auto_resolve_inactive(now=now)
        event_count = len(
            list(
                (
                    await session.scalars(
                        select(BusinessEvent).where(
                            BusinessEvent.event_type
                            == BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED
                        )
                    )
                ).all()
            )
        )
    assert repeated["resolved"] == 0
    assert event_count == 1


def test_auto_resolve_task_uses_the_existing_scheduler_queue() -> None:
    from app.crm.tasks import auto_resolve_inactive_conversations
    from app.queue.registry import SCHEDULER_TICK

    assert auto_resolve_inactive_conversations.queue_name == SCHEDULER_TICK
