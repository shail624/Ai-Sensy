"""WAHA session recovery, health projection and teardown — QR-06.

QR-03 could bring a session **up**; QR-06 is the first milestone that may take one **down** and
bring it back. That asymmetry ended here deliberately, so this module carries the safety rules that
make destructive lifecycle operations survivable.

## Reconnect never guesses from an ambiguous provider status

QR-02 established, from physical-phone certification, that ``STARTING`` is genuinely ambiguous:

* a **fresh** session goes ``STARTING → SCAN_QR_CODE`` (it has no credentials);
* an **already-paired** session goes ``STARTING → WORKING`` (it has credentials and is resuming).

The provider status alone therefore cannot distinguish "never paired" from "paired and
reconnecting", and ``STOPPED``/``FAILED`` are equally undetermined. :func:`plan_reconnect` is driven
by the **durable** pairing truth the platform already owns, never by the provider status alone. A
session whose durable state is not ``PAIRED`` is never auto-restarted as if it were: restarting an
unpaired session cannot restore anything, and would present a QR nobody asked for.

## Provider unavailability must not destroy durable truth

If the provider cannot be reached, the correct answer is "unknown", not "unpaired". A transport
failure yields :attr:`ReconnectDecision.PROVIDER_UNAVAILABLE`, which explicitly instructs the caller
to leave durable pairing state alone and retry later. Overwriting a real pairing because a container
was briefly down is exactly the data loss this milestone must not cause.

## Reconnect is bounded

:func:`plan_reconnect` refuses once ``attempts`` reaches ``max_attempts``, and
:func:`backoff_delay` grows exponentially to a ceiling. Together they prevent a reconnect storm
against a provider that is already struggling. The delay is a pure function of the attempt number,
so it is identical in every worker and needs no shared coordination.

## Stop and logout are not the same thing

* **STOP** halts the session. Stored WhatsApp credentials may survive, so a stopped session can
  often be started again without a new scan.
* **LOGOUT** invalidates the credentials at WhatsApp. Certification proved the observable result:
  ``WORKING → SCAN_QR_CODE`` with ``me=null`` and the QR endpoint answering again. That is
  re-authentication-required truth, and it is the *intended* outcome of a logout rather than a
  failure to be repaired.

Collapsing the two would let a routine restart silently unpair a customer's WhatsApp account, so
they are separate operations with separate capabilities and separate durable meanings.

## Ownership is the existing lease, not a new one

This module invents no runtime ownership. :class:`RuntimeLease` is a value object describing a lease
the existing session authority already issued (``ChannelSession`` lease/fencing, driven by
``SessionManager``/``ProviderRuntimeManager``). :func:`assert_lease_current` refuses any mutation
whose fencing token is not the session's current one, so a worker that lost its lease — or slept
through a takeover — cannot start, stop, log out, or write health over a newer owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.channels.capabilities import CONNECTOR_WAHA, Capability, ChannelType
from app.channels.errors import ChannelConfigError
from app.channels.foundation import ChannelMetadata
from app.channels.models import HealthSignal
from app.channels.registry import ProviderRegistry
from app.channels.runtime import PairingState, RuntimeMetadata
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionState
from app.channels.waha.lifecycle import WahaSessionSnapshot, WahaSessionStatus

#: Capabilities the WAHA runtime may declare. Mirrors the adapter's own declared set — a runtime
#: may never advertise more than the provider implements, and ``ProviderRuntimeRegistry`` enforces
#: exactly that on registration.
WAHA_RUNTIME_CAPABILITIES: Final[frozenset[Capability]] = frozenset(
    {
        Capability.HEALTH,
        Capability.QR_AUTH,
        Capability.SESSION_STREAM,
        Capability.TEXT,
        Capability.SESSION_RECONNECT,
        Capability.SESSION_LOGOUT,
    }
)

#: Maximum automatic reconnect attempts before a session is left for an operator. Bounded so a
#: provider that is down cannot be hammered indefinitely.
DEFAULT_MAX_RECONNECT_ATTEMPTS: Final = 5
#: First backoff step, in seconds.
BASE_BACKOFF_SECONDS: Final = 2.0
#: Ceiling for a single backoff step, in seconds.
MAX_BACKOFF_SECONDS: Final = 60.0


class ReconnectDecision(StrEnum):
    """What a supervisor may safely do next for one session."""

    #: Already usable — nothing to do.
    CONNECTED = "connected"
    #: Durable truth says paired and the provider is idle/failed: a restart is safe.
    RECONNECT = "reconnect"
    #: The provider is mid-transition. Wait; do not mutate.
    WAIT = "wait"
    #: Only an authorized human re-pairing can resolve this. Never auto-repaired.
    REQUIRES_REAUTH = "requires_reauth"
    #: Bounded attempts exhausted; escalate rather than keep retrying.
    ATTEMPTS_EXHAUSTED = "attempts_exhausted"
    #: The provider could not be reached. Durable state must be left untouched.
    PROVIDER_UNAVAILABLE = "provider_unavailable"


#: Durable pairing states from which an automatic restart can possibly help. Anything else either
#: has no credentials to restore or is an explicit human-driven pairing flow.
_RESTORABLE_PAIRING: Final[frozenset[PairingState]] = frozenset({PairingState.PAIRED})

#: Durable pairing states that only an operator can resolve.
_REAUTH_PAIRING: Final[frozenset[PairingState]] = frozenset(
    {
        PairingState.PAIRING_EXPIRED,
        PairingState.PAIRING_CANCELLED,
        PairingState.UNPAIRED,
    }
)


def backoff_delay(attempt: int, *, base: float = BASE_BACKOFF_SECONDS) -> float:
    """Bounded exponential backoff for reconnect attempt ``attempt`` (0-based).

    A pure function of the attempt number: every worker computes the same delay without shared
    state, and the ceiling keeps a long outage from producing an unbounded wait.
    """

    if attempt < 0:
        raise ChannelConfigError("attempt must be zero or positive")
    return float(min(base * (2**attempt), MAX_BACKOFF_SECONDS))


def plan_reconnect(
    *,
    provider_status: WahaSessionStatus | None,
    durable_pairing_state: PairingState,
    attempts: int = 0,
    max_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS,
) -> ReconnectDecision:
    """Decide what may safely be done for one session.

    ``provider_status`` is ``None`` when the provider could not be reached — deliberately distinct
    from any observed status, because "unknown" must never be treated as "unpaired".

    The durable pairing state is consulted **before** the provider status, so an ambiguous
    ``STARTING`` can never be read as evidence that a session is unpaired.
    """

    if provider_status is None:
        return ReconnectDecision.PROVIDER_UNAVAILABLE

    if provider_status is WahaSessionStatus.WORKING:
        # Usable regardless of attempt count; never "exhaust" a session that is actually fine.
        return ReconnectDecision.CONNECTED

    if durable_pairing_state in _REAUTH_PAIRING:
        # No credentials to restore. Restarting would present a QR nobody asked for.
        return ReconnectDecision.REQUIRES_REAUTH

    if provider_status is WahaSessionStatus.SCAN_QR_CODE:
        # The provider is actively asking for a scan: an operator must act, not a supervisor.
        return ReconnectDecision.REQUIRES_REAUTH

    if provider_status is WahaSessionStatus.STARTING:
        # Ambiguous by construction (see the module docstring). Never mutate mid-transition.
        return ReconnectDecision.WAIT

    if durable_pairing_state not in _RESTORABLE_PAIRING:
        # Indeterminate durable truth (e.g. a pairing attempt in flight): refuse to guess.
        return ReconnectDecision.WAIT

    if attempts >= max_attempts:
        return ReconnectDecision.ATTEMPTS_EXHAUSTED

    # STOPPED or FAILED with a durable PAIRED record: a restart can genuinely restore the session.
    return ReconnectDecision.RECONNECT


@dataclass(frozen=True, slots=True)
class RuntimeLease:
    """A lease the existing session authority already issued.

    Not a new ownership system — this only carries the identifiers needed to prove the caller is
    still the current holder. Issuing, extending and revoking leases remain the job of
    ``SessionManager``/``ProviderRuntimeManager`` against ``channel_sessions``.
    """

    session_public_id: str
    runtime_id: str
    fencing_token: int

    def __post_init__(self) -> None:
        if not self.session_public_id.strip():
            raise ChannelConfigError("session_public_id is required")
        if not self.runtime_id.strip():
            raise ChannelConfigError("runtime_id is required")
        if self.fencing_token <= 0:
            raise ChannelConfigError("fencing_token must be a positive integer")


class StaleRuntimeLease(ChannelConfigError):
    """A mutation was attempted by a worker that no longer owns the session."""


def assert_lease_current(
    lease: RuntimeLease,
    *,
    current_runtime_id: str | None,
    current_fencing_token: int,
) -> None:
    """Refuse any lifecycle mutation from a worker that is not the current lease holder.

    Guards start, stop, logout and health writes alike. A worker that was paused past a takeover
    must not resume and overwrite the newer owner's state, so both the holder identity **and** the
    fencing token must match: a token alone would let a re-claimed session accept a stale writer
    that happened to hold the same number.
    """

    if current_runtime_id is None or current_runtime_id != lease.runtime_id:
        raise StaleRuntimeLease(
            "This runtime no longer holds the session lease; refusing to mutate session state."
        )
    if current_fencing_token != lease.fencing_token:
        raise StaleRuntimeLease(
            "Fencing token is stale; the session has been claimed by a newer owner."
        )


def waha_channel_metadata() -> ChannelMetadata:
    """Provider metadata describing what the WAHA runtime manages.

    ``lifecycle_managed``/``health_managed`` are what
    :meth:`~app.channels.runtime_registry.ProviderRuntimeRegistry.register` requires before a
    runtime may declare lifecycle or health capabilities — true only now that QR-06 actually
    implements them.
    """

    return ChannelMetadata(
        connector_type=CONNECTOR_WAHA,
        channel_type=ChannelType.WHATSAPP,
        display_name="WAHA (QR)",
        capabilities=WAHA_RUNTIME_CAPABILITIES,
        lifecycle_managed=True,
        health_managed=True,
    )


def waha_runtime_metadata() -> RuntimeMetadata:
    """Runtime-host facts for the WAHA provider.

    Registration is **opt-in**: nothing in this package registers it automatically. Importing the
    package still adds no runtime, so a deployment that has not configured WAHA keeps exactly the
    inert behaviour QR-01 established. ``register_waha_runtime`` is the explicit entry point.
    """

    return RuntimeMetadata(
        connector_type=CONNECTOR_WAHA,
        display_name="WAHA (QR)",
        capabilities=WAHA_RUNTIME_CAPABILITIES,
        pairing_managed=True,
        pairing_ttl_seconds=60,
        heartbeat_interval_seconds=30,
        lease_seconds=60,
    )


def register_waha_runtime(
    providers: ProviderRegistry,
    runtimes: ProviderRuntimeRegistry,
    *,
    replace: bool = False,
) -> None:
    """Explicitly register the WAHA provider and runtime metadata.

    Deliberately not called at import time. A runtime registration means "a supervisor may drive
    this provider's sessions", which is a deployment decision, not a side effect of importing a
    module — and every milestone through QR-05 guaranteed that merely importing the package
    registers no runtime.
    """

    providers.register(waha_channel_metadata(), replace=replace)
    runtimes.register(waha_runtime_metadata(), replace=replace)


def project_health(snapshot: WahaSessionSnapshot | None) -> HealthSignal:
    """Provider-neutral health for one session.

    ``healthy`` means **this WhatsApp session can carry traffic**, which is true only for
    ``WORKING``. A reachable WAHA server with no working session is explicitly *not* healthy: QR-01
    established that server health and session health are different facts, and conflating them would
    tell an operator a dead channel is fine.

    ``None`` — provider unreachable — is unhealthy and reported as unknown rather than being
    optimistically treated as fine.
    """

    if snapshot is None:
        return HealthSignal(
            healthy=False,
            detail="WAHA session state is unknown: the provider could not be reached.",
        )

    session_state = snapshot.session_state
    pairing_state = snapshot.pairing_state
    connected = snapshot.status is WahaSessionStatus.WORKING

    if session_state is SessionState.WAITING_FOR_PAIRING:
        # Re-auth outranks generic health: an operator must scan, and no amount of provider
        # uptime changes that.
        return HealthSignal(
            healthy=False,
            detail=(
                "WAHA session requires re-authentication: the provider is awaiting a QR scan "
                f"(provider status={snapshot.status.value})."
            ),
        )

    detail = (
        f"WAHA session status={snapshot.status.value}, "
        f"session_state={session_state.value}, "
        f"pairing_state={pairing_state.value if pairing_state else 'indeterminate'}"
    )
    return HealthSignal(healthy=connected, detail=detail)
