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

import httpx
import pytest
from sqlalchemy import select

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
from app.models.role import Permission, Role, UserRole
from app.models.settings import FeatureFlag
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
