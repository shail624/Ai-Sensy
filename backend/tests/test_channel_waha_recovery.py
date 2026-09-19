"""QR-06 — WAHA session recovery, health projection and teardown.

Fully hermetic. The lifecycle shapes asserted here were captured during physical-phone certification
against ``devlikeapro/waha@sha256:33ecd1b7…`` (2026.7.2 / NOWEB / CORE): the controlled restart that
returned a paired session to ``WORKING`` without a new QR, and the logout that produced
``SCAN_QR_CODE`` with ``me=null`` and a QR endpoint answering again.

This suite guards the safety rules as much as the feature. QR-06 is the first milestone that can
take a session down, so most of what follows asserts what it must *refuse* to do.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError, ChannelNotSupported
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime import PairingState
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionState
from app.channels.waha import (
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    PROHIBITED_CAPABILITIES,
    ReconnectDecision,
    RuntimeLease,
    StaleRuntimeLease,
    WahaChannelAdapter,
    WahaCredentials,
    WahaSessionSnapshot,
    WahaSessionStatus,
    assert_lease_current,
    backoff_delay,
    plan_reconnect,
    project_health,
    register_waha_runtime,
    waha_runtime_metadata,
)
from app.channels.waha.client import WahaClient
from app.channels.waha.recovery import MAX_BACKOFF_SECONDS

CREDS = WahaCredentials(
    base_url="http://waha.internal:3000", api_key="test-key-never-logged", session="phonecert"
)
LEASE = RuntimeLease(session_public_id="sess-1", runtime_id="worker-a", fencing_token=7)

WORKING_BODY = {
    "name": "phonecert",
    "status": "WORKING",
    "me": {"id": "919355585553@c.us", "lid": "210912345485@lid"},
    "engine": {"engine": "NOWEB"},
}
STOPPED_BODY = {"name": "phonecert", "status": "STOPPED", "me": None, "engine": {"engine": "NOWEB"}}
SCAN_BODY = {"name": "phonecert", "status": "SCAN_QR_CODE", "me": None, "engine": {"engine": "NOWEB"}}
STARTING_BODY = {"name": "phonecert", "status": "STARTING", "me": None, "engine": {"engine": "NOWEB"}}
FAILED_BODY = {"name": "phonecert", "status": "FAILED", "me": None, "engine": {"engine": "NOWEB"}}


def _adapter(handler) -> WahaChannelAdapter:
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(
        CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport))
    )


def _snapshot(body: dict) -> WahaSessionSnapshot:
    return WahaSessionSnapshot.from_payload(body)


# --- Health projection ------------------------------------------------------------------------


def test_working_session_is_healthy() -> None:
    signal = project_health(_snapshot(WORKING_BODY))
    assert signal.healthy is True
    assert "working" in (signal.detail or "").lower()


@pytest.mark.parametrize("body", [STOPPED_BODY, STARTING_BODY, FAILED_BODY])
def test_server_up_but_session_down_is_not_healthy(body: dict) -> None:
    """QR-01 established server health != session health; conflating them hides a dead channel."""
    assert project_health(_snapshot(body)).healthy is False


def test_awaiting_scan_reports_reauth_not_generic_health() -> None:
    """Re-auth outranks provider health: no amount of server uptime resolves a needed scan."""
    signal = project_health(_snapshot(SCAN_BODY))
    assert signal.healthy is False
    assert "re-authentication" in (signal.detail or "").lower()


def test_unreachable_provider_is_unknown_not_healthy() -> None:
    signal = project_health(None)
    assert signal.healthy is False
    assert "unknown" in (signal.detail or "").lower()


@pytest.mark.anyio
async def test_adapter_session_health_maps_transport_failure_to_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    signal = await _adapter(handler).session_health("phonecert")
    assert signal.healthy is False
    assert "unknown" in (signal.detail or "").lower()


@pytest.mark.anyio
async def test_adapter_session_health_working() -> None:
    signal = await _adapter(lambda r: httpx.Response(200, json=WORKING_BODY)).session_health(
        "phonecert"
    )
    assert signal.healthy is True


# --- Reconnect planning: the STARTING ambiguity ---------------------------------------------------


def test_starting_never_triggers_a_reconnect() -> None:
    """QR-02 proved STARTING is ambiguous: fresh → SCAN_QR_CODE, paired restart → WORKING.

    Mutating mid-transition could restart a session that was about to come up on its own.
    """
    assert (
        plan_reconnect(
            provider_status=WahaSessionStatus.STARTING,
            durable_pairing_state=PairingState.PAIRED,
        )
        is ReconnectDecision.WAIT
    )


def test_starting_never_implies_unpaired() -> None:
    """The decisive property: STARTING must not be read as evidence a session lost its pairing."""
    decision = plan_reconnect(
        provider_status=WahaSessionStatus.STARTING,
        durable_pairing_state=PairingState.PAIRED,
    )
    assert decision is not ReconnectDecision.REQUIRES_REAUTH
    assert decision is not ReconnectDecision.RECONNECT


@pytest.mark.parametrize("status", [WahaSessionStatus.STOPPED, WahaSessionStatus.FAILED])
def test_paired_session_may_reconnect(status: WahaSessionStatus) -> None:
    assert (
        plan_reconnect(provider_status=status, durable_pairing_state=PairingState.PAIRED)
        is ReconnectDecision.RECONNECT
    )


@pytest.mark.parametrize(
    "pairing",
    [PairingState.UNPAIRED, PairingState.PAIRING_EXPIRED, PairingState.PAIRING_CANCELLED],
)
def test_unpaired_session_is_never_auto_restarted(pairing: PairingState) -> None:
    """Restarting a session with no credentials cannot restore anything and would raise a QR."""
    assert (
        plan_reconnect(provider_status=WahaSessionStatus.STOPPED, durable_pairing_state=pairing)
        is ReconnectDecision.REQUIRES_REAUTH
    )


def test_awaiting_scan_requires_an_operator_not_a_supervisor() -> None:
    assert (
        plan_reconnect(
            provider_status=WahaSessionStatus.SCAN_QR_CODE,
            durable_pairing_state=PairingState.PAIRED,
        )
        is ReconnectDecision.REQUIRES_REAUTH
    )


def test_indeterminate_durable_state_waits_rather_than_guessing() -> None:
    for pairing in (PairingState.PAIRING_REQUESTED, PairingState.PAIRING_AVAILABLE):
        assert (
            plan_reconnect(
                provider_status=WahaSessionStatus.STOPPED, durable_pairing_state=pairing
            )
            is ReconnectDecision.WAIT
        )


def test_working_session_needs_no_action() -> None:
    assert (
        plan_reconnect(
            provider_status=WahaSessionStatus.WORKING,
            durable_pairing_state=PairingState.PAIRED,
        )
        is ReconnectDecision.CONNECTED
    )


def test_working_session_is_never_reported_exhausted() -> None:
    """A healthy session must not be escalated just because earlier attempts were counted."""
    assert (
        plan_reconnect(
            provider_status=WahaSessionStatus.WORKING,
            durable_pairing_state=PairingState.PAIRED,
            attempts=99,
        )
        is ReconnectDecision.CONNECTED
    )


# --- Provider unavailability ------------------------------------------------------------------------


def test_unreachable_provider_does_not_destroy_durable_truth() -> None:
    """"Unknown" must never be treated as "unpaired" — a brief outage must not unpair a customer."""
    decision = plan_reconnect(
        provider_status=None, durable_pairing_state=PairingState.PAIRED
    )
    assert decision is ReconnectDecision.PROVIDER_UNAVAILABLE
    assert decision is not ReconnectDecision.REQUIRES_REAUTH


@pytest.mark.anyio
async def test_adapter_plan_maps_timeout_to_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    decision = await _adapter(handler).plan_session_recovery(
        "phonecert", durable_pairing_state=PairingState.PAIRED
    )
    assert decision is ReconnectDecision.PROVIDER_UNAVAILABLE


# --- Bounded reconnect ---------------------------------------------------------------------------------


def test_reconnect_is_bounded() -> None:
    assert (
        plan_reconnect(
            provider_status=WahaSessionStatus.STOPPED,
            durable_pairing_state=PairingState.PAIRED,
            attempts=DEFAULT_MAX_RECONNECT_ATTEMPTS,
        )
        is ReconnectDecision.ATTEMPTS_EXHAUSTED
    )


def test_backoff_grows_and_is_capped() -> None:
    """Prevents a reconnect storm against a provider that is already struggling."""
    delays = [backoff_delay(i) for i in range(10)]
    assert delays == sorted(delays)
    assert delays[0] < delays[3]
    assert max(delays) <= MAX_BACKOFF_SECONDS


def test_backoff_is_deterministic_across_workers() -> None:
    """A pure function of the attempt number — no shared coordination required."""
    assert [backoff_delay(i) for i in range(6)] == [backoff_delay(i) for i in range(6)]


def test_backoff_rejects_negative_attempt() -> None:
    with pytest.raises(ChannelConfigError):
        backoff_delay(-1)


# --- Lease / fencing ------------------------------------------------------------------------------------


def test_current_lease_holder_may_act() -> None:
    assert_lease_current(LEASE, current_runtime_id="worker-a", current_fencing_token=7)


def test_stale_fencing_token_is_rejected() -> None:
    """A worker that slept through a takeover must not overwrite the newer owner's state."""
    with pytest.raises(StaleRuntimeLease):
        assert_lease_current(LEASE, current_runtime_id="worker-a", current_fencing_token=8)


def test_lost_lease_holder_is_rejected() -> None:
    with pytest.raises(StaleRuntimeLease):
        assert_lease_current(LEASE, current_runtime_id="worker-b", current_fencing_token=7)


def test_unowned_session_is_rejected() -> None:
    with pytest.raises(StaleRuntimeLease):
        assert_lease_current(LEASE, current_runtime_id=None, current_fencing_token=7)


def test_matching_token_under_a_different_owner_is_still_rejected() -> None:
    """Identity *and* token must match: a re-claimed session can reuse a token number."""
    with pytest.raises(StaleRuntimeLease):
        assert_lease_current(LEASE, current_runtime_id="worker-b", current_fencing_token=7)


def test_lease_requires_positive_fencing_token() -> None:
    for bad in (0, -1):
        with pytest.raises(ChannelConfigError):
            RuntimeLease(session_public_id="s", runtime_id="w", fencing_token=bad)


def test_lease_requires_identifiers() -> None:
    with pytest.raises(ChannelConfigError):
        RuntimeLease(session_public_id="  ", runtime_id="w", fencing_token=1)
    with pytest.raises(ChannelConfigError):
        RuntimeLease(session_public_id="s", runtime_id="  ", fencing_token=1)


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["reconnect_session", "stop_session", "logout_session"])
async def test_lifecycle_mutation_refuses_without_a_lease(method: str) -> None:
    """No caller may skip ownership proof by simply omitting it."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=WORKING_BODY)

    adapter = _adapter(handler)
    with pytest.raises(ChannelConfigError):
        await getattr(adapter, method)("phonecert")
    assert seen == [], "no provider call may happen without proven ownership"


# --- Lifecycle operations -------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_reconnect_starts_and_does_not_create() -> None:
    """Reconnect resumes an existing session; creating one would be an unrequested new pairing."""
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json=WORKING_BODY)

    snapshot = await _adapter(handler).reconnect_session("phonecert", lease=LEASE)
    assert seen == [("POST", "/api/sessions/phonecert/start")]
    assert snapshot.status is WahaSessionStatus.WORKING


@pytest.mark.anyio
async def test_stop_reports_stopped_semantics() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=STOPPED_BODY)

    snapshot = await _adapter(handler).stop_session("phonecert", lease=LEASE)
    assert seen == ["/api/sessions/phonecert/stop"]
    assert snapshot.status is WahaSessionStatus.STOPPED
    assert snapshot.session_state is SessionState.PAUSED
    # STOP is non-destructive to pairing: it must not claim the session became unpaired.
    assert snapshot.pairing_state is None


@pytest.mark.anyio
async def test_logout_produces_reauth_required_truth() -> None:
    """Certification: WORKING → SCAN_QR_CODE with me=null. That is the intended outcome."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=SCAN_BODY)

    snapshot = await _adapter(handler).logout_session("phonecert", lease=LEASE)
    assert seen == ["/api/sessions/phonecert/logout"]
    assert snapshot.status is WahaSessionStatus.SCAN_QR_CODE
    assert snapshot.identity is None
    assert snapshot.session_state is SessionState.WAITING_FOR_PAIRING
    assert snapshot.pairing_state is PairingState.PAIRING_AVAILABLE
    assert project_health(snapshot).healthy is False


@pytest.mark.anyio
async def test_stop_and_logout_are_distinct_operations() -> None:
    """Collapsing them would let a routine restart silently unpair a customer's account."""
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json=STOPPED_BODY)

    adapter = _adapter(handler)
    await adapter.stop_session("phonecert", lease=LEASE)
    await adapter.logout_session("phonecert", lease=LEASE)
    assert paths == ["/api/sessions/phonecert/stop", "/api/sessions/phonecert/logout"]


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["reconnect_session", "stop_session", "logout_session"])
async def test_lifecycle_operations_are_idempotent(method: str) -> None:
    """Repeating an operation converges on the same reported state rather than erroring."""
    body = {"reconnect_session": WORKING_BODY, "stop_session": STOPPED_BODY}.get(method, SCAN_BODY)
    adapter = _adapter(lambda r: httpx.Response(200, json=body))
    first = await getattr(adapter, method)("phonecert", lease=LEASE)
    second = await getattr(adapter, method)("phonecert", lease=LEASE)
    assert first.status is second.status


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["reconnect_session", "stop_session", "logout_session"])
async def test_lifecycle_validates_session_name_before_any_request(method: str) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=WORKING_BODY)

    adapter = _adapter(handler)
    with pytest.raises(ChannelConfigError):
        await getattr(adapter, method)("../admin", lease=LEASE)
    assert seen == []


@pytest.mark.anyio
async def test_lifecycle_engine_guard() -> None:
    from app.channels.waha import WahaEngineNotApproved

    body = dict(WORKING_BODY, engine={"engine": "GOWS"})
    adapter = _adapter(lambda r: httpx.Response(200, json=body))
    with pytest.raises(WahaEngineNotApproved):
        await adapter.reconnect_session("phonecert", lease=LEASE)


# --- No auto-pairing -------------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_recovery_never_fetches_a_qr() -> None:
    """A logout deliberately produces re-auth-required truth; nothing may auto-repair it."""
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json=SCAN_BODY)

    adapter = _adapter(handler)
    await adapter.logout_session("phonecert", lease=LEASE)
    await adapter.plan_session_recovery("phonecert", durable_pairing_state=PairingState.PAIRED)
    assert not any("auth/qr" in p for p in paths)
    assert not any(p == "/api/sessions" for p in paths), "no session creation during recovery"


@pytest.mark.anyio
async def test_recovery_never_creates_a_session() -> None:
    methods: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append((request.method, request.url.path))
        return httpx.Response(200, json=WORKING_BODY)

    await _adapter(handler).reconnect_session("phonecert", lease=LEASE)
    assert ("POST", "/api/sessions") not in methods


def test_no_delete_session_surface() -> None:
    """QR-06 needs stop and logout; permanent deletion is neither required nor recoverable."""
    for name in ("delete_session", "destroy_session", "purge_session"):
        assert not hasattr(WahaChannelAdapter, name)
        assert not hasattr(WahaClient, name)


# --- Runtime registry -------------------------------------------------------------------------------------


def test_importing_the_package_registers_no_runtime() -> None:
    """Every milestone through QR-05 guaranteed this; QR-06 keeps registration opt-in."""
    runtimes = ProviderRuntimeRegistry(ProviderRegistry(CapabilityRegistry()))
    assert runtimes.available() == ()
    assert runtimes.get("waha") is None


def test_explicit_registration_installs_the_runtime() -> None:
    providers = ProviderRegistry(CapabilityRegistry())
    runtimes = ProviderRuntimeRegistry(providers)
    register_waha_runtime(providers, runtimes)
    metadata = runtimes.require("waha")
    assert metadata.connector_type == "waha"
    assert metadata.pairing_managed is True
    assert Capability.SESSION_RECONNECT in metadata.capabilities
    assert Capability.SESSION_LOGOUT in metadata.capabilities


def test_runtime_capabilities_never_exceed_the_adapter() -> None:
    """A runtime may not advertise more than the provider actually implements."""
    assert waha_runtime_metadata().capabilities <= WahaChannelAdapter.capabilities


def test_runtime_metadata_declares_no_prohibited_capability() -> None:
    assert not (waha_runtime_metadata().capabilities & PROHIBITED_CAPABILITIES)


def test_registration_is_idempotent() -> None:
    providers = ProviderRegistry(CapabilityRegistry())
    runtimes = ProviderRuntimeRegistry(providers)
    register_waha_runtime(providers, runtimes)
    register_waha_runtime(providers, runtimes)  # identical metadata must not raise
    assert runtimes.available() == ("waha",)


def test_runtime_lease_bounds_are_sane() -> None:
    metadata = waha_runtime_metadata()
    assert metadata.heartbeat_interval_seconds <= metadata.lease_seconds
    assert metadata.pairing_ttl_seconds >= 15


# --- Capability boundary -------------------------------------------------------------------------------------


def test_session_lifecycle_capabilities_declared() -> None:
    assert Capability.SESSION_RECONNECT in WahaChannelAdapter.capabilities
    assert Capability.SESSION_LOGOUT in WahaChannelAdapter.capabilities


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["reconnect_session", "stop_session"])
async def test_reconnect_is_capability_gated(method: str) -> None:
    class _NoReconnect(WahaChannelAdapter):
        capabilities = frozenset({Capability.HEALTH})

    adapter = _NoReconnect(CREDS)
    with pytest.raises(ChannelNotSupported):
        await getattr(adapter, method)("phonecert", lease=LEASE)


@pytest.mark.anyio
async def test_logout_is_capability_gated() -> None:
    class _NoLogout(WahaChannelAdapter):
        capabilities = frozenset({Capability.HEALTH, Capability.SESSION_RECONNECT})

    with pytest.raises(ChannelNotSupported):
        await _NoLogout(CREDS).logout_session("phonecert", lease=LEASE)


def test_qr06_declares_no_later_capability() -> None:
    withheld = {
        Capability.MEDIA,
        Capability.MEDIA_UPLOAD,
        Capability.MEDIA_DOWNLOAD,
        Capability.HISTORY_SYNC,
        Capability.INTERACTIVE,
        Capability.REACTION,
        Capability.LOCATION,
        Capability.CONTACT,
    }
    assert not (WahaChannelAdapter.capabilities & withheld)


def test_prohibited_capabilities_remain_absent() -> None:
    assert not (WahaChannelAdapter.capabilities & PROHIBITED_CAPABILITIES)
    assert frozenset(
        {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
    ) == PROHIBITED_CAPABILITIES


def test_qr06_adds_no_history_or_media_surface() -> None:
    for name in ("sync_history", "get_chats", "get_messages", "download_media"):
        assert not hasattr(WahaChannelAdapter, name)
        assert not hasattr(WahaClient, name)
