"""QR-07 — WhatsApp Scan/Connect orchestration.

QR-01..06 built a WAHA adapter that can probe, pair, ingest, send and recover a session, but
nothing before this milestone ever bridged its **live** provider I/O to the durable,
tenant/RBAC/lease-governed control plane M13-03/04/05 already built (`ChannelConnection`,
`ChannelSession`, :class:`SessionManager`, :class:`PairingManager`). This module is exactly that
bridge, and nothing else: it creates no table, no parallel session/lease/pairing model, and no
provider-specific persistence. Every durable fact lives in the columns those services already own.

## Why exactly one connection, not a per-organization store

ADR-0021's deployment scope for WAHA is explicit: **internal, self-hosted, single organization —
not multi-tenant SaaS**. QR-01..06 already reflect that: WAHA credentials come from process-wide
settings (`WahaCredentials.from_settings()`), never a per-tenant secret. This service keeps that
architecture rather than building a multi-tenant credential store WAHA was never designed for:
`settings.waha_organization_id` names the single organization the QR surface exists for, and every
other organization sees ``configured=False`` — indistinguishable from "WAHA isn't deployed here" so
the API never confirms or denies which organization owns it to a caller who does not.

## Every mutation holds the real M13-05 lease

Every method that can change durable state — connect, pair, refresh (read-repair), reconnect,
logout — acquires the session's actual database lease via :class:`SessionManager` before touching
the provider and releases it before returning. A second request arriving mid-operation gets the
`SessionManager`'s own "lease is held by another active runtime" conflict, not a bespoke lock this
module invented. This is what "only the current lease holder may mutate" means reused rather than
reinvented, and it is also what prevents two concurrent clicks from racing a pairing transition.

## Pairing safety carried forward

:func:`~app.channels.waha.recovery.plan_reconnect` — built in QR-06 specifically because QR-02
proved ``STARTING`` is ambiguous — is the only thing allowed to authorize a reconnect. Read-repair
never overwrites durable ``pairing_state`` when the live snapshot's mapping is ``None`` (ambiguous),
and it never regresses ``session_state`` either: every transition it applies is checked against the
existing ``can_transition``/``can_transition_pairing`` legality tables, so an ambiguous or
out-of-order observation can advance state but never walk it backwards.

## Logout retires a revision; it does not reverse one

``PairingState.PAIRED`` is **terminal** in the existing M13-05 pairing state machine — the same rule
that requires a brand-new session revision to re-authenticate an already-``EXPIRED`` one. Logout
respects that rather than working around it: it terminates the paired revision (an honest, queryable
historical record — "this revision was paired, then explicitly logged out") and registers a fresh
``UNPAIRED`` revision on the same connection. The session identity the caller sees therefore changes
after logout; that is the correct signal that a new pairing attempt is required, not an artefact.

## The QR image is never persisted

:meth:`WhatsAppQrService.qr_image` calls :meth:`WahaChannelAdapter.pairing_challenge` fresh on every
request and returns the bytes directly to the caller. Nothing here writes them to a row, a log, or
an audit payload — the existing "QR images and challenge bytes are deliberately absent" boundary
from M13-05 is preserved, not widened.
"""

from __future__ import annotations

import re
import uuid as uuidlib
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import CONNECTOR_WAHA, Capability, ChannelType
from app.channels.errors import ChannelApiError, ChannelError, ChannelTransportError
from app.channels.flags import ChannelFeatureFlagResolver, OmnichannelFeatureFlag
from app.channels.foundation import ProviderDesiredState
from app.channels.registry import ProviderRegistry
from app.channels.runtime import PairingState
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionState
from app.channels.waha import (
    ReconnectDecision,
    WahaChannelAdapter,
    WahaQrChallenge,
    WahaSessionNotFound,
    WahaSessionSnapshot,
    WahaSessionStatus,
    map_session_status,
    plan_reconnect,
)
from app.channels.waha import RuntimeLease as WahaRuntimeLease
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.db.mixins import utcnow
from app.models.channel_connection import ChannelConnection
from app.models.channel_session import ChannelSession
from app.models.user import User
from app.repositories.channel_connection import (
    ChannelConnectionRepository,
    ChannelEndpointRepository,
)
from app.repositories.channel_session import ChannelSessionRepository
from app.services.channel_connection_service import ChannelConnectionService
from app.services.rbac_service import RBACService
from app.services.session_manager import SessionManager

if TYPE_CHECKING:
    from app.services.pairing_manager import PairingManager

#: RBAC permission gating this entire surface — matches the vocabulary
#: ``PairingManager.AUTHENTICATE_PERMISSION`` already established for "manage pairing lifecycle".
OPERATE_PERMISSION = "channels:authenticate"
READ_PERMISSION = "channels:read"

#: Capabilities recorded against the session so `PairingManager` will operate on it (it requires
#: `qr_auth` to be declared) — mirrors exactly what the adapter implements, no more.
_SESSION_CAPABILITIES = [
    Capability.HEALTH.value,
    Capability.QR_AUTH.value,
    Capability.SESSION_STREAM.value,
    Capability.TEXT.value,
    Capability.SESSION_RECONNECT.value,
    Capability.SESSION_LOGOUT.value,
]

_IDENTITY_DIGITS = re.compile(r"\d{6,15}")


def _mask_identity(raw: str | None) -> str | None:
    """Mask the digit run of a provider identity, keeping only enough to recognise the account."""

    if not raw:
        return None

    def _mask(match: re.Match[str]) -> str:
        digits = match.group()
        if len(digits) <= 7:
            return "*" * len(digits)
        return digits[:4] + "*" * (len(digits) - 7) + digits[-3:]

    return _IDENTITY_DIGITS.sub(_mask, raw)


@dataclass(frozen=True, slots=True)
class WhatsAppQrState:
    """Everything the API layer needs to build a response — no ORM row escapes this module."""

    configured: bool
    session_public_id: str | None = None
    row_version: int | None = None
    session_state: SessionState | None = None
    pairing_state: PairingState | None = None
    provider_status: str | None = None
    connected: bool = False
    requires_reauthentication: bool = False
    healthy: bool = False
    health_detail: str = "WhatsApp is not configured for this organization."
    can_reconnect: bool = False
    reconnect_blocked_reason: str | None = None
    identity_masked: str | None = None
    push_name: str | None = None
    qr_available: bool = False
    #: The provider is reachable and reports it holds no session under the configured name
    #: (QR-09-D2). Derived from a live observation, never persisted — the durable pairing record is
    #: the platform's own truth and is deliberately left untouched by this observation.
    provider_session_missing: bool = False
    updated_at: datetime | None = None


#: Pairing states that can only be resolved by a human re-pairing — mirrors
#: `app.channels.waha.recovery`'s `_REAUTH_PAIRING` exactly. `UNPAIRED` is deliberately excluded:
#: it is the idle starting state of every fresh session (first-ever connect, or the new revision
#: `logout()` registers) and is resolved by starting pairing, not by "re-authenticating" — folding
#: it into this set stops `deriveViewState` from ever reaching "creating-session" and its
#: "Begin pairing" action after `connect()`, a dead end caught live in the QR-07 UI preview.
_REAUTH_PAIRING = frozenset({PairingState.PAIRING_EXPIRED, PairingState.PAIRING_CANCELLED})


class _ProviderObservation(StrEnum):
    """What the current status read actually learned from the provider.

    This is deliberately internal.  Durable session state and current provider reachability are
    separate facts, and collapsing both into the old ``provider_session_missing`` boolean made a
    transport outage indistinguishable from a successful observation (QR-09-D8).
    """

    NOT_OBSERVED = "not_observed"
    OBSERVED = "observed"
    SESSION_MISSING = "session_missing"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class WhatsAppQrService:
    """Organization-scoped façade over the WAHA adapter and the existing session control plane."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        providers: ProviderRegistry,
        runtimes: ProviderRuntimeRegistry,
        adapter: WahaChannelAdapter | None = None,
    ) -> None:
        self._session = session
        self._connections = ChannelConnectionRepository(session)
        self._sessions = ChannelSessionRepository(session)
        self._session_manager = SessionManager(session, providers=providers)
        self._flags = ChannelFeatureFlagResolver(session)
        self._rbac = RBACService(session)
        self._runtimes = runtimes
        self._adapter = adapter or WahaChannelAdapter()

    # --- Read ------------------------------------------------------------------------------

    async def get_status(self, *, organization_id: int, actor: User) -> WhatsAppQrState:
        """Read current status, live-reconciling durable state under the session's own lease.

        A live provider check on every read keeps the screen honest without a background poller;
        WAHA's own reads are cheap and this is a low-traffic admin surface. Reconciliation never
        claims a pairing state the live status cannot determine (see the module docstring).
        """
        if not await self._available(organization_id, actor, require=READ_PERMISSION):
            return WhatsAppQrState(configured=False)

        row, connection = await self._current(organization_id)
        if row is None or connection is None:
            return WhatsAppQrState(configured=True, health_detail="WhatsApp is not connected yet.")

        # Another request may be reconciling right now; report the last-known durable state
        # rather than failing a read for lease contention.
        observation = _ProviderObservation.NOT_OBSERVED
        with suppress(ConflictError):
            observation = await self._reconcile(
                organization_id=organization_id, actor=actor, row=row
            )
        row = await self._sessions.get_scoped(organization_id, uuidlib.UUID(row.public_id))
        assert row is not None
        return self._state_from_row(row, provider_observation=observation)

    # --- Bootstrap ---------------------------------------------------------------------------

    async def connect(self, *, organization_id: int, actor: User) -> WhatsAppQrState:
        """Idempotently ensure a durable connection/session exists. Does not begin pairing."""

        if not self._provider_configured():
            raise ConflictError("WAHA is not configured on this deployment.")
        if organization_id != self._organization_scope():
            raise ForbiddenError("WhatsApp QR connection is not assigned to this organization.")
        await self._require_permission(actor, OPERATE_PERMISSION)

        row, connection = await self._current(organization_id)
        if row is not None:
            assert connection is not None
            await self._ensure_endpoint(organization_id, actor, connection)
            return self._state_from_row(row)

        if connection is None:
            connection = await ChannelConnectionService(self._session).create_connection(
                organization_id=organization_id,
                actor=actor,
                channel_family=ChannelType.WHATSAPP.value,
                connector_type=CONNECTOR_WAHA,
                display_name="WhatsApp (WAHA)",
                provider_connection_id=self._adapter.client.credentials.session or None,
                desired_state=ProviderDesiredState.ENABLED,
                capability_snapshot=_SESSION_CAPABILITIES,
            )
        await self._ensure_endpoint(organization_id, actor, connection)

        row = await self._session_manager.register_session(
            organization_id=organization_id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            capability_references=_SESSION_CAPABILITIES,
        )
        return self._state_from_row(row)

    async def _ensure_endpoint(
        self, organization_id: int, actor: User, connection: ChannelConnection
    ) -> None:
        """Idempotently give the connection its one addressable identity (QR-08).

        The Inbox needs a durable, stable owner to link a WAHA conversation/message to — exactly
        what ``channel_endpoints`` (M13-03) exists for, and exactly what QR-07 never created because
        nothing needed it yet. The WAHA session name is used as ``provider_endpoint_id`` rather than
        the paired phone number: it is known immediately (before any pairing) and stays stable across
        a logout/re-pair cycle, unlike the phone number behind it — WAHA is a single, session-scoped
        endpoint for the deployment's lifetime, not one per paired number.
        """
        endpoints = await ChannelEndpointRepository(self._session).list_for_connection(
            organization_id, connection.id
        )
        if endpoints:
            return
        session_name = self._provider_session_name()
        await ChannelConnectionService(self._session).create_endpoint(
            organization_id=organization_id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            endpoint_type="whatsapp_qr",
            normalized_address=session_name,
            provider_endpoint_id=session_name,
            display_name="WhatsApp (WAHA)",
            enabled=True,
        )

    # --- Pairing -----------------------------------------------------------------------------

    async def begin_pairing(self, *, organization_id: int, actor: User) -> WhatsAppQrState:
        """Create/start the WAHA session and mark pairing as requested, then available."""

        row = await self._require_row(organization_id, actor, permission=OPERATE_PERMISSION)

        # QR-09-D10: first-time pairing and its expired-QR recovery are for connections that have
        # never been paired. A durably PAIRED connection belongs to the reconnect/re-authentication
        # and logout paths, which own credential-bearing state deliberately — routing it here could
        # restart a live pairing to raise an unrequested QR. `PairingState.PAIRED` is terminal in
        # `LEGAL_PAIRING_TRANSITIONS`, so this refusal states an existing invariant rather than
        # inventing one. The adapter refuses a provider-reported linked account as well; this is the
        # durable half of the same guard, and it is checked before any provider call.
        if PairingState(row.pairing_state) is PairingState.PAIRED:
            raise ConflictError(
                "This connection is already paired. Log out first to link a different account."
            )

        # QR-09-D9: a durable session that was paused (the automatic reaction to an observed
        # STOPPED provider status) can never be leased again, so pairing — the only action that
        # can move a never-paired connection forward — used to fail with "the session is paused
        # and cannot acquire a runtime lease" while `reconnect()` simultaneously told the operator
        # to pair. That left the connection unrecoverable without direct database intervention.
        #
        # This reuses the exact control-plane pattern `reconnect()` already established: PAUSED ->
        # INITIALIZING is a legal, lease-free governed transition that puts the row back into a
        # leasable state, after which the normal lease/mutate path below runs unchanged. The
        # `SessionManager` invariant that a PAUSED row cannot be leased is deliberately left
        # untouched — this leaves PAUSED first, it does not lease a paused row.
        #
        # Narrow by design: `PairingState.PAIRED` is the only state meaning credentials were ever
        # established, it is terminal in `LEGAL_PAIRING_TRANSITIONS`, and a paused paired session
        # is the reconnect/re-authentication domain (`can_reconnect` covers exactly that pair).
        # Such a session keeps the pre-existing refusal below rather than being quietly restarted
        # as a first-time pairing.
        if (
            SessionState(row.state) is SessionState.PAUSED
            and PairingState(row.pairing_state) is not PairingState.PAIRED
        ):
            row = await self._session_manager.transition_session(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(row.public_id),
                expected_row_version=row.row_version,
                target_state=SessionState.INITIALIZING,
            )

        lease = await self._session_manager.acquire_lock(
            organization_id=organization_id,
            actor=actor,
            public_id=uuidlib.UUID(row.public_id),
            runtime_id=self._request_runtime_id(),
            lease_seconds=self._lease_seconds(),
            expected_row_version=row.row_version,
        )
        try:
            snapshot = await self._adapter.prepare_pairing(
                self._provider_session_name(), lease=self._waha_lease(row, lease)
            )
            row = await self._apply_snapshot(
                organization_id=organization_id,
                actor=actor,
                row=row,
                lease_runtime_id=lease.holder_runtime_id,
                fencing_token=lease.fencing_token,
                snapshot=snapshot,
                request_pairing=True,
            )
        except ChannelTransportError as exc:
            # The provider genuinely could not be reached.
            raise ServiceUnavailableError(
                "WhatsApp couldn't be reached to start pairing. Try again in a moment."
            ) from exc
        except ChannelApiError as exc:
            # The provider *was* reached and refused (QR-09-D10). Reporting that as an outage sent
            # the operator to wait out a problem that was not happening, and hid the real state.
            # The provider's own message is deliberately not echoed: it is remote text, and the
            # operator needs their next action rather than the provider's wording.
            raise ConflictError(
                "WhatsApp refused to start pairing for this connection. Refresh the connection "
                "status and try again."
            ) from exc
        except ChannelError as exc:
            # Configuration/authentication/capability failures keep their existing truthful
            # semantics rather than being reclassified by this milestone.
            raise ServiceUnavailableError(
                "WhatsApp couldn't be reached to start pairing. Try again in a moment."
            ) from exc
        finally:
            await self._release(organization_id, actor, row, lease)
        row = await self._refetch(organization_id, row)
        return self._state_from_row(row)

    async def qr_image(self, *, organization_id: int, actor: User) -> WahaQrChallenge:
        """Fetch the transient QR. Never persisted, never logged, returned exactly once per call."""

        row = await self._require_row(organization_id, actor, permission=OPERATE_PERMISSION)
        if PairingState(row.pairing_state) is not PairingState.PAIRING_AVAILABLE:
            raise ConflictError("No QR is currently available; refresh the connection status.")
        try:
            return await self._adapter.pairing_challenge(self._provider_session_name())
        except ChannelApiError as exc:
            raise ConflictError(str(exc)) from exc

    # --- Reconnect ---------------------------------------------------------------------------

    async def reconnect(self, *, organization_id: int, actor: User) -> WhatsAppQrState:
        row = await self._require_row(organization_id, actor, permission=OPERATE_PERMISSION)

        # Live-plan first, with no lease held: this is a read-only check and must be cheap to
        # repeat (the frontend disables the button on `can_reconnect`, and the API re-validates).
        try:
            decision = await self._adapter.plan_session_recovery(
                self._provider_session_name(),
                durable_pairing_state=PairingState(row.pairing_state),
                attempts=row.reconnect_attempts,
                max_attempts=row.max_reconnect_attempts,
            )
        except WahaSessionNotFound as exc:
            # There is nothing to reconnect *to*: QR-06 restarts an existing session, and the
            # provider holds none. Refusing explicitly is the truthful answer, and it keeps this
            # path from silently recreating a session or raising an unhandled 500 (QR-09-D2).
            raise ConflictError(
                "WhatsApp no longer has this connection's session, so there is nothing to "
                "reconnect. Pair the connection again to link an account."
            ) from exc
        if decision is ReconnectDecision.CONNECTED:
            return self._state_from_row(row)
        if decision is not ReconnectDecision.RECONNECT:
            raise ConflictError(f"Reconnect is not currently possible: {decision.value}.")

        # `SessionManager.acquire_lock` refuses to lease a PAUSED session outright (a durable
        # invariant, not a QR-07 choice) — a paused session must leave PAUSED before it can be
        # driven. PAUSED -> INITIALIZING is legal without a lease (`channels:manage`), and puts
        # the row in a leasable state for the actual reconnect attempt that follows.
        if SessionState(row.state) is SessionState.PAUSED:
            row = await self._session_manager.transition_session(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(row.public_id),
                expected_row_version=row.row_version,
                target_state=SessionState.INITIALIZING,
            )

        lease = await self._session_manager.acquire_lock(
            organization_id=organization_id,
            actor=actor,
            public_id=uuidlib.UUID(row.public_id),
            runtime_id=self._request_runtime_id(),
            lease_seconds=self._lease_seconds(),
            expected_row_version=row.row_version,
        )
        try:
            snapshot = await self._adapter.reconnect_session(
                self._provider_session_name(), lease=self._waha_lease(row, lease)
            )
            row = await self._apply_snapshot(
                organization_id=organization_id,
                actor=actor,
                row=row,
                lease_runtime_id=lease.holder_runtime_id,
                fencing_token=lease.fencing_token,
                snapshot=snapshot,
                request_pairing=False,
            )
        except ChannelError as exc:
            raise ServiceUnavailableError(
                "WhatsApp couldn't be reached to reconnect. Try again in a moment."
            ) from exc
        finally:
            await self._release(organization_id, actor, row, lease)
        row = await self._refetch(organization_id, row)
        return self._state_from_row(row)

    # --- Logout (destructive, explicit) --------------------------------------------------------

    async def logout(self, *, organization_id: int, actor: User, confirm: bool) -> WhatsAppQrState:
        """Invalidate WhatsApp credentials. Requires explicit confirmation; never auto-triggered.

        ``PairingState.PAIRED`` is terminal in the existing pairing state machine — by design, a
        pairing attempt does not reverse, it retires (the same rule that requires a *new session
        revision* to re-authenticate an expired one). Logout therefore does not try to walk the
        current row backwards: it terminates this revision, recording that it was explicitly
        logged out, and registers a fresh ``UNPAIRED`` revision for the same connection so a new
        pairing attempt can begin. The returned identity is the new revision's.
        """

        if not confirm:
            raise ConflictError("Logout requires explicit confirmation.")
        row = await self._require_row(organization_id, actor, permission=OPERATE_PERMISSION)
        connection_id = row.connection_id
        lease = await self._session_manager.acquire_lock(
            organization_id=organization_id,
            actor=actor,
            public_id=uuidlib.UUID(row.public_id),
            runtime_id=self._request_runtime_id(),
            lease_seconds=self._lease_seconds(),
            expected_row_version=row.row_version,
        )
        try:
            await self._adapter.logout_session(
                self._provider_session_name(), lease=self._waha_lease(row, lease)
            )
            row = await self._session_manager.transition_session(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(row.public_id),
                expected_row_version=row.row_version,
                target_state=SessionState.TERMINATED,
                detail="Logged out by operator; credentials invalidated.",
                runtime_id=lease.holder_runtime_id,
                fencing_token=lease.fencing_token,
            )
        except ChannelError as exc:
            # Do not claim a local "logged out" success we can't back up with a confirmed remote
            # invalidation — the same honesty rule the rest of this module follows.
            raise ServiceUnavailableError(
                "WhatsApp couldn't be reached to log out. Try again in a moment."
            ) from exc
        finally:
            await self._release(organization_id, actor, row, lease)

        connection = await self._connections.get_by_id(connection_id)
        assert connection is not None
        new_row = await self._session_manager.register_session(
            organization_id=organization_id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            capability_references=_SESSION_CAPABILITIES,
        )
        return self._state_from_row(new_row)

    # --- Internal --------------------------------------------------------------------------

    async def _reconcile(
        self, *, organization_id: int, actor: User, row: ChannelSession
    ) -> _ProviderObservation:
        """Reconcile durable state against one live provider read.

        Returns a typed current observation so the response can distinguish a reachable provider,
        a missing provider session and an unreachable provider. Two live outcomes deliberately
        mutate nothing:

        * :class:`ChannelTransportError` — the provider could not be reached, so there is no
          observation to reconcile from (QR-06: an outage must never rewrite pairing truth).
        * :class:`WahaSessionNotFound` — the provider *was* reached and holds no such session
          (QR-09-D2). The durable record is still the platform's own truth about what was paired,
          so it is preserved verbatim; the caller is told about the divergence instead, and decides
          how to present it. Nothing here recreates the session, starts pairing, or requests a QR —
          re-establishing a session stays an explicit operator action.
        """
        try:
            lease = await self._session_manager.acquire_lock(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(row.public_id),
                runtime_id=self._request_runtime_id(),
                lease_seconds=self._lease_seconds(),
                expected_row_version=row.row_version,
            )
        except ConflictError:
            # The row cannot be driven right now — it is PAUSED (QR-09-D9), or another runtime
            # genuinely holds the lease. Reading the provider is not a mutation, so refusing to
            # look was what left a paused never-paired session projecting stale metadata forever
            # and reporting an outage that was not happening. Observe read-only instead.
            return await self._observe_without_lease()

        try:
            try:
                snapshot = await self._adapter.session_snapshot(self._provider_session_name())
            except WahaSessionNotFound:
                return _ProviderObservation.SESSION_MISSING
            except ChannelTransportError:
                return _ProviderObservation.PROVIDER_UNAVAILABLE
            await self._apply_snapshot(
                organization_id=organization_id,
                actor=actor,
                row=row,
                lease_runtime_id=lease.holder_runtime_id,
                fencing_token=lease.fencing_token,
                snapshot=snapshot,
                request_pairing=False,
            )
            return _ProviderObservation.OBSERVED
        finally:
            await self._release(organization_id, actor, row, lease)

    async def _observe_without_lease(self) -> _ProviderObservation:
        """Read the provider without holding a lease, reporting only non-mutating facts.

        Used when the durable row cannot be leased at all (QR-09-D9). A missing session and an
        unreachable provider are both facts that need no durable write, so reporting them keeps
        the status honest — that is what lets the operator see the real recovery action instead of
        a permanent, untrue "WhatsApp can't be reached".

        A *successful* observation is deliberately downgraded to ``NOT_OBSERVED``: applying it
        requires the very lease that could not be taken, and this module's rule is that nothing
        claims a state it cannot reconcile. Nothing here creates, starts or mutates provider or
        durable state — it is a read.
        """
        try:
            await self._adapter.session_snapshot(self._provider_session_name())
        except WahaSessionNotFound:
            return _ProviderObservation.SESSION_MISSING
        except ChannelTransportError:
            return _ProviderObservation.PROVIDER_UNAVAILABLE
        return _ProviderObservation.NOT_OBSERVED

    async def _apply_snapshot(
        self,
        *,
        organization_id: int,
        actor: User,
        row: ChannelSession,
        lease_runtime_id: str,
        fencing_token: int,
        snapshot: WahaSessionSnapshot,
        request_pairing: bool,
    ) -> ChannelSession:
        """Apply one live snapshot to durable state, ordered so `PairingManager` never refuses.

        `PairingManager` only accepts a pairing transition while the session is still
        INITIALIZING/WAITING_FOR_PAIRING (Doc's own pairing-session-state guard). That makes the
        ordering state-dependent rather than fixed:

        * Reaching a *non-ACTIVE* session target (INITIALIZING, WAITING_FOR_PAIRING, ...) must
          happen **before** the pairing step, because pairing may need that state to have already
          arrived (e.g. requesting pairing needs INITIALIZING to exist first).
        * Reaching ACTIVE must happen **after** the pairing step, because pairing can only land
          (e.g. PAIRING_AVAILABLE -> PAIRED) while the session is still WAITING_FOR_PAIRING —
          advancing to ACTIVE first would make that transition (correctly) refuse.
        """
        target_session_state, target_pairing_state = map_session_status(snapshot.status)
        session_args = (organization_id, actor, lease_runtime_id, fencing_token)
        provider_confirmed_pairing = (
            snapshot.status is WahaSessionStatus.WORKING
            and snapshot.identity is not None
            and snapshot.name == self._provider_session_name()
        )

        if target_session_state is not SessionState.ACTIVE:
            row = await self._advance_session(row, target_session_state, *session_args)
            row = await self._advance_pairing(
                row,
                target_pairing_state,
                request_pairing,
                provider_confirmed_pairing,
                *session_args,
            )
        else:
            row = await self._advance_pairing(
                row,
                target_pairing_state,
                request_pairing,
                provider_confirmed_pairing,
                *session_args,
            )
            row = await self._advance_session(row, target_session_state, *session_args)

        row.provider_metadata_json = {
            "provider_status": snapshot.status.value,
            "identity": snapshot.identity,
            "lid": snapshot.lid,
            "push_name": snapshot.push_name,
        }
        row.health_state = "healthy" if snapshot.connected else "degraded"
        row.health_observed_at = utcnow()
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._session.commit()
        return row

    async def _advance_session(
        self,
        row: ChannelSession,
        target: SessionState,
        organization_id: int,
        actor: User,
        lease_runtime_id: str,
        fencing_token: int,
    ) -> ChannelSession:
        current = SessionState(row.state)
        if target is current or not self._can_advance_session(current, target):
            return row
        return await self._session_manager.transition_session(
            organization_id=organization_id,
            actor=actor,
            public_id=uuidlib.UUID(row.public_id),
            expected_row_version=row.row_version,
            target_state=target,
            runtime_id=lease_runtime_id,
            fencing_token=fencing_token,
        )

    async def _advance_pairing(
        self,
        row: ChannelSession,
        target: PairingState | None,
        request_pairing: bool,
        provider_confirmed_pairing: bool,
        organization_id: int,
        actor: User,
        lease_runtime_id: str,
        fencing_token: int,
    ) -> ChannelSession:
        current = PairingState(row.pairing_state)

        if request_pairing and current is PairingState.UNPAIRED:
            row = await self._pairing_manager().transition_pairing(
                organization_id=organization_id,
                actor=actor,
                session_public_id=uuidlib.UUID(row.public_id),
                runtime_id=lease_runtime_id,
                fencing_token=fencing_token,
                expected_row_version=row.row_version,
                target_state=PairingState.PAIRING_REQUESTED,
            )
            current = PairingState.PAIRING_REQUESTED

        # Ambiguous live status (target is None) never overwrites durable truth — the QR-02/QR-06
        # safety rule enforced at the one place that could regress it.
        if target is None:
            return row

        # QR-09-D11: an explicit operator refresh that has successfully obtained current provider
        # evidence of SCAN_QR_CODE renews the short-lived human pairing window. This is deliberately
        # not a PAIRING_AVAILABLE self-transition, and ordinary GET reconciliation passes
        # request_pairing=False so it can never make a QR immortal.
        if (
            request_pairing
            and current is PairingState.PAIRING_AVAILABLE
            and target is PairingState.PAIRING_AVAILABLE
        ):
            return await self._pairing_manager().renew_pairing_availability(
                organization_id=organization_id,
                actor=actor,
                session_public_id=uuidlib.UUID(row.public_id),
                runtime_id=lease_runtime_id,
                fencing_token=fencing_token,
                expected_row_version=row.row_version,
            )

        if target is current or not self._can_advance_pairing(current, target):
            return row

        # A provider-authenticated WORKING snapshot with identity is authoritative proof that the
        # scan succeeded. The local TTL governs the QR representation, not the provider session;
        # accept this one narrow expired-window completion under the same current lease/fence.
        if (
            current is PairingState.PAIRING_AVAILABLE
            and target is PairingState.PAIRED
            and (row.pairing_expires_at is None or row.pairing_expires_at <= utcnow())
            and provider_confirmed_pairing
        ):
            return await self._pairing_manager().complete_provider_confirmed_pairing(
                organization_id=organization_id,
                actor=actor,
                session_public_id=uuidlib.UUID(row.public_id),
                runtime_id=lease_runtime_id,
                fencing_token=fencing_token,
                expected_row_version=row.row_version,
                provider_identity_present=True,
            )

        expires_at = None
        if target is PairingState.PAIRING_AVAILABLE:
            ttl = self._runtimes.require(CONNECTOR_WAHA).pairing_ttl_seconds
            expires_at = utcnow() + timedelta(seconds=ttl)
        return await self._pairing_manager().transition_pairing(
            organization_id=organization_id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id=lease_runtime_id,
            fencing_token=fencing_token,
            expected_row_version=row.row_version,
            target_state=target,
            expires_at=expires_at,
        )

    @staticmethod
    def _can_advance_session(current: SessionState, target: SessionState) -> bool:
        from app.channels.session import can_transition

        return can_transition(current, target)

    @staticmethod
    def _can_advance_pairing(current: PairingState, target: PairingState) -> bool:
        from app.channels.runtime import can_transition_pairing

        return can_transition_pairing(current, target)

    @staticmethod
    def _waha_lease(row: ChannelSession, lease: object) -> WahaRuntimeLease:
        """Translate the real M13-05 DB lease into the adapter's own lease proof (QR-06).

        The adapter's :func:`~app.channels.waha.recovery.assert_lease_current` check is a
        lightweight non-``None`` guard by design (see its own docstring) — the durable
        enforcement is the DB lease this wraps, acquired moments earlier via
        :meth:`SessionManager.acquire_lock`.
        """
        from app.channels.session import SessionLease

        assert isinstance(lease, SessionLease)
        return WahaRuntimeLease(
            session_public_id=row.public_id,
            runtime_id=lease.holder_runtime_id,
            fencing_token=lease.fencing_token,
        )

    async def _release(
        self, organization_id: int, actor: User, row: ChannelSession, lease: object
    ) -> None:
        from app.channels.session import SessionLease

        assert isinstance(lease, SessionLease)
        try:
            fresh = await self._sessions.get_scoped(organization_id, uuidlib.UUID(row.public_id))
            if fresh is None or fresh.holder_runtime_id != lease.holder_runtime_id:
                return
            await self._session_manager.release_lock(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(row.public_id),
                runtime_id=lease.holder_runtime_id,
                fencing_token=lease.fencing_token,
                expected_row_version=fresh.row_version,
            )
        except ConflictError:
            # The lease already expired or moved on; nothing to release.
            pass

    def _pairing_manager(self) -> PairingManager:
        from app.services.pairing_manager import PairingManager

        return PairingManager(self._session, runtimes=self._runtimes)

    async def _refetch(self, organization_id: int, row: ChannelSession) -> ChannelSession:
        """Re-read a row after a service call that may have committed a new revision.

        A small helper rather than repeating the null-check at every call site: the row is known
        to exist (we just transitioned it), so the assertion documents that invariant once.
        """
        fresh = await self._sessions.get_scoped(organization_id, uuidlib.UUID(row.public_id))
        assert fresh is not None
        return fresh

    def _state_from_row(
        self,
        row: ChannelSession,
        *,
        provider_observation: _ProviderObservation = _ProviderObservation.NOT_OBSERVED,
    ) -> WhatsAppQrState:
        session_state = SessionState(row.state)
        pairing_state = PairingState(row.pairing_state)
        metadata = row.provider_metadata_json or {}
        provider_status = metadata.get("provider_status")
        connected = session_state is SessionState.ACTIVE and pairing_state is PairingState.PAIRED
        requires_reauth = pairing_state in _REAUTH_PAIRING

        live_provider_status: WahaSessionStatus | None = None
        if provider_observation is _ProviderObservation.OBSERVED and provider_status is not None:
            with suppress(ValueError):
                live_provider_status = WahaSessionStatus(provider_status)

        decision = plan_reconnect(
            provider_status=live_provider_status,
            durable_pairing_state=pairing_state,
            attempts=row.reconnect_attempts,
            max_attempts=row.max_reconnect_attempts,
        )
        can_reconnect = session_state in (SessionState.PAUSED, SessionState.DEGRADED) and (
            pairing_state is PairingState.PAIRED
        )
        blocked_reason = (
            None
            if can_reconnect
            else (
                decision.value
                if provider_observation is _ProviderObservation.OBSERVED
                else ReconnectDecision.WAIT.value
            )
        )
        healthy = row.health_state == "healthy"
        health_detail = row.state_detail or f"Session state: {session_state.value}."
        qr_available = (
            pairing_state is PairingState.PAIRING_AVAILABLE
            and provider_status == WahaSessionStatus.SCAN_QR_CODE.value
        )
        provider_session_missing = provider_observation is _ProviderObservation.SESSION_MISSING

        if provider_session_missing:
            # The provider answered and holds no session under the configured name (QR-09-D2).
            # Every live-derived signal below is corrected to say so, while the durable pairing
            # record itself is left exactly as it was — this is a projection, not a state change.
            #
            # The distinction that matters to an operator is whether credentials were lost:
            #   * durable PAIRED  -> the account really was linked and the provider no longer holds
            #                        it, so a fresh scan is genuinely required.
            #   * anything else   -> nothing was linked yet; this is the ordinary "connect and pair"
            #                        path, not a re-authentication.
            # Reconnect is refused either way: QR-06 restarts an existing session, and there is no
            # session here to restart. Nothing auto-creates one.
            credentials_lost = pairing_state is PairingState.PAIRED
            connected = False
            healthy = False
            provider_status = None
            qr_available = False
            can_reconnect = False
            requires_reauth = requires_reauth or credentials_lost
            blocked_reason = "provider_session_missing"
            health_detail = (
                "WhatsApp is reachable but no longer has this connection's session, so the linked "
                "account must be paired again by scanning a new QR code."
                if credentials_lost
                else "WhatsApp is reachable but has no session for this connection yet; "
                "start the connection and scan the QR code to link an account."
            )
        elif provider_observation is _ProviderObservation.PROVIDER_UNAVAILABLE:
            # Current action availability fails closed while durable lifecycle truth remains
            # untouched. In particular, stale PAIRING_AVAILABLE/provider metadata must not claim
            # that the binary QR endpoint can answer while the provider cannot be reached.
            connected = False
            healthy = False
            provider_status = None
            qr_available = False
            can_reconnect = False
            blocked_reason = ReconnectDecision.PROVIDER_UNAVAILABLE.value
            health_detail = "WhatsApp is temporarily unavailable. Try again shortly."

        return WhatsAppQrState(
            configured=True,
            session_public_id=row.public_id,
            row_version=row.row_version,
            session_state=session_state,
            pairing_state=pairing_state,
            provider_status=provider_status,
            connected=connected,
            requires_reauthentication=requires_reauth,
            healthy=healthy,
            health_detail=health_detail,
            can_reconnect=can_reconnect,
            reconnect_blocked_reason=blocked_reason,
            identity_masked=_mask_identity(metadata.get("identity")),
            push_name=metadata.get("push_name"),
            qr_available=qr_available,
            provider_session_missing=provider_session_missing,
            updated_at=row.health_observed_at,
        )

    async def _current(
        self, organization_id: int
    ) -> tuple[ChannelSession | None, ChannelConnection | None]:
        connections = await self._connections.list_scoped(organization_id)
        connection = next((c for c in connections if c.connector_type == CONNECTOR_WAHA), None)
        if connection is None:
            return None, None
        row = await self._sessions.get_current_for_connection(organization_id, connection.id)
        return row, connection

    async def _require_row(
        self, organization_id: int, actor: User, *, permission: str
    ) -> ChannelSession:
        if not await self._available(organization_id, actor, require=permission):
            raise NotFoundError("WhatsApp connection is not available for this organization.")
        row, connection = await self._current(organization_id)
        if row is None or connection is None:
            raise NotFoundError("WhatsApp is not connected yet.")
        return row

    async def _available(self, organization_id: int, actor: User, *, require: str) -> bool:
        if not self._provider_configured():
            return False
        if organization_id != self._organization_scope():
            return False
        if actor.organization_id != organization_id or not actor.is_active:
            return False
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER):
            return False
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_READ):
            return False
        return await self._rbac.has_permissions(actor, {require})

    async def _require_permission(self, actor: User, permission: str) -> None:
        if not await self._rbac.has_permissions(actor, {permission}):
            raise ForbiddenError("The actor cannot manage the WhatsApp QR connection.")

    def _provider_configured(self) -> bool:
        return self._adapter.configured and self._organization_scope() is not None

    def _organization_scope(self) -> int | None:
        from app.core.config import settings

        return settings.waha_organization_id

    def _provider_session_name(self) -> str:
        return self._adapter.client.credentials.session

    @staticmethod
    def _lease_seconds() -> int:
        return 60

    @staticmethod
    def _request_runtime_id() -> str:
        return f"api:whatsapp-qr:{uuidlib.uuid4()}"
