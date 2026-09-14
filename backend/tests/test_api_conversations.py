"""Conversation & message-ledger tests (Doc 03 §9.1/§9.2/§9.3; FR-WA-06/07/09/12) — M4 Step 4.

No network and no broker: deliveries are signed and posted to the public endpoint, and the
processing tasks' service bodies are driven directly.
"""

from __future__ import annotations

from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.conversation import WINDOW, Conversation
from app.models.message import (
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    MSG_ACCEPTED,
    MSG_DELIVERED,
    MSG_FAILED,
    MSG_READ,
    MSG_SENT,
    Message,
    MessageStatusHistory,
    advances,
)
from app.models.webhook import WH_PROCESSED
from app.repositories.message import MessageRepository
from app.schemas.settings import InboxOperationsSettings
from app.services.inbox_operations_service import InboxOperationsService
from app.services.message_service import (
    APPLIED,
    DUPLICATE,
    IGNORED_STALE,
    LedgerError,
    MessageNotFound,
    MessageService,
)
from app.services.webhook_service import WebhookService
from tests.test_api_webhooks import (  # one Meta delivery shape, defined in one place
    WAMID,
    _delivery,
    _events,
    _message,
    _post,
    _seed_number,
    _status,
)

SENDER = "919990329329"


async def _rows(session_factory, model):
    async with session_factory() as session:
        return list((await session.scalars(select(model).order_by(model.id))).all())


async def _deliver(client, session_factory, monkeypatch, make_user, payload) -> list[int]:
    """Post a signed delivery and run the webhook processor over every event it produced."""
    await _post(client, payload)
    routed: list[int] = []
    for row in await _events(session_factory):
        if row.status != WH_PROCESSED:
            async with session_factory() as session:
                await WebhookService(session).process(row.id, dispatch_inbound=routed.append)
    return routed


async def _inbound(client, make_user, session_factory, monkeypatch, message=None) -> dict:
    """Seed a number, deliver one inbound message, and apply it end-to-end."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[message or _message()]),
    )
    assert routed, "the webhook processor must route an inbound message to inbound.process"
    async with session_factory() as session:
        return await MessageService(session).apply_inbound(routed[0])


async def _set_inbox_operations(session_factory, **overrides) -> None:
    """Persist a validated organization policy through the same service as the API."""
    from app.models.user import User

    async with session_factory() as session:
        owner = (await session.scalars(select(User).where(User.email == "owner@vi.co"))).one()
        policy = InboxOperationsSettings.model_validate(overrides)
        await InboxOperationsService(session).update(
            organization_id=owner.organization_id, actor=owner, policy=policy
        )


def _fresh_message(*, wamid: str, body: str = "hello") -> dict:
    occurred_at = utcnow().replace(tzinfo=UTC)
    return _message(wamid=wamid, body=body) | {"timestamp": str(int(occurred_at.timestamp()))}


def _closed_week() -> list[dict[str, object]]:
    """A one-hour interval six hours ahead of now, guaranteed closed at test execution."""
    start_hour = (utcnow().hour + 6) % 24
    end_hour = (start_hour + 1) % 24
    return [
        {
            "day": day,
            "enabled": True,
            "start": f"{start_hour:02d}:00",
            "end": f"{end_hour:02d}:00",
        }
        for day in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    ]


# --- Inbound application (FR-WA-06) ------------------------------------------
async def test_inbound_message_creates_contact_conversation_and_ledger_row(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    result = await _inbound(client, make_user, session_factory, monkeypatch)
    assert result["status"] == APPLIED

    (contact,) = await _rows(session_factory, Contact)
    assert contact.wa_id == SENDER and contact.phone_e164 == f"+{SENDER}"
    assert contact.profile_name == "Priya" and contact.source == "webhook"
    # Active detection: a message can only come from a live WhatsApp number (FR-WA-09).
    assert contact.is_active_on_wa is True and contact.last_inbound_at is not None

    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.contact_id == contact.id and conversation.status == "open"
    assert conversation.unread_count == 1
    assert conversation.last_message_preview == "hello"
    assert conversation.channel_type == "whatsapp"

    (message,) = await _rows(session_factory, Message)
    assert message.direction == DIRECTION_INBOUND and message.wamid == WAMID
    assert message.message_type == "text" and message.status == MSG_ACCEPTED
    # Canonical content, not Graph's nesting.
    assert message.content_json == {"body": "hello"}
    assert message.conversation_id == conversation.id and message.contact_id == contact.id


async def test_inbound_contact_creation_is_audited_and_timelined(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """A new person's PII entering the system is audited on this path exactly as on the API path."""
    from app.models.audit import ACTOR_SYSTEM, AuditLog
    from app.models.contact_event import ContactEvent

    await _inbound(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        audit = list(
            (
                await session.scalars(select(AuditLog).where(AuditLog.action == "contact.created"))
            ).all()
        )
        events = list((await session.scalars(select(ContactEvent))).all())
    assert len(audit) == 1 and audit[0].actor_type == ACTOR_SYSTEM
    assert audit[0].actor_user_id is None
    assert [e.event_type for e in events] == ["contact_created"]


async def test_configured_consent_keyword_updates_contact_in_the_inbound_transaction(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    from app.models.audit import ACTOR_SYSTEM, AuditLog
    from app.models.contact_event import ContactEvent

    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(
        session_factory,
        consent={
            "enabled": True,
            "opt_in_keywords": ["START"],
            "opt_out_keywords": ["STOP"],
        },
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_message(wamid="wamid.STOP", body="  stop  ")]),
    )
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    (contact,) = await _rows(session_factory, Contact)
    assert contact.opt_in_status == "opted_out"
    assert contact.opt_out_at is not None
    async with session_factory() as session:
        events = list(
            (
                await session.scalars(
                    select(ContactEvent).where(ContactEvent.event_type == "optin_changed")
                )
            ).all()
        )
        audit = list(
            (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "contact.updated",
                        AuditLog.actor_type == ACTOR_SYSTEM,
                    )
                )
            ).all()
        )
    assert len(events) == 1
    assert events[0].payload_json == {
        "from": "unknown",
        "to": "opted_out",
        "source": "inbound_keyword",
    }
    assert len(audit) == 1 and audit[0].metadata_json["keyword"] == "STOP"


async def test_least_open_policy_assigns_a_new_thread_to_an_eligible_user(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    from app.models.audit import ACTOR_SYSTEM, AuditLog
    from app.models.user import User

    # Created first so the zero-load tie resolves to the agent, not the later Owner account.
    agent = await make_user(email="agent@vi.co", password="Agent-Pass1", roles=("agent",))
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(session_factory, assignment_mode="least_open")
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_message(wamid="wamid.ASSIGNED")]),
    )
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.assigned_user_id == agent.user.id
    async with session_factory() as session:
        assigned = (
            await session.scalars(
                select(AuditLog).where(AuditLog.action == "conversation.assigned")
            )
        ).one()
        assignee = await session.get(User, conversation.assigned_user_id)
    assert assigned.actor_type == ACTOR_SYSTEM
    assert assigned.after_json["policy"] == "least_open"
    assert assignee is not None and assignee.email == "agent@vi.co"


async def test_welcome_reply_is_atomic_idempotent_and_limited_to_a_new_window(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    from app.models.audit import ACTOR_SYSTEM, AuditLog
    from app.models.business_event import (
        BUSINESS_EVENT_AUTOMATIC_REPLY_ACCEPTED,
        BusinessEvent,
    )

    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(
        session_factory,
        automatic_replies={
            "welcome_enabled": True,
            "welcome_body": "Thanks for contacting Vi.",
        },
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.WELCOME")]),
    )
    async with session_factory() as session:
        first = await MessageService(session).apply_inbound(routed[0])
    assert first["auto_reply_message_pk"]

    messages = await _rows(session_factory, Message)
    assert [(row.direction, row.content_json) for row in messages] == [
        (DIRECTION_INBOUND, {"body": "hello"}),
        (DIRECTION_OUTBOUND, {"body": "Thanks for contacting Vi."}),
    ]
    async with session_factory() as session:
        event = (
            await session.scalars(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == BUSINESS_EVENT_AUTOMATIC_REPLY_ACCEPTED
                )
            )
        ).one()
        audit = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "message.sent",
                    AuditLog.actor_type == ACTOR_SYSTEM,
                )
            )
        ).one()
    assert event.payload_json["kind"] == "welcome"
    assert event.payload_json["reply_message_id"] == first["auto_reply_message_pk"]
    assert audit.metadata_json["source"] == "inbox_operations"

    # A post-commit task retry recovers the same reply id for dispatch and creates no second row.
    async with session_factory() as session:
        duplicate = await MessageService(session).apply_inbound(routed[0])
    assert duplicate["status"] == DUPLICATE
    assert duplicate["auto_reply_message_pk"] == first["auto_reply_message_pk"]
    assert len(await _rows(session_factory, Message)) == 2

    second_routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.SAME-WINDOW", body="One more question")]),
    )
    async with session_factory() as session:
        second = await MessageService(session).apply_inbound(second_routed[-1])
    assert "auto_reply_message_pk" not in second
    assert len(await _rows(session_factory, Message)) == 3


async def test_locked_duplicate_recheck_recovers_the_same_automatic_reply(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """A concurrent waiter that missed the optimistic lookup rechecks after the thread lock."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(
        session_factory,
        automatic_replies={"welcome_enabled": True, "welcome_body": "Welcome once."},
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.LOCKED-DUPLICATE")]),
    )
    async with session_factory() as session:
        first = await MessageService(session).apply_inbound(routed[0])

    original_lookup = MessageRepository.get_by_provider_message_id
    lookups = 0

    async def miss_before_lock(self, provider_message_id, *, phone_number_id):
        nonlocal lookups
        lookups += 1
        if lookups == 1:
            return None
        return await original_lookup(self, provider_message_id, phone_number_id=phone_number_id)

    monkeypatch.setattr(MessageRepository, "get_by_provider_message_id", miss_before_lock)
    async with session_factory() as session:
        duplicate = await MessageService(session).apply_inbound(routed[0])

    assert lookups == 2
    assert duplicate["status"] == DUPLICATE
    assert duplicate["message_pk"] == first["message_pk"]
    assert duplicate["auto_reply_message_pk"] == first["auto_reply_message_pk"]
    assert len(await _rows(session_factory, Message)) == 2


async def test_off_hours_reply_takes_precedence_and_is_rate_limited(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    from app.models.business_event import BusinessEvent

    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(
        session_factory,
        working_hours={"enabled": True, "days": _closed_week()},
        automatic_replies={
            "welcome_enabled": True,
            "welcome_body": "Welcome.",
            "off_hours_enabled": True,
            "off_hours_body": "We are closed right now.",
        },
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.OFF-HOURS")]),
    )
    async with session_factory() as session:
        first = await MessageService(session).apply_inbound(routed[0])
    assert first["auto_reply_message_pk"]
    assert (await _rows(session_factory, Message))[-1].content_json == {
        "body": "We are closed right now."
    }

    routed_again = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.OFF-HOURS-AGAIN")]),
    )
    async with session_factory() as session:
        second = await MessageService(session).apply_inbound(routed_again[-1])
        events = list((await session.scalars(select(BusinessEvent))).all())
    assert "auto_reply_message_pk" not in second
    assert [
        event.payload_json["kind"]
        for event in events
        if event.event_type.endswith("reply.accepted")
    ] == ["off_hours"]


async def test_stale_or_opted_out_inbound_never_triggers_an_automatic_reply(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _set_inbox_operations(
        session_factory,
        consent={
            "enabled": True,
            "opt_in_keywords": ["START"],
            "opt_out_keywords": ["STOP"],
        },
        automatic_replies={
            "welcome_enabled": True,
            "welcome_body": "Welcome.",
        },
    )
    stale_at = (utcnow() - timedelta(hours=25)).replace(tzinfo=UTC)
    stale = _message(wamid="wamid.STALE", body="hello") | {
        "timestamp": str(int(stale_at.timestamp()))
    }
    stale_routed = await _deliver(
        client, session_factory, monkeypatch, make_user, _delivery(messages=[stale])
    )
    async with session_factory() as session:
        stale_result = await MessageService(session).apply_inbound(stale_routed[0])
    assert "auto_reply_message_pk" not in stale_result

    stop_routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.STOP-FRESH", body="STOP")]),
    )
    async with session_factory() as session:
        stop_result = await MessageService(session).apply_inbound(stop_routed[-1])
    assert "auto_reply_message_pk" not in stop_result
    assert all(row.direction == DIRECTION_INBOUND for row in await _rows(session_factory, Message))


async def test_second_message_reuses_contact_and_thread(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _inbound(client, make_user, session_factory, monkeypatch)
    await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_message(wamid="wamid.SECOND", body="are you there?")]),
    )
    routed = [r.id for r in await _events(session_factory)][-1:]
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    assert len(await _rows(session_factory, Contact)) == 1
    # uq_conv_number_contact: one thread per (number, contact), however many messages arrive.
    conversations = await _rows(session_factory, Conversation)
    assert len(conversations) == 1
    assert conversations[0].unread_count == 2
    assert conversations[0].last_message_preview == "are you there?"
    assert len(await _rows(session_factory, Message)) == 2


async def test_new_inbound_reopens_resolved_thread_but_duplicate_and_stale_delivery_do_not(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    from app.models.audit import ACTOR_SYSTEM, AuditLog

    await _seed_number(client, make_user, session_factory, monkeypatch)
    first_routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_fresh_message(wamid="wamid.REOPEN-BASE")]),
    )
    async with session_factory() as session:
        await MessageService(session).apply_inbound(first_routed[0])
        conversation = (await session.scalars(select(Conversation))).one()
        conversation.status = "resolved"
        await session.commit()

    # A broker retry is not a new customer action and must leave the manual/automatic resolution.
    async with session_factory() as session:
        duplicate = await MessageService(session).apply_inbound(first_routed[0])
    assert duplicate["status"] == DUPLICATE

    stale_at = (utcnow() - timedelta(hours=1)).replace(tzinfo=UTC)
    stale_routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[
                _message(wamid="wamid.REOPEN-STALE", body="older delivery")
                | {"timestamp": str(int(stale_at.timestamp()))}
            ]
        ),
    )
    async with session_factory() as session:
        await MessageService(session).apply_inbound(stale_routed[-1])
        assert (await session.scalars(select(Conversation))).one().status == "resolved"

    fresh_at = (utcnow() + timedelta(seconds=5)).replace(tzinfo=UTC)
    fresh_routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[
                _message(wamid="wamid.REOPEN-FRESH", body="new question")
                | {"timestamp": str(int(fresh_at.timestamp()))}
            ]
        ),
    )
    async with session_factory() as session:
        await MessageService(session).apply_inbound(fresh_routed[-1])
        conversation = (await session.scalars(select(Conversation))).one()
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
    assert conversation.status == "open"
    assert len(audits) == 1
    assert audits[0].metadata_json == {"source": "inbound_message"}


async def test_media_message_stores_a_canonical_reference(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """Media download is a later step; losing the reference now would lose the message."""
    image = {
        "from": SENDER,
        "id": "wamid.IMAGE",
        "timestamp": "1752739200",
        "type": "image",
        "image": {
            "id": "media-99",
            "mime_type": "image/jpeg",
            "sha256": "abc",
            "caption": "my bill",
        },
    }
    await _inbound(client, make_user, session_factory, monkeypatch, message=image)

    (message,) = await _rows(session_factory, Message)
    assert message.message_type == "image"
    assert message.content_json["media"]["channel_media_id"] == "media-99"
    assert message.content_json["media"]["mime_type"] == "image/jpeg"
    # The caption is what the inbox shows when there is no text body.
    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.last_message_preview == "my bill"


async def test_unsupported_type_preview_falls_back_to_the_type(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    location = {
        "from": SENDER,
        "id": "wamid.LOC",
        "timestamp": "1752739200",
        "type": "location",
        "location": {"latitude": 12.9, "longitude": 77.5},
    }
    await _inbound(client, make_user, session_factory, monkeypatch, message=location)
    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.last_message_preview == "[location]"
    (message,) = await _rows(session_factory, Message)
    assert message.content_json["location"]["latitude"] == 12.9


# --- 24-hour window (FR-WA-12) -----------------------------------------------
async def test_inbound_opens_the_24h_window(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    just_now = _message() | {"timestamp": str(int(utcnow().replace(tzinfo=UTC).timestamp()))}
    await _inbound(client, make_user, session_factory, monkeypatch, message=just_now)
    (conversation,) = await _rows(session_factory, Conversation)

    # The window runs from the customer's message, not from when we processed it.
    assert conversation.window_expires_at == conversation.last_inbound_at + WINDOW
    assert conversation.is_window_open is True and conversation.window_is_open is True


async def test_a_stale_inbound_message_does_not_open_the_window(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """The default fixture message is long past: replaying it must not re-open a dead window."""
    await _inbound(client, make_user, session_factory, monkeypatch)
    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.is_window_open is False and conversation.window_is_open is False


async def test_window_truth_is_computed_not_read_from_the_flag(session_factory) -> None:
    """Nothing writes to a thread when its window lapses, so the stored flag goes stale."""
    stale = Conversation(
        organization_id=1,
        phone_number_id=1,
        contact_id=1,
        is_window_open=True,  # what the last inbound message left behind
        window_expires_at=utcnow() - timedelta(minutes=1),
    )
    assert stale.is_window_open is True
    assert stale.window_is_open is False

    fresh = Conversation(
        organization_id=1,
        phone_number_id=1,
        contact_id=1,
        window_expires_at=utcnow() + timedelta(hours=1),
    )
    assert fresh.window_is_open is True
    assert Conversation(organization_id=1, phone_number_id=1, contact_id=1).window_is_open is False


# --- Idempotency (FR-WA-07) --------------------------------------------------
async def test_redelivered_inbound_message_is_applied_once(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """At-least-once delivery: the same wamid must not double the thread or the unread badge."""
    result = await _inbound(client, make_user, session_factory, monkeypatch)
    (event,) = await _events(session_factory)

    async with session_factory() as session:
        again = await MessageService(session).apply_inbound(event.id)

    assert again["status"] == DUPLICATE and again["message_id"] == result["message_id"]
    assert len(await _rows(session_factory, Message)) == 1
    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.unread_count == 1


async def test_replayed_older_message_does_not_rewind_the_thread(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """Replay is ordered by Meta's timestamp (Doc 04 §23.1); an older message is still older."""
    await _inbound(client, make_user, session_factory, monkeypatch)
    (conversation_before,) = await _rows(session_factory, Conversation)

    older = {
        "from": SENDER,
        "id": "wamid.OLDER",
        "timestamp": "1752652800",  # a day earlier than the first message
        "type": "text",
        "text": {"body": "sent earlier, arrived later"},
    }
    await _deliver(client, session_factory, monkeypatch, make_user, _delivery(messages=[older]))
    routed = [r.id for r in await _events(session_factory)][-1:]
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    (conversation,) = await _rows(session_factory, Conversation)
    # The newest message keeps the preview and the window; the older one is still stored.
    assert conversation.last_message_preview == "hello"
    assert conversation.last_inbound_at == conversation_before.last_inbound_at
    assert conversation.window_expires_at == conversation_before.window_expires_at
    assert len(await _rows(session_factory, Message)) == 2
    # It is unread all the same.
    assert conversation.unread_count == 2


# --- Status callbacks (FR-WA-06/07; Doc 06 §11.3) ----------------------------
def test_status_only_moves_forward() -> None:
    """Decision D16 in one table: this is what makes reordered webhooks safe."""
    assert advances(MSG_ACCEPTED, MSG_SENT)
    assert advances(MSG_SENT, MSG_DELIVERED)
    assert advances(MSG_DELIVERED, MSG_READ)
    assert not advances(MSG_READ, MSG_DELIVERED)
    assert not advances(MSG_DELIVERED, MSG_SENT)
    assert not advances(MSG_READ, MSG_READ)
    # `failed` can arrive from any live state, and nothing follows it.
    assert advances(MSG_SENT, MSG_FAILED)
    assert not advances(MSG_FAILED, MSG_READ)
    assert not advances(MSG_FAILED, MSG_DELIVERED)


async def _outbound_message(session_factory, wamid: str = "wamid.OUT") -> Message:
    """A message to hang statuses on. Outbound sending is a later step; the ledger row is not."""
    async with session_factory() as session:
        message = Message(
            organization_id=1,
            conversation_id=1,
            phone_number_id=1,
            contact_id=1,
            direction="outbound",
            wamid=wamid,
            message_type="text",
            status=MSG_ACCEPTED,
        )
        session.add(message)
        await session.commit()
        return message


async def test_status_callback_advances_the_message_and_logs_it(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _outbound_message(session_factory)
    await _post(client, _delivery(statuses=[_status("sent", wamid="wamid.OUT")]))
    (event,) = await _events(session_factory)

    async with session_factory() as session:
        result = await WebhookService(session).process(event.id, dispatch_inbound=_fail_routing)
    assert result["outcome"] == APPLIED

    (message,) = await _rows(session_factory, Message)
    assert message.status == MSG_SENT and message.sent_at is not None
    (history,) = await _rows(session_factory, MessageStatusHistory)
    assert history.status == MSG_SENT and history.wamid == "wamid.OUT"
    assert history.recipient_id == SENDER
    # The event is settled in the same transaction as the status it carried.
    assert (await _events(session_factory))[0].status == WH_PROCESSED


def _fail_routing(event_pk: int) -> None:
    raise AssertionError("a status callback must not be routed to inbound.process")


async def test_out_of_order_status_is_a_no_op(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """A late `delivered` arriving after `read` must not regress the ledger (Doc 06 §11.3)."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _outbound_message(session_factory)
    await _post(client, _delivery(statuses=[_status("read", wamid="wamid.OUT")]))
    await _post(client, _delivery(statuses=[_status("delivered", wamid="wamid.OUT")]))

    outcomes = []
    for event in await _events(session_factory):
        async with session_factory() as session:
            outcomes.append(
                (await WebhookService(session).process(event.id, dispatch_inbound=_fail_routing))[
                    "outcome"
                ]
            )
    assert outcomes == [APPLIED, IGNORED_STALE]

    (message,) = await _rows(session_factory, Message)
    assert message.status == MSG_READ
    # Both transitions are still logged: the log records what Meta told us, stale or not.
    assert [h.status for h in await _rows(session_factory, MessageStatusHistory)] == [
        MSG_READ,
        MSG_DELIVERED,
    ]


async def test_failed_status_records_the_error(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _outbound_message(session_factory)
    failed = _status("failed", wamid="wamid.OUT") | {
        "errors": [
            {
                "code": 131047,
                "title": "Re-engagement message",
                "error_data": {"details": "Message failed to send because more than 24 hours..."},
            }
        ]
    }
    await _post(client, _delivery(statuses=[failed]))
    (event,) = await _events(session_factory)
    async with session_factory() as session:
        await WebhookService(session).process(event.id, dispatch_inbound=_fail_routing)

    (message,) = await _rows(session_factory, Message)
    assert message.status == MSG_FAILED and message.error_code == "131047"
    (history,) = await _rows(session_factory, MessageStatusHistory)
    assert history.error_title == "Re-engagement message"
    assert history.error_detail.startswith("Message failed to send")


async def test_status_for_an_unknown_message_is_retryable_not_poison(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """The only thing that produces this is a race with our own send, which backoff resolves."""
    from app.queue.retry import FailureClass, classify

    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(statuses=[_status("delivered", wamid="wamid.NEVER-SENT")]))
    (event,) = await _events(session_factory)

    async with session_factory() as session:
        with pytest.raises(MessageNotFound):
            await WebhookService(session).process(event.id, dispatch_inbound=_fail_routing)

    assert classify(MessageNotFound("x")) is FailureClass.TRANSIENT_PROC
    assert classify(LedgerError("x")) is FailureClass.TERMINAL_DATA


# --- Queue integration (Doc 06 §2.3 / §11.2 `WP → INB`) ----------------------
async def test_webhook_processor_routes_messages_and_applies_statuses(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))
    (event,) = await _events(session_factory)

    routed: list[int] = []
    async with session_factory() as session:
        result = await WebhookService(session).process(event.id, dispatch_inbound=routed.append)

    # The webhook lane routes rather than applies: the conversation upsert belongs to the
    # inbound.process lane, off the Meta firehose.
    assert result["outcome"] == "routed" and routed == [event.id]
    assert await _rows(session_factory, Message) == []


def test_inbound_task_is_bound_to_the_inbound_process_queue() -> None:
    import app.channels.tasks as tasks

    assert tasks.process_inbound_message.queue_name == "inbound.process"


def test_inbound_task_dispatches_a_persisted_automatic_reply(monkeypatch) -> None:
    import app.channels.tasks as tasks

    queued: list[list[int]] = []
    monkeypatch.setattr(tasks.send_message, "apply_async", lambda args: queued.append(args))

    async def _with_reply(event_pk: int):
        return {
            "status": "applied",
            "message_pk": 42,
            "media_pending": False,
            "auto_reply_message_pk": 77,
        }

    monkeypatch.setattr(tasks, "_apply_inbound", _with_reply)
    tasks.process_inbound_message.run(1)

    assert queued == [[77]]


def test_inbound_task_dispatches_durable_automation_receipts(monkeypatch) -> None:
    import app.channels.tasks as tasks

    queued: list[tuple[list[int], str | None]] = []
    monkeypatch.setattr(
        tasks.consume_automation_trigger_receipt,
        "apply_async",
        lambda args, task_id=None: queued.append((args, task_id)),
    )

    async def _with_receipts(event_pk: int):
        return {
            "status": "applied",
            "message_pk": 42,
            "media_pending": False,
            "automation_receipts": [
                {"receipt_pk": 9, "task_id": "receipt-task-9"},
                {"receipt_pk": 10, "task_id": "receipt-task-10"},
            ],
        }

    monkeypatch.setattr(tasks, "_apply_inbound", _with_receipts)
    tasks.process_inbound_message.run(1)

    assert queued == [([9], "receipt-task-9"), ([10], "receipt-task-10")]


def test_ledger_error_dead_letters_instead_of_retrying(monkeypatch) -> None:
    import app.channels.tasks as tasks

    parked: list[tuple[int, str]] = []

    async def _boom(event_pk: int):
        raise LedgerError("inbound payload cannot be read")

    async def _park(event_pk: int, error: str):
        parked.append((event_pk, error))
        return {"status": "dead_lettered", "event_pk": event_pk}

    monkeypatch.setattr(tasks, "_apply_inbound", _boom)
    monkeypatch.setattr(tasks, "_dead_letter", _park)

    assert tasks.process_inbound_message.run(5)["status"] == "dead_lettered"
    assert len(parked) == 1 and "LedgerError" in parked[0][1]


# --- The seam (Doc 07 §5.3) --------------------------------------------------
def test_the_ledger_never_sees_a_graph_payload() -> None:
    """The adapter is the only thing that understands Meta's message shape."""
    from app.channels.base import get_adapter
    from app.channels.capabilities import CONNECTOR_META_CLOUD

    adapter = get_adapter(CONNECTOR_META_CLOUD)
    message = adapter.to_inbound_message(
        {"contacts": [{"profile": {"name": "Priya"}}], "message": _message()}
    )
    assert message.channel_message_id == WAMID and message.from_id == SENDER
    assert message.message_type == "text" and message.content == {"body": "hello"}
    assert message.profile_name == "Priya" and message.occurred_at is not None

    update = adapter.to_status_update({"status": _status("read")})
    assert update.channel_message_id == WAMID and update.status == MSG_READ
    assert update.recipient_id == SENDER


def test_a_quick_reply_button_canonicalises_as_interactive() -> None:
    from app.channels.base import get_adapter
    from app.channels.capabilities import CONNECTOR_META_CLOUD

    button = {
        "from": SENDER,
        "id": "wamid.BTN",
        "timestamp": "1752739200",
        "type": "button",
        "button": {"text": "Yes", "payload": "YES"},
    }
    message = get_adapter(CONNECTOR_META_CLOUD).to_inbound_message({"message": button})
    # Graph calls a quick reply `button` and a list reply `interactive`; both are the customer
    # picking an option, so the ledger sees one type.
    assert message.message_type == "interactive"
    assert message.content["interactive"]["payload"] == "YES"


def test_unreadable_payloads_are_rejected_as_ledger_errors(session_factory) -> None:
    from app.channels.meta.webhooks import MetaMessageError, to_inbound_message, to_status_update

    with pytest.raises(MetaMessageError):
        to_inbound_message({"message": {}})
    with pytest.raises(MetaMessageError):
        to_status_update({"status": {"id": "x", "status": "invented"}})
