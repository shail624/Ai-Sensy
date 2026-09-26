"""WAHA outbound send and delivery-state translation — QR-05.

QR-04 accepted the events a paired session produces. QR-05 sends a text through it and translates
the provider's acknowledgements into the platform's **existing** delivery vocabulary.

## Monotonicity is inherited, not reinvented

``messages`` already encodes delivery as one-way (Doc 06 §11.3 / decision D16):
:data:`~app.models.message.STATUS_RANK` ranks ``accepted < sent < delivered < read`` and
:func:`~app.models.message.advances` refuses anything that does not move forward. QR-05 therefore
only has to *map* provider acknowledgements onto that vocabulary — it deliberately introduces no
second ordering, no "latest wins" path and no parallel status column.

This matters because certification observed acknowledgements arriving **out of order**:
``DEVICE(2) → SERVER(1) → READ(3)``. Mapped onto the existing ranks that becomes
``delivered → sent → read``; ``advances()`` ignores the late ``sent`` and applies ``read``. A
last-write-wins implementation would have regressed a delivered message back to "sent".

## Unknown acknowledgements fail closed

An acknowledgement code this deployment has not certified maps to ``None`` rather than being
guessed at. A guess would either invent progress the provider never reported, or — worse — be
treated as a low rank and appear to regress a message. ``None`` means "no state change", which is
always safe.

## Ambiguous sends are never blindly retried

If the transport outcome is uncertain — a timeout, a dropped connection — the message may or may not
have reached WhatsApp. Resending would risk delivering the same text twice to a real person, which
cannot be undone. :class:`WahaSendIndeterminate` marks exactly this case and is deliberately **not**
retry-safe; the caller must reconcile first (:meth:`~app.channels.waha.adapter.WahaChannelAdapter.reconcile_send`),
and may only resend if reconciliation proves the message is *absent*. If absence cannot be proven,
the honest outcome is an indeterminate failure, not a duplicate WhatsApp delivery.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Final

from app.channels.errors import ChannelApiError
from app.channels.models import StatusUpdate
from app.channels.waha.webhook import canonical_message_id
from app.models.message import MSG_ACCEPTED, MSG_DELIVERED, MSG_FAILED, MSG_READ, MSG_SENT

#: Provider event carrying an acknowledgement.
EVENT_MESSAGE_ACK: Final = "message.ack"


class WahaAck(IntEnum):
    """Acknowledgement codes observed on the certified build.

    Every member was seen during physical-phone certification (``ERROR`` excepted, which the
    provider documents and which is mapped defensively to the platform's terminal state).
    """

    ERROR = -1
    PENDING = 0
    SERVER = 1
    DEVICE = 2
    READ = 3


#: Provider acknowledgement → the platform's own ``messages.status`` vocabulary.
#:
#: The ranks these map onto (``accepted 0 < sent 1 < delivered 2 < read 3``) are what make
#: out-of-order acknowledgements safe; see the module docstring.
ACK_TO_STATUS: Final[dict[WahaAck, str]] = {
    WahaAck.ERROR: MSG_FAILED,
    WahaAck.PENDING: MSG_ACCEPTED,
    WahaAck.SERVER: MSG_SENT,
    WahaAck.DEVICE: MSG_DELIVERED,
    WahaAck.READ: MSG_READ,
}


class WahaSendIndeterminate(ChannelApiError):
    """A send whose outcome is genuinely unknown.

    **Not retry-safe.** The message may already have reached the recipient. Reconcile before any
    resend; if absence cannot be proven, surface this rather than risk a duplicate delivery.
    """


def map_ack(value: object) -> str | None:
    """Provider acknowledgement code → platform status, or ``None`` when uncertified.

    ``None`` is deliberate: it means "make no state change". Guessing a status could invent
    progress or, mapped to a low rank, look like a regression.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    try:
        ack = WahaAck(value)
    except ValueError:
        return None
    return ACK_TO_STATUS[ack]


def to_status_update(delivery: dict[str, Any]) -> StatusUpdate:
    """A verified ``message.ack`` delivery → the delivery-state change it represents.

    The acknowledgement's message id arrives with ``@lid`` addressing while the send response and
    history use ``@c.us``; certification proved only the **trailing** component is stable across
    all three. That trailing value is what correlates, so it is what is returned.
    """

    payload = delivery.get("payload")
    payload_obj: dict[str, Any] = payload if isinstance(payload, dict) else {}

    canonical = canonical_message_id(payload_obj.get("id"))
    if canonical is None:
        raise ChannelApiError("WAHA acknowledgement has no usable provider message id")

    status = map_ack(payload_obj.get("ack"))
    if status is None:
        raise ChannelApiError(
            "WAHA reported an uncertified acknowledgement code; no delivery state was applied"
        )

    recipient = payload_obj.get("from")
    return StatusUpdate(
        channel_message_id=canonical,
        status=status,
        recipient_id=recipient if isinstance(recipient, str) and recipient else None,
    )


def extract_sent_id(body: dict[str, Any]) -> str | None:
    """The canonical provider message id from a send response.

    The certified build answers with ``{"key": {"id": "...", "remoteJid": ..., "fromMe": true}}``.
    The bare ``key.id`` is already the canonical trailing form, and certification proved it matches
    the trailing component seen later in history and acknowledgements.
    """

    key = body.get("key")
    if isinstance(key, dict):
        raw = key.get("id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    # Some responses nest the composite form instead; reduce it the same way as everywhere else.
    return canonical_message_id(body.get("id"))
