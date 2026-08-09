"""QR-07 — WhatsApp Scan/Connect: BFF service, API, RBAC, tenant and safety regression.

Fully hermetic against the provider: every ``WahaChannelAdapter`` the service uses is wired to an
``httpx.MockTransport`` returning payloads captured during physical-phone certification, so no test
here opens a socket or needs a WAHA server.

This suite is as much about what QR-07 must refuse as what it renders: the STARTING ambiguity QR-02
proved, the confirmation logout requires, reconnect eligibility, provider-unavailable truth, no-store
QR delivery, and that no secret of any kind crosses the API boundary.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.channels.errors import ChannelConfigError
from app.channels.flags import OmnichannelFeatureFlag
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime import PairingState
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionState
from app.channels.waha import (
    CONNECTOR_WAHA,
    WahaChannelAdapter,
    WahaCredentials,
    register_waha_runtime,
)
from app.channels.waha.client import WahaClient
from app.core.config import settings
from app.core.exceptions import ConflictError, ServiceUnavailableError
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.channel_session import ChannelSession
from app.models.role import Permission, Role, UserRole
from app.models.settings import FeatureFlag
from app.services.audit_service import AuditAction
from app.services.whatsapp_qr_service import WhatsAppQrService

PASSWORD = "Sup3r-Secret-Pass!"
CREDS = WahaCredentials(base_url="http://waha.internal:3000", api_key="never-logged", session="phonecert")

WORKING_BODY = {
    "name": "phonecert",
    "status": "WORKING",
    "me": {"id": "919355585553@c.us", "pushName": "Neha Sharma", "lid": "210912345485@lid"},
    "engine": {"engine": "NOWEB"},
}
STARTING_BODY = {"name": "phonecert", "status": "STARTING", "me": None, "engine": {"engine": "NOWEB"}}
SCAN_BODY = {"name": "phonecert", "status": "SCAN_QR_CODE", "me": None, "engine": {"engine": "NOWEB"}}
STOPPED_BODY = {"name": "phonecert", "status": "STOPPED", "me": None, "engine": {"engine": "NOWEB"}}
CREATE_BODY = dict(STARTING_BODY)
PNG_BYTES = bytes.fromhex("89504e470d0a1a0a") + b"transient-qr"


def _adapter(handler) -> WahaChannelAdapter:
    transport = httpx.MockTransport(handler)
    return WahaChannelAdapter(CREDS, client=WahaClient(CREDS, http=httpx.AsyncClient(transport=transport)))


def _sequenced_adapter(bodies: list[dict]):
    """An adapter whose GET /api/sessions/{name} answers each body once, in order."""
    calls: list[str] = []
    remaining = list(bodies)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(201, json=CREATE_BODY)
        if request.method == "POST" and request.url.path.endswith("/start"):
            return httpx.Response(200, json=remaining.pop(0) if remaining else WORKING_BODY)
        if request.method == "POST" and request.url.path.endswith("/logout"):
            return httpx.Response(200, json=SCAN_BODY)
        body = remaining.pop(0) if remaining else (bodies[-1] if bodies else WORKING_BODY)
        return httpx.Response(200, json=body)

    return _adapter(handler), calls


def _registries() -> tuple[ProviderRegistry, ProviderRuntimeRegistry]:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    runtimes = ProviderRuntimeRegistry(providers)
    register_waha_runtime(providers, runtimes)
    return providers, runtimes


async def _enable_flags(session, organization_id: int) -> None:
    for flag in OmnichannelFeatureFlag:
        session.add(FeatureFlag(key_name=flag.value, organization_id=organization_id, is_enabled=True))
    await session.commit()


async def _grant(session, organization_id: int, user, *, codes: tuple[str, ...]) -> None:
    permissions = (
        await session.scalars(select(Permission).where(Permission.code.in_(codes)))
    ).all()
    role = Role(organization_id=organization_id, name=f"qr-test-{user.id}", description="test role")
    role.permissions = list(permissions)
    session.add(role)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()


def _service(db_session, providers, runtimes, adapter) -> WhatsAppQrService:
    return WhatsAppQrService(db_session, providers=providers, runtimes=runtimes, adapter=adapter)


async def _reach_paired(db_session, providers, runtimes, organization, actor):
    """Drive one adapter through connect -> pair -> SCAN_QR_CODE -> WORKING/PAIRED.

    Mirrors the real, multi-poll flow: `begin_pairing()` only sees the create response
    (STARTING); a subsequent status read observes `SCAN_QR_CODE`, and a later one observes
    `WORKING`. All three steps share one adapter/service so the scenario is coherent.
    """
    adapter, calls = _sequenced_adapter([SCAN_BODY, WORKING_BODY])
    service = _service(db_session, providers, runtimes, adapter)
    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)
    available = await service.get_status(organization_id=organization.id, actor=actor)
    assert available.pairing_state is PairingState.PAIRING_AVAILABLE
    working = await service.get_status(organization_id=organization.id, actor=actor)
    assert working.pairing_state is PairingState.PAIRED
    return service, working, calls


@pytest.fixture(autouse=True)
def _waha_scope(monkeypatch: pytest.MonkeyPatch):
    """Every test in this file gets a fresh, deterministic WAHA org scope."""
    monkeypatch.setattr(settings, "waha_organization_id", None)
    yield


def _scope_to(monkeypatch: pytest.MonkeyPatch, organization_id: int) -> None:
    monkeypatch.setattr(settings, "waha_organization_id", organization_id)


# --- Not configured -------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_unconfigured_deployment_reports_not_configured(db_session, organization, make_user) -> None:
    """Default settings: no organization is assigned, so every org sees 'not configured'."""
    actor = (await make_user(email="qr-unconf@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = _service(db_session, providers, runtimes, _adapter(lambda r: httpx.Response(200, json=WORKING_BODY)))
    state = await service.get_status(organization_id=organization.id, actor=actor)
    assert state.configured is False


@pytest.mark.anyio
async def test_wrong_organization_sees_not_configured_not_forbidden(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller from a different org gets the SAME 'not configured' signal — existence not leaked."""
    _scope_to(monkeypatch, organization.id + 999)
    actor = (await make_user(email="qr-wrongorg@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = _service(db_session, providers, runtimes, _adapter(lambda r: httpx.Response(200, json=WORKING_BODY)))
    state = await service.get_status(organization_id=organization.id, actor=actor)
    assert state.configured is False


@pytest.mark.anyio
async def test_configured_but_flags_disabled_reports_not_configured(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disabled-by-default flags are preserved: configuration alone is not enough."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-noflags@vi.co", roles=("admin",))).user
    providers, runtimes = _registries()
    service = _service(db_session, providers, runtimes, _adapter(lambda r: httpx.Response(200, json=WORKING_BODY)))
    state = await service.get_status(organization_id=organization.id, actor=actor)
    assert state.configured is False


# --- Connect / begin pairing -----------------------------------------------------------------------


@pytest.mark.anyio
async def test_connect_then_pair_reaches_scan_qr_code(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-connect@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, calls = _sequenced_adapter([SCAN_BODY])

    service = _service(db_session, providers, runtimes, adapter)
    connected = await service.connect(organization_id=organization.id, actor=actor)
    assert connected.configured is True
    assert connected.session_state is SessionState.REGISTERED
    # A brand-new, never-paired session is the idle starting point, not a re-auth condition — it
    # must reach the "creating-session"/"begin pairing" UI path, never the dead-end "reauth"
    # screen a fresh UNPAIRED session was wrongly classified into before this fix.
    assert connected.requires_reauthentication is False

    # begin_pairing only observes the create response (STARTING) — creating a session is not
    # yet "QR available"; that requires a subsequent poll, exactly like the real provider.
    creating = await service.begin_pairing(organization_id=organization.id, actor=actor)
    assert creating.qr_available is False

    available = await service.get_status(organization_id=organization.id, actor=actor)
    assert available.pairing_state is PairingState.PAIRING_AVAILABLE
    assert available.qr_available is True
    assert any(c == "POST /api/sessions" for c in calls)


@pytest.mark.anyio
async def test_connect_is_idempotent(db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-idempotent@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, _ = _sequenced_adapter([])
    service = _service(db_session, providers, runtimes, adapter)
    first = await service.connect(organization_id=organization.id, actor=actor)
    second = await service.connect(organization_id=organization.id, actor=actor)
    assert first.session_public_id == second.session_public_id


# --- STARTING ambiguity ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_starting_never_regresses_durable_pairing_state(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR-02: STARTING cannot tell fresh-session from paired-session-resuming.

    A read-repair poll landing on STARTING must not downgrade a PAIRED durable record.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-starting@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    # Reach WORKING/PAIRED first.
    await _reach_paired(db_session, providers, runtimes, organization, actor)

    # Now a poll observes STARTING (e.g. a container restart mid-poll).
    starting_adapter, _ = _sequenced_adapter([STARTING_BODY])
    service2 = _service(db_session, providers, runtimes, starting_adapter)
    reconciled = await service2.get_status(organization_id=organization.id, actor=actor)
    assert reconciled.pairing_state is PairingState.PAIRED, "STARTING must not overwrite PAIRED"
    # ACTIVE -> INITIALIZING is not a legal forward transition either: an ambiguous STARTING
    # observation must not regress session state any more than it may regress pairing state.
    assert reconciled.session_state is SessionState.ACTIVE


# --- Reconnect --------------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_connected_session_offers_no_reconnect_action(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-reconnect@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    _, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert working.connected is True
    assert working.can_reconnect is False, "an already-connected session offers no reconnect action"


@pytest.mark.anyio
async def test_reconnect_refuses_when_never_paired(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unpaired session must never be auto-restarted — it would only raise an unrequested QR."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-reconnect-unpaired@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, _ = _sequenced_adapter([STOPPED_BODY])
    service = _service(db_session, providers, runtimes, adapter)
    await service.connect(organization_id=organization.id, actor=actor)
    with pytest.raises(ConflictError):
        await service.reconnect(organization_id=organization.id, actor=actor)


@pytest.mark.anyio
async def test_reconnect_eligible_once_paired_session_stops(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A durably-PAIRED session that the provider now reports STOPPED/FAILED may reconnect."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-reconnect-eligible@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)

    # The provider now reports STOPPED; durable state is still PAIRED from the flow above.
    stopped = STOPPED_BODY

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/start"):
            return httpx.Response(200, json=WORKING_BODY)
        return httpx.Response(200, json=stopped)

    service._adapter = _adapter(handler)  # simulate the provider-observed transition
    paused = await service.get_status(organization_id=organization.id, actor=actor)
    assert paused.session_state is SessionState.PAUSED
    assert paused.pairing_state is PairingState.PAIRED
    assert paused.can_reconnect is True

    reconnected = await service.reconnect(organization_id=organization.id, actor=actor)
    assert reconnected.session_state is SessionState.ACTIVE
    assert reconnected.connected is True


# --- Provider unavailable -------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_provider_unavailable_reports_unhealthy_not_unpaired(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transport failure must be reported honestly and must never regress durable state."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-unavailable@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, before, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert before.pairing_state is PairingState.PAIRED

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    during_outage = await service.get_status(organization_id=organization.id, actor=actor)
    assert during_outage.configured is True
    # Durable pairing truth survives the outage untouched.
    assert during_outage.pairing_state is PairingState.PAIRED
    assert during_outage.session_state is SessionState.ACTIVE
    assert during_outage.connected is False
    assert during_outage.requires_reauthentication is False
    assert during_outage.healthy is False
    assert during_outage.can_reconnect is False
    assert during_outage.qr_available is False
    assert during_outage.provider_session_missing is False
    assert during_outage.provider_status is None
    assert during_outage.reconnect_blocked_reason == "provider_unavailable"


@pytest.mark.anyio
async def test_pairing_available_outage_fails_closed_without_mutation_and_recovers(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D8: live QR availability must fail closed while durable pairing truth survives."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09f-outage@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, _ = _sequenced_adapter([SCAN_BODY])
    service = _service(db_session, providers, runtimes, adapter)

    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)
    available = await service.get_status(organization_id=organization.id, actor=actor)
    assert available.pairing_state is PairingState.PAIRING_AVAILABLE
    assert available.qr_available is True
    assert available.reconnect_blocked_reason != "provider_unavailable"

    row_before = (
        await db_session.scalars(
            select(ChannelSession).where(
                ChannelSession.uuid == uuidlib.UUID(available.session_public_id).bytes
            )
        )
    ).one()
    durable_before = (
        row_before.state,
        row_before.pairing_state,
        dict(row_before.provider_metadata_json or {}),
        row_before.health_state,
        row_before.state_detail,
        row_before.reconnect_attempts,
    )

    outage_calls: list[str] = []

    def down(request: httpx.Request) -> httpx.Response:
        outage_calls.append(f"{request.method} {request.url.path}")
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    during_outage = await service.get_status(organization_id=organization.id, actor=actor)

    assert during_outage.session_state is SessionState.WAITING_FOR_PAIRING
    assert during_outage.pairing_state is PairingState.PAIRING_AVAILABLE
    assert during_outage.connected is False
    assert during_outage.requires_reauthentication is False
    assert during_outage.healthy is False
    assert during_outage.can_reconnect is False
    assert during_outage.qr_available is False
    assert during_outage.provider_session_missing is False
    assert during_outage.provider_status is None
    assert during_outage.reconnect_blocked_reason == "provider_unavailable"
    assert during_outage.health_detail == "WhatsApp is temporarily unavailable. Try again shortly."
    rendered = f"{during_outage.health_detail} {during_outage.reconnect_blocked_reason}"
    assert CREDS.api_key not in rendered
    assert CREDS.base_url not in rendered
    assert outage_calls == ["GET /api/sessions/phonecert"]

    row_after = (
        await db_session.scalars(
            select(ChannelSession).where(
                ChannelSession.uuid == uuidlib.UUID(available.session_public_id).bytes
            )
        )
    ).one()
    assert (
        row_after.state,
        row_after.pairing_state,
        dict(row_after.provider_metadata_json or {}),
        row_after.health_state,
        row_after.state_detail,
        row_after.reconnect_attempts,
    ) == durable_before

    recovery_calls: list[str] = []

    def recovered(request: httpx.Request) -> httpx.Response:
        recovery_calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, json=SCAN_BODY)

    service._adapter = _adapter(recovered)
    after_recovery = await service.get_status(organization_id=organization.id, actor=actor)
    assert after_recovery.pairing_state is PairingState.PAIRING_AVAILABLE
    assert after_recovery.qr_available is True
    assert after_recovery.provider_session_missing is False
    assert after_recovery.reconnect_blocked_reason != "provider_unavailable"
    assert recovery_calls == ["GET /api/sessions/phonecert"]


@pytest.mark.anyio
async def test_begin_pairing_provider_unavailable_raises_service_unavailable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A transport failure during begin_pairing must surface as a clean 503, never a raw crash.

    Caught live: an unguarded adapter call let ``ChannelTransportError`` escape as an unhandled
    exception, returning the caller a raw stack trace instead of an RFC 7807 problem response.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-pair-down@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service = _service(db_session, providers, runtimes, _adapter(down))
    await service.connect(organization_id=organization.id, actor=actor)
    with pytest.raises(ServiceUnavailableError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)


@pytest.mark.anyio
async def test_reconnect_provider_unavailable_raises_service_unavailable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-reconnect-down@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert working.connected is True

    def down(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/start"):
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json=STOPPED_BODY)

    service._adapter = _adapter(down)
    paused = await service.get_status(organization_id=organization.id, actor=actor)
    assert paused.can_reconnect is True
    with pytest.raises(ServiceUnavailableError):
        await service.reconnect(organization_id=organization.id, actor=actor)


# --- Logout: explicit, confirmed, deterministic ----------------------------------------------------------


@pytest.mark.anyio
async def test_logout_requires_explicit_confirmation(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-logout-confirm@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, _, calls = await _reach_paired(db_session, providers, runtimes, organization, actor)

    with pytest.raises(ConflictError):
        await service.logout(organization_id=organization.id, actor=actor, confirm=False)
    assert not any("logout" in c for c in calls), "an unconfirmed logout must never reach the provider"


@pytest.mark.anyio
async def test_logout_provider_unavailable_raises_service_unavailable_without_local_termination(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not claim a local logout succeeded when the remote invalidation could not be confirmed."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-logout-down@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    with pytest.raises(ServiceUnavailableError):
        await service.logout(organization_id=organization.id, actor=actor, confirm=True)

    from app.models.channel_session import ChannelSession as ChannelSessionModel

    row = (
        await db_session.scalars(
            select(ChannelSessionModel).where(
                ChannelSessionModel.uuid == uuidlib.UUID(working.session_public_id).bytes
            )
        )
    ).one()
    assert row.state == SessionState.ACTIVE.value, "an unconfirmed logout must not terminate the row"


@pytest.mark.anyio
async def test_confirmed_logout_reaches_reauth_required_truth(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Certification: WORKING -> logout -> SCAN_QR_CODE / me=null. The intended outcome.

    PAIRED is terminal in the existing pairing state machine (the same rule that requires a new
    session revision to re-authenticate an expired one), so logout terminates the paired
    revision and registers a fresh UNPAIRED one rather than reversing it in place.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-logout@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert working.connected is True

    after = await service.logout(organization_id=organization.id, actor=actor, confirm=True)
    assert after.session_public_id != working.session_public_id, "logout starts a fresh revision"
    assert after.session_state is SessionState.REGISTERED
    assert after.pairing_state is PairingState.UNPAIRED
    assert after.identity_masked is None
    assert after.connected is False

    # The old, paired revision is retired, not silently vanished: it stays queryable as history.
    from app.models.channel_session import ChannelSession as ChannelSessionModel

    old_row = (
        await db_session.scalars(
            select(ChannelSessionModel).where(
                ChannelSessionModel.uuid == uuidlib.UUID(working.session_public_id).bytes
            )
        )
    ).one()
    assert old_row.state == SessionState.TERMINATED.value
    assert old_row.pairing_state == PairingState.PAIRED.value, "history is not rewritten"


# --- QR image: no-store, no secret --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_qr_image_only_available_while_pairing_available(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-image-not-ready@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, _ = _sequenced_adapter([])
    service = _service(db_session, providers, runtimes, adapter)
    await service.connect(organization_id=organization.id, actor=actor)
    with pytest.raises(ConflictError):
        await service.qr_image(organization_id=organization.id, actor=actor)


@pytest.mark.anyio
async def test_qr_image_bytes_are_fetched_fresh_and_not_leaked(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-image@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(201, json=CREATE_BODY)
        if "auth/qr" in request.url.path:
            return httpx.Response(200, content=PNG_BYTES, headers={"Content-Type": "image/png"})
        return httpx.Response(200, json=SCAN_BODY)

    service = _service(db_session, providers, runtimes, _adapter(handler))
    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)
    available = await service.get_status(organization_id=organization.id, actor=actor)
    assert available.qr_available is True
    challenge = await service.qr_image(organization_id=organization.id, actor=actor)
    assert challenge.data == PNG_BYTES
    assert "transient-qr" not in repr(challenge)


# --- API layer: RBAC, no-store header, secret safety -------------------------------------------------------------


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_api_requires_authentication(client) -> None:
    response = await client.get("/api/v1/channels/whatsapp-qr/session")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_api_rbac_denies_unprivileged_actor(client, db_session, organization, make_user) -> None:
    await make_user(email="qr-api-unpriv@vi.co", password=PASSWORD, roles=())
    headers = await _headers(client, "qr-api-unpriv@vi.co")
    response = await client.get("/api/v1/channels/whatsapp-qr/session", headers=headers)
    assert response.status_code == 403


@pytest.mark.anyio
async def test_api_reports_not_configured_for_authorized_actor(
    client, db_session, organization, make_user
) -> None:
    """Default settings: even an authorized, correctly-permissioned actor sees 'not configured'."""
    await make_user(email="qr-api-ok@vi.co", password=PASSWORD, roles=("admin",))
    headers = await _headers(client, "qr-api-ok@vi.co")
    response = await client.get("/api/v1/channels/whatsapp-qr/session", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert "api_key" not in str(body).lower() and "waha_api_key" not in str(body).lower()


@pytest.mark.anyio
async def test_api_logout_endpoint_rejects_missing_confirmation(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="qr-api-logout@vi.co", password=PASSWORD, roles=("admin",))
    headers = await _headers(client, "qr-api-logout@vi.co")
    response = await client.post(
        "/api/v1/channels/whatsapp-qr/session/logout", json={"confirm": False}, headers=headers
    )
    assert response.status_code in (404, 409), "unconfigured or confirmation-refused, never a silent 200"


# --- Concurrency / lease reuse --------------------------------------------------------------------------------


@pytest.mark.anyio
async def test_concurrent_mutation_is_serialised_by_the_real_session_lease(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two requests racing a mutation must not both succeed — the existing lease rejects the loser.

    Reuses `SessionManager`'s own lease/fencing rather than a bespoke lock: this test proves that
    reuse, not a parallel concurrency primitive QR-07 might have invented instead.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr-race@vi.co", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, _ = _sequenced_adapter([])
    service = _service(db_session, providers, runtimes, adapter)
    connected = await service.connect(organization_id=organization.id, actor=actor)

    from app.services.session_manager import SessionManager

    manager = SessionManager(db_session, providers=providers)
    held = await manager.acquire_lock(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(connected.session_public_id),
        runtime_id="external-holder",
        lease_seconds=60,
        expected_row_version=connected.row_version,
    )
    assert held.holder_runtime_id == "external-holder"

    with pytest.raises(ConflictError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)


# --- Runtime registration opt-in (composition root) ------------------------------------------------------------


def test_get_channel_foundation_registers_waha_only_when_fully_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.channels.dependencies import get_channel_foundation

    get_channel_foundation.cache_clear()
    monkeypatch.setattr(settings, "waha_base_url", "")
    monkeypatch.setattr(settings, "waha_api_key", "")
    monkeypatch.setattr(settings, "waha_session_name", "")
    unconfigured = get_channel_foundation()
    assert unconfigured.runtimes.available() == ()

    get_channel_foundation.cache_clear()
    monkeypatch.setattr(settings, "waha_base_url", "http://waha.internal:3000")
    monkeypatch.setattr(settings, "waha_api_key", "k")
    monkeypatch.setattr(settings, "waha_session_name", "phonecert")
    configured = get_channel_foundation()
    assert configured.runtimes.available() == (CONNECTOR_WAHA,)
    get_channel_foundation.cache_clear()


# --- QR-09-D2: provider reachable, configured session absent ---------------------------------
#
# QR-09 reproduced this against the real pinned WAHA container: restarting the provider without
# persistent session storage leaves it up and answering, but holding no session under the
# configured name. Every status read then returned HTTP 500, so the operator could not even load
# the screen they needed in order to recover. These tests pin the corrected behaviour.

_SESSION_NOT_FOUND_BODY = {
    "message": "Session not found",
    "error": "Not Found",
    "statusCode": 404,
}


def _session_absent_adapter(*, before: list[dict] | None = None) -> WahaChannelAdapter:
    """Answers each `before` body once, then 404s every session read.

    Models the real provider timeline: the session existed, the provider restarted, and the same
    GET now returns the provider's genuine "Session not found".
    """
    remaining = list(before or [])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(201, json=CREATE_BODY)
        if remaining:
            return httpx.Response(200, json=remaining.pop(0))
        return httpx.Response(404, json=_SESSION_NOT_FOUND_BODY)

    return _adapter(handler)


@pytest.mark.anyio
async def test_session_absent_is_not_reported_as_provider_unavailable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reachable provider holding no session is a different fact from an unreachable one.

    Reporting `provider_unavailable` here would tell the operator to wait out an outage that is
    not happening, and would hide the action that actually resolves it.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-absent@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service = _service(db_session, providers, runtimes, _session_absent_adapter())
    await service.connect(organization_id=organization.id, actor=actor)
    state = await service.get_status(organization_id=organization.id, actor=actor)

    assert state.provider_session_missing is True
    assert state.reconnect_blocked_reason == "provider_session_missing"
    assert state.connected is False
    assert state.healthy is False
    assert state.can_reconnect is False
    assert state.qr_available is False


@pytest.mark.anyio
async def test_session_absent_on_a_fresh_connection_is_not_a_reauthentication(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing was ever paired, so this is the ordinary connect-and-scan path, not a re-auth."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-fresh@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service = _service(db_session, providers, runtimes, _session_absent_adapter())
    await service.connect(organization_id=organization.id, actor=actor)
    state = await service.get_status(organization_id=organization.id, actor=actor)

    assert state.provider_session_missing is True
    assert state.requires_reauthentication is False
    assert "scan the QR code" in state.health_detail


@pytest.mark.anyio
async def test_session_absent_after_pairing_requires_reauth_but_keeps_durable_truth(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A paired account whose provider session vanished genuinely needs a fresh scan.

    The durable pairing record remains the platform's own truth about what was linked, so it must
    survive the observation unchanged — the projection reports the divergence rather than erasing
    history.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-paired@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    _, paired, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert paired.pairing_state is PairingState.PAIRED

    after_restart = _service(db_session, providers, runtimes, _session_absent_adapter())
    state = await after_restart.get_status(organization_id=organization.id, actor=actor)

    assert state.provider_session_missing is True
    assert state.requires_reauthentication is True
    assert state.connected is False
    assert "paired again" in state.health_detail
    assert state.pairing_state is PairingState.PAIRED


@pytest.mark.anyio
async def test_session_absent_does_not_recreate_a_session_or_request_a_qr(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading status must never be a write: no session creation, no pairing, no QR fetch."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-noside@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(201, json=CREATE_BODY)
        return httpx.Response(404, json=_SESSION_NOT_FOUND_BODY)

    service = _service(db_session, providers, runtimes, _adapter(handler))
    await service.connect(organization_id=organization.id, actor=actor)
    calls.clear()

    await service.get_status(organization_id=organization.id, actor=actor)
    await service.get_status(organization_id=organization.id, actor=actor)

    assert not [c for c in calls if c.startswith("POST")], f"status read wrote: {calls}"
    assert not [c for c in calls if "auth/qr" in c], f"status read fetched a QR: {calls}"


@pytest.mark.anyio
async def test_reconnect_refuses_when_the_provider_has_no_session(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR-06 restarts an *existing* session; there is none, so reconnect refuses truthfully."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-reconnect@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    await _reach_paired(db_session, providers, runtimes, organization, actor)
    after_restart = _service(db_session, providers, runtimes, _session_absent_adapter())

    with pytest.raises(ConflictError):
        await after_restart.reconnect(organization_id=organization.id, actor=actor)


@pytest.mark.anyio
async def test_provider_unreachable_is_still_an_outage_not_a_missing_session(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR-06's outage semantics are untouched: unreachable stays unreachable, never 'gone'."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-outage@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    await _reach_paired(db_session, providers, runtimes, organization, actor)

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    outage = _service(db_session, providers, runtimes, _adapter(down))
    state = await outage.get_status(organization_id=organization.id, actor=actor)

    assert state.provider_session_missing is False
    assert state.reconnect_blocked_reason != "provider_session_missing"
    assert state.pairing_state is PairingState.PAIRED


@pytest.mark.anyio
async def test_session_absent_state_leaks_no_credential_url_or_traceback(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The recoverable message is operator-facing prose, never provider internals."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09a-secret@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service = _service(db_session, providers, runtimes, _session_absent_adapter())
    await service.connect(organization_id=organization.id, actor=actor)
    state = await service.get_status(organization_id=organization.id, actor=actor)

    rendered = f"{state.health_detail} {state.reconnect_blocked_reason}"
    assert CREDS.api_key not in rendered
    assert "waha.internal" not in rendered
    assert "404" not in rendered
    assert "Traceback" not in rendered


# --- QR-09-D9: a paused, never-paired session must stay recoverable ----------------------------


async def _reach_paused_never_paired(db_session, providers, runtimes, organization, actor):
    """connect -> begin_pairing -> the provider reports STOPPED -> durable PAUSED, never paired.

    This is the exact timeline reproduced on the certified runtime: STOPPED is an ordinary WAHA
    status (a restart, or a provider-side session removal), `map_session_status` turns it into
    PAUSED, and the pairing state is left untouched because STOPPED cannot determine it. The
    result is a durable session that has never been paired and can no longer be leased.
    """
    adapter, _ = _sequenced_adapter([SCAN_BODY])
    service = _service(db_session, providers, runtimes, adapter)
    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    service._adapter = _adapter(lambda request: httpx.Response(200, json=STOPPED_BODY))
    paused = await service.get_status(organization_id=organization.id, actor=actor)
    assert paused.session_state is SessionState.PAUSED
    assert paused.pairing_state is not PairingState.PAIRED
    return service, paused


def _pairing_recovery_adapter() -> tuple[WahaChannelAdapter, list[str]]:
    """The provider holds no session (the D9 state) and accepts exactly one create."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(201, json=CREATE_BODY)
        if request.method == "GET" and request.url.path.startswith("/api/sessions/"):
            return httpx.Response(404, json=_SESSION_NOT_FOUND_BODY)
        return httpx.Response(200, json=SCAN_BODY)

    return _adapter(handler), calls


@pytest.mark.anyio
async def test_paused_never_paired_session_recovers_through_explicit_pairing(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D9: pairing is the only action that can move this forward, so it must not be refused.

    Before this fix `begin_pairing()` raised "the session is paused and cannot acquire a runtime
    lease" while `reconnect()` simultaneously told the operator to pair — an unrecoverable
    control-plane dead end that needed direct database intervention to escape.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-recover@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, paused = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    adapter, calls = _pairing_recovery_adapter()
    service._adapter = adapter

    recovered = await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert recovered.session_state is not SessionState.PAUSED
    assert recovered.pairing_state is not PairingState.PAIRED
    # Exactly one provider session was created, and nothing was started twice.
    assert calls.count("POST /api/sessions") == 1
    assert recovered.session_public_id == paused.session_public_id


@pytest.mark.anyio
async def test_paused_recovery_never_requests_a_lease_while_still_paused(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The row must leave PAUSED first; the PAUSED lease prohibition is never asked to bend."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-order@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    service._adapter = _pairing_recovery_adapter()[0]

    manager = service._session_manager
    original_acquire = manager.acquire_lock
    states_when_leasing: list[str] = []

    async def recording_acquire(**kwargs):
        row = (await db_session.scalars(select(ChannelSession))).one()
        await db_session.refresh(row)
        states_when_leasing.append(row.state)
        return await original_acquire(**kwargs)

    manager.acquire_lock = recording_acquire  # type: ignore[method-assign]
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert states_when_leasing, "the pairing path must still acquire a real runtime lease"
    assert SessionState.PAUSED.value not in states_when_leasing


@pytest.mark.anyio
async def test_session_manager_still_refuses_to_lease_a_paused_session(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The durable invariant is untouched: QR-09G leaves PAUSED, it does not lease a paused row."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-invariant@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, paused = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    row = (await db_session.scalars(select(ChannelSession))).one()

    with pytest.raises(ConflictError):
        await service._session_manager.acquire_lock(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(paused.session_public_id),
            runtime_id="qr09g-direct-probe",
            lease_seconds=60,
            expected_row_version=row.row_version,
        )


@pytest.mark.anyio
async def test_paused_paired_session_is_not_restarted_as_first_time_pairing(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Durable credentials stay in the reconnect/re-auth domain — recovery is narrow by design."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-paired@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    service._adapter = _adapter(lambda request: httpx.Response(200, json=STOPPED_BODY))
    paused = await service.get_status(organization_id=organization.id, actor=actor)
    assert paused.session_state is SessionState.PAUSED
    assert paused.pairing_state is PairingState.PAIRED
    # Reconnect — not first-time pairing — is the governed recovery for lost credentials.
    assert paused.can_reconnect is True

    created: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/sessions":
            created.append(request.url.path)
        return httpx.Response(200, json=STOPPED_BODY)

    service._adapter = _adapter(handler)
    with pytest.raises(ConflictError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)
    assert created == [], "a paired paused session must never be re-created as a fresh pairing"

    after = await service.get_status(organization_id=organization.id, actor=actor)
    assert after.pairing_state is PairingState.PAIRED
    assert after.session_state is SessionState.PAUSED


@pytest.mark.anyio
async def test_paused_recovery_reports_provider_failure_honestly(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider that fails after the row left PAUSED must not be reported as a success."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-honest@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    with pytest.raises(ServiceUnavailableError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)

    after = await service.get_status(organization_id=organization.id, actor=actor)
    assert after.connected is False
    assert after.qr_available is False
    assert after.pairing_state is not PairingState.PAIRED


@pytest.mark.anyio
async def test_paused_recovery_preserves_row_version_and_fencing_progress(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Optimistic concurrency and fencing keep advancing — recovery is not a back door."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-fencing@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, paused = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    before = (await db_session.scalars(select(ChannelSession))).one()
    await db_session.refresh(before)
    version_before, fencing_before = before.row_version, before.fencing_token

    service._adapter = _pairing_recovery_adapter()[0]
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    after = (await db_session.scalars(select(ChannelSession))).one()
    await db_session.refresh(after)
    assert after.row_version > version_before
    assert after.fencing_token > fencing_before

    # A second recovery driven from the now-stale version must be refused, so two concurrent
    # attempts can never both drive the provider.
    with pytest.raises(ConflictError):
        await service._session_manager.transition_session(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(paused.session_public_id),
            expected_row_version=version_before,
            target_state=SessionState.INITIALIZING,
        )


@pytest.mark.anyio
async def test_paused_recovery_creates_no_duplicate_durable_session(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recovery reuses the one durable session; it never registers a second one."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-single@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    service._adapter = _pairing_recovery_adapter()[0]
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    rows = (await db_session.scalars(select(ChannelSession))).all()
    assert len(rows) == 1


@pytest.mark.anyio
async def test_paused_session_status_reports_missing_provider_session_truthfully(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D9 projection: an unleasable row must still tell the truth about the provider.

    A PAUSED row cannot be leased, so reconciliation used to be skipped entirely and the response
    fell back to stale durable metadata — reporting an outage that was not happening and hiding
    the recovery action. Reading the provider is not a mutation, so the read still happens.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-projection@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    service._adapter = _session_absent_adapter()

    state = await service.get_status(organization_id=organization.id, actor=actor)

    assert state.provider_session_missing is True
    assert state.reconnect_blocked_reason == "provider_session_missing"
    assert state.requires_reauthentication is False
    assert state.qr_available is False
    assert state.connected is False
    # Durable truth is untouched by a read.
    assert state.session_state is SessionState.PAUSED


@pytest.mark.anyio
async def test_paused_session_status_still_reports_a_real_outage_as_unavailable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR-09F stays intact on the unleasable path: an outage is still an outage."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-outage@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    state = await service.get_status(organization_id=organization.id, actor=actor)

    assert state.reconnect_blocked_reason == "provider_unavailable"
    assert state.provider_session_missing is False
    assert state.qr_available is False
    assert state.provider_status is None
    assert state.session_state is SessionState.PAUSED


@pytest.mark.anyio
async def test_unleasable_read_never_creates_or_mutates_provider_state(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lease-free observation is a read: no create, start, delete or QR request."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09g-readonly@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()

    service, _ = await _reach_paused_never_paired(
        db_session, providers, runtimes, organization, actor
    )
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(404, json=_SESSION_NOT_FOUND_BODY)

    service._adapter = _adapter(handler)
    await service.get_status(organization_id=organization.id, actor=actor)
    await service.get_status(organization_id=organization.id, actor=actor)

    assert calls, "the provider must still be observed"
    assert all(call.startswith("GET ") for call in calls), calls
    assert not any("/auth/qr" in call for call in calls)


# --- QR-09-D10: an expired QR must not be terminal --------------------------------------------

_ALREADY_EXISTS_BODY = {
    "message": "Session 'phonecert' already exists. Use PUT to update it.",
    "error": "Unprocessable Entity",
    "statusCode": 422,
}


def _existing_session_adapter(*, status: str, me: dict | None = None, after_start: str = "SCAN_QR_CODE"):
    """The provider already holds this session, so `POST /api/sessions` is refused exactly as the
    certified build refuses it. Stop/start mutate the modelled status the way 2026.7.2 does.
    """
    state = {"status": status, "me": me}
    calls: list[str] = []

    def body() -> dict:
        return {
            "name": "phonecert",
            "status": state["status"],
            "me": state["me"],
            "engine": {"engine": "NOWEB"},
        }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if request.method == "POST" and path == "/api/sessions":
            return httpx.Response(422, json=_ALREADY_EXISTS_BODY)
        if request.method == "POST" and path.endswith("/stop"):
            state["status"] = "STOPPED"
            return httpx.Response(201, json=body())
        if request.method == "POST" and path.endswith("/start"):
            state["status"] = after_start
            return httpx.Response(201, json=body())
        return httpx.Response(200, json=body())

    return _adapter(handler), calls, state


async def _reach_expired_qr(db_session, providers, runtimes, organization, actor):
    """connect -> begin_pairing -> QR shown -> operator never scans it.

    Leaves the exact D10 precondition: durable `waiting_for_pairing`/`pairing_available`, never
    paired, and a provider session object that survives with a non-working status.
    """
    adapter, _ = _sequenced_adapter([SCAN_BODY])
    service = _service(db_session, providers, runtimes, adapter)
    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)
    shown = await service.get_status(organization_id=organization.id, actor=actor)
    assert shown.pairing_state is PairingState.PAIRING_AVAILABLE
    return service


@pytest.mark.anyio
async def test_missing_provider_session_still_takes_the_plain_create_path(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 1: nothing to recover, so pairing creates once and never stops/starts anything."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-create@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    adapter, calls = _sequenced_adapter([SCAN_BODY])
    service = _service(db_session, providers, runtimes, adapter)

    await service.connect(organization_id=organization.id, actor=actor)
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert calls.count("POST /api/sessions") == 1
    assert not any(c.endswith("/stop") for c in calls)
    assert not any(c.endswith("/start") for c in calls)


@pytest.mark.anyio
async def test_expired_qr_recovers_through_the_certified_stop_start_pair(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 3 — the D10 defect. An unscanned QR lapsed and left the session object behind.

    Before this fix every retry hit the provider's `already exists` refusal, which the service
    reported as an outage, so the channel could never issue another QR without direct provider
    intervention.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-expired@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    before = (await db_session.scalars(select(ChannelSession))).one()
    original_expiry = before.pairing_expires_at
    original_revision = before.pairing_revision
    assert original_expiry is not None

    adapter, calls, state = _existing_session_adapter(status="FAILED")
    service._adapter = adapter

    recovered = await service.begin_pairing(organization_id=organization.id, actor=actor)

    # The certified recovery is stop-then-start, in that order, and nothing else.
    assert [c for c in calls if c.startswith("POST ")] == [
        "POST /api/sessions",
        "POST /api/sessions/phonecert/stop",
        "POST /api/sessions/phonecert/start",
    ]
    assert state["status"] == "SCAN_QR_CODE"
    assert state["me"] is None
    assert recovered.pairing_state is PairingState.PAIRING_AVAILABLE
    assert recovered.requires_reauthentication is False
    assert recovered.row_version is not None
    renewed = (await db_session.scalars(select(ChannelSession))).one()
    assert renewed.pairing_expires_at is not None
    assert renewed.pairing_expires_at > original_expiry
    assert renewed.pairing_revision == original_revision
    renewal_audits = list(
        (
            await db_session.scalars(
                select(AuditLog).where(
                    AuditLog.action == AuditAction.CHANNEL_PAIRING_AVAILABILITY_RENEWED
                )
            )
        ).all()
    )
    assert len(renewal_audits) == 1
    # Exactly one durable session; nothing was recreated.
    assert len((await db_session.scalars(select(ChannelSession))).all()) == 1


@pytest.mark.anyio
async def test_expired_qr_recovery_is_repeatable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QR expiry must never become terminal — the cycle has to survive being repeated."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-repeat@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    for cycle in range(2):
        adapter, calls, state = _existing_session_adapter(status="FAILED")
        service._adapter = adapter
        recovered = await service.begin_pairing(organization_id=organization.id, actor=actor)
        assert state["status"] == "SCAN_QR_CODE", f"cycle {cycle}"
        assert recovered.pairing_state is PairingState.PAIRING_AVAILABLE, f"cycle {cycle}"
        assert calls.count("POST /api/sessions/phonecert/start") == 1, f"cycle {cycle}"

    assert len((await db_session.scalars(select(ChannelSession))).all()) == 1


@pytest.mark.anyio
async def test_stopped_session_is_started_without_a_redundant_stop(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An already-stopped session only needs starting; stopping it again is pointless churn."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-stopped@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    adapter, calls, state = _existing_session_adapter(status="STOPPED")
    service._adapter = adapter
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert not any(c.endswith("/stop") for c in calls)
    assert calls.count("POST /api/sessions/phonecert/start") == 1
    assert state["status"] == "SCAN_QR_CODE"


@pytest.mark.anyio
async def test_session_already_showing_a_qr_is_reused_untouched(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 2: a session already presenting a QR must not be churned to produce another."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-reuse@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    before = (await db_session.scalars(select(ChannelSession))).one()
    original_expiry = before.pairing_expires_at
    original_revision = before.pairing_revision
    assert original_expiry is not None

    adapter, calls, state = _existing_session_adapter(status="SCAN_QR_CODE")
    service._adapter = adapter
    reused = await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert not any(c.endswith("/stop") for c in calls)
    assert not any(c.endswith("/start") for c in calls)
    assert state["status"] == "SCAN_QR_CODE"
    assert reused.pairing_state is PairingState.PAIRING_AVAILABLE
    renewed = (await db_session.scalars(select(ChannelSession))).one()
    assert renewed.pairing_expires_at is not None
    assert renewed.pairing_expires_at > original_expiry
    assert renewed.pairing_revision == original_revision


@pytest.mark.anyio
async def test_provider_confirmed_working_completes_an_expired_pairing_window(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D11: a linked, identity-bearing live session outranks the expired QR representation."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09i-working@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    before = (await db_session.scalars(select(ChannelSession))).one()
    original_public_id = before.public_id
    original_revision = before.pairing_revision
    before.pairing_expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    adapter, calls, _ = _existing_session_adapter(
        status="WORKING",
        me={"id": "919355585553@c.us", "pushName": "Neha Sharma"},
    )
    service._adapter = adapter
    converged = await service.get_status(organization_id=organization.id, actor=actor)

    assert calls == ["GET /api/sessions/phonecert"]
    assert converged.session_public_id == original_public_id
    assert converged.session_state is SessionState.ACTIVE
    assert converged.pairing_state is PairingState.PAIRED
    assert converged.connected is True
    assert converged.qr_available is False
    assert converged.provider_status == "WORKING"
    assert converged.identity_masked is not None
    assert "919355585553" not in converged.identity_masked
    durable = (await db_session.scalars(select(ChannelSession))).one()
    assert durable.pairing_expires_at is None
    assert durable.pairing_revision == original_revision
    assert len((await db_session.scalars(select(ChannelSession))).all()) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("provider_name", "provider_identity"),
    [("phonecert", None), ("different-session", "919355585553@c.us")],
)
async def test_expired_pairing_rejects_unproven_or_wrong_session_working_claim(
    db_session,
    organization,
    make_user,
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    provider_identity: str | None,
) -> None:
    """An arbitrary stale row cannot use D11 completion without same-session identity evidence."""
    _scope_to(monkeypatch, organization.id)
    actor = (
        await make_user(
            email=f"qr09i-unproven-{provider_name}@vi.co",
            is_superuser=True,
        )
    ).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    row = (await db_session.scalars(select(ChannelSession))).one()
    row.pairing_expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    body = {
        "name": provider_name,
        "status": "WORKING",
        "me": ({"id": provider_identity} if provider_identity is not None else None),
        "engine": {"engine": "NOWEB"},
    }
    service._adapter = _adapter(lambda request: httpx.Response(200, json=body))
    projected = await service.get_status(organization_id=organization.id, actor=actor)

    assert projected.pairing_state is PairingState.PAIRING_AVAILABLE
    assert projected.session_state is SessionState.WAITING_FOR_PAIRING
    assert projected.connected is False
    durable = (await db_session.scalars(select(ChannelSession))).one()
    assert durable.pairing_state == PairingState.PAIRING_AVAILABLE.value
    assert durable.pairing_expires_at is not None


@pytest.mark.anyio
async def test_recovery_refuses_a_provider_session_with_a_linked_account(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 4 (provider half): a linked account is never restarted into first-time pairing."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-linked@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    adapter, calls, _ = _existing_session_adapter(
        status="FAILED", me={"id": "919355585553@c.us", "pushName": "Neha Sharma"}
    )
    service._adapter = adapter
    with pytest.raises(ConflictError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert not any(c.endswith("/stop") for c in calls)
    assert not any(c.endswith("/start") for c in calls)


@pytest.mark.anyio
async def test_durably_paired_connection_never_enters_pairing_recovery(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 4 (durable half): refused before any provider call is made at all."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-paired@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service, working, _ = await _reach_paired(db_session, providers, runtimes, organization, actor)
    assert working.pairing_state is PairingState.PAIRED

    adapter, calls, _ = _existing_session_adapter(status="FAILED")
    service._adapter = adapter
    with pytest.raises(ConflictError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)

    assert calls == [], "a paired connection must not reach the provider through this path"


@pytest.mark.anyio
async def test_transport_outage_during_pairing_is_still_service_unavailable(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 5: an unreachable provider keeps its existing truthful outage classification."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-outage@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    before = (await db_session.scalars(select(ChannelSession))).one()
    original_expiry = before.pairing_expires_at

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service._adapter = _adapter(down)
    with pytest.raises(ServiceUnavailableError):
        await service.begin_pairing(organization_id=organization.id, actor=actor)
    after = (await db_session.scalars(select(ChannelSession))).one()
    assert after.pairing_expires_at == original_expiry


@pytest.mark.anyio
async def test_reached_provider_refusal_is_a_conflict_not_a_false_outage(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CASE 6 — the second half of D10. The provider answered, so "couldn't be reached" is a lie.

    Also proves the provider's own wording never reaches the operator: remote text must not be
    interpolated into an operator-facing message.
    """
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-conflict@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    before = (await db_session.scalars(select(ChannelSession))).one()
    original_expiry = before.pairing_expires_at

    # Create is refused *and* the session genuinely is not there: a reached-provider disagreement
    # that no recovery can resolve, which must still be reported honestly.
    def conflicting(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/sessions":
            return httpx.Response(422, json=_ALREADY_EXISTS_BODY)
        return httpx.Response(404, json=_SESSION_NOT_FOUND_BODY)

    service._adapter = _adapter(conflicting)
    with pytest.raises(ConflictError) as caught:
        await service.begin_pairing(organization_id=organization.id, actor=actor)

    rendered = str(caught.value)
    assert "already exists" not in rendered
    assert "Use PUT" not in rendered
    assert "422" not in rendered
    assert CREDS.api_key not in rendered
    assert "waha.internal" not in rendered
    after = (await db_session.scalars(select(ChannelSession))).one()
    assert after.pairing_expires_at == original_expiry


@pytest.mark.anyio
async def test_provider_authentication_failure_keeps_its_existing_semantics(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auth/configuration failures are not reclassified by this milestone."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-auth@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    service._adapter = _adapter(lambda r: httpx.Response(401, json={"message": "bad key"}))
    with pytest.raises(ServiceUnavailableError) as caught:
        await service.begin_pairing(organization_id=organization.id, actor=actor)
    assert "bad key" not in str(caught.value)


@pytest.mark.anyio
async def test_pairing_recovery_requires_a_runtime_lease() -> None:
    """No caller can drive the provider through this path without holding the governed lease."""
    adapter = _adapter(lambda r: httpx.Response(422, json=_ALREADY_EXISTS_BODY))
    with pytest.raises(ChannelConfigError):
        await adapter.prepare_pairing("phonecert")


@pytest.mark.anyio
async def test_polling_never_stops_or_starts_the_provider_session(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading status is not an operator action: it may never mutate provider state."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-poll@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)
    before = (await db_session.scalars(select(ChannelSession))).one()
    original_expiry = before.pairing_expires_at

    adapter, calls, state = _existing_session_adapter(status="FAILED")
    service._adapter = adapter
    for _ in range(3):
        await service.get_status(organization_id=organization.id, actor=actor)

    assert calls, "status must still observe the provider"
    assert all(c.startswith("GET ") for c in calls), calls
    assert state["status"] == "FAILED", "polling must not have recovered anything by itself"
    after = (await db_session.scalars(select(ChannelSession))).one()
    assert after.pairing_expires_at == original_expiry


@pytest.mark.anyio
async def test_concurrent_pairing_cannot_be_driven_from_a_stale_row_version(
    db_session, organization, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Optimistic concurrency still gates the recovery path, so two clicks cannot both drive it."""
    _scope_to(monkeypatch, organization.id)
    actor = (await make_user(email="qr09h-concurrent@vi.co", is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    service = await _reach_expired_qr(db_session, providers, runtimes, organization, actor)

    before = (await db_session.scalars(select(ChannelSession))).one()
    await db_session.refresh(before)
    stale_version, public_id = before.row_version, before.public_id

    adapter, _, _ = _existing_session_adapter(status="FAILED")
    service._adapter = adapter
    await service.begin_pairing(organization_id=organization.id, actor=actor)

    with pytest.raises(ConflictError):
        await service._session_manager.acquire_lock(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(public_id),
            runtime_id="qr09h-stale-probe",
            lease_seconds=60,
            expected_row_version=stale_version,
        )
