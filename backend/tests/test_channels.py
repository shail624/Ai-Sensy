"""Channel abstraction tests (Doc 07 §5) — M4 Step 1.

Exercises the seam itself: capability gating, the registry, and the canonical→Graph translation.
No network: every Meta call is served by an ``httpx.MockTransport`` (Doc 10 §8).
"""

from __future__ import annotations

import httpx
import pytest

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter + error map
from app.channels.base import (
    ChannelAdapter,
    available_adapters,
    get_adapter,
    register_adapter,
)
from app.channels.capabilities import CONNECTOR_META_CLOUD, Capability, ChannelType
from app.channels.errors import (
    ChannelAuthError,
    ChannelConfigError,
    ChannelError,
    ChannelNotSupported,
    ChannelTransportError,
)
from app.channels.meta.adapter import MetaChannelAdapter
from app.channels.meta.client import MetaCloudClient, MetaCredentials
from app.channels.meta.errors import MetaApiError, classify_meta
from app.channels.models import (
    MediaKind,
    MessageType,
    OutboundMessage,
    SendResult,
    TextContent,
)
from app.queue.retry import FailureClass, classify

TOKEN = "test-system-user-token"
NUMBER = "10555000111"
WAMID = "wamid.HBgLMTQxNTU1NTAwMDEVAgARGBI5"


def _credentials(**overrides) -> MetaCredentials:
    values = {
        "access_token": TOKEN,
        "phone_number_id": NUMBER,
        "waba_id": "waba-1",
        "api_version": "v21.0",
        "base_url": "https://graph.test",
    }
    values.update(overrides)
    return MetaCredentials(**values)


def _adapter(handler, **overrides) -> MetaChannelAdapter:
    """A Meta adapter whose transport is a mock — never touches the network."""
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return MetaChannelAdapter(client=MetaCloudClient(_credentials(**overrides), http=http))


def _json(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def _error(code: int | None, status: int = 400, **extra) -> httpx.Response:
    error = {"message": "boom", "type": "OAuthException", "fbtrace_id": "trace-1"}
    if code is not None:
        error["code"] = code
    error.update(extra)
    return httpx.Response(status, json={"error": error})


# --- Registry (Doc 07 §5.4) --------------------------------------------------
def test_meta_adapter_registers_itself_on_import() -> None:
    assert CONNECTOR_META_CLOUD in available_adapters()
    adapter = get_adapter(CONNECTOR_META_CLOUD, credentials=_credentials())
    assert isinstance(adapter, MetaChannelAdapter)
    assert adapter.channel_type is ChannelType.WHATSAPP


def test_unregistered_connector_fails_loudly() -> None:
    with pytest.raises(ChannelError, match="not registered"):
        get_adapter("carrier-pigeon")


def test_registry_resolves_by_connector_type() -> None:
    class Fake(ChannelAdapter):
        channel_type = ChannelType.WHATSAPP
        connector_type = "fake"

        async def authenticate(self): ...
        async def status(self): ...
        async def _dispatch(self, message): ...

    register_adapter("fake", lambda **kw: Fake())
    assert isinstance(get_adapter("fake"), Fake)


# --- Capability gating (Doc 07 §5.2) ----------------------------------------
def test_meta_declares_the_capabilities_doc7_assigns_it() -> None:
    adapter = _adapter(lambda request: _json({}))
    for capability in (
        Capability.TEXT,
        Capability.MEDIA,
        Capability.INTERACTIVE,
        Capability.TEMPLATE,
        Capability.BULK,
        Capability.CAMPAIGNS,
    ):
        assert adapter.supports(capability)
    # Not in Meta's column — the CRM must not offer them.
    for capability in (Capability.LOCATION, Capability.CONTACT, Capability.REACTION, Capability.CALLS):
        assert not adapter.supports(capability)


async def test_undeclared_capability_raises_not_supported() -> None:
    """The gate is on the base class, so an adapter cannot forget it."""

    class Minimal(ChannelAdapter):
        channel_type = ChannelType.WHATSAPP
        connector_type = "minimal"
        capabilities = frozenset({Capability.TEXT})

        async def authenticate(self): ...
        async def status(self): ...
        async def _dispatch(self, message) -> SendResult:
            return SendResult(to=message.to, channel_message_id="x")

    adapter = Minimal()
    assert (await adapter.send_text("1", "hi")).channel_message_id == "x"
    with pytest.raises(ChannelNotSupported, match="template"):
        await adapter.send_template("1", "welcome", "en_US")
    with pytest.raises(ChannelNotSupported):
        await adapter.upload_attachment(b"x", mime_type="image/png")
    with pytest.raises(ChannelNotSupported):
        await adapter.health_signal()


# --- Canonical → Graph translation ------------------------------------------
async def test_send_text_builds_the_graph_envelope_and_returns_wamid() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = httpx.Response(200, content=request.content).json()
        return _json({"messages": [{"id": WAMID}], "contacts": [{"wa_id": "14155550001"}]})

    result = await _adapter(handler).send_text("14155550001", "Hello", preview_url=True)

    assert seen["url"] == f"https://graph.test/v21.0/{NUMBER}/messages"
    assert seen["auth"] == f"Bearer {TOKEN}"
    assert seen["body"] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "14155550001",
        "type": "text",
        "text": {"body": "Hello", "preview_url": True},
    }
    assert result.to == "14155550001"
    assert result.channel_message_id == WAMID and result.accepted is True
    # The provider's reply is preserved verbatim for the caller that will persist it.
    assert result.raw["contacts"] == [{"wa_id": "14155550001"}]


async def test_send_template_and_interactive_payloads() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(httpx.Response(200, content=request.content).json())
        return _json({"messages": [{"id": WAMID}]})

    adapter = _adapter(handler)
    await adapter.send_template("14155550001", "welcome", "en_US", body=["Priya"])
    await adapter.send_interactive("14155550001", {"type": "button", "body": {"text": "hi"}})

    assert bodies[0]["type"] == "template"
    # The caller passed a value; Graph's parameter shape was built here, behind the seam.
    assert bodies[0]["template"] == {
        "name": "welcome",
        "language": {"code": "en_US"},
        "components": [{"type": "body", "parameters": [{"type": "text", "text": "Priya"}]}],
    }
    assert bodies[1]["type"] == "interactive"
    assert bodies[1]["interactive"] == {"type": "button", "body": {"text": "hi"}}


async def test_send_media_by_id_and_by_link() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(httpx.Response(200, content=request.content).json())
        return _json({"messages": [{"id": WAMID}]})

    adapter = _adapter(handler)
    await adapter.send_media("1", MediaKind.IMAGE, media_id="m1", caption="hi")
    await adapter.send_media("1", MediaKind.DOCUMENT, link="https://x/y.pdf", filename="y.pdf")

    assert bodies[0]["type"] == "image" and bodies[0]["image"] == {"id": "m1", "caption": "hi"}
    assert bodies[1]["document"] == {"link": "https://x/y.pdf", "filename": "y.pdf"}


async def test_send_media_requires_exactly_one_source() -> None:
    adapter = _adapter(lambda request: _json({}))
    for kwargs in ({}, {"media_id": "m1", "link": "https://x/y.png"}):
        with pytest.raises(ChannelConfigError, match="exactly one"):
            await adapter.send_media("1", MediaKind.IMAGE, **kwargs)


async def test_send_result_is_not_accepted_when_meta_returns_no_wamid() -> None:
    result = await _adapter(lambda request: _json({"messages": []})).send_text("1", "hi")
    assert result.accepted is False and result.channel_message_id is None


# --- Auth / config -----------------------------------------------------------
async def test_authenticate_reads_the_number_without_sending() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.params["fields"] == "display_phone_number,verified_name"
        return _json({"display_phone_number": "+1 555 000 111", "verified_name": "Vi Team"})

    status = await _adapter(handler).authenticate()
    assert status.connected and status.identity == "+1 555 000 111"
    assert status.detail == "Vi Team"


async def test_missing_token_and_number_are_config_errors_not_network_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("no request may be made without credentials")

    with pytest.raises(ChannelConfigError, match="META_ACCESS_TOKEN"):
        await _adapter(handler, access_token="").send_text("1", "hi")
    with pytest.raises(ChannelConfigError, match="META_PHONE_NUMBER_ID"):
        await _adapter(handler, phone_number_id="").send_text("1", "hi")


async def test_token_never_appears_in_the_url() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return _json({"messages": [{"id": WAMID}]})

    await _adapter(handler).send_text("1", "hi")
    assert TOKEN not in seen["url"]


# --- Media transfer ----------------------------------------------------------
async def test_upload_attachment_returns_media_id_and_hash() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(f"/{NUMBER}/media")
        assert b"whatsapp" in request.content
        return _json({"id": "media-123"})

    attachment = await _adapter(handler).upload_attachment(
        b"bytes", mime_type="image/png", filename="a.png"
    )
    assert attachment.media_id == "media-123"
    assert attachment.byte_size == 5 and attachment.filename == "a.png"
    assert len(attachment.sha256) == 64


async def test_download_attachment_resolves_url_then_fetches_bytes() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path.endswith("/media-123"):
            return _json({"url": "https://lookaside.test/asset", "mime_type": "image/png"})
        assert request.headers.get("authorization") == f"Bearer {TOKEN}"
        return httpx.Response(200, content=b"PNGDATA")

    result = await _adapter(handler).download_attachment("media-123")
    assert result.content == b"PNGDATA" and result.mime_type == "image/png"
    assert result.byte_size == 7 and len(calls) == 2


async def test_download_without_url_is_a_config_error() -> None:
    with pytest.raises(ChannelConfigError, match="no download url"):
        await _adapter(lambda request: _json({})).download_attachment("media-123")


# --- Health ------------------------------------------------------------------
async def test_health_signal_maps_quality_to_healthy() -> None:
    def green(request: httpx.Request) -> httpx.Response:
        return _json({"quality_rating": "GREEN", "throughput": {"level": "STANDARD"}})

    signal = await _adapter(green).health_signal()
    assert signal.healthy and signal.quality_rating == "GREEN"
    assert signal.throughput_limit == "STANDARD"

    red = await _adapter(lambda r: _json({"quality_rating": "RED"})).health_signal()
    assert red.healthy is False


# --- Error mapping (Doc 06 §6.2/§6.6) ---------------------------------------
async def test_graph_error_envelope_becomes_a_meta_api_error() -> None:
    with pytest.raises(MetaApiError) as excinfo:
        await _adapter(lambda r: _error(131026, status=400)).send_text("1", "hi")
    error = excinfo.value
    assert error.code == 131026 and error.http_status == 400
    assert error.fbtrace_id == "trace-1"


async def test_401_becomes_channel_auth_error() -> None:
    with pytest.raises(ChannelAuthError):
        await _adapter(lambda r: _error(190, status=401)).send_text("1", "hi")


async def test_timeout_becomes_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("too slow")

    with pytest.raises(ChannelTransportError, match="timed out"):
        await _adapter(handler).send_text("1", "hi")


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        (4, 400, FailureClass.THROTTLE),  # application request limit
        (130429, 400, FailureClass.THROTTLE),  # throughput limit
        (131048, 400, FailureClass.THROTTLE),  # spam rate limit
        (1, 400, FailureClass.TRANSIENT),  # unknown API error
        (131053, 400, FailureClass.TRANSIENT_MEDIA),  # media error
        (131026, 400, FailureClass.TERMINAL_DATA),  # not a WhatsApp user
        (131047, 400, FailureClass.TERMINAL_POLICY),  # 24h window closed
        (132015, 400, FailureClass.TERMINAL_CONFIG),  # template paused
        (None, 429, FailureClass.THROTTLE),  # unmapped code → HTTP shape
        (None, 503, FailureClass.TRANSIENT),
        (None, 400, FailureClass.TERMINAL),
        (999999, 400, FailureClass.TERMINAL),  # unknown code, 4xx shape
    ],
)
def test_meta_codes_map_to_the_doc6_failure_classes(code, status, expected) -> None:
    error = MetaApiError("boom", code=code, http_status=status)
    assert classify_meta(error) == expected


def test_error_map_is_registered_with_the_retry_engine() -> None:
    """The engine must classify a Meta error without knowing Meta exists (Doc 06 §6.6)."""
    assert classify(MetaApiError("boom", code=130429, http_status=400)) == FailureClass.THROTTLE
    assert classify(ChannelTransportError("reset")) == FailureClass.TRANSIENT


def test_classifier_declines_unrelated_exceptions() -> None:
    assert classify_meta(ValueError("not mine")) is None


def test_unclassifiable_meta_error_is_unknown_not_retried() -> None:
    """No code and no usable status → poison; the engine parks it (Doc 06 §7.2)."""
    assert classify_meta(MetaApiError("boom")) == FailureClass.UNKNOWN


# --- Transport hygiene -------------------------------------------------------
async def test_client_url_builds_from_version_and_base() -> None:
    client = MetaCloudClient(_credentials(), http=httpx.AsyncClient())
    assert client.url("123/messages") == "https://graph.test/v21.0/123/messages"
    assert client.url("/123") == "https://graph.test/v21.0/123"
    await client.close()


async def test_close_is_safe_and_leaves_injected_clients_alone() -> None:
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: _json({})))
    adapter = MetaChannelAdapter(client=MetaCloudClient(_credentials(), http=http))
    await adapter.close()
    await adapter.close()
    # An injected transport belongs to the caller (the test), so it stays usable.
    assert not http.is_closed
    await http.aclose()


def test_outbound_message_is_immutable() -> None:
    message = OutboundMessage(to="1", type=MessageType.TEXT, content=TextContent("hi"))
    with pytest.raises((AttributeError, TypeError)):
        message.to = "2"  # type: ignore[misc]
