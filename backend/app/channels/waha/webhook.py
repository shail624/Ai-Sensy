"""WAHA webhook verification and event normalization — QR-04.

QR-03 could pair a session. QR-04 accepts the events that session produces: verify the delivery is
authentic, translate it into the platform's canonical :class:`InboundEvent` vocabulary, and hand it
to the **existing** ingest authority (``WebhookService`` → ``webhook_events``). No parallel ingest
path, no second dedupe store, no provider vocabulary downstream.

## Signature is checked before anything is parsed

:func:`verify_signature` takes the **raw body**, because that is what the provider signed — any
re-serialisation would change the bytes and break verification. The comparison is constant-time,
an absent or malformed signature is a rejection rather than a bypass, and an oversized body is
refused before it is hashed so an unauthenticated caller cannot force unbounded work.

## Why ``envelope.id`` alone cannot be the dedupe key

Physical-phone certification established three facts that together rule it out:

* delivery is **at-least-once** — a retry is normal, not an error;
* a retry repeats *both* ``envelope.id`` and ``X-Webhook-Request-Id``, so neither distinguishes a
  first delivery from a redelivery;
* the same underlying provider message is delivered as **both** ``message`` and ``message.any``
  **sharing one ``envelope.id``**.

Deduplicating on ``envelope.id`` alone would therefore silently discard a genuine second event type.
:func:`event_identity` scopes the key by session **and** provider event type, so a retry of the same
event collapses while two distinct event types over one message both survive. The session component
keeps two tenants' sessions from ever colliding on a provider-chosen id.

## Identity is a digest, not a truncated concatenation

An earlier version of :func:`event_identity` built ``f"waha:{session}:{event_type}:{envelope_id}"``
and sliced it to 128 characters — the width of ``webhook_events.event_id`` — believing that placing
``envelope_id`` last made it "survive truncation". That was backwards: Python's ``s[:128]`` keeps the
**left** prefix and discards everything past index 128, which is exactly where the last-placed
component lives. A long enough ``session``/``event_type`` pushed ``envelope_id`` partly or entirely
past the cut, so two genuinely different events could produce an identical stored key — a verified
collision, reproduced in ``test_channel_waha_webhook.py`` before the fix and proven absent after it.
The same concatenation was independently ambiguous even at short lengths: plain ``":"`` delimiters
let one component's content be mistaken for another's boundary (``session="tenant", event_type="a:b"``
collided with ``session="tenant:a", event_type="b"``).

:func:`event_identity` now hashes a **length-prefixed** (netstring-style) canonical encoding of all
three full components with SHA-256, and returns ``"waha:" + hexdigest`` — a fixed 69 characters,
always within the 128-character column, independent of how long any component is. Each component is
preceded by its own exact character count before a literal boundary marker, so a decoder could always
recover the original three strings unambiguously: no value any component holds — colons, pipes, digit
runs designed to mimic a length prefix — can shift where one component ends and the next begins. This
makes the digest not merely "unlikely to collide" but constructively injective over the encoding, on
top of SHA-256 collision resistance. ``hashlib.sha256`` is used rather than Python's built-in
``hash()``, which is randomized per process (``PYTHONHASHSEED``) and would make the key
non-reproducible across processes, threads or a restart.

## Unknown shapes fail closed, but are not dropped

An event type this milestone does not interpret becomes :attr:`InboundEventType.UNKNOWN` rather than
being skipped: Doc 06 §11.6 isolates unknown events to the dead-letter queue for inspection, and
that requires the adapter to *emit* them. Silently dropping provider traffic is how ingestion gaps
hide.

## Identity is reported, never normalised away

Certification proved one account is addressed as ``@c.us``, ``@lid`` and ``@s.whatsapp.net``
depending on the surface. This module preserves whatever the provider sent and additionally exposes
the canonical trailing provider message id, which certification proved stable across send response,
webhook, history and acknowledgement. It performs no global provider-message lookup.
"""

from __future__ import annotations

import hmac
from hashlib import sha256, sha512
from typing import Any, Final

from app.channels.models import InboundEvent, InboundEventType, InboundMessage

#: Header carrying the provider's HMAC over the raw request body.
SIGNATURE_HEADER: Final = "X-Webhook-Hmac"
#: Header naming the algorithm; the certified build sends ``sha512``.
ALGORITHM_HEADER: Final = "X-Webhook-Hmac-Algorithm"
#: The only algorithm this deployment accepts. Certification observed sha512; accepting whatever the
#: payload names would let a caller downgrade the check.
APPROVED_ALGORITHM: Final = "sha512"

#: Largest body accepted before verification. A webhook delivery is small; anything larger is
#: refused rather than hashed, so an unauthenticated caller cannot force unbounded work.
MAX_BODY_BYTES: Final = 1_048_576

#: Provider event names QR-04 interprets. Everything else becomes ``UNKNOWN`` (dead-lettered).
EVENT_MESSAGE: Final = "message"
EVENT_MESSAGE_ANY: Final = "message.any"
_INBOUND_MESSAGE_EVENTS: Final[frozenset[str]] = frozenset({EVENT_MESSAGE, EVENT_MESSAGE_ANY})


class WahaBodyTooLarge(ValueError):
    """The delivery exceeded :data:`MAX_BODY_BYTES` and was refused before hashing."""


def verify_signature(body: bytes, signature: str | None, secret: str, *, algorithm: str | None = None) -> bool:
    """Return whether ``body`` carries a valid provider HMAC.

    Fails closed on: an empty secret (an unconfigured deployment must never accept unsigned
    traffic), a missing or non-hex signature, an algorithm other than the approved one, and an
    oversized body. The comparison is constant-time so a mismatch leaks no timing information.
    """

    if len(body) > MAX_BODY_BYTES:
        raise WahaBodyTooLarge(
            f"WAHA webhook body exceeds {MAX_BODY_BYTES} bytes and was refused before hashing"
        )
    if not secret:
        # An unconfigured secret must reject, never accept. Returning True here would make an
        # unset environment variable a silent authentication bypass.
        return False
    if not signature:
        return False
    if algorithm is not None and algorithm.strip().lower() != APPROVED_ALGORITHM:
        return False
    expected = hmac.new(secret.encode(), body, sha512).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


def canonical_message_id(raw: object) -> str | None:
    """The stable trailing component of a provider message id, or ``None``.

    Certification proved the composite form varies (``true_<addr>@c.us_<ID>`` in history versus
    ``...@lid_<ID>`` in an acknowledgement) while the trailing ``<ID>`` stays constant across send
    response, webhook, history and ACK. That trailing value is the correlation key; the full
    composite is preserved separately rather than being discarded.
    """

    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.rsplit("_", 1)[-1] or None


def _canonicalize(*parts: str) -> bytes:
    """Length-prefix each part so no adversarial content can forge a component boundary.

    Each component is written as ``"<char-count>:<content>"`` followed by ``"|"``. Because the
    prefix is the component's own exact length, decoding is unambiguous regardless of what
    characters the component contains — including delimiters this scheme itself uses. Two distinct
    tuples of parts can never canonicalize to the same bytes (see the module docstring).
    """

    encoded = "".join(f"{len(part)}:{part}|" for part in parts)
    return encoded.encode("utf-8")


def event_identity(*, session: str, event_type: str, envelope_id: str) -> str:
    """Build the dedupe key for one provider event.

    Scoped by session **and** event type because certification proved ``envelope.id`` alone is not
    unique — see the module docstring. The key is a fixed-length SHA-256 digest over all three full
    components (never truncated, never delimiter-ambiguous — see the module docstring), so it
    always fits well within the 128 characters ``webhook_events.event_id`` stores no matter how long
    ``session``, ``event_type`` or ``envelope_id`` are.
    """

    digest = sha256(_canonicalize(session, event_type, envelope_id)).hexdigest()
    return f"waha:{digest}"


def _text_content(payload: dict[str, Any]) -> dict[str, Any] | None:
    body = payload.get("body")
    if not isinstance(body, str) or not body:
        return None
    return {"body": body}


def parse_events(delivery: dict[str, Any]) -> list[InboundEvent]:
    """One verified WAHA delivery → canonical events.

    The delivery envelope carries ``id``, ``event``, ``session``, ``me``, ``payload`` and
    ``timestamp``. A delivery whose envelope is unusable — no session, or no event name — yields a
    single ``UNKNOWN`` event so it is dead-lettered for inspection rather than vanishing.
    """

    envelope_id = delivery.get("id")
    event_type = delivery.get("event")
    session = delivery.get("session")

    session_name = session if isinstance(session, str) and session.strip() else None
    type_name = event_type if isinstance(event_type, str) and event_type.strip() else None
    envelope = envelope_id if isinstance(envelope_id, str) and envelope_id.strip() else None

    if session_name is None or type_name is None or envelope is None:
        # Deliberately no event_id: nothing here is trustworthy enough to dedupe on, and a
        # fabricated key could collapse two genuinely different malformed deliveries.
        return [
            InboundEvent(
                event_id=None,
                type=InboundEventType.UNKNOWN,
                channel_number_id=session_name or "",
                payload=delivery,
                occurred_at=None,
            )
        ]

    payload = delivery.get("payload")
    payload_obj: dict[str, Any] = payload if isinstance(payload, dict) else {}

    if type_name in _INBOUND_MESSAGE_EVENTS and payload_obj.get("fromMe") is False:
        kind = InboundEventType.MESSAGES
    else:
        # Includes outbound echoes (``fromMe`` true), acknowledgements and session events. QR-04
        # does not interpret delivery state — that is QR-05 — so they are recorded, not applied.
        kind = InboundEventType.UNKNOWN

    return [
        InboundEvent(
            event_id=event_identity(
                session=session_name, event_type=type_name, envelope_id=envelope
            ),
            type=kind,
            channel_number_id=session_name,
            payload=delivery,
            occurred_at=None,
        )
    ]


def to_inbound_message(delivery: dict[str, Any]) -> InboundMessage:
    """A verified ``MESSAGES`` delivery → the message it represents.

    Only text is translated at QR-04; media ingestion is a later milestone, so a media delivery is
    reported as its provider type with no content rather than being silently rendered as an empty
    text message.
    """

    payload = delivery.get("payload")
    payload_obj: dict[str, Any] = payload if isinstance(payload, dict) else {}

    raw_id = payload_obj.get("id")
    canonical = canonical_message_id(raw_id)
    if canonical is None:
        raise ValueError("WAHA inbound message has no usable provider message id")

    sender = payload_obj.get("from")
    from_id = sender if isinstance(sender, str) and sender.strip() else ""

    push_name = payload_obj.get("notifyName") or payload_obj.get("pushName")
    profile_name = push_name if isinstance(push_name, str) and push_name.strip() else None

    content = _text_content(payload_obj)
    if content is None:
        message_type = "unsupported"
        content = {"provider_has_media": bool(payload_obj.get("hasMedia"))}
    else:
        message_type = "text"

    timestamp = payload_obj.get("timestamp")
    occurred_at = None
    if isinstance(timestamp, int | float) and timestamp > 0:
        from datetime import UTC, datetime

        occurred_at = datetime.fromtimestamp(float(timestamp), tz=UTC)

    return InboundMessage(
        channel_message_id=canonical,
        from_id=from_id,
        message_type=message_type,
        content=content,
        profile_name=profile_name,
        occurred_at=occurred_at,
    )
