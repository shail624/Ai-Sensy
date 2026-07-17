"""Meta's inbound webhook: signature, handshake & payload normalization (Doc 04 §23, Doc 06 §11).

The only module that understands what Meta *sends*, mirroring :mod:`app.channels.meta.adapter`,
which is the only one that understands what Meta *accepts*. Everything here turns a Graph delivery
into the canonical :class:`~app.channels.models.InboundEvent` list the platform ingests, so the
webhook endpoint, the queue and the processor never learn a Graph shape (Doc 07 §5.3/§18.2).

Every function is **pure and synchronous**: they run on the request path that must persist and ack
in <200 ms (Doc 06 §11.2), so nothing here may touch the network or the database.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.channels.errors import ChannelConfigError, ChannelError
from app.channels.models import InboundEvent, InboundEventType, InboundMessage, StatusUpdate

#: Header carrying the HMAC-SHA256 of the raw body (Doc 04 §10/§23).
SIGNATURE_HEADER = "X-Hub-Signature-256"
_SIGNATURE_PREFIX = "sha256="

#: Meta's subscription handshake parameters (`GET` with `hub.*`).
_HUB_MODE = "hub.mode"
_HUB_TOKEN = "hub.verify_token"
_HUB_CHALLENGE = "hub.challenge"
_SUBSCRIBE = "subscribe"

#: The `object` Meta stamps on a WhatsApp delivery; anything else is not ours to interpret.
_OBJECT = "whatsapp_business_account"


class MetaWebhookPayloadError(ChannelError):
    """The body was signed by Meta but is not a delivery envelope we can read.

    Rare in practice (a signed body is a Meta body), so it means a contract change rather than an
    attack — the event is persisted and isolated to the DLQ for a human, never dropped (§11.6).
    """


def verify_signature(body: bytes, signature: str | None, *, app_secret: str) -> bool:
    """HMAC-SHA256 the **raw** body with the app secret and compare in constant time.

    The raw bytes matter: re-serializing parsed JSON changes whitespace/key order and would break
    an authentic signature. A missing secret is a configuration fault, not a rejected request —
    silently answering 403 to every event would look exactly like an attack while being our bug.
    """
    if not app_secret:
        raise ChannelConfigError(
            "Meta app secret is not configured; set META_APP_SECRET to accept webhooks."
        )
    if not signature or not signature.startswith(_SIGNATURE_PREFIX):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[len(_SIGNATURE_PREFIX) :].strip())


def challenge(params: Mapping[str, str], *, verify_token: str) -> str | None:
    """Meta's subscription handshake — return ``hub.challenge`` iff the verify token matches."""
    if not verify_token:
        raise ChannelConfigError(
            "Webhook verify token is not configured; set META_WEBHOOK_VERIFY_TOKEN."
        )
    if params.get(_HUB_MODE) != _SUBSCRIBE:
        return None
    if not hmac.compare_digest(params.get(_HUB_TOKEN) or "", verify_token):
        return None
    return params.get(_HUB_CHALLENGE) or None


def _occurred_at(timestamp: Any) -> datetime | None:
    """Meta sends unix seconds as a string. Stored UTC-naive like every other time (Doc 03 §1.3)."""
    try:
        return datetime.fromtimestamp(int(timestamp), UTC).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def parse(payload: dict[str, Any]) -> list[InboundEvent]:
    """Graph delivery → canonical events (Doc 06 §11.2 step 4's input).

    One delivery batches several entries/changes, and one change batches several messages and
    statuses. Each becomes its own event so it can be deduped, routed, replayed and dead-lettered
    on its own — a single poison message never blocks the rest of the batch (§11.6).
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("entry"), list):
        raise MetaWebhookPayloadError("not a Meta webhook envelope: no 'entry' list")
    if payload.get("object") != _OBJECT:
        raise MetaWebhookPayloadError(f"unexpected webhook object {payload.get('object')!r}")

    events: list[InboundEvent] = []
    for entry in payload["entry"]:
        if not isinstance(entry, dict):
            continue
        # Meta identifies the entry by WABA id; it is context for the event, not our routing key.
        waba_id = entry.get("id")
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            events.extend(_change_events(change, waba_id))
    if not events:
        raise MetaWebhookPayloadError("Meta envelope carried no entries/changes")
    return events


#: Meta's message `type` → Doc 03 ``messages.message_type``. The vocabularies agree except where
#: noted, so this is a guard against drift rather than a translation table: an unlisted type passes
#: through, because FR-WA-06 ingests **all** inbound types and refusing an unknown one would lose a
#: real customer message over a name we had not seen yet.
_MESSAGE_TYPE = {"button": "interactive"}

#: Meta's status names → Doc 03 ``messages.status``. Identical today; mapped explicitly so a Meta
#: rename cannot silently become an unknown state in the ledger.
_STATUS = {
    "sent": "sent",
    "delivered": "delivered",
    "read": "read",
    "failed": "failed",
}

#: Graph nests media under its own type key with these fields (Doc 03 ``content_json``).
_MEDIA_TYPES = ("image", "video", "audio", "document", "sticker")


class MetaMessageError(ChannelError):
    """A stored event's payload is not the message/status shape it was recorded as."""


def to_inbound_message(payload: dict[str, Any]) -> InboundMessage:
    """A stored ``MESSAGES`` payload → canonical :class:`InboundMessage`."""
    message = (payload or {}).get("message")
    if not isinstance(message, dict) or not message.get("id"):
        raise MetaMessageError("payload carries no Meta message object")

    native_type = str(message.get("type") or "unknown")
    message_type = _MESSAGE_TYPE.get(native_type, native_type)
    # The sender's profile arrives beside the message, not inside it.
    contacts = payload.get("contacts") or []
    profile = (contacts[0].get("profile") or {}) if contacts else {}

    return InboundMessage(
        channel_message_id=str(message["id"]),
        from_id=str(message.get("from") or ""),
        message_type=message_type[:20],
        content=_content(native_type, message),
        profile_name=profile.get("name"),
        occurred_at=_occurred_at(message.get("timestamp")),
    )


def _content(native_type: str, message: dict[str, Any]) -> dict[str, Any]:
    """Graph message body → canonical ``content_json`` (Doc 03 §9.2).

    Canonical means *ours*: a caption is a caption on every channel, and a media reference is a
    reference the media pipeline resolves later — never Graph's nesting.
    """
    if native_type == "text":
        return {"body": (message.get("text") or {}).get("body", "")}

    if native_type in _MEDIA_TYPES:
        obj = message.get(native_type) or {}
        return {
            "media": {
                "channel_media_id": obj.get("id"),
                "mime_type": obj.get("mime_type"),
                "sha256": obj.get("sha256"),
                "caption": obj.get("caption"),
                "filename": obj.get("filename"),
            }
        }

    if native_type == "location":
        return {"location": message.get("location") or {}}
    if native_type == "contacts":
        return {"contacts": message.get("contacts") or []}
    if native_type == "reaction":
        return {"reaction": message.get("reaction") or {}}
    if native_type in ("interactive", "button"):
        # A tapped reply: Graph reports quick-reply buttons as `button`, list/reply buttons as
        # `interactive`. Both are the customer choosing an option, so both canonicalise the same.
        return {"interactive": message.get("interactive") or message.get("button") or {}}

    # An inbound type we have no canonical shape for is still a real message: keep the body under
    # its own name rather than dropping it (FR-WA-06).
    return {native_type: message.get(native_type)}


def to_status_update(payload: dict[str, Any]) -> StatusUpdate:
    """A stored ``STATUSES`` payload → canonical :class:`StatusUpdate`."""
    status = (payload or {}).get("status")
    if not isinstance(status, dict) or not status.get("id"):
        raise MetaMessageError("payload carries no Meta status object")

    native = str(status.get("status") or "")
    state = _STATUS.get(native)
    if state is None:
        raise MetaMessageError(f"unknown Meta delivery status {native!r}")

    # Meta reports failures as a list; the first is the actionable one.
    errors = status.get("errors") or []
    error = errors[0] if errors and isinstance(errors[0], dict) else {}
    return StatusUpdate(
        channel_message_id=str(status["id"]),
        status=state,
        recipient_id=status.get("recipient_id"),
        occurred_at=_occurred_at(status.get("timestamp")),
        error_code=str(error["code"]) if error.get("code") is not None else None,
        error_title=error.get("title"),
        # Graph puts the human-readable cause in `error_data.details`.
        error_detail=(error.get("error_data") or {}).get("details") or error.get("message"),
    )


def _change_events(change: dict[str, Any], waba_id: Any) -> list[InboundEvent]:
    value = change.get("value") or {}
    metadata = value.get("metadata") or {}
    number_id = str(metadata.get("phone_number_id") or "")
    # Context every event of this change needs to stand on its own when replayed.
    context = {
        "waba_id": waba_id,
        "field": change.get("field"),
        "metadata": metadata,
    }

    events: list[InboundEvent] = []
    for message in value.get("messages") or []:
        events.append(
            InboundEvent(
                # Meta's message id is the dedup key for an inbound message (FR-WA-07).
                event_id=message.get("id"),
                type=InboundEventType.MESSAGES,
                channel_number_id=number_id,
                # The profile of the sender arrives beside the message, not inside it.
                payload=context | {"contacts": value.get("contacts") or [], "message": message},
                occurred_at=_occurred_at(message.get("timestamp")),
            )
        )
    for status in value.get("statuses") or []:
        message_id = status.get("id")
        state = status.get("status")
        events.append(
            InboundEvent(
                # Dedup on message id **plus** state (Doc 06 §11.4): one message legitimately
                # yields sent → delivered → read, which are three distinct events, not retries.
                event_id=f"{message_id}:{state}" if message_id and state else None,
                type=InboundEventType.STATUSES,
                channel_number_id=number_id,
                payload=context | {"status": status},
                occurred_at=_occurred_at(status.get("timestamp")),
            )
        )

    if not events:
        # A change we do not model yet (template status, account update, …). Surfaced rather than
        # skipped so §11.6 can isolate it — silently dropping a signed event is data loss.
        events.append(
            InboundEvent(
                event_id=None,
                type=InboundEventType.UNKNOWN,
                channel_number_id=number_id,
                payload=context | {"value": value},
                occurred_at=None,
            )
        )
    return events
