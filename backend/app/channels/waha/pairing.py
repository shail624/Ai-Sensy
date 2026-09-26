"""WAHA QR pairing contracts — QR-03.

QR-02 could *observe* a session's lifecycle. QR-03 adds the ability to *begin* one: create a session
configured the way certification proved is required, and retrieve the QR challenge a handset scans.

## What QR-03 deliberately does not add

Stopping, restarting and logging out are **QR-06** (`SESSION_RECONNECT`/`SESSION_LOGOUT`); webhook
ingestion is QR-04; sending is QR-05. QR-03 adds exactly two provider writes/reads beyond QR-02 —
create a session, and fetch its QR — because that is the whole of "authenticate by QR".

## The QR challenge is never persisted and never logged

M13-05's pairing manager records lifecycle facts, expiry and a machine reason code only: "QR images,
challenge bytes, login material and provider credentials are deliberately absent." QR-03 honours
that boundary rather than widening it. :class:`WahaQrChallenge` is therefore a transient value —
it carries raw image bytes, redacts itself in ``repr``, and nothing in this package writes it to a
row, a log or an audit payload. A scanned QR is a live credential: anyone who photographs it can
link their own device.

## Why the store configuration lives here

Certification established that ``fullSync`` must be spelled in **camelCase** at session creation.
The provider accepts ``full_sync`` with HTTP 201 and then silently stores ``fullSync: false``, so a
session created with the snake_case spelling looks healthy and quietly has no history. That is a
silent-failure trap, so the payload is built in one place and asserted by test rather than being
retyped per call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from app.channels.errors import ChannelConfigError

#: Session configuration proven correct by physical-phone certification.
#:
#: ``fullSync`` is camelCase on purpose — see the module docstring. Do not "normalise" this to
#: snake_case: the provider will accept it and silently disable history.
CERTIFIED_NOWEB_STORE: Final[dict[str, Any]] = {
    "noweb": {"store": {"enabled": True, "fullSync": True}}
}


def build_session_config() -> dict[str, Any]:
    """Return a fresh copy of the certified session configuration.

    A copy, so a caller mutating the result cannot corrupt the module-level constant for every
    subsequent pairing attempt.
    """

    store = CERTIFIED_NOWEB_STORE["noweb"]["store"]
    return {"noweb": {"store": dict(store)}}


@dataclass(frozen=True, slots=True)
class WahaQrChallenge:
    """A transient QR challenge for one session.

    **Not** a durable record. The bytes are a live linking credential: whoever scans them pairs a
    device to the WhatsApp account. They are held only long enough to reach the operator surface
    that displays them, and are deliberately absent from persistence, logs and audit payloads.
    """

    session: str
    mimetype: str
    data: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not self.data:
            raise ChannelConfigError("QR challenge is empty")

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        """Render size and type only — never the challenge itself."""
        return (
            f"WahaQrChallenge(session={self.session!r}, mimetype={self.mimetype!r}, "
            f"size_bytes={self.size_bytes}, data=***withheld***)"
        )

    def __str__(self) -> str:
        return self.__repr__()
