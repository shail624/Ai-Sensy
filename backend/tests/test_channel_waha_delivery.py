"""QR-05 — WAHA send path and delivery-state reconciliation.

Fully hermetic. The shapes asserted here were captured during physical-phone certification against
``devlikeapro/waha@sha256:33ecd1b7…`` (2026.7.2 / NOWEB / CORE): the real cross-account send
response, and the acknowledgement chain that arrived **out of order** as
``DEVICE(2) → SERVER(1) → READ(3)``.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.capabilities import Capability
from app.channels.errors import ChannelApiError, ChannelConfigError, ChannelNotSupported
from app.channels.models import (
    MediaContent,
    MediaKind,
    MessageType,
    OutboundMessage,
    TextContent,
)
from app.channels.waha import (
    PROHIBITED_CAPABILITIES,
    WahaAck,
    WahaChannelAdapter,
    WahaCredentials,
    WahaSendIndeterminate,
    extract_sent_id,
    map_ack,
)
from app.channels.waha.client import WahaClient
from app.channels.waha.delivery import to_status_update
from app.models.message import (
    MSG_ACCEPTED,
    MSG_DELIVERED,
    MSG_FAILED,
    MSG_READ,
    MSG_SENT,
    STATUS_RANK,
    advances,
)

CREDS = WahaCredentials(
    base_url="http://waha.internal:3000", api_key="test-key-never-logged", session="phonecert"
)
OTHER_ENDPOINT = WahaCredentials(
    base_url="http://waha.internal:3000", api_key="test-key-never-logged", session="otherorg"
)

# Real cross-account send response.
SEND_BODY = {
    "key": {
        "remoteJid": "918376035760@s.whatsapp.net",
        "fromMe": True,
        "id": "3EB0D11C8F76C5EB15AD6B",
    },
    "messageTimestamp": 1786134979,
    "status": "PENDING",
}
CANONICAL = "3EB0D11C8F76C5EB15AD6B"


def _adapter(handler, creds: WahaCredentials = CREDS) -> WahaChannelAdapter:
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(
        creds, client=WahaClient(creds, http=httpx.AsyncClient(transport=transport))
    )


def _ack(code: int, message_id: str = f"true_651430587620@lid_{CANONICAL}") -> dict:
    """A real ack envelope — note the @lid addressing acks actually arrive with."""
    return {
        "id": "evt_ack",
        "event": "message.ack",
        "session": "phonecert",
        "payload": {"id": message_id, "from": "918376035760@c.us", "fromMe": True, "ack": code},
    }


def _text(to: str = "918376035760@c.us", body: str = "QRCERT-OUTBOUND-TEST") -> OutboundMessage:
    return OutboundMessage(to=to, type=MessageType.TEXT, content=TextContent(body=body))


# --- Send ---------------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_successful_text_send() -> None:
    seen: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.content))
        return httpx.Response(201, json=SEND_BODY)

    adapter = _adapter(handler)
    result = await adapter.send(_text())
    assert seen[0][0] == "/api/sendText"
    assert b'"session": "phonecert"' in seen[0][1] or b'"session":"phonecert"' in seen[0][1]
    assert result.accepted is True
    assert result.channel_message_id == CANONICAL
    assert result.to == "918376035760@c.us"


@pytest.mark.anyio
async def test_send_requires_configured_session() -> None:
    """A send without an explicit endpoint scope fails closed before any request."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(201, json=SEND_BODY)

    creds = WahaCredentials(base_url="http://waha.internal:3000", api_key="k", session="")
    adapter = _adapter(handler, creds)
    with pytest.raises(ChannelConfigError):
        await adapter.send(_text())
    assert seen == []


@pytest.mark.anyio
async def test_non_text_is_refused_not_degraded() -> None:
    adapter = _adapter(lambda r: httpx.Response(201, json=SEND_BODY))
    message = OutboundMessage(
        to="918376035760@c.us",
        type=MessageType.MEDIA,
        content=MediaContent(kind=MediaKind.IMAGE, link="http://x/y.png"),
    )
    with pytest.raises(ChannelNotSupported):
        await adapter.send(message)


@pytest.mark.anyio
async def test_send_without_provider_id_is_not_accepted() -> None:
    """No id means nothing can ever correlate an ack or be reconciled — not a success."""
    adapter = _adapter(lambda r: httpx.Response(201, json={"status": "PENDING"}))
    result = await adapter.send(_text())
    assert result.accepted is False
    assert result.channel_message_id is None


def test_provider_id_extraction_and_canonicalization() -> None:
    assert extract_sent_id(SEND_BODY) == CANONICAL
    assert extract_sent_id({"id": f"true_918376035760@c.us_{CANONICAL}"}) == CANONICAL
    assert extract_sent_id({}) is None


# --- Ambiguous send -------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_transport_failure_is_indeterminate_not_failed() -> None:
    """The request may have reached WhatsApp; the outcome is unknown, not a clean failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    adapter = _adapter(handler)
    with pytest.raises(WahaSendIndeterminate) as excinfo:
        await adapter.send(_text())
    assert "reconcile" in str(excinfo.value).lower()


@pytest.mark.anyio
async def test_indeterminate_is_not_a_plain_transport_error() -> None:
    """It must not be swept up by generic transport-retry handling."""
    from app.channels.errors import ChannelTransportError

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    adapter = _adapter(handler)
    with pytest.raises(WahaSendIndeterminate) as excinfo:
        await adapter.send(_text())
    assert not isinstance(excinfo.value, ChannelTransportError)


@pytest.mark.anyio
async def test_reconcile_known_present() -> None:
    """Message found → it was delivered; a resend would duplicate it to a real person."""
    body = [{"id": f"true_918376035760@c.us_{CANONICAL}", "fromMe": True}]
    adapter = _adapter(lambda r: httpx.Response(200, json=body))
    assert await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL) is True


@pytest.mark.anyio
async def test_reconcile_known_absent() -> None:
    body = [{"id": "true_918376035760@c.us_SOMETHINGELSE", "fromMe": True}]
    adapter = _adapter(lambda r: httpx.Response(200, json=body))
    assert await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL) is False


@pytest.mark.anyio
async def test_reconcile_matches_across_addressing_forms() -> None:
    """Certification: the same message appears as @c.us and @lid; only the trailing id is stable."""
    body = [{"id": f"true_651430587620@lid_{CANONICAL}", "fromMe": True}]
    adapter = _adapter(lambda r: httpx.Response(200, json=body))
    assert await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL) is True


@pytest.mark.anyio
async def test_reconcile_failure_does_not_downgrade_to_absent() -> None:
    """If the lookup itself fails, the outcome stays indeterminate — never 'safe to resend'."""
    adapter = _adapter(lambda r: httpx.Response(500, json={"message": "boom"}))
    with pytest.raises(ChannelApiError):
        await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL)


@pytest.mark.anyio
async def test_reconcile_is_endpoint_scoped() -> None:
    """The lookup runs inside the configured session only — no global provider-message search."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=[])

    adapter = _adapter(handler, OTHER_ENDPOINT)
    await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL)
    assert seen[0].startswith("/api/otherorg/chats/")
    assert "phonecert" not in seen[0]


@pytest.mark.anyio
async def test_no_automatic_resend_exists() -> None:
    """There must be no code path that retries a send on its own."""
    for name in ("resend", "retry_send", "send_with_retry", "auto_resend"):
        assert not hasattr(WahaChannelAdapter, name)
        assert not hasattr(WahaClient, name)


# --- Acknowledgement mapping ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (WahaAck.ERROR, MSG_FAILED),
        (WahaAck.PENDING, MSG_ACCEPTED),
        (WahaAck.SERVER, MSG_SENT),
        (WahaAck.DEVICE, MSG_DELIVERED),
        (WahaAck.READ, MSG_READ),
    ],
)
def test_ack_mapping(code: int, expected: str) -> None:
    assert map_ack(int(code)) == expected


@pytest.mark.parametrize("raw", [99, -7, None, "3", True, 1.5, {"ack": 3}])
def test_unknown_ack_fails_closed(raw: object) -> None:
    """An uncertified code makes no state change rather than inventing or regressing one."""
    assert map_ack(raw) is None


def test_unknown_ack_raises_rather_than_silently_applying() -> None:
    with pytest.raises(ChannelApiError):
        to_status_update(_ack(99))


def test_ack_without_message_id_rejected() -> None:
    delivery = _ack(3)
    delivery["payload"]["id"] = None
    with pytest.raises(ChannelApiError):
        to_status_update(delivery)


def test_ack_correlates_on_trailing_id_across_lid() -> None:
    """The ack arrives @lid while the send response was @c.us — only the tail correlates."""
    update = to_status_update(_ack(3))
    assert update.channel_message_id == CANONICAL
    assert update.status == MSG_READ


def test_adapter_status_update_is_capability_gated() -> None:
    class _NoStream(WahaChannelAdapter):
        capabilities = frozenset({Capability.HEALTH})

    with pytest.raises(ChannelNotSupported):
        _NoStream(CREDS).to_status_update(_ack(3))


# --- Monotonicity ------------------------------------------------------------------------------------


def test_certified_out_of_order_chain_stays_monotonic() -> None:
    """Certification observed DEVICE(2) → SERVER(1) → READ(3).

    Mapped onto the existing ranks that is delivered → sent → read. The late ``sent`` must be
    ignored; last-write-wins would have regressed a delivered message.
    """
    current = MSG_ACCEPTED
    applied = []
    for code in (WahaAck.DEVICE, WahaAck.SERVER, WahaAck.READ):
        incoming = map_ack(int(code))
        assert incoming is not None
        if advances(current, incoming):
            current = incoming
            applied.append(incoming)
    assert applied == [MSG_DELIVERED, MSG_READ]
    assert current == MSG_READ


def test_ack_ranks_are_ordered_like_the_platform() -> None:
    """The mapping must respect the platform's own ordering, not impose a second one."""
    ranks = [
        STATUS_RANK[map_ack(int(code))]  # type: ignore[index]
        for code in (WahaAck.PENDING, WahaAck.SERVER, WahaAck.DEVICE, WahaAck.READ)
    ]
    assert ranks == sorted(ranks)


def test_duplicate_ack_is_idempotent() -> None:
    """QR-04 delivery is at-least-once, so the same ack will arrive more than once."""
    current = MSG_DELIVERED
    for _ in range(5):
        incoming = map_ack(int(WahaAck.DEVICE))
        assert incoming is not None
        assert advances(current, incoming) is False
    assert current == MSG_DELIVERED


def test_regressive_ack_never_moves_state_back() -> None:
    for code in (WahaAck.PENDING, WahaAck.SERVER, WahaAck.DEVICE):
        incoming = map_ack(int(code))
        assert incoming is not None
        assert advances(MSG_READ, incoming) is False


def test_concurrent_ack_updates_converge() -> None:
    """Interleaved acks in any order converge on the highest state reached."""
    import itertools

    codes = [WahaAck.DEVICE, WahaAck.SERVER, WahaAck.READ, WahaAck.DEVICE]
    for order in itertools.permutations(codes):
        current = MSG_ACCEPTED
        for code in order:
            incoming = map_ack(int(code))
            assert incoming is not None
            if advances(current, incoming):
                current = incoming
        assert current == MSG_READ


def test_failed_is_terminal_and_not_overwritten() -> None:
    from app.models.message import TERMINAL_STATUSES

    assert MSG_FAILED in TERMINAL_STATUSES
    for code in (WahaAck.READ, WahaAck.DEVICE):
        incoming = map_ack(int(code))
        assert incoming is not None
        assert advances(MSG_FAILED, incoming) is False


# --- Tenancy / isolation ------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_send_uses_only_the_configured_endpoint() -> None:
    seen: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.content)
        return httpx.Response(201, json=SEND_BODY)

    adapter = _adapter(handler, OTHER_ENDPOINT)
    await adapter.send(_text())
    assert b"otherorg" in seen[0]
    assert b"phonecert" not in seen[0]


@pytest.mark.anyio
async def test_wrong_endpoint_cannot_confirm_another_sessions_message() -> None:
    """A different endpoint's chat does not contain the message, so it cannot advance it."""
    adapter = _adapter(lambda r: httpx.Response(200, json=[]), OTHER_ENDPOINT)
    assert await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL) is False


@pytest.mark.anyio
async def test_reconcile_rejects_invalid_session_before_request() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=[])

    creds = WahaCredentials(base_url="http://x", api_key="k", session="../admin")
    adapter = _adapter(handler, creds)
    with pytest.raises(ChannelConfigError):
        await adapter.reconcile_send(to="918376035760@c.us", canonical_id=CANONICAL)
    assert seen == []


# --- Security / secrets ---------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_send_error_never_leaks_api_key() -> None:
    adapter = _adapter(lambda r: httpx.Response(401, json={"message": "Unauthorized"}))
    with pytest.raises(Exception) as excinfo:
        await adapter.send(_text())
    assert "test-key-never-logged" not in str(excinfo.value)


def test_credentials_repr_hides_key_but_shows_scope() -> None:
    rendered = repr(CREDS)
    assert "test-key-never-logged" not in rendered
    assert "phonecert" in rendered


def test_session_name_default_is_empty() -> None:
    from app.core.config import settings

    assert type(settings).model_fields["waha_session_name"].default == ""


# --- Capability boundary --------------------------------------------------------------------------------


def test_text_declared() -> None:
    assert Capability.TEXT in WahaChannelAdapter.capabilities


def test_qr05_declares_no_later_capability() -> None:
    withheld = {
        Capability.MEDIA,
        Capability.MEDIA_UPLOAD,
        Capability.MEDIA_DOWNLOAD,
        Capability.INTERACTIVE,
        Capability.REACTION,
        Capability.LOCATION,
        Capability.CONTACT,
        Capability.HISTORY_SYNC,
    }
    assert not (WahaChannelAdapter.capabilities & withheld)


def test_prohibited_capabilities_remain_absent() -> None:
    assert not (WahaChannelAdapter.capabilities & PROHIBITED_CAPABILITIES)
    assert frozenset(
        {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
    ) == PROHIBITED_CAPABILITIES


@pytest.mark.anyio
async def test_template_send_still_refused() -> None:
    """QR must never become a route around campaign/template controls."""
    from app.channels.models import TemplateContent

    adapter = _adapter(lambda r: httpx.Response(201, json=SEND_BODY))
    message = OutboundMessage(
        to="918376035760@c.us",
        type=MessageType.TEMPLATE,
        content=TemplateContent(name="promo", language="en"),
    )
    with pytest.raises(ChannelNotSupported):
        await adapter.send(message)


def test_qr05_adds_no_teardown_or_history_surface() -> None:
    for name in ("delete_session", "destroy_session", "sync_history"):
        assert not hasattr(WahaChannelAdapter, name)
        assert not hasattr(WahaClient, name)
