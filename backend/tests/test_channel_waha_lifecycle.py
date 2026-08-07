"""QR-02 — WAHA session lifecycle read and provider-neutral mapping.

Fully hermetic: every HTTP interaction uses ``httpx.MockTransport``, so this suite never opens a
socket and never needs a WAHA server.

The payloads asserted here were captured from the certified build
(``devlikeapro/waha@sha256:33ecd1b7…``, 2026.7.2 / NOWEB / CORE) during physical-phone
certification — including the real ``STARTING → SCAN_QR_CODE → WORKING`` pairing path, the
controlled-restart ``STARTING → WORKING`` path that required no new QR, the unscanned-QR ``FAILED``
path, and the post-logout return to ``SCAN_QR_CODE``. They are faithful rather than invented.

As with QR-01, this suite is as much about what QR-02 must **not** do: no session is created,
started, stopped, restarted, paired or logged out, no capability is added, and no runtime is
registered.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.capabilities import Capability
from app.channels.errors import ChannelApiError, ChannelConfigError
from app.channels.models import ChannelStatus
from app.channels.runtime import PairingState
from app.channels.session import SESSION_TERMINAL_STATES, SessionState
from app.channels.waha import (
    WahaChannelAdapter,
    WahaCredentials,
    WahaEngineNotApproved,
    WahaSessionSnapshot,
    WahaSessionStatus,
    map_session_status,
    parse_session_status,
    validate_session_name,
)
from app.channels.waha.client import WahaClient

CREDS = WahaCredentials(base_url="http://waha.internal:3000", api_key="test-key-never-logged")

# Captured verbatim from the certified build.
WORKING_BODY = {
    "name": "phonecert",
    "status": "WORKING",
    "config": {"noweb": {"markOnline": True, "store": {"enabled": True, "fullSync": True}}},
    "me": {
        "id": "919355585553@c.us",
        "pushName": "Neha Sharma",
        "lid": "210912345485@lid",
    },
    "engine": {"engine": "NOWEB"},
}
SCAN_BODY = {
    "name": "phonecert",
    "status": "SCAN_QR_CODE",
    "config": {},
    "me": None,
    "engine": {"engine": "NOWEB"},
}
STARTING_BODY = {"name": "phonecert", "status": "STARTING", "me": None, "engine": {"engine": "NOWEB"}}
FAILED_BODY = {"name": "phonecert", "status": "FAILED", "me": None, "engine": {"engine": "NOWEB"}}
STOPPED_BODY = {"name": "phonecert", "status": "STOPPED", "me": None, "engine": {"engine": "NOWEB"}}


def _adapter(handler) -> WahaChannelAdapter:
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(
        CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport))
    )


def _serving(body: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return handler


# --- Status vocabulary --------------------------------------------------------------------------


def test_certified_statuses_are_exactly_those_observed() -> None:
    """The enum records what certification actually saw — no speculative members."""
    assert {status.value for status in WahaSessionStatus} == {
        "STARTING",
        "SCAN_QR_CODE",
        "WORKING",
        "FAILED",
        "STOPPED",
    }


@pytest.mark.parametrize("raw", ["WORKING", "working", "  Working  "])
def test_parse_session_status_normalises(raw: str) -> None:
    assert parse_session_status(raw) is WahaSessionStatus.WORKING


@pytest.mark.parametrize("raw", ["PAIRING", "", None, 7, {"status": "WORKING"}])
def test_parse_session_status_fails_closed(raw: object) -> None:
    """An uncertified status is a provider contract change, not something to degrade quietly."""
    with pytest.raises(ChannelApiError):
        parse_session_status(raw)


def test_uncertified_status_value_is_not_echoed() -> None:
    """Provider output of unknown provenance must not be interpolated into an error."""
    with pytest.raises(ChannelApiError) as excinfo:
        parse_session_status("<script>alert(1)</script>")
    assert "script" not in str(excinfo.value)


# --- Provider-neutral mapping -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected_session", "expected_pairing"),
    [
        (WahaSessionStatus.STARTING, SessionState.INITIALIZING, None),
        (
            WahaSessionStatus.SCAN_QR_CODE,
            SessionState.WAITING_FOR_PAIRING,
            PairingState.PAIRING_AVAILABLE,
        ),
        (WahaSessionStatus.WORKING, SessionState.ACTIVE, PairingState.PAIRED),
        (WahaSessionStatus.FAILED, SessionState.DEGRADED, None),
        (WahaSessionStatus.STOPPED, SessionState.PAUSED, None),
    ],
)
def test_status_mapping(
    status: WahaSessionStatus,
    expected_session: SessionState,
    expected_pairing: PairingState | None,
) -> None:
    assert map_session_status(status) == (expected_session, expected_pairing)


def test_every_certified_status_is_mapped() -> None:
    """No certified status may be left without a provider-neutral translation."""
    for status in WahaSessionStatus:
        session_state, _ = map_session_status(status)
        assert isinstance(session_state, SessionState)


def test_failed_is_recoverable_not_terminal() -> None:
    """Certification recovered a FAILED session with a controlled restart.

    Mapping it to a terminal state would strand a session the provider can still revive.
    """
    session_state, _ = map_session_status(WahaSessionStatus.FAILED)
    assert session_state not in SESSION_TERMINAL_STATES


def test_ambiguous_statuses_refuse_to_claim_pairing() -> None:
    """STARTING/STOPPED/FAILED do not determine whether credentials exist.

    Certification observed STARTING on both a fresh session (-> SCAN_QR_CODE) and a controlled
    restart of a paired one (-> WORKING with no new QR), so the status alone cannot decide.
    """
    for status in (
        WahaSessionStatus.STARTING,
        WahaSessionStatus.STOPPED,
        WahaSessionStatus.FAILED,
    ):
        assert map_session_status(status)[1] is None


def test_mapping_is_pure_and_order_independent() -> None:
    """Carry-forward: certification proved provider events can arrive out of order.

    The mapping must therefore be a pure function of the status alone — repeated and interleaved
    calls can never make an earlier reading change a later one.
    """
    sequence = [
        WahaSessionStatus.WORKING,
        WahaSessionStatus.STARTING,
        WahaSessionStatus.WORKING,
        WahaSessionStatus.FAILED,
        WahaSessionStatus.WORKING,
    ]
    results = [map_session_status(status) for status in sequence]
    assert results[0] == results[2] == results[4] == (SessionState.ACTIVE, PairingState.PAIRED)


# --- Snapshot parsing ---------------------------------------------------------------------------


def test_snapshot_from_working_payload() -> None:
    snapshot = WahaSessionSnapshot.from_payload(WORKING_BODY)
    assert snapshot.name == "phonecert"
    assert snapshot.status is WahaSessionStatus.WORKING
    assert snapshot.engine == "NOWEB"
    assert snapshot.identity == "919355585553@c.us"
    assert snapshot.lid == "210912345485@lid"
    assert snapshot.push_name == "Neha Sharma"
    assert snapshot.session_state is SessionState.ACTIVE
    assert snapshot.pairing_state is PairingState.PAIRED
    assert snapshot.connected is True


def test_snapshot_carries_both_addressing_forms() -> None:
    """Certification proved one account is addressed as both @c.us and @lid.

    Neither is normalised away, so a later milestone can correlate whichever form a surface uses.
    """
    snapshot = WahaSessionSnapshot.from_payload(WORKING_BODY)
    assert snapshot.identity is not None and snapshot.identity.endswith("@c.us")
    assert snapshot.lid is not None and snapshot.lid.endswith("@lid")


def test_snapshot_unpaired_has_no_identity() -> None:
    snapshot = WahaSessionSnapshot.from_payload(SCAN_BODY)
    assert snapshot.identity is None
    assert snapshot.lid is None
    assert snapshot.connected is False
    assert snapshot.session_state is SessionState.WAITING_FOR_PAIRING
    assert snapshot.pairing_state is PairingState.PAIRING_AVAILABLE


@pytest.mark.parametrize(
    "body", [STARTING_BODY, FAILED_BODY, STOPPED_BODY, SCAN_BODY]
)
def test_only_working_is_connected(body: dict) -> None:
    """A reachable server, a booting session and a QR-showing session are all not connected."""
    assert WahaSessionSnapshot.from_payload(body).connected is False


def test_snapshot_requires_a_name() -> None:
    with pytest.raises(ChannelApiError):
        WahaSessionSnapshot.from_payload({"status": "WORKING"})


def test_snapshot_tolerates_missing_engine() -> None:
    snapshot = WahaSessionSnapshot.from_payload({"name": "s1", "status": "WORKING"})
    assert snapshot.engine is None


def test_snapshot_ignores_non_string_identity() -> None:
    snapshot = WahaSessionSnapshot.from_payload(
        {"name": "s1", "status": "WORKING", "me": {"id": 123, "lid": None}}
    )
    assert snapshot.identity is None
    assert snapshot.lid is None


# --- Session name validation --------------------------------------------------------------------


@pytest.mark.parametrize("name", ["phonecert", "a", "A-1_b", "s" * 64])
def test_valid_session_names(name: str) -> None:
    assert validate_session_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["", "  ", "../admin", "a/b", "a?x=1", "a b", "-lead", "_lead", "s" * 65, "sess#1", "a%2f"],
)
def test_rejected_session_names(name: str) -> None:
    """The name is interpolated into a request path, so it is validated, not escaped."""
    with pytest.raises(ChannelConfigError):
        validate_session_name(name)


@pytest.mark.anyio
async def test_traversal_name_never_reaches_the_network() -> None:
    """A hostile name must fail before a URL is built."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=WORKING_BODY)

    adapter = _adapter(handler)
    with pytest.raises(ChannelConfigError):
        await adapter.session_snapshot("../server/version")
    assert seen == []


# --- Client / adapter read ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_session_status_requests_the_named_session() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=WORKING_BODY)

    adapter = _adapter(handler)
    snapshot = await adapter.session_snapshot("phonecert")
    assert seen == ["/api/sessions/phonecert"]
    assert snapshot.status is WahaSessionStatus.WORKING


@pytest.mark.anyio
async def test_adapter_session_status_is_provider_neutral() -> None:
    adapter = _adapter(_serving(WORKING_BODY))
    status = await adapter.session_status("phonecert")
    assert isinstance(status, ChannelStatus)
    assert status.connected is True
    assert status.identity == "919355585553@c.us"
    assert "session_state=active" in (status.detail or "")
    assert "pairing_state=paired" in (status.detail or "")


@pytest.mark.anyio
async def test_indeterminate_pairing_is_reported_honestly() -> None:
    adapter = _adapter(_serving(STARTING_BODY))
    status = await adapter.session_status("phonecert")
    assert status.connected is False
    assert "pairing_state=indeterminate" in (status.detail or "")


@pytest.mark.anyio
async def test_session_engine_guard_fails_closed() -> None:
    """An adapter certified against NOWEB must not interpret another engine's session payload."""
    body = dict(WORKING_BODY, engine={"engine": "GOWS"})
    adapter = _adapter(_serving(body))
    with pytest.raises(WahaEngineNotApproved):
        await adapter.session_snapshot("phonecert")


@pytest.mark.anyio
async def test_uncertified_session_status_fails_closed_over_http() -> None:
    adapter = _adapter(_serving({"name": "phonecert", "status": "PAIRING"}))
    with pytest.raises(ChannelApiError):
        await adapter.session_snapshot("phonecert")


@pytest.mark.anyio
async def test_api_key_is_sent_but_never_exposed() -> None:
    seen: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(200, json=WORKING_BODY)

    adapter = _adapter(handler)
    snapshot = await adapter.session_snapshot("phonecert")
    assert seen[0]["X-Api-Key"] == "test-key-never-logged"
    assert "test-key-never-logged" not in repr(snapshot)


# --- Milestone boundary -------------------------------------------------------------------------


def test_lifecycle_capabilities_are_earned_not_assumed() -> None:
    """Every lifecycle capability is declared only by the milestone that implemented it.

    QR-03 earned ``QR_AUTH``, QR-04 ``SESSION_STREAM``, QR-06 ``SESSION_RECONNECT``/
    ``SESSION_LOGOUT``. What this suite still guards is that capabilities nothing implements —
    history and media transfer — remain undeclared.
    """
    earned = {
        Capability.QR_AUTH,
        Capability.SESSION_STREAM,
        Capability.SESSION_RECONNECT,
        Capability.SESSION_LOGOUT,
    }
    assert earned <= WahaChannelAdapter.capabilities

    unimplemented = {
        Capability.HISTORY_SYNC,
        Capability.MEDIA,
        Capability.MEDIA_UPLOAD,
        Capability.MEDIA_DOWNLOAD,
    }
    assert not (WahaChannelAdapter.capabilities & unimplemented)


def test_no_session_teardown_surface() -> None:
    """Bringing a session up is QR-03; tearing one down is QR-06 and must not exist yet.

    Updated by QR-03: ``create_session``/QR retrieval are now legitimate. Teardown is not, so a
    working pairing cannot be destroyed by anything shipped so far.
    """
    forbidden = (
        "delete_session",
        "destroy_session",
        "purge_session",
    )
    for name in forbidden:
        assert not hasattr(WahaChannelAdapter, name), f"teardown is QR-06: {name!r}"
        assert not hasattr(WahaClient, name), f"teardown is QR-06: {name!r}"


@pytest.mark.anyio
async def test_generic_status_still_reports_server_only() -> None:
    """The QR-01 guarantee is preserved: a bare status() never claims a WhatsApp session."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"version": "2026.7.2", "engine": "NOWEB", "tier": "CORE", "platform": "linux/x64"},
        )

    adapter = _adapter(handler)
    status = await adapter.status()
    assert status.connected is False
    assert status.identity is None
