"""UI-AIS-05 — start a QR chat with a new number, and fetch a customer's profile photo safely."""

from __future__ import annotations

import uuid as uuidlib

import httpx
import pytest
from sqlalchemy import select

from app.channels.waha import WahaChannelAdapter, WahaCredentials
from app.channels.waha.client import MAX_PROFILE_PICTURE_BYTES, WahaClient
from app.core.exceptions import ConflictError, ValidationError
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.services.whatsapp_qr_service import WhatsAppQrService, normalize_phone_input
from tests.test_qr08_inbox_integration import _enable_flags, _registries, _waha_endpoint

SESSION = "waha-session-NEW"


def _client(handler) -> WahaClient:
    credentials = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="k", session=SESSION
    )
    return WahaClient(credentials, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


# --- phone input ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "digits"),
    [
        ("9891000010", "919891000010"),
        ("+91 98910 00010", "919891000010"),
        ("+1 (415) 555-2671", "14155552671"),
    ],
)
def test_phone_input_accepts_common_forms(typed: str, digits: str) -> None:
    assert normalize_phone_input(typed) == digits


@pytest.mark.parametrize("typed", ["12345", "abc", "+91 98910", "1234567890123456"])
def test_phone_input_rejects_what_cannot_be_a_number(typed: str) -> None:
    with pytest.raises(ValidationError):
        normalize_phone_input(typed)


# --- photo download guard ------------------------------------------------------------------------


@pytest.mark.anyio
async def test_photo_download_only_follows_whatsapp_https_images() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert "X-Api-Key" not in request.headers  # the WAHA key never leaves for WhatsApp's CDN
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"\xff\xd8jpeg")

    client = _client(handler)
    assert await client.download_profile_picture("https://pps.whatsapp.net/v/t61/abc.jpg") == (
        b"\xff\xd8jpeg",
        "image/jpeg",
    )
    for refused in (
        "http://pps.whatsapp.net/x.jpg",
        "https://evil.example/x.jpg",
        "https://whatsapp.net.evil.example/x.jpg",
        "https://169.254.169.254/latest/meta-data",
    ):
        assert await client.download_profile_picture(refused) is None
    assert seen == ["https://pps.whatsapp.net/v/t61/abc.jpg"]


@pytest.mark.anyio
async def test_photo_download_refuses_non_images_and_oversized_files() -> None:
    responses = iter(
        [
            httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>"),
            httpx.Response(
                200,
                headers={"content-type": "image/jpeg"},
                content=b"x" * (MAX_PROFILE_PICTURE_BYTES + 1),
            ),
        ]
    )
    client = _client(lambda request: next(responses))
    assert await client.download_profile_picture("https://pps.whatsapp.net/a.jpg") is None
    assert await client.download_profile_picture("https://pps.whatsapp.net/b.jpg") is None


# --- start a chat ----------------------------------------------------------------------------------


def _service(db_session, handler) -> WhatsAppQrService:
    providers, runtimes = _registries()
    credentials = WahaCredentials(
        base_url="http://waha.internal:3000", api_key="k", session=SESSION
    )
    adapter = WahaChannelAdapter(
        credentials,
        client=WahaClient(
            credentials, http=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        ),
    )
    return WhatsAppQrService(db_session, providers=providers, runtimes=runtimes, adapter=adapter)


@pytest.fixture
def _waha_configured(monkeypatch, organization) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "waha_base_url", "http://waha.internal:3000")
    monkeypatch.setattr(settings, "waha_api_key", "k")
    monkeypatch.setattr(settings, "waha_session_name", SESSION)
    monkeypatch.setattr(settings, "waha_organization_id", organization.id)


@pytest.mark.anyio
async def test_start_chat_creates_contact_route_and_thread_once(
    db_session, organization, make_user, _waha_configured
) -> None:
    actor = (await make_user(email="start-chat@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="NEW")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/contacts/check-exists"
        assert request.url.params["phone"] == "919891000010"
        return httpx.Response(200, json={"numberExists": True, "chatId": "919891000010@c.us"})

    service = _service(db_session, handler)
    first = await service.start_chat(
        organization_id=organization.id, actor=actor, phone="98910 00010"
    )
    again = await service.start_chat(
        organization_id=organization.id, actor=actor, phone="+919891000010"
    )

    assert first == again
    (contact,) = (await db_session.scalars(select(Contact))).all()
    assert contact.wa_id == "919891000010"
    (conversation,) = (await db_session.scalars(select(Conversation))).all()
    assert conversation.public_id == first and conversation.channel_endpoint_id is not None


@pytest.mark.anyio
async def test_start_chat_refuses_a_number_without_whatsapp(
    db_session, organization, make_user, _waha_configured
) -> None:
    actor = (await make_user(email="start-chat-none@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="NEW")
    service = _service(
        db_session, lambda request: httpx.Response(200, json={"numberExists": False})
    )

    with pytest.raises(ConflictError, match="not on WhatsApp"):
        await service.start_chat(organization_id=organization.id, actor=actor, phone="9100000000")
    assert (await db_session.scalars(select(Contact))).all() == []
    assert (await db_session.scalars(select(Conversation))).all() == []


@pytest.mark.anyio
async def test_start_chat_requires_a_paired_connection(
    db_session, organization, make_user, _waha_configured
) -> None:
    actor = (await make_user(email="start-chat-unpaired@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="NEW", connected=False)
    service = _service(db_session, lambda request: pytest.fail("WhatsApp must not be asked"))

    with pytest.raises(ConflictError, match="not connected"):
        await service.start_chat(organization_id=organization.id, actor=actor, phone="9891000010")


@pytest.mark.anyio
async def test_contact_photo_is_fetched_through_the_qr_phone(
    db_session, organization, make_user, _waha_configured
) -> None:
    actor = (await make_user(email="photo@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="NEW")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/contacts/check-exists":
            return httpx.Response(200, json={"numberExists": True, "chatId": "919891000010@c.us"})
        if request.url.path == "/api/contacts/profile-picture":
            assert request.url.params["contactId"] == "919891000010@c.us"
            return httpx.Response(200, json={"profilePictureURL": "https://pps.whatsapp.net/p.jpg"})
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"jpeg")

    service = _service(db_session, handler)
    conversation_id = await service.start_chat(
        organization_id=organization.id, actor=actor, phone="9891000010"
    )

    assert await service.contact_photo(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(conversation_id),
    ) == (b"jpeg", "image/jpeg")


@pytest.mark.anyio
async def test_official_api_chat_gets_its_photo_through_the_qr_phone(
    db_session, organization, make_user, _waha_configured
) -> None:
    """Meta shares no profile photos, so API chats use the QR WhatsApp's view (UI-AIS-11)."""
    from tests.test_qr08_inbox_integration import _meta_endpoint

    actor = (await make_user(email="photo-api@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    await _waha_endpoint(db_session, organization.id, actor, suffix="API")
    number = await _meta_endpoint(db_session, organization.id, suffix="APIP")
    contact = Contact(
        organization_id=organization.id, wa_id="919891000011", phone_e164="+919891000011"
    )
    db_session.add(contact)
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id, phone_number_id=number.id, contact_id=contact.id
    )
    db_session.add(conversation)
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/contacts/profile-picture":
            assert request.url.params["contactId"] == "919891000011@c.us"
            return httpx.Response(200, json={"profilePictureURL": "https://pps.whatsapp.net/q.jpg"})
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"api-jpeg")

    photo = await _service(db_session, handler).contact_photo(
        organization_id=organization.id,
        actor=actor,
        conversation_public_id=uuidlib.UUID(bytes=conversation.uuid),
    )
    assert photo == (b"api-jpeg", "image/jpeg")
