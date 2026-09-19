"""Operator-facing session attention projection (Doc 33 §6.1 "Health").

Design Document 33 requires the control plane to be able to represent four operator-facing
signals: **Healthy**, **Warning**, **Critical** and **Re-authentication Required**. The stored
:class:`~app.channels.foundation.ProviderHealthState` vocabulary supplies the first three
(``healthy``/``degraded``/``unhealthy``, plus ``unknown``) but has no re-auth value.

That gap is closed here by **derivation, not by a new stored state**. Re-authentication-required is
not an independent observation a provider reports — it is a *consequence* of the durable session
lifecycle this repository already models and already constrains:
:class:`~app.channels.session.SessionState` and :class:`~app.channels.runtime.PairingState`. Adding
a fourth persisted health value would duplicate information those two columns already carry, widen
three ``CHECK`` constraints (``channel_connections``, ``channel_endpoints``, ``channel_sessions``),
and create states that could disagree with one another. A pure projection cannot drift.

Nothing here is provider-specific: it reads only the frozen provider-neutral state machines, so a
Meta connection, a QR connection and any future adapter all project through the same rules.
"""

from __future__ import annotations

from enum import StrEnum

from app.channels.foundation import ProviderHealthState
from app.channels.runtime import PairingState
from app.channels.session import SessionState


class SessionAttentionState(StrEnum):
    """What an operator must be shown about a session (Doc 33 §6.1).

    Distinct from :class:`ProviderHealthState`, which is the *observed* provider health that gets
    persisted. This is the derived, actionable view layered on top of it.
    """

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    REAUTH_REQUIRED = "reauth_required"


#: Session states that can only be resolved by an authorized human re-pairing the session.
#: ``WAITING_FOR_PAIRING`` is an active request for a scan; ``EXPIRED`` is a session whose material
#: is no longer usable and which the provider will not recover on its own.
_REAUTH_SESSION_STATES: frozenset[SessionState] = frozenset(
    {SessionState.WAITING_FOR_PAIRING, SessionState.EXPIRED}
)

#: Pairing outcomes that leave the session unusable until a fresh pairing attempt is started.
#: A lapsed or cancelled attempt is not a provider fault and will not self-heal.
_REAUTH_PAIRING_STATES: frozenset[PairingState] = frozenset(
    {PairingState.PAIRING_EXPIRED, PairingState.PAIRING_CANCELLED}
)

#: Observed provider health → operator signal. ``degraded``/``unhealthy`` are renamed to the
#: Doc 33 §6.1 vocabulary; the underlying stored values are unchanged.
_HEALTH_PROJECTION: dict[ProviderHealthState, SessionAttentionState] = {
    ProviderHealthState.UNKNOWN: SessionAttentionState.UNKNOWN,
    ProviderHealthState.HEALTHY: SessionAttentionState.HEALTHY,
    ProviderHealthState.DEGRADED: SessionAttentionState.WARNING,
    ProviderHealthState.UNHEALTHY: SessionAttentionState.CRITICAL,
}


def requires_reauthentication(
    *, session_state: SessionState | str, pairing_state: PairingState | str
) -> bool:
    """Whether this session can only be restored by an authorized operator re-pairing it.

    ``TERMINATED`` is deliberately excluded: a terminated session was ended on purpose and is
    finished, not broken. Surfacing it as "needs re-authentication" would invite an operator to
    re-pair a connection somebody intentionally shut down. It is checked first so a terminated
    session never inherits a re-auth signal from a stale pairing value.
    """
    session = SessionState(session_state)
    pairing = PairingState(pairing_state)

    if session is SessionState.TERMINATED:
        return False
    if session in _REAUTH_SESSION_STATES:
        return True
    return pairing in _REAUTH_PAIRING_STATES


def project_attention_state(
    *,
    health_state: ProviderHealthState | str,
    session_state: SessionState | str,
    pairing_state: PairingState | str,
) -> SessionAttentionState:
    """Project stored health + session lifecycle into the operator-facing signal.

    Re-authentication **outranks** observed health on purpose. A session awaiting a scan may still
    be reported ``unknown`` or ``degraded`` by its provider, but the only useful thing to tell an
    operator is that it needs re-pairing — the specific, actionable state must not be masked by a
    vaguer one.
    """
    if requires_reauthentication(session_state=session_state, pairing_state=pairing_state):
        return SessionAttentionState.REAUTH_REQUIRED
    return _HEALTH_PROJECTION[ProviderHealthState(health_state)]
