"""Provider-neutral session lifecycle and lease contracts for M13-04.

The module defines durable control-plane vocabulary only. It does not generate QR codes, pair a
provider account, open a live provider session, synchronize messages, or perform provider I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SessionState(StrEnum):
    """Provider-neutral durable session lifecycle."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    WAITING_FOR_PAIRING = "waiting_for_pairing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    PAUSED = "paused"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class SessionRestartPolicy(StrEnum):
    """Durable restart intent; execution belongs to a later runtime milestone."""

    NEVER = "never"
    ON_FAILURE = "on_failure"
    ALWAYS = "always"


SESSION_TERMINAL_STATES = frozenset({SessionState.EXPIRED, SessionState.TERMINATED})

LEGAL_SESSION_TRANSITIONS: dict[SessionState, frozenset[SessionState]] = {
    SessionState.REGISTERED: frozenset(
        {
            SessionState.INITIALIZING,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.INITIALIZING: frozenset(
        {
            SessionState.WAITING_FOR_PAIRING,
            SessionState.ACTIVE,
            SessionState.DEGRADED,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.WAITING_FOR_PAIRING: frozenset(
        {
            SessionState.INITIALIZING,
            SessionState.ACTIVE,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.ACTIVE: frozenset(
        {
            SessionState.DEGRADED,
            SessionState.RECONNECTING,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.DEGRADED: frozenset(
        {
            SessionState.ACTIVE,
            SessionState.RECONNECTING,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.RECONNECTING: frozenset(
        {
            SessionState.ACTIVE,
            SessionState.DEGRADED,
            SessionState.PAUSED,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.PAUSED: frozenset(
        {
            SessionState.INITIALIZING,
            SessionState.ACTIVE,
            SessionState.EXPIRED,
            SessionState.TERMINATED,
        }
    ),
    SessionState.EXPIRED: frozenset({SessionState.INITIALIZING, SessionState.TERMINATED}),
    SessionState.TERMINATED: frozenset(),
}


def can_transition(current: SessionState, target: SessionState) -> bool:
    """Return whether the provider-neutral state machine permits the transition."""

    return target in LEGAL_SESSION_TRANSITIONS[current]


@dataclass(frozen=True, slots=True)
class SessionLease:
    """Lease evidence returned to the runtime holder; it contains no provider secret."""

    session_public_id: str
    holder_runtime_id: str
    fencing_token: int
    lease_expires_at: datetime
    session_revision: int
