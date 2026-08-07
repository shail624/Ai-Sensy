"""WAHA session lifecycle vocabulary and provider-neutral mapping — QR-02.

QR-01 could only ask the WAHA *server* whether it was alive. QR-02 adds the next honest step: read
one **session's** lifecycle status and translate it into the provider-neutral vocabulary the
platform already owns (:class:`~app.channels.session.SessionState` and
:class:`~app.channels.runtime.PairingState`).

## What this module is not

It is a **translation table, not a runtime**. Nothing here starts, stops, restarts, pairs, logs out
or supervises a session; those are QR-03 (QR/pairing) and QR-06 (reconnect/health). Nothing here
persists anything — the durable authority remains ``channel_sessions``.

## Why some statuses refuse to claim a pairing state

The certified build reports session status only. For three of the five statuses that is genuinely
not enough to know whether WhatsApp credentials exist, so this module returns ``None`` rather than
guessing:

* ``STARTING`` is emitted both when a brand-new session boots *and* when an already-paired session
  resumes. Physical-phone certification observed both paths — ``STARTING → SCAN_QR_CODE`` on a fresh
  session, and ``STARTING → WORKING`` on a controlled restart with no new QR. The status alone
  therefore cannot distinguish "never paired" from "paired and reconnecting".
* ``STOPPED`` means the session is not running; it says nothing about whether stored credentials
  survived, because a stopped session and a logged-out session both stop.
* ``FAILED`` is a generic failure. Certification reached it by letting a QR lapse unscanned, but the
  status does not encode *why*, so inferring ``PAIRING_EXPIRED`` from it would promote one observed
  cause into a universal rule.

Returning ``None`` lets the caller keep the pairing state it already holds. Inventing a state here
would silently overwrite durable truth with a guess.

## Why an unknown status fails closed

An unrecognised status is a provider contract change. The adapter is certified against exactly one
build, and the engine guard already refuses unapproved engines for the same reason: a mapping that
quietly degraded unknown input to "something safe-looking" would let an uncertified provider state
flow into session persistence. See :func:`map_session_status`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from app.channels.errors import ChannelApiError, ChannelConfigError
from app.channels.runtime import PairingState
from app.channels.session import SessionState

#: A session name is interpolated into a request path, so it is validated as a strict identifier
#: rather than escaped. Anything outside this alphabet — a slash, a dot segment, whitespace, a
#: query character — is rejected before a URL is built, so no caller can steer the request at
#: another endpoint.
_SESSION_NAME: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_session_name(value: str) -> str:
    """Validate a WAHA session name before it reaches a request path."""

    candidate = value.strip()
    if not _SESSION_NAME.fullmatch(candidate):
        raise ChannelConfigError(
            "WAHA session name must be 1-64 characters of letters, digits, '-' or '_' "
            "and start with a letter or digit"
        )
    return candidate


class WahaSessionStatus(StrEnum):
    """Session statuses observed on the certified build (2026.7.2 / NOWEB / CORE).

    Every member was seen during physical-phone certification, not read off documentation.
    """

    STARTING = "STARTING"
    SCAN_QR_CODE = "SCAN_QR_CODE"
    WORKING = "WORKING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


#: WAHA session status → provider-neutral lifecycle.
#:
#: ``FAILED`` maps to ``DEGRADED`` rather than ``EXPIRED`` deliberately: ``EXPIRED`` is terminal
#: (``SESSION_TERMINAL_STATES``), and certification proved a ``FAILED`` session recovers through a
#: controlled restart. Marking it terminal would strand a session the provider can still revive.
_LIFECYCLE: Final[dict[WahaSessionStatus, tuple[SessionState, PairingState | None]]] = {
    WahaSessionStatus.STARTING: (SessionState.INITIALIZING, None),
    WahaSessionStatus.SCAN_QR_CODE: (
        SessionState.WAITING_FOR_PAIRING,
        PairingState.PAIRING_AVAILABLE,
    ),
    WahaSessionStatus.WORKING: (SessionState.ACTIVE, PairingState.PAIRED),
    WahaSessionStatus.FAILED: (SessionState.DEGRADED, None),
    WahaSessionStatus.STOPPED: (SessionState.PAUSED, None),
}


def parse_session_status(value: object) -> WahaSessionStatus:
    """Parse a provider status string, failing closed on anything uncertified."""

    if isinstance(value, str):
        try:
            return WahaSessionStatus(value.strip().upper())
        except ValueError:
            pass
    known = ", ".join(sorted(status.value for status in WahaSessionStatus))
    # The raw value is not interpolated: it is provider output of unknown provenance.
    raise ChannelApiError(
        f"WAHA reported an uncertified session status; this deployment maps only: {known}"
    )


def map_session_status(
    status: WahaSessionStatus,
) -> tuple[SessionState, PairingState | None]:
    """Translate one certified WAHA status into provider-neutral lifecycle facts.

    Returns ``(session_state, pairing_state)`` where ``pairing_state`` is ``None`` when the status
    genuinely does not determine it — see the module docstring. Pure: no I/O, no persistence, and
    no dependence on call order, so it cannot regress durable state.
    """

    return _LIFECYCLE[status]


@dataclass(frozen=True, slots=True)
class WahaSessionSnapshot:
    """One point-in-time reading of a WAHA session.

    A *reading*, not a durable record. ``identity``/``lid`` are the provider's account identifiers
    for the paired WhatsApp account and are personal data: they cross the seam so the platform can
    correlate an endpoint, and must never be logged.

    Certification proved the same account is addressed as both ``@c.us`` and ``@lid`` depending on
    the surface, which is why both are carried rather than one being normalised away here.
    """

    name: str
    status: WahaSessionStatus
    engine: str | None = None
    identity: str | None = None
    lid: str | None = None
    push_name: str | None = None

    @property
    def session_state(self) -> SessionState:
        """Provider-neutral durable-lifecycle equivalent of :attr:`status`."""
        return map_session_status(self.status)[0]

    @property
    def pairing_state(self) -> PairingState | None:
        """Provider-neutral pairing equivalent, or ``None`` when the status cannot determine it."""
        return map_session_status(self.status)[1]

    @property
    def connected(self) -> bool:
        """Whether this session can actually carry WhatsApp traffic right now.

        Only ``WORKING`` qualifies. A reachable server, a booting session and a session showing a QR
        are all *not* connected, and reporting otherwise would let a caller conclude it can message.
        """
        return self.status is WahaSessionStatus.WORKING

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> WahaSessionSnapshot:
        """Build a snapshot from ``GET /api/sessions/{name}``, failing closed on unknown status.

        Shapes follow the certified build: ``engine`` is a nested object (``{"engine": "NOWEB"}``)
        and ``me`` is ``null`` until a session is paired.
        """
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ChannelApiError("WAHA session response is missing 'name'")

        engine_field = body.get("engine")
        engine: str | None = None
        if isinstance(engine_field, dict):
            nested = engine_field.get("engine")
            engine = nested if isinstance(nested, str) else None
        elif isinstance(engine_field, str):
            engine = engine_field

        me = body.get("me")
        identity = lid = push_name = None
        if isinstance(me, dict):
            raw_id = me.get("id")
            raw_lid = me.get("lid")
            raw_push = me.get("pushName")
            identity = raw_id if isinstance(raw_id, str) else None
            lid = raw_lid if isinstance(raw_lid, str) else None
            push_name = raw_push if isinstance(raw_push, str) else None

        return cls(
            name=name,
            status=parse_session_status(body.get("status")),
            engine=engine,
            identity=identity,
            lid=lid,
            push_name=push_name,
        )
