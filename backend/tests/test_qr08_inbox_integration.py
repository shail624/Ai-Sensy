"""QR-08 — Unified Inbox integration: Meta + WAHA conversations in one Inbox.

Wires QR-04's already-built WAHA webhook verification/parsing and QR-05's already-built send/ack
translation into the **same** existing conversation/message ingestion and Inbox authorities Meta
already uses — the durable bridge ADR-0020 calls "one message ledger and event path", completed
here for the first time for a non-Meta provider.

Fully hermetic: Meta fixtures build `PhoneNumber`/`WhatsAppBusinessAccount` rows directly (the
`test_provider_message_identity.py` pattern); WAHA fixtures build `ChannelConnection`/
`ChannelEndpoint`/`ChannelSession` rows directly via the real provider-neutral services QR-07
already proved. Neither opens a socket.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid as uuidlib

import pytest
from sqlalchemy import select

from app.channels.capabilities import CONNECTOR_META_CLOUD, CONNECTOR_WAHA, ChannelType
from app.channels.foundation import ProviderDesiredState
from app.channels.models import MessageType
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime import PairingState
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionState
from app.channels.waha import register_waha_runtime
from app.core.exceptions import NotFoundError
from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.contact import Contact
from app.models.contact_identity import ContactIdentity
from app.models.conversation import Conversation
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
)
from app.models.settings import FeatureFlag
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.repositories.message import MessageRepository
from app.services.channel_connection_service import ChannelConnectionService
from app.services.conversation_service import ConversationService
from app.services.inbox_query_service import InboxQueryService
from app.services.message_service import DUPLICATE, MessageService
from app.services.send_service import (
    ChannelCapabilityNotSupportedError,
    ChannelNotConnectedError,
    SendService,
)
from app.services.session_manager import SessionManager
from app.services.webhook_service import WebhookService

PASSWORD = "Sup3r-Secret-Pass!"


@pytest.fixture(autouse=True)
def _waha_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file that ingests a WAHA delivery needs a configured HMAC secret."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "waha_webhook_hmac_secret", "qr08-test-hmac-secret")


# --- Meta fixtures (mirrors test_provider_message_identity.py's `_endpoint`) --------------------


async def _meta_endpoint(session, organization_id: int, *, suffix: str = "A") -> PhoneNumber:
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id,
        waba_id=f"WABA-{suffix}",
        business_name=f"Business {suffix}",
        access_token_enc=b"cipher",
    )
    session.add(waba)
    await session.flush()
    number = PhoneNumber(
        organization_id=organization_id,
        waba_id=waba.id,
        phone_number_id=f"PN-{suffix}",
        display_number=f"+9999000{suffix}",
    )
    session.add(number)
    await session.flush()
    return number


# --- WAHA fixtures (reuses the real M13-03/QR-07 services, not hand-built rows) ------------------


def _registries() -> tuple[ProviderRegistry, ProviderRuntimeRegistry]:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    runtimes = ProviderRuntimeRegistry(providers)
    register_waha_runtime(providers, runtimes)
    return providers, runtimes


async def _enable_flags(session, organization_id: int) -> None:
    from app.channels.flags import OmnichannelFeatureFlag

    for flag in OmnichannelFeatureFlag:
        session.add(
            FeatureFlag(key_name=flag.value, organization_id=organization_id, is_enabled=True)
        )
    await session.commit()


async def _waha_endpoint(
    session, organization_id: int, actor, *, suffix: str = "A", connected: bool = True
) -> ChannelEndpoint:
    """A real `ChannelConnection` + `ChannelEndpoint`, optionally with an ACTIVE/PAIRED session.

    Uses the actual QR-07 services (`ChannelConnectionService`, `SessionManager`) rather than
    hand-built rows, so this fixture is only as fake as "no live WAHA server was involved" — every
    row shape and write path is the real one.
    """
    providers, _runtimes = _registries()
    connection = await ChannelConnectionService(session).create_connection(
        organization_id=organization_id,
        actor=actor,
        channel_family=ChannelType.WHATSAPP.value,
        connector_type=CONNECTOR_WAHA,
        display_name=f"WhatsApp (WAHA) {suffix}",
        desired_state=ProviderDesiredState.ENABLED,
    )
    endpoint = await ChannelConnectionService(session).create_endpoint(
        organization_id=organization_id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_type="whatsapp_qr",
        normalized_address=f"waha-session-{suffix}",
        provider_endpoint_id=f"waha-session-{suffix}",
        enabled=True,
    )
    session_manager = SessionManager(session, providers=providers)
    row = await session_manager.register_session(
        organization_id=organization_id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        capability_references=["health", "text"],
    )
    if connected:
        # A fixture shortcut, not a re-test of QR-02..07's transition legality (already proven
        # elsewhere): only the resulting state matters to the code under test here.
        row.state = SessionState.ACTIVE.value
        row.pairing_state = PairingState.PAIRED.value
        await session.flush()
        await session.commit()
    return endpoint


def _waha_delivery(
    *,
    event: str,
    envelope_id: str,
    session: str,
    body: str,
    from_id: str,
    from_me: bool = False,
    alternate_from_id: str | None = None,
) -> dict:
    provider_address = from_id if "@" in from_id else f"{from_id}@c.us"
    payload: dict = {
        "id": f"true_{provider_address}_{envelope_id}",
        "from": provider_address,
        "fromMe": from_me,
        "body": body,
        "notifyName": "Priya",
    }
    if alternate_from_id is not None:
        payload["_data"] = {
            "key": {
                "remoteJid": provider_address,
                "remoteJidAlt": alternate_from_id,
            }
        }
    return {
        "id": envelope_id,
        "event": event,
        "session": session,
        "payload": payload,
    }


def _waha_ack_delivery(
    *, session: str, envelope_id: str, message_id: str, ack: int, recipient: str
) -> dict:
    return {
        "id": envelope_id,
        "event": "message.ack",
        "session": session,
        "payload": {
            "id": f"true_{recipient}_{message_id}",
            "from": recipient,
            "fromMe": True,
            "ack": ack,
        },
    }


async def _ingest_waha(session, delivery: dict) -> list[int]:
    """Verify+persist a WAHA delivery exactly as the public route does, minus the HTTP layer."""
    from app.core.config import settings

    body = json.dumps(delivery).encode()
    signature = hmac.new(
        settings.waha_webhook_hmac_secret.encode(), body, hashlib.sha512
    ).hexdigest()
    return await WebhookService(session, connector_type=CONNECTOR_WAHA).ingest(
        body=body, signature=signature
    )


async def _remember_waha_route(
    session, *, endpoint: ChannelEndpoint, contact: Contact, provider_address: str
) -> None:
    from app.channels.waha.identity import phone_wa_id, route_identity_namespace
    from app.db.mixins import utcnow

    connection = await session.get(ChannelConnection, endpoint.connection_id)
    assert connection is not None
    await ConversationService(session).remember_endpoint_contact_identity(
        endpoint=endpoint,
        connection=connection,
        contact=contact,
        provider_address=provider_address,
        route_namespace=route_identity_namespace(provider_address),
        phone_wa_id=phone_wa_id(provider_address),
        occurred_at=utcnow(),
    )
    await session.commit()


# =================================================================================================
# 1-3. Meta + WAHA inbound both land in the same Inbox; mixed list
# =================================================================================================


@pytest.mark.anyio
async def test_waha_inbound_creates_a_conversation_and_message(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="qr08-inbound@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor)

    delivery = _waha_delivery(
        event="message",
        envelope_id="evt-1",
        session="waha-session-A",
        body="hello from WAHA",
        from_id="919990001111",
    )
    event_ids = await _ingest_waha(db_session, delivery)
    assert len(event_ids) == 1
    result = await MessageService(db_session).apply_inbound(event_ids[0])
    assert result["status"] == "applied"

    (contact,) = (await db_session.scalars(select(Contact))).all()
    assert contact.wa_id == "919990001111"
    (conversation,) = (await db_session.scalars(select(Conversation))).all()
    assert conversation.channel_endpoint_id == endpoint.id
    assert conversation.phone_number_id is None
    (message,) = (await db_session.scalars(select(Message))).all()
    assert message.direction == DIRECTION_INBOUND
    assert message.channel_endpoint_id == endpoint.id
    assert message.content_json == {"body": "hello from WAHA"}


@pytest.mark.anyio
async def test_mixed_meta_and_waha_conversations_appear_in_one_inbox_list(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="qr08-mixed@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)

    # A Meta conversation.
    meta_number = await _meta_endpoint(db_session, organization.id, suffix="M")
    meta_contact = Contact(
        organization_id=organization.id, wa_id="919990002222", phone_e164="+919990002222"
    )
    db_session.add(meta_contact)
    await db_session.flush()
    meta_conv = Conversation(
        organization_id=organization.id, phone_number_id=meta_number.id, contact_id=meta_contact.id
    )
    db_session.add(meta_conv)
    await db_session.commit()

    # A WAHA conversation, via the real inbound path.
    waha_endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="W")
    delivery = _waha_delivery(
        event="message",
        envelope_id="evt-mix-1",
        session="waha-session-W",
        body="hi",
        from_id="919990003333",
    )
    event_ids = await _ingest_waha(db_session, delivery)
    await MessageService(db_session).apply_inbound(event_ids[0])

    result = await InboxQueryService(db_session).list_conversations(
        organization_id=organization.id,
        limit=10,
        cursor=None,
        contact=None,
        status=None,
        assignee=None,
        number=None,
        tag=None,
        q=None,
    )
    assert len(result.conversations) == 2
    connectors = [
        (
            result.endpoint_connectors.get(c.channel_endpoint_id, CONNECTOR_META_CLOUD)
            if c.channel_endpoint_id is not None
            else CONNECTOR_META_CLOUD
        )
        for c in result.conversations
    ]
    assert sorted(connectors) == sorted([CONNECTOR_META_CLOUD, CONNECTOR_WAHA])
    waha_conv = next(c for c in result.conversations if c.channel_endpoint_id == waha_endpoint.id)
    assert waha_conv.phone_number_id is None


# =================================================================================================
# 4-6. Stored-message dedupe proof (endpoint-scoped, canonical provider id)
# =================================================================================================


@pytest.mark.anyio
async def test_message_and_message_any_produce_one_stored_message(
    db_session, organization, make_user
) -> None:
    """The exact scenario the task calls out: `message` and `message.any` share one envelope.id
    and represent the SAME underlying WAHA message — event dedupe treats them as two valid events
    (different event types), but stored-message dedupe (endpoint + canonical provider id) must
    still collapse them to one row."""
    actor = (await make_user(email="qr08-dupe-any@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="D")

    shared_envelope = "evt-shared-1"
    first = _waha_delivery(
        event="message",
        envelope_id=shared_envelope,
        session="waha-session-D",
        body="dupe test",
        from_id="919990004444",
    )
    first["payload"]["timestamp"] = 1786135647
    second = _waha_delivery(
        event="message.any",
        envelope_id=shared_envelope,
        session="waha-session-D",
        body="dupe test",
        from_id="919990004444",
    )
    second["payload"]["timestamp"] = 1786135647
    ids_first = await _ingest_waha(db_session, first)
    ids_second = await _ingest_waha(db_session, second)
    # Two DISTINCT webhook_events rows — event dedupe is scoped by session+type, so both events
    # are genuinely persisted (this is not the bug; conflating them would be).
    assert ids_first != ids_second

    result_first = await MessageService(db_session).apply_inbound(ids_first[0])
    result_second = await MessageService(db_session).apply_inbound(ids_second[0])
    assert result_first["status"] == "applied"
    assert result_second["status"] == DUPLICATE
    assert result_first["message_pk"] == result_second["message_pk"]

    messages = (await db_session.scalars(select(Message))).all()
    assert len(messages) == 1
    conversations = (await db_session.scalars(select(Conversation))).all()
    assert len(conversations) == 1
    assert conversations[0].unread_count == 1
    assert conversations[0].last_inbound_at is not None
    assert conversations[0].last_inbound_at.tzinfo is None


@pytest.mark.anyio
async def test_concurrent_duplicate_waha_delivery_produces_one_message(
    db_session, organization, make_user
) -> None:
    """A retried delivery of the *same* event (redelivery, not a second event type) must also
    collapse to one stored message."""
    actor = (await make_user(email="qr08-dupe-retry@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="R")

    delivery = _waha_delivery(
        event="message",
        envelope_id="evt-retry-1",
        session="waha-session-R",
        body="retry test",
        from_id="919990005555",
    )
    ids_a = await _ingest_waha(db_session, delivery)
    ids_b = await _ingest_waha(db_session, delivery)  # at-least-once redelivery of the same event

    outcome_a = await MessageService(db_session).apply_inbound(ids_a[0])
    outcome_b = await MessageService(db_session).apply_inbound(ids_b[0])
    assert outcome_a["status"] == "applied"
    assert outcome_b["status"] == DUPLICATE
    assert (await db_session.scalars(select(Message))).all().__len__() == 1


@pytest.mark.anyio
async def test_same_provider_message_id_on_different_endpoints_does_not_collide(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="qr08-diff-endpoint@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint_a = await _waha_endpoint(db_session, organization.id, actor, suffix="EA")
    endpoint_b = await _waha_endpoint(db_session, organization.id, actor, suffix="EB")

    shared_id = "evt-collide-1"
    delivery_a = _waha_delivery(
        event="message",
        envelope_id=shared_id,
        session="waha-session-EA",
        body="on A",
        from_id="919990006666",
    )
    delivery_b = _waha_delivery(
        event="message",
        envelope_id=shared_id,
        session="waha-session-EB",
        body="on B",
        from_id="919990006666",
    )
    ids_a = await _ingest_waha(db_session, delivery_a)
    ids_b = await _ingest_waha(db_session, delivery_b)
    result_a = await MessageService(db_session).apply_inbound(ids_a[0])
    result_b = await MessageService(db_session).apply_inbound(ids_b[0])

    assert result_a["status"] == "applied"
    assert result_b["status"] == "applied"
    assert result_a["message_pk"] != result_b["message_pk"]

    repo = MessageRepository(db_session)
    found_a = await repo.get_by_provider_message_id_for_endpoint(
        "evt-collide-1", channel_endpoint_id=endpoint_a.id
    )
    found_b = await repo.get_by_provider_message_id_for_endpoint(
        "evt-collide-1", channel_endpoint_id=endpoint_b.id
    )
    assert found_a is not None and found_b is not None
    assert found_a.id != found_b.id


@pytest.mark.anyio
async def test_endpoint_scoped_lookup_has_no_unscoped_variant() -> None:
    """Same discipline QR-00 established for `phone_number_id` (test_provider_message_identity.py):
    the scope is keyword-only and required, so a global cross-tenant fallback cannot exist."""
    import inspect

    signature = inspect.signature(MessageRepository.get_by_provider_message_id_for_endpoint)
    scope = signature.parameters["channel_endpoint_id"]
    assert scope.kind is inspect.Parameter.KEYWORD_ONLY
    assert scope.default is inspect.Parameter.empty


# =================================================================================================
# 7-9. Outbound provider routing proof
# =================================================================================================


@pytest.mark.anyio
async def test_meta_reply_routes_through_meta(db_session, organization, make_user) -> None:
    from datetime import timedelta

    from app.db.mixins import utcnow

    actor = (await make_user(email="qr08-meta-reply@vi.co", is_superuser=True)).user
    number = await _meta_endpoint(db_session, organization.id, suffix="MR")
    contact = Contact(
        organization_id=organization.id, wa_id="919990007777", phone_e164="+919990007777"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id,
        phone_number_id=number.id,
        contact_id=contact.id,
        # An open 24h window (FR-WA-12) — this test proves routing, not the window rule itself.
        last_inbound_at=utcnow(),
        window_expires_at=utcnow() + timedelta(hours=1),
        is_window_open=True,
    )
    db_session.add(conversation)
    await db_session.commit()

    message = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.TEXT,
        content={"body": "reply via meta", "preview_url": False},
    )
    assert message.phone_number_id == number.id
    assert message.channel_endpoint_id is None


@pytest.mark.anyio
async def test_waha_reply_routes_through_waha(db_session, organization, make_user) -> None:
    actor = (await make_user(email="qr08-waha-reply@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="WR")
    contact = Contact(
        organization_id=organization.id, wa_id="919990008888", phone_e164="+919990008888"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    message = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.TEXT,
        content={"body": "reply via waha"},
    )
    assert message.channel_endpoint_id == endpoint.id
    assert message.phone_number_id is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("provider_address", "alternate_address", "phone_id", "route_namespace"),
    [
        ("919990018181@c.us", None, "919990018181", "whatsapp_jid"),
        (
            "919990018182@s.whatsapp.net",
            None,
            "919990018182",
            "whatsapp_jid",
        ),
        (
            "651430587620@lid",
            "919990018183@s.whatsapp.net",
            "919990018183",
            "whatsapp_lid",
        ),
    ],
    ids=("c-us", "s-whatsapp-net", "lid-with-phone-alias"),
)
async def test_waha_provider_identity_is_durable_and_exact_reply_route_is_reused(
    db_session,
    organization,
    make_user,
    provider_address: str,
    alternate_address: str | None,
    phone_id: str,
    route_namespace: str,
) -> None:
    """Provider routing evidence is endpoint-scoped; a LID never becomes a phone number."""
    import httpx

    from app.channels.base import _ADAPTERS
    from app.channels.waha import WahaChannelAdapter, WahaCredentials
    from app.channels.waha.client import WahaClient

    actor = (
        await make_user(email=f"qr09l-{route_namespace}-{phone_id}@vi.co", is_superuser=True)
    ).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="ID")
    delivery = _waha_delivery(
        event="message",
        envelope_id=f"identity-{phone_id}",
        session="waha-session-ID",
        body="provider identity observation",
        from_id=provider_address,
        alternate_from_id=alternate_address,
    )
    (event_pk,) = await _ingest_waha(db_session, delivery)

    # Constructed with the ordinary Meta default on purpose: persisted endpoint ownership must
    # select WAHA once the event is read, just as the background worker does.
    result = await MessageService(db_session).apply_inbound(event_pk)
    assert result["status"] == "applied"
    (contact,) = (await db_session.scalars(select(Contact))).all()
    assert contact.wa_id == phone_id
    if provider_address.endswith("@lid"):
        assert contact.wa_id != provider_address.removesuffix("@lid")

    identities = list(
        (
            await db_session.scalars(
                select(ContactIdentity)
                .where(ContactIdentity.contact_id == contact.id)
                .order_by(ContactIdentity.id.asc())
            )
        ).all()
    )
    route = next(row for row in identities if row.identity_namespace == route_namespace)
    phone = next(row for row in identities if row.identity_namespace == "whatsapp_phone")
    assert route.normalized_value == provider_address
    assert route.endpoint_ref == endpoint.public_id
    assert phone.normalized_value == f"+{phone_id}"

    (conversation,) = (await db_session.scalars(select(Conversation))).all()
    outbound = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.TEXT,
        content={"body": "exact provider route"},
    )

    seen: list[dict] = []

    def sent(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            201,
            json={
                "key": {
                    "remoteJid": provider_address,
                    "fromMe": True,
                    "id": f"QR09L-{phone_id}",
                }
            },
        )

    credentials = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="test-key", session="waha-session-ID"
    )
    adapter = WahaChannelAdapter(
        credentials,
        client=WahaClient(
            credentials,
            http=httpx.AsyncClient(transport=httpx.MockTransport(sent)),
        ),
    )
    original = _ADAPTERS.get(CONNECTOR_WAHA)
    _ADAPTERS[CONNECTOR_WAHA] = lambda **_: adapter
    try:
        outcome = await SendService(db_session).deliver(outbound.id)
    finally:
        if original is None:
            _ADAPTERS.pop(CONNECTOR_WAHA, None)
        else:
            _ADAPTERS[CONNECTOR_WAHA] = original

    assert outcome["status"] == "sent"
    assert seen == [
        {
            "session": "waha-session-ID",
            "chatId": provider_address,
            "text": "exact provider route",
        }
    ]


@pytest.mark.anyio
async def test_historical_duplicate_inbound_backfills_route_without_duplicating_message(
    db_session, organization, make_user
) -> None:
    """A preserved conversation can learn its provider route through normal event replay."""
    actor = (await make_user(email="qr09l-history-route@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="HISTORY")
    contact = Contact(
        organization_id=organization.id,
        wa_id="919990018184",
        phone_e164="+919990018184",
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id,
        channel_endpoint_id=endpoint.id,
        contact_id=contact.id,
    )
    db_session.add(conversation)
    await db_session.flush()
    existing = Message(
        organization_id=organization.id,
        conversation_id=conversation.id,
        channel_endpoint_id=endpoint.id,
        contact_id=contact.id,
        direction=DIRECTION_INBOUND,
        wamid="historical-provider-id",
        message_type="text",
        content_json={"body": "already preserved"},
        status=MSG_ACCEPTED,
    )
    db_session.add(existing)
    await db_session.commit()

    replay = _waha_delivery(
        event="message",
        envelope_id="historical-provider-id",
        session="waha-session-HISTORY",
        body="already preserved",
        from_id="651430587621@lid",
        alternate_from_id="919990018184@s.whatsapp.net",
    )
    (event_pk,) = await _ingest_waha(db_session, replay)
    result = await MessageService(db_session).apply_inbound(event_pk)

    assert result["status"] == DUPLICATE
    assert (await db_session.scalars(select(Message))).all() == [existing]
    identities = list((await db_session.scalars(select(ContactIdentity))).all())
    assert {(row.identity_namespace, row.normalized_value) for row in identities} == {
        ("whatsapp_lid", "651430587621@lid"),
        ("whatsapp_phone", "+919990018184"),
    }


@pytest.mark.anyio
async def test_unowned_lid_without_phone_alias_fails_closed(
    db_session, organization, make_user
) -> None:
    from app.services.message_service import LedgerError

    actor = (await make_user(email="qr09l-lid-no-alias@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="NOALIAS")
    delivery = _waha_delivery(
        event="message",
        envelope_id="lid-no-alias",
        session="waha-session-NOALIAS",
        body="must not become a phone",
        from_id="651430587622@lid",
    )
    (event_pk,) = await _ingest_waha(db_session, delivery)

    with pytest.raises(LedgerError, match="no provider-supplied phone alias"):
        await MessageService(db_session).apply_inbound(event_pk)
    assert (await db_session.scalars(select(Contact))).all() == []
    assert (await db_session.scalars(select(ContactIdentity))).all() == []


@pytest.mark.anyio
async def test_signed_waha_ack_worker_path_is_monotonic_idempotent_and_endpoint_scoped(
    db_session, organization, make_user
) -> None:
    """QR-09L: the default worker service derives WAHA from persisted endpoint ownership."""
    import httpx

    from app.channels.base import _ADAPTERS
    from app.channels.waha import WahaChannelAdapter, WahaCredentials
    from app.channels.waha.client import WahaClient
    from app.services.message_service import LedgerError

    actor = (await make_user(email="qr09l-ack-worker@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="ACK")
    inbound = _waha_delivery(
        event="message",
        envelope_id="ack-contact",
        session="waha-session-ACK",
        body="open acknowledgement conversation",
        from_id="919990019191@c.us",
    )
    (inbound_pk,) = await _ingest_waha(db_session, inbound)
    inbound_result = await MessageService(db_session).apply_inbound(inbound_pk)
    (conversation,) = (await db_session.scalars(select(Conversation))).all()
    outbound = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.TEXT,
        content={"body": "ack route"},
    )
    canonical_id = "QR09LACK3EB0D11C8F76C5EB15AD6B"

    credentials = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="test-key", session="waha-session-ACK"
    )
    adapter = WahaChannelAdapter(
        credentials,
        client=WahaClient(
            credentials,
            http=httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        201,
                        json={
                            "key": {
                                "remoteJid": "919990019191@c.us",
                                "fromMe": True,
                                "id": canonical_id,
                            }
                        },
                    )
                )
            ),
        ),
    )
    original = _ADAPTERS.get(CONNECTOR_WAHA)
    _ADAPTERS[CONNECTOR_WAHA] = lambda **_: adapter
    try:
        await SendService(db_session).deliver(outbound.id)
    finally:
        if original is None:
            _ADAPTERS.pop(CONNECTOR_WAHA, None)
        else:
            _ADAPTERS[CONNECTOR_WAHA] = original

    # Same canonical provider id on another endpoint must never be touched by this callback.
    endpoint_other = await _waha_endpoint(db_session, organization.id, actor, suffix="ACK-OTHER")
    other_conversation = Conversation(
        organization_id=organization.id,
        channel_endpoint_id=endpoint_other.id,
        contact_id=outbound.contact_id,
    )
    db_session.add(other_conversation)
    await db_session.flush()
    other = Message(
        organization_id=organization.id,
        conversation_id=other_conversation.id,
        channel_endpoint_id=endpoint_other.id,
        contact_id=outbound.contact_id,
        direction=DIRECTION_OUTBOUND,
        wamid=canonical_id,
        message_type="text",
        content_json={"body": "other endpoint"},
        status=MSG_ACCEPTED,
    )
    db_session.add(other)
    await db_session.commit()

    deliveries = [
        _waha_ack_delivery(
            session="waha-session-ACK",
            envelope_id="ack-device",
            message_id=canonical_id,
            ack=2,
            recipient="919990019191@c.us",
        ),
        _waha_ack_delivery(
            session="waha-session-ACK",
            envelope_id="ack-server-late",
            message_id=canonical_id,
            ack=1,
            recipient="919990019191@c.us",
        ),
        _waha_ack_delivery(
            session="waha-session-ACK",
            envelope_id="ack-read",
            message_id=canonical_id,
            ack=3,
            recipient="919990019191@c.us",
        ),
    ]
    outcomes: list[str] = []
    for delivery in deliveries:
        (event_pk,) = await _ingest_waha(db_session, delivery)
        processed = await WebhookService(db_session).process(
            event_pk, dispatch_inbound=lambda pk: pytest.fail(f"status routed inbound: {pk}")
        )
        outcomes.append(processed["outcome"])

    assert outcomes == ["applied", "ignored_stale", "applied"]
    await db_session.refresh(outbound)
    await db_session.refresh(other)
    assert outbound.status == MSG_READ
    assert outbound.delivered_at is not None and outbound.read_at is not None
    assert other.status == MSG_ACCEPTED
    histories = list(
        (
            await db_session.scalars(
                select(MessageStatusHistory)
                .where(MessageStatusHistory.message_id == outbound.id)
                .order_by(MessageStatusHistory.id.asc())
            )
        ).all()
    )
    assert [row.status for row in histories] == [MSG_DELIVERED, MSG_SENT, MSG_READ]

    # A provider redelivery is stored as evidence, then settled as a duplicate without a second
    # status-history row or a second message.
    (duplicate_pk,) = await _ingest_waha(db_session, deliveries[-1])
    duplicate = await WebhookService(db_session).process(
        duplicate_pk, dispatch_inbound=lambda pk: pytest.fail(f"status routed inbound: {pk}")
    )
    assert duplicate["status"] == "duplicate"
    assert (
        len(
            (
                await db_session.scalars(
                    select(MessageStatusHistory).where(
                        MessageStatusHistory.message_id == outbound.id
                    )
                )
            ).all()
        )
        == 3
    )
    scoped = list(
        (
            await db_session.scalars(
                select(Message).where(
                    Message.channel_endpoint_id == endpoint.id,
                    Message.wamid == canonical_id,
                )
            )
        ).all()
    )
    assert scoped == [outbound]

    unknown_delivery = _waha_ack_delivery(
        session="waha-session-ACK",
        envelope_id="ack-unknown",
        message_id=canonical_id,
        ack=99,
        recipient="919990019191@c.us",
    )
    (unknown_pk,) = await _ingest_waha(db_session, unknown_delivery)
    with pytest.raises(LedgerError, match="uncertified acknowledgement"):
        await WebhookService(db_session).process(
            unknown_pk, dispatch_inbound=lambda pk: pytest.fail(f"status routed inbound: {pk}")
        )
    await db_session.refresh(outbound)
    assert outbound.status == MSG_READ
    assert inbound_result["status"] == "applied"


@pytest.mark.anyio
async def test_forged_frontend_provider_cannot_reroute_a_waha_conversation(
    db_session, organization, make_user
) -> None:
    """There is no provider field on the conversation-scoped send request at all (QR-08's
    `MessageSendRequest`/`accept_for_conversation`) — routing comes only from the conversation's
    own durable ownership. Proven here by calling the real entry point with a WAHA conversation and
    confirming the result is WAHA-routed regardless of what a caller might have wished for."""
    actor = (await make_user(email="qr08-forge@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="FG")
    contact = Contact(
        organization_id=organization.id, wa_id="919990009999", phone_e164="+919990009999"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    # `accept_for_conversation` has no `phone_number_id`/`connector`/`provider` parameter at all —
    # there is nothing to forge. It is called exactly as the API route calls it.
    message = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.TEXT,
        content={"body": "cannot be Meta"},
    )
    assert message.channel_endpoint_id == endpoint.id
    assert message.phone_number_id is None

    # A prohibited-capability send (e.g. TEMPLATE) against a WAHA conversation is refused, not
    # silently downgraded to text or routed to Meta.
    with pytest.raises(ChannelCapabilityNotSupportedError):
        await SendService(db_session).accept_for_conversation(
            organization_id=organization.id,
            actor=actor,
            conversation_public_id=uuidlib.UUID(conversation.public_id),
            message_type=MessageType.TEMPLATE,
            content={"template": {"id": str(uuidlib.uuid4()), "header": [], "body": []}},
        )


# =================================================================================================
# 10. Tenant/RBAC proof
# =================================================================================================


@pytest.mark.anyio
async def test_cross_org_conversation_read_and_send_are_rejected(
    db_session, organization, make_user
) -> None:
    from app.models.organization import Organization

    other_org = Organization(name="Other Tenant", slug="qr08-other-tenant")
    db_session.add(other_org)
    await db_session.flush()

    owner = (await make_user(email="qr08-tenant-owner@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, owner, suffix="TN")
    contact = Contact(
        organization_id=organization.id, wa_id="919990010101", phone_e164="+919990010101"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    # A read scoped to the OTHER organization must not find this conversation.
    result = await InboxQueryService(db_session).list_conversations(
        organization_id=other_org.id,
        limit=10,
        cursor=None,
        contact=None,
        status=None,
        assignee=None,
        number=None,
        tag=None,
        q=None,
    )
    assert result.conversations == []

    intruder = (await make_user(email="qr08-intruder@vi.co", full_name="Intruder")).user
    intruder.organization_id = other_org.id
    await db_session.commit()
    with pytest.raises(NotFoundError):
        await SendService(db_session).accept_for_conversation(
            organization_id=other_org.id,
            actor=intruder,
            conversation_public_id=uuidlib.UUID(conversation.public_id),
            message_type=MessageType.TEXT,
            content={"body": "should never send"},
        )


@pytest.mark.anyio
async def test_same_org_user_without_permission_cannot_read_or_send_to_waha_conversation(
    client, db_session, organization, make_user
) -> None:
    """RBAC applies uniformly regardless of provider: `inbox:read`/`messages:send` gate a WAHA
    conversation exactly as they gate a Meta one — there is no separate, weaker WAHA permission
    surface an under-permissioned same-org user could fall through."""
    owner = (await make_user(email="qr08-rbac-owner@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, owner, suffix="RBAC")
    contact = Contact(
        organization_id=organization.id, wa_id="919990013131", phone_e164="+919990013131"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    # A same-org user with NO roles/permissions granted at all.
    await make_user(email="qr08-no-perms@vi.co", password=PASSWORD)
    login = await client.post(
        "/api/v1/auth/login", json={"email": "qr08-no-perms@vi.co", "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    read_resp = await client.get(f"/api/v1/conversations/{conversation.public_id}", headers=headers)
    assert read_resp.status_code == 403

    send_resp = await client.post(
        "/api/v1/messages/send",
        headers={**headers, "Idempotency-Key": "qr08-rbac-key-1"},
        json={
            "conversation_id": conversation.public_id,
            "type": "text",
            "text": {"body": "should never send"},
        },
    )
    assert send_resp.status_code == 403


# =================================================================================================
# 11-12. Ambiguous / unavailable WAHA send truth
# =================================================================================================


@pytest.mark.anyio
async def test_ambiguous_waha_send_is_marked_indeterminate_not_auto_retried(
    db_session, organization, make_user
) -> None:
    import httpx

    from app.channels.waha import WahaChannelAdapter, WahaCredentials
    from app.channels.waha.client import WahaClient

    actor = (await make_user(email="qr08-indeterminate@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(db_session, organization.id, actor, suffix="AMB")
    contact = Contact(
        organization_id=organization.id, wa_id="919990011111", phone_e164="+919990011111"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()
    await _remember_waha_route(
        db_session,
        endpoint=endpoint,
        contact=contact,
        provider_address="919990011111@c.us",
    )

    message = await SendService(db_session).accept_endpoint(
        organization_id=organization.id,
        actor=actor,
        endpoint=endpoint,
        conversation=conversation,
        contact=contact,
        body="ambiguous outcome",
    )
    assert message.status == MSG_ACCEPTED

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    creds = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="k", session="waha-session-AMB"
    )
    transport = httpx.MockTransport(down)
    down_adapter = WahaChannelAdapter(
        creds, client=WahaClient(creds, http=httpx.AsyncClient(transport=transport))
    )

    from app.channels.base import _ADAPTERS  # the module-level registry `get_adapter` reads

    original = _ADAPTERS.get(CONNECTOR_WAHA)
    _ADAPTERS[CONNECTOR_WAHA] = lambda **_: down_adapter
    try:
        outcome = await SendService(db_session).deliver(message.id)
    finally:
        if original is not None:
            _ADAPTERS[CONNECTOR_WAHA] = original

    assert outcome["status"] == MSG_FAILED
    refreshed = await db_session.get(Message, message.id)
    assert refreshed.status == MSG_FAILED
    assert refreshed.error_code == "indeterminate"
    assert refreshed.wamid is None  # never claimed a wamid it doesn't have


@pytest.mark.anyio
async def test_waha_send_blocked_truthfully_when_not_connected(
    db_session, organization, make_user
) -> None:
    """provider outage / re-auth required must refuse the send honestly at accept time, not
    silently queue something that will only fail later."""
    actor = (await make_user(email="qr08-not-connected@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    endpoint = await _waha_endpoint(
        db_session, organization.id, actor, suffix="DOWN", connected=False
    )
    contact = Contact(
        organization_id=organization.id, wa_id="919990012121", phone_e164="+919990012121"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, channel_endpoint_id=endpoint.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    with pytest.raises(ChannelNotConnectedError):
        await SendService(db_session).accept_endpoint(
            organization_id=organization.id,
            actor=actor,
            endpoint=endpoint,
            conversation=conversation,
            contact=contact,
            body="should be refused",
        )
    assert (await db_session.scalars(select(Message))).all() == []


# =================================================================================================
# QR-09-D3 — an oversized WAHA delivery is a client error, not a server fault
# =================================================================================================
#
# The 1 MiB bound itself is QR-04's and is not changed here: the body is still refused *before* it
# is hashed. What QR-09 found is that `WahaBodyTooLarge` had no HTTP mapping, so the public route
# answered 500. That matters operationally, not just cosmetically: WAHA delivery is at-least-once
# and a 5xx is exactly what it retries, so one oversized delivery became an endless redelivery
# loop, while genuine server faults were drowned in the noise.


def _oversized_delivery() -> bytes:
    from app.channels.waha.webhook import MAX_BODY_BYTES

    payload = {
        "id": "qr09a-oversized",
        "event": "message",
        "session": "waha-session-A",
        "payload": {
            "id": "true_919990001111@c.us_qr09a-oversized",
            "from": "919990001111@c.us",
            "fromMe": False,
            "body": "A" * (MAX_BODY_BYTES + 4096),
        },
    }
    raw = json.dumps(payload).encode()
    assert len(raw) > MAX_BODY_BYTES
    return raw


@pytest.mark.anyio
async def test_oversized_waha_delivery_is_refused_as_a_client_error_not_a_500(
    client, db_session
) -> None:
    """413, not 500 — so the provider stops redelivering instead of looping forever."""
    raw = _oversized_delivery()
    signature = hmac.new(b"qr08-test-hmac-secret", raw, hashlib.sha512).hexdigest()

    response = await client.post(
        "/api/v1/webhooks/waha",
        content=raw,
        headers={"Content-Type": "application/json", "X-Webhook-Hmac": signature},
    )

    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "payload_too_large"
    assert body["status"] == 413


@pytest.mark.anyio
async def test_oversized_waha_delivery_persists_nothing(client, db_session) -> None:
    """Refused before hashing means refused before ingestion: no event row, no message row."""
    from app.models.webhook import WebhookEvent

    raw = _oversized_delivery()
    signature = hmac.new(b"qr08-test-hmac-secret", raw, hashlib.sha512).hexdigest()

    await client.post(
        "/api/v1/webhooks/waha",
        content=raw,
        headers={"Content-Type": "application/json", "X-Webhook-Hmac": signature},
    )

    assert (await db_session.scalars(select(WebhookEvent))).all() == []
    assert (await db_session.scalars(select(Message))).all() == []


@pytest.mark.anyio
async def test_oversized_waha_delivery_echoes_no_body_content(client) -> None:
    """The refusal states the bound, never the attacker-influencable body it refused."""
    raw = _oversized_delivery()
    signature = hmac.new(b"qr08-test-hmac-secret", raw, hashlib.sha512).hexdigest()

    response = await client.post(
        "/api/v1/webhooks/waha",
        content=raw,
        headers={"Content-Type": "application/json", "X-Webhook-Hmac": signature},
    )

    rendered = response.text
    assert "AAAA" not in rendered
    assert "919990001111" not in rendered
    assert "Traceback" not in rendered


@pytest.mark.anyio
async def test_normal_sized_and_badly_signed_deliveries_are_unaffected(client) -> None:
    """The bound is the only thing D3 changed: valid stays 200, invalid HMAC stays 403."""
    delivery = _waha_delivery(
        event="message",
        envelope_id="qr09a-normal",
        session="waha-session-A",
        body="normal sized",
        from_id="919990001111",
    )
    raw = json.dumps(delivery).encode()

    ok = await client.post(
        "/api/v1/webhooks/waha",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Hmac": hmac.new(b"qr08-test-hmac-secret", raw, hashlib.sha512).hexdigest(),
        },
    )
    assert ok.status_code == 200

    forged = await client.post(
        "/api/v1/webhooks/waha",
        content=raw,
        headers={"Content-Type": "application/json", "X-Webhook-Hmac": "deadbeef"},
    )
    assert forged.status_code == 403
