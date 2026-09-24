"""Sending photos, videos, audio and documents on a QR (WAHA) chat (UI-AIS-07)."""

from __future__ import annotations

import base64
import json
import uuid as uuidlib

import httpx
import pytest
from sqlalchemy import select

from app.channels.base import _ADAPTERS
from app.channels.capabilities import CONNECTOR_WAHA
from app.channels.models import MessageType
from app.channels.waha import WahaChannelAdapter, WahaCredentials
from app.channels.waha.client import WahaClient
from app.core.exceptions import ValidationError
from app.models.conversation import Conversation
from app.services.media_service import MediaService
from app.services.message_service import MessageService
from app.services.send_service import ChannelCapabilityNotSupportedError, SendService
from tests.test_qr08_inbox_integration import (
    _enable_flags,
    _ingest_waha,
    _waha_delivery,
    _waha_endpoint,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


async def _qr_thread(db_session, organization, actor) -> Conversation:
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="MD")
    delivery = _waha_delivery(
        event="message",
        envelope_id="media-thread",
        session="waha-session-MD",
        body="hi",
        from_id="919990021212@c.us",
    )
    (event_pk,) = await _ingest_waha(db_session, delivery)
    await MessageService(db_session).apply_inbound(event_pk)
    (conversation,) = (await db_session.scalars(select(Conversation))).all()
    return conversation


@pytest.mark.anyio
async def test_photo_is_stored_then_sent_inline(db_session, organization, make_user) -> None:
    actor = (await make_user(email="qr-media@vi.co", is_superuser=True)).user
    conversation = await _qr_thread(db_session, organization, actor)
    asset, _ = await MediaService(db_session).upload(
        organization_id=organization.id,
        actor=actor,
        data=PNG,
        media_type="image",
        mime_type="image/png",
        file_name="plan.png",
    )
    await db_session.commit()

    message = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.MEDIA,
        content={
            "media": {"kind": "image", "media_asset_id": asset.public_id, "caption": "New plan"}
        },
    )
    assert message.message_type == "image"
    assert message.media_asset_id == asset.id
    await db_session.refresh(conversation)
    assert conversation.last_message_preview == "New plan"

    seen: list[tuple[str, dict]] = []

    def sent(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, json.loads(request.content)))
        return httpx.Response(
            201, json={"key": {"remoteJid": "919990021212@c.us", "fromMe": True, "id": "IMG-1"}}
        )

    credentials = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="test-key", session="waha-session-MD"
    )
    adapter = WahaChannelAdapter(
        credentials,
        client=WahaClient(credentials, http=httpx.AsyncClient(transport=httpx.MockTransport(sent))),
    )
    original = _ADAPTERS.get(CONNECTOR_WAHA)
    _ADAPTERS[CONNECTOR_WAHA] = lambda **_: adapter
    try:
        outcome = await SendService(db_session).deliver(message.id)
    finally:
        if original is None:
            _ADAPTERS.pop(CONNECTOR_WAHA, None)
        else:
            _ADAPTERS[CONNECTOR_WAHA] = original

    assert outcome["status"] == "sent"
    ((path, payload),) = seen
    assert path == "/api/sendImage"
    assert payload["caption"] == "New plan"
    assert payload["file"]["filename"] == "plan.png"
    assert base64.b64decode(payload["file"]["data"]) == PNG


@pytest.mark.anyio
async def test_media_needs_a_stored_file_and_other_types_stay_refused(
    db_session, organization, make_user
) -> None:
    actor = (await make_user(email="qr-media-refuse@vi.co", is_superuser=True)).user
    conversation = await _qr_thread(db_session, organization, actor)
    service = SendService(db_session)
    public = uuidlib.UUID(conversation.public_id)

    with pytest.raises(ValidationError):
        await service.accept_for_conversation(
            organization_id=organization.id,
            actor=actor,
            conversation_public_id=public,
            message_type=MessageType.MEDIA,
            content={"media": {"kind": "image", "link": "https://example.com/a.png"}},
        )
    with pytest.raises(ChannelCapabilityNotSupportedError):
        await service.accept_for_conversation(
            organization_id=organization.id,
            actor=actor,
            conversation_public_id=public,
            message_type=MessageType.TEMPLATE,
            content={"template": {"id": str(uuidlib.uuid4())}},
        )


@pytest.mark.anyio
async def test_location_is_accepted_on_a_qr_chat(db_session, organization, make_user) -> None:
    actor = (await make_user(email="qr-location@vi.co", is_superuser=True)).user
    conversation = await _qr_thread(db_session, organization, actor)
    message = await SendService(db_session).accept_for_conversation(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation.public_id),
        message_type=MessageType.LOCATION,
        content={"location": {"latitude": 28.61, "longitude": 77.2, "name": "Vi Store"}},
    )
    assert message.message_type == "location"
    await db_session.refresh(conversation)
    assert conversation.last_message_preview == "📍 Vi Store"
