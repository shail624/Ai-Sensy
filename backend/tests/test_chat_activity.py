"""Manage → Analytics daily chat and agent activity (UI-AIS-10)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.exceptions import BadRequestError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM, AuditLog
from app.models.message import Message
from app.services.chat_activity_service import ChatActivityService
from tests.test_sale_status import _thread


@pytest.mark.anyio
async def test_counts_messages_and_agent_activity_per_day(db_session, organization) -> None:
    thread = await _thread(db_session, organization.id, "919990040404", "CA")
    now = utcnow()

    def message(direction: str, when) -> Message:
        return Message(
            organization_id=organization.id,
            conversation_id=thread.id,
            phone_number_id=thread.phone_number_id,
            contact_id=thread.contact_id,
            direction=direction,
            message_type="text",
            content_json={"body": "x"},
            status="sent",
            created_at=when,
        )

    bot = message("outbound", now)
    db_session.add_all(
        [message("inbound", now), message("inbound", now), message("outbound", now), bot]
    )
    db_session.add(message("inbound", now - timedelta(days=40)))  # outside the range
    await db_session.flush()
    db_session.add_all(
        [
            AuditLog(
                organization_id=organization.id,
                actor_type=ACTOR_SYSTEM,
                action="message.sent",
                entity_type="message",
                entity_id=bot.id,
                created_at=now,
            ),
            AuditLog(
                organization_id=organization.id,
                action="conversation.status_changed",
                after_json={"status": "resolved"},
                created_at=now,
            ),
            AuditLog(
                organization_id=organization.id,
                action="conversation.status_changed",
                after_json={"status": "open"},
                metadata_json={"source": "agent_intervention"},
                created_at=now,
            ),
        ]
    )
    await db_session.commit()

    days = await ChatActivityService(db_session).daily(
        organization_id=organization.id, days=7, timezone="UTC"
    )
    assert len(days) == 7
    today = days[-1]
    assert (today.user_messages, today.business_messages, today.chatbot_messages) == (2, 1, 1)
    assert (today.closed, today.intervened) == (1, 1)
    assert sum(day.user_messages for day in days[:-1]) == 0

    with pytest.raises(BadRequestError):
        await ChatActivityService(db_session).daily(
            organization_id=organization.id, days=90, timezone="UTC"
        )
    with pytest.raises(BadRequestError):
        await ChatActivityService(db_session).daily(
            organization_id=organization.id, days=7, timezone="Mars/Base"
        )
