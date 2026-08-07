"""QR-03 — WAHA QR pairing.

Fully hermetic: every HTTP interaction uses ``httpx.MockTransport``, so this suite never opens a
socket and never needs a WAHA server.

The payloads and behaviours asserted here were captured during physical-phone certification against
``devlikeapro/waha@sha256:33ecd1b7…`` (2026.7.2 / NOWEB / CORE) — including the real
``SCAN_QR_CODE → STARTING → WORKING`` pairing path, the 292x292 PNG the QR endpoint returns, the
``422`` it answers once a session is no longer awaiting a scan, and the silent ``full_sync``
spelling trap that leaves history disabled.

As with earlier milestones this suite guards the boundary as much as the feature: QR-03 may bring a
session **up**, and must still be unable to stop, restart or log one out.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.capabilities import Capability
from app.channels.errors import (
    ChannelApiError,
    ChannelConfigError,
    ChannelNotSupported,
    ChannelTransportError,
)
from app.channels.runtime import PairingState
from app.channels.waha import (
    CERTIFIED_NOWEB_STORE,
    PROHIBITED_CAPABILITIES,
    WahaChannelAdapter,
    WahaCredentials,
    WahaEngineNotApproved,
    WahaQrChallenge,
    WahaSessionStatus,
    build_session_config,
)
from app.channels.waha.client import WahaClient

CREDS = WahaCredentials(base_url="http://waha.internal:3000", api_key="test-key-never-logged")

# Captured verbatim from the certified build.
CREATED_BODY = {
    "name": "phonecert",
    "status": "STARTING",
    "config": {"noweb": {"markOnline": True, "store": {"enabled": True, "fullSync": True}}},
    "me": None,
    "engine": {"engine": "NOWEB"},
}
SCAN_BODY = {
    "name": "phonecert",
    "status": "SCAN_QR_CODE",
    "me": None,
    "engine": {"engine": "NOWEB"},
}
WORKING_BODY = {
    "name": "phonecert",
    "status": "WORKING",
    "me": {"id": "919355585553@c.us", "pushName": "Neha Sharma", "lid": "210912345485@lid"},
    "engine": {"engine": "NOWEB"},
}
# The certified build answers 422 once the session is no longer awaiting a scan.
QR_NOT_READY_BODY = {
    "error": "Session status is not as expected. Try again later or restart the session",
    "session": "phonecert",
    "status": "FAILED",
    "expected": ["SCAN_QR_CODE"],
}
PNG_BYTES = bytes.fromhex("89504e470d0a1a0a") + b"certified-qr-payload"


def _adapter(handler) -> WahaChannelAdapter:
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(
        CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport))
    )


def _png(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=PNG_BYTES, headers={"Content-Type": "image/png"})


# --- Certified session configuration ------------------------------------------------------------


def test_store_config_uses_camelcase_full_sync() -> None:
    """Certification proved ``full_sync`` is accepted and then silently ignored.

    A session created with the snake_case spelling returns HTTP 201, reports healthy, and quietly
    has no history. The camelCase spelling is the only one the provider honours.
    """
    store = build_session_config()["noweb"]["store"]
    assert store == {"enabled": True, "fullSync": True}
    assert "full_sync" not in store


def test_store_config_is_copied_not_shared() -> None:
    """A caller mutating the result must not corrupt every later pairing attempt."""
    first = build_session_config()
    first["noweb"]["store"]["enabled"] = False
    assert build_session_config()["noweb"]["store"]["enabled"] is True
    assert CERTIFIED_NOWEB_STORE["noweb"]["store"]["enabled"] is True


# --- QR challenge is a secret ---------------------------------------------------------------------


def test_qr_challenge_never_renders_its_payload() -> None:
    """A QR is a live linking credential: whoever scans it pairs a device to the account."""
    challenge = WahaQrChallenge(session="phonecert", mimetype="image/png", data=PNG_BYTES)
    for rendered in (repr(challenge), str(challenge), f"{challenge}"):
        assert "certified-qr-payload" not in rendered
        assert "***withheld***" in rendered
    assert challenge.size_bytes == len(PNG_BYTES)


def test_qr_challenge_rejects_empty_payload() -> None:
    with pytest.raises(ChannelConfigError):
        WahaQrChallenge(session="phonecert", mimetype="image/png", data=b"")


def test_qr_challenge_is_not_persistable_by_accident() -> None:
    """The dataclass excludes the bytes from its generated repr, so logging it cannot leak them."""
    challenge = WahaQrChallenge(session="phonecert", mimetype="image/png", data=PNG_BYTES)
    assert challenge.data == PNG_BYTES  # still reachable deliberately
    assert "data=***withheld***" in repr(challenge)


# --- Pairing: create ------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_begin_pairing_posts_certified_config() -> None:
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(201, json=CREATED_BODY)

    adapter = _adapter(handler)
    snapshot = await adapter.begin_pairing("phonecert")

    method, path, content = seen[0]
    assert (method, path) == ("POST", "/api/sessions")
    assert b'"fullSync": true' in content or b'"fullSync":true' in content
    assert b"full_sync" not in content
    assert b'"start": true' in content or b'"start":true' in content
    assert snapshot.status is WahaSessionStatus.STARTING


@pytest.mark.anyio
async def test_begin_pairing_does_not_claim_pairing_from_starting() -> None:
    """Pairing safety: STARTING is ambiguous and must not overwrite durable pairing truth.

    Certification observed STARTING both for a fresh session heading toward a QR and for an
    already-paired session restarting toward WORKING.
    """
    adapter = _adapter(lambda r: httpx.Response(201, json=CREATED_BODY))
    snapshot = await adapter.begin_pairing("phonecert")
    assert snapshot.pairing_state is None
    assert snapshot.connected is False


@pytest.mark.anyio
async def test_begin_pairing_engine_guard() -> None:
    body = dict(CREATED_BODY, engine={"engine": "GOWS"})
    adapter = _adapter(lambda r: httpx.Response(201, json=body))
    with pytest.raises(WahaEngineNotApproved):
        await adapter.begin_pairing("phonecert")


@pytest.mark.anyio
async def test_begin_pairing_surfaces_conflict_rather_than_guessing() -> None:
    """An existing session is not silently reused or recreated — QR-03 owns no teardown."""
    adapter = _adapter(lambda r: httpx.Response(422, json={"message": "already exists"}))
    with pytest.raises(ChannelApiError):
        await adapter.begin_pairing("phonecert")


@pytest.mark.anyio
async def test_begin_pairing_validates_session_name() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(201, json=CREATED_BODY)

    adapter = _adapter(handler)
    with pytest.raises(ChannelConfigError):
        await adapter.begin_pairing("../evil")
    assert seen == []


# --- Pairing: QR retrieval ------------------------------------------------------------------------


@pytest.mark.anyio
async def test_pairing_challenge_fetches_image() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return _png(request)

    adapter = _adapter(handler)
    challenge = await adapter.pairing_challenge("phonecert")
    assert "/api/phonecert/auth/qr" in seen[0]
    assert challenge.mimetype == "image/png"
    assert challenge.data.startswith(bytes.fromhex("89504e47"))
    assert challenge.session == "phonecert"


@pytest.mark.anyio
async def test_pairing_challenge_surfaces_not_ready() -> None:
    """422 means "no QR right now" — a real state, not something to smooth over."""
    adapter = _adapter(lambda r: httpx.Response(422, json=QR_NOT_READY_BODY))
    with pytest.raises(ChannelApiError):
        await adapter.pairing_challenge("phonecert")


@pytest.mark.anyio
async def test_pairing_challenge_rejects_non_image() -> None:
    """An HTML login page or JSON error must never be handed back as a QR."""
    adapter = _adapter(
        lambda r: httpx.Response(200, content=b"<html>", headers={"Content-Type": "text/html"})
    )
    with pytest.raises(ChannelApiError):
        await adapter.pairing_challenge("phonecert")


@pytest.mark.anyio
async def test_pairing_challenge_validates_session_name() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return _png(request)

    adapter = _adapter(handler)
    with pytest.raises(ChannelConfigError):
        await adapter.pairing_challenge("a/b")
    assert seen == []


@pytest.mark.anyio
async def test_qr_error_does_not_leak_api_key() -> None:
    adapter = _adapter(lambda r: httpx.Response(401, json={"message": "Unauthorized"}))
    with pytest.raises(Exception) as excinfo:
        await adapter.pairing_challenge("phonecert")
    assert "test-key-never-logged" not in str(excinfo.value)


@pytest.mark.anyio
async def test_qr_transport_failure_is_channel_neutral() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    adapter = _adapter(handler)
    with pytest.raises(ChannelTransportError):
        await adapter.pairing_challenge("phonecert")


# --- Pairing state --------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_pairing_state_paired_when_working() -> None:
    adapter = _adapter(lambda r: httpx.Response(200, json=WORKING_BODY))
    assert await adapter.pairing_state("phonecert") is PairingState.PAIRED


@pytest.mark.anyio
async def test_pairing_state_available_when_awaiting_scan() -> None:
    adapter = _adapter(lambda r: httpx.Response(200, json=SCAN_BODY))
    assert await adapter.pairing_state("phonecert") is PairingState.PAIRING_AVAILABLE


@pytest.mark.anyio
async def test_pairing_state_is_none_when_provider_is_ambiguous() -> None:
    """Fail closed: a None result must leave durable pairing truth untouched."""
    adapter = _adapter(lambda r: httpx.Response(200, json=CREATED_BODY))
    assert await adapter.pairing_state("phonecert") is None


# --- Capability gating ----------------------------------------------------------------------------


def test_qr_auth_is_declared() -> None:
    """QR-03 implements pairing, so it may finally advertise it."""
    assert Capability.QR_AUTH in WahaChannelAdapter.capabilities


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["begin_pairing", "pairing_challenge", "pairing_state"])
async def test_pairing_is_capability_gated(method: str) -> None:
    """The gate is real: an adapter without QR_AUTH must refuse to pair, before any I/O."""

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(201, json=CREATED_BODY)

    class _NoQrAuth(WahaChannelAdapter):
        capabilities = frozenset({Capability.HEALTH})

    transport = httpx.MockTransport(handler)
    adapter = _NoQrAuth(CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport)))
    with pytest.raises(ChannelNotSupported):
        await getattr(adapter, method)("phonecert")
    assert seen == []


def test_prohibited_capabilities_still_never_declared() -> None:
    """QR-03 must not become a route around campaign/broadcast/template controls."""
    assert not (WahaChannelAdapter.capabilities & PROHIBITED_CAPABILITIES)
    assert frozenset(
        {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
    ) == PROHIBITED_CAPABILITIES


# --- Milestone boundary ---------------------------------------------------------------------------


def test_qr03_adds_no_teardown() -> None:
    """QR-03 can bring a session up; only QR-06 may take one down."""
    for name in ("delete_session", "destroy_session", "sync_history"):
        assert not hasattr(WahaChannelAdapter, name)
        assert not hasattr(WahaClient, name)


def test_qr03_adds_no_waha_specific_qr04_or_qr05_surface() -> None:
    """No WAHA webhook/ingestion/send/media/history surface exists at QR-03.

    The generic ``ChannelAdapter`` seam (``send_text``, ``parse_webhook``, ``download_attachment``…)
    is inherited by every adapter and is capability-gated, so its *presence* proves nothing; it is
    covered behaviourally below and by the QR-01 suite. What must not exist is a WAHA-specific
    implementation of any of it.
    """
    for name in (
        "handle_webhook",
        "ingest_event",
        "verify_hmac",
        "send_image",
        "sync_history",
        "download_media",
        "get_messages",
        "get_chats",
    ):
        assert not hasattr(WahaChannelAdapter, name), f"{name!r} is a later milestone"
        assert not hasattr(WahaClient, name), f"{name!r} is a later milestone"


@pytest.mark.anyio
async def test_unimplemented_send_types_still_refuse() -> None:
    """Re-pointed by QR-05: text sending is now implemented, media and interactive are not.

    The guard still does its job — the inherited seam must not quietly accept a type no milestone
    has built.
    """
    adapter = _adapter(lambda r: httpx.Response(200, json=WORKING_BODY))
    with pytest.raises(ChannelNotSupported):
        await adapter.send_interactive("919355585553", {"type": "button"})


def test_qr03_declares_no_runtime_or_messaging_capability() -> None:
    """``SESSION_STREAM`` left this list when QR-04 implemented ingestion; runtime/messaging stay."""
    withheld = {
        Capability.HISTORY_SYNC,
        Capability.MEDIA,
    }
    assert not (WahaChannelAdapter.capabilities & withheld)


def test_no_waha_runtime_registered() -> None:
    """QR-06 owns the runtime; declaring QR_AUTH does not install a supervisor."""
    from app.channels.registry import CapabilityRegistry, ProviderRegistry
    from app.channels.runtime_registry import ProviderRuntimeRegistry

    registry = ProviderRuntimeRegistry(ProviderRegistry(CapabilityRegistry()))
    assert registry.available() == ()
    assert registry.get("waha") is None
