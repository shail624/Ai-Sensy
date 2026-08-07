"""QR-01 — WAHA provider adapter foundation.

Fully hermetic: every HTTP interaction uses ``httpx.MockTransport``, so this suite never opens a
socket and never needs a WAHA server. The response shapes asserted here were captured from the real
certified build (``devlikeapro/waha:noweb-2026.7.2``,
digest ``sha256:33ecd1b7…``) during the QR-01 evidence spike, so the mocks are faithful rather than
invented.

The suite's job is as much about what the adapter **must not** do as what it does: no session, no
QR, no pairing, no messaging, no live runtime, and never `BULK`/`CAMPAIGNS`/`TEMPLATE`.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.base import available_adapters, get_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD, CONNECTOR_WAHA, Capability, ChannelType
from app.channels.errors import (
    ChannelApiError,
    ChannelAuthError,
    ChannelConfigError,
    ChannelNotSupported,
    ChannelTransportError,
)
from app.channels.models import MessageType, OutboundMessage, TextContent
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.waha import (
    PROHIBITED_CAPABILITIES,
    WahaChannelAdapter,
    WahaCredentials,
    WahaEngineNotApproved,
    redact_headers,
)
from app.channels.waha.client import API_KEY_HEADER, WahaClient, WahaServerInfo
from app.core.config import settings

CREDS = WahaCredentials(base_url="http://waha.internal:3000", api_key="test-key-never-logged")

# Captured verbatim from the certified build.
VERSION_BODY = {
    "version": "2026.7.2",
    "engine": "NOWEB",
    "tier": "CORE",
    "browser": None,
    "platform": "linux/x64",
    "worker": {"id": None},
}
HEALTH_BODY = {
    "status": "ok",
    "info": {"mediaFiles.space": {"status": "up"}, "sessionsFiles.space": {"status": "up"}},
    "error": {},
    "details": {"mediaFiles.space": {"status": "up"}},
}
UNAUTHORIZED_BODY = {"message": "Unauthorized", "statusCode": 401}


def _adapter(handler) -> WahaChannelAdapter:
    """An adapter wired to a mock transport — no socket is ever opened."""
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport)))


def _json(body: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=body)


# --- Connector identity & metadata --------------------------------------------------------------


def test_connector_identity() -> None:
    assert CONNECTOR_WAHA == "waha"
    assert WahaChannelAdapter.connector_type == "waha"
    assert WahaChannelAdapter.channel_type is ChannelType.WHATSAPP
    # A second implementation of the same channel family, not a second channel (ADR-0020).
    assert WahaChannelAdapter.channel_type.value == "whatsapp"
    assert CONNECTOR_WAHA != CONNECTOR_META_CLOUD


# --- Capabilities: conservative, evidence-led ---------------------------------------------------


def test_declares_only_implemented_capabilities() -> None:
    """The adapter advertises exactly what it implements — no more.

    ``HEALTH`` from QR-01's server probe, ``QR_AUTH`` from QR-03's pairing path. Everything else is
    still withheld; see the parametrized test below.
    """
    assert WahaChannelAdapter.capabilities == frozenset(
        {Capability.HEALTH, Capability.QR_AUTH}
    )


@pytest.mark.parametrize(
    "capability",
    [
        Capability.SESSION_STREAM,
        Capability.SESSION_RECONNECT,
        Capability.SESSION_LOGOUT,
        Capability.HISTORY_SYNC,
        Capability.TEXT,
        Capability.MEDIA,
        Capability.MEDIA_UPLOAD,
        Capability.MEDIA_DOWNLOAD,
        Capability.INTERACTIVE,
        Capability.REACTION,
        Capability.LOCATION,
        Capability.CONTACT,
    ],
)
def test_unimplemented_capabilities_are_not_advertised(capability: Capability) -> None:
    """A provider endpoint existing is not the same as this adapter being able to use it.

    The QR-00 spike proved WAHA supports QR pairing, sessions, media and history — but none of that
    is implemented here, and none is proven with a paired WhatsApp account. Declaring any of it
    would let the CRM offer an action that cannot run.
    """
    assert not WahaChannelAdapter().supports(capability)


# --- Permanently prohibited capabilities --------------------------------------------------------


@pytest.mark.parametrize(
    "capability", [Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE]
)
def test_prohibited_capabilities_are_never_declared(capability: Capability) -> None:
    """ADR-0020 §5 / ADR-0021 / owner Class B approval: forbidden for this provider **forever**.

    Not "not yet" — no future milestone may add these. QR must never become a route around the
    official channel's campaign, broadcast and template controls.
    """
    assert capability in PROHIBITED_CAPABILITIES
    assert capability not in WahaChannelAdapter.capabilities
    assert not WahaChannelAdapter().supports(capability)


def test_prohibited_set_is_exactly_the_three_forbidden_capabilities() -> None:
    assert frozenset(
        {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
    ) == PROHIBITED_CAPABILITIES


def test_prohibited_capabilities_never_intersect_declared_capabilities() -> None:
    """The invariant a future milestone would have to break deliberately to regress."""
    assert not (WahaChannelAdapter.capabilities & PROHIBITED_CAPABILITIES)


async def test_template_send_is_refused_by_the_capability_gate() -> None:
    adapter = WahaChannelAdapter(CREDS)
    with pytest.raises(ChannelNotSupported):
        await adapter.send_template("999", "any_template", "en_US")


async def test_text_send_is_refused_by_the_capability_gate() -> None:
    """The outbound path is QR-05; today the gate stops it before any dispatch."""
    adapter = WahaChannelAdapter(CREDS)
    with pytest.raises(ChannelNotSupported):
        await adapter.send_text("999", "hello")


async def test_dispatch_refuses_even_if_reached_directly() -> None:
    """Defence in depth behind the capability gate."""
    adapter = WahaChannelAdapter(CREDS)
    message = OutboundMessage(to="999", type=MessageType.TEXT, content=TextContent("hi", False))
    with pytest.raises(ChannelNotSupported):
        await adapter._dispatch(message)


# --- Registration ------------------------------------------------------------------------------


def test_adapter_is_statically_registered() -> None:
    assert CONNECTOR_WAHA in available_adapters()
    assert isinstance(get_adapter(CONNECTOR_WAHA), WahaChannelAdapter)


def test_meta_registration_is_unchanged() -> None:
    assert CONNECTOR_META_CLOUD in available_adapters()


def test_registration_opens_no_socket_and_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing/registering/constructing must never touch the network.

    Any attempt to open a connection fails the test outright, so a future change that dialled the
    provider at import time cannot pass silently.
    """
    import socket

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("WAHA registration must not open a network connection")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(settings, "waha_base_url", "")
    monkeypatch.setattr(settings, "waha_api_key", "")

    import importlib

    import app.channels.waha as waha_pkg

    importlib.reload(waha_pkg)
    adapter = get_adapter(CONNECTOR_WAHA)
    assert isinstance(adapter, WahaChannelAdapter)
    assert adapter.configured is False


def test_no_live_waha_runtime_is_registered() -> None:
    """ProviderRuntimeRegistry must not gain a WAHA runtime at QR-01 (no session supervisor)."""
    from app.channels.registry import CapabilityRegistry, ProviderRegistry

    runtimes = ProviderRuntimeRegistry(ProviderRegistry(CapabilityRegistry()))
    assert CONNECTOR_WAHA not in runtimes.available()
    assert runtimes.get(CONNECTOR_WAHA) is None


# --- Disabled / unconfigured by default ---------------------------------------------------------


def test_unconfigured_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "waha_base_url", "")
    monkeypatch.setattr(settings, "waha_api_key", "")
    assert WahaChannelAdapter().configured is False


def test_there_is_no_default_api_key() -> None:
    """An empty key must never silently fall back to a built-in value."""
    fields = type(settings).model_fields
    assert fields["waha_api_key"].default == ""
    assert fields["waha_base_url"].default == ""


async def test_unconfigured_fails_closed_before_any_network_call() -> None:
    adapter = WahaChannelAdapter(WahaCredentials())
    with pytest.raises(ChannelConfigError, match="WAHA base URL is not configured"):
        await adapter.server_info()


async def test_missing_api_key_fails_closed() -> None:
    adapter = WahaChannelAdapter(WahaCredentials(base_url="http://waha.internal:3000"))
    with pytest.raises(ChannelConfigError, match="WAHA API key is not configured"):
        await adapter.server_info()


def test_qr_feature_flags_are_off_by_default() -> None:
    from app.channels.flags import ChannelFeatureFlagSnapshot, OmnichannelFeatureFlag

    snapshot = ChannelFeatureFlagSnapshot(organization_id=1)
    assert not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER)
    assert not snapshot.is_enabled(OmnichannelFeatureFlag.QR_AUTH)


# --- Authenticated server probe -----------------------------------------------------------------


async def test_server_info_returns_version_and_engine() -> None:
    adapter = _adapter(lambda request: _json(VERSION_BODY))
    info = await adapter.server_info()
    assert info.version == "2026.7.2"
    assert info.engine == "NOWEB"
    assert info.tier == "CORE"
    await adapter.close()


async def test_api_key_is_sent_as_header() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return _json(VERSION_BODY)

    adapter = _adapter(handler)
    await adapter.server_info()
    assert seen[API_KEY_HEADER.lower()] == "test-key-never-logged"
    await adapter.close()


async def test_health_signal_reports_server_health() -> None:
    adapter = _adapter(lambda request: _json(HEALTH_BODY))
    signal = await adapter.health_signal()
    assert signal.healthy is True
    await adapter.close()


async def test_unhealthy_server_is_reported_with_component_names_only() -> None:
    body = {**HEALTH_BODY, "status": "error", "error": {"mongodb": {"status": "down"}}}
    adapter = _adapter(lambda request: _json(body))
    signal = await adapter.health_signal()
    assert signal.healthy is False
    assert "mongodb" in (signal.detail or "")
    await adapter.close()


# --- Server health is NOT session health --------------------------------------------------------


async def test_authenticated_server_does_not_report_a_connected_whatsapp_session() -> None:
    """The distinction QR-01 exists to make: a healthy WAHA server with no paired account cannot
    message, so ``connected`` must be False."""
    adapter = _adapter(lambda request: _json(VERSION_BODY))
    status = await adapter.authenticate()
    assert status.connected is False
    assert status.identity is None
    assert "No WhatsApp session" in (status.detail or "")
    await adapter.close()


async def test_status_matches_authenticate_at_qr01() -> None:
    adapter = _adapter(lambda request: _json(VERSION_BODY))
    assert (await adapter.status()).connected is False
    await adapter.close()


async def test_health_signal_detail_states_it_is_server_only() -> None:
    adapter = _adapter(lambda request: _json(HEALTH_BODY))
    signal = await adapter.health_signal()
    assert "server health only, not session health" in (signal.detail or "")
    await adapter.close()


# --- Deterministic error mapping ----------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_failure_maps_to_channel_auth_error(status: int) -> None:
    adapter = _adapter(lambda request: _json(UNAUTHORIZED_BODY, status))
    with pytest.raises(ChannelAuthError):
        await adapter.server_info()
    await adapter.close()


async def test_timeout_maps_to_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = _adapter(handler)
    with pytest.raises(ChannelTransportError, match="timed out"):
        await adapter.server_info()
    await adapter.close()


async def test_unavailable_maps_to_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    adapter = _adapter(handler)
    with pytest.raises(ChannelTransportError, match="unavailable"):
        await adapter.server_info()
    await adapter.close()


async def test_malformed_non_json_body_maps_to_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not json", headers={"content-type": "application/json"})

    adapter = _adapter(handler)
    with pytest.raises(ChannelApiError, match="malformed"):
        await adapter.server_info()
    await adapter.close()


async def test_unexpected_content_type_maps_to_api_error() -> None:
    """Observed on the real build: the root path answers ``text/html``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>login</html>", headers={"content-type": "text/html"})

    adapter = _adapter(handler)
    with pytest.raises(ChannelApiError, match="unexpected content type"):
        await adapter.server_info()
    await adapter.close()


async def test_provider_5xx_maps_to_api_error_with_status() -> None:
    adapter = _adapter(lambda request: _json({"message": "boom"}, 503))
    with pytest.raises(ChannelApiError) as excinfo:
        await adapter.server_info()
    assert excinfo.value.http_status == 503
    await adapter.close()


async def test_non_object_json_maps_to_api_error() -> None:
    adapter = _adapter(lambda request: httpx.Response(200, json=[1, 2, 3]))
    with pytest.raises(ChannelApiError, match="unexpected JSON shape"):
        await adapter.server_info()
    await adapter.close()


async def test_version_response_missing_fields_maps_to_api_error() -> None:
    adapter = _adapter(lambda request: _json({"tier": "CORE"}))
    with pytest.raises(ChannelApiError, match="missing"):
        await adapter.server_info()
    await adapter.close()


# --- Secret handling ----------------------------------------------------------------------------


def test_redact_headers_masks_sensitive_values() -> None:
    redacted = redact_headers(
        {API_KEY_HEADER: "super-secret", "Authorization": "Bearer x", "Accept": "application/json"}
    )
    assert "super-secret" not in str(redacted)
    assert "Bearer x" not in str(redacted)
    assert redacted["Accept"] == "application/json"


def test_credentials_repr_never_shows_the_key() -> None:
    creds = WahaCredentials(base_url="http://waha.internal:3000", api_key="super-secret-key")
    assert "super-secret-key" not in repr(creds)
    assert "http://waha.internal:3000" in repr(creds)


async def test_auth_error_message_never_contains_the_key() -> None:
    adapter = _adapter(lambda request: _json(UNAUTHORIZED_BODY, 401))
    with pytest.raises(ChannelAuthError) as excinfo:
        await adapter.server_info()
    assert "test-key-never-logged" not in str(excinfo.value)
    await adapter.close()


async def test_api_error_does_not_echo_the_provider_body() -> None:
    """An error body is attacker-influencable and may echo request material; it is never quoted."""
    secret_ish = "SENSITIVE-PROVIDER-ECHO"
    adapter = _adapter(lambda request: _json({"message": secret_ish}, 500))
    with pytest.raises(ChannelApiError) as excinfo:
        await adapter.server_info()
    assert secret_ish not in str(excinfo.value)
    await adapter.close()


async def test_error_log_records_status_only(caplog: pytest.LogCaptureFixture) -> None:
    adapter = _adapter(lambda request: _json(UNAUTHORIZED_BODY, 401))
    with caplog.at_level("WARNING"), pytest.raises(ChannelAuthError):
        await adapter.server_info()
    assert "test-key-never-logged" not in caplog.text
    await adapter.close()


# --- Version / engine safety --------------------------------------------------------------------


def test_certified_baseline_defaults() -> None:
    assert settings.waha_certified_version == "2026.7.2"
    assert settings.waha_approved_engine == "NOWEB"


async def test_unapproved_engine_fails_closed() -> None:
    body = {**VERSION_BODY, "engine": "GOWS"}
    adapter = _adapter(lambda request: _json(body))
    with pytest.raises(WahaEngineNotApproved, match="GOWS"):
        await adapter.server_info()
    await adapter.close()


async def test_chrome_engine_also_fails_closed() -> None:
    body = {**VERSION_BODY, "engine": "WEBJS"}
    adapter = _adapter(lambda request: _json(body))
    with pytest.raises(WahaEngineNotApproved):
        await adapter.server_info()
    await adapter.close()


def test_engine_comparison_is_case_insensitive() -> None:
    WahaChannelAdapter._assert_engine_approved(WahaServerInfo(version="2026.7.2", engine="noweb"))


def test_version_drift_is_reported_not_corrected() -> None:
    drift = WahaChannelAdapter.version_drift(WahaServerInfo(version="2026.9.9", engine="NOWEB"))
    assert drift is not None and "2026.9.9" in drift and "2026.7.2" in drift


def test_certified_version_reports_no_drift() -> None:
    assert WahaChannelAdapter.version_drift(WahaServerInfo(version="2026.7.2", engine="NOWEB")) is None


async def test_drift_is_surfaced_in_authenticate_detail() -> None:
    adapter = _adapter(lambda request: _json({**VERSION_BODY, "version": "2026.9.9"}))
    status = await adapter.authenticate()
    assert "version drift" in (status.detail or "")
    await adapter.close()


# --- Scope: no session / QR / pairing / messaging surface ---------------------------------------


def test_adapter_exposes_no_teardown_or_messaging_surface() -> None:
    """The boundary moved with QR-03, but it still exists — and teardown stays out.

    QR-03 legitimately added ``begin_pairing``/``pairing_challenge``/``pairing_state``, so this
    guard no longer forbids bringing a session *up*. It still forbids tearing one **down**
    (QR-06) and messaging/history (QR-05/QR-06), so a paired session cannot be stopped, restarted
    or logged out by anything shipped so far.
    """
    forbidden = {
        "stop_session",
        "restart_session",
        "logout",
        "logout_session",
        "delete_session",
        "pair_phone",
        "sync_history",
    }
    assert not forbidden & set(dir(WahaChannelAdapter))


def test_adapter_declares_no_webhook_ingestion() -> None:
    """Webhook ingestion is QR-04; the inherited defaults must remain unimplemented."""
    adapter = WahaChannelAdapter(CREDS)
    with pytest.raises(ChannelNotSupported):
        adapter.verify_webhook_signature(b"{}", "sig")
    with pytest.raises(ChannelNotSupported):
        adapter.parse_webhook({})


async def test_adapter_cannot_transfer_media() -> None:
    adapter = WahaChannelAdapter(CREDS)
    with pytest.raises(ChannelNotSupported):
        await adapter.upload_attachment(b"x", mime_type="image/png")
    with pytest.raises(ChannelNotSupported):
        await adapter.download_attachment("media-id")
