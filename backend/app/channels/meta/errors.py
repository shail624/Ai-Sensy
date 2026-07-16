"""Meta error taxonomy → platform failure classes (Doc 06 §6.2/§6.6, decision D12).

The retry engine is generic and never hard-codes a provider's codes; a channel registers its own
map into it (:func:`app.queue.retry.register_error_map`). This module is that map for Meta — the
one place in the codebase that knows what a Meta error code means.

The mapping is **data**, mirroring the Doc 06 §6.2 table row for row, so a code moving class is a
one-line edit here and nothing else changes. Codes not listed fall back to HTTP-status shape, and
anything still unrecognised stays ``UNKNOWN`` → the engine parks it for a human rather than
retrying blind (§7.2). D12 wants this map updatable without a deploy; loading overrides from
settings is a later step's concern — the shape here is already a lookup, not a branch.
"""

from __future__ import annotations

from app.channels.errors import ChannelApiError, ChannelAuthError, ChannelTransportError
from app.queue.retry import FailureClass, register_error_map


class MetaApiError(ChannelApiError):
    """An error envelope returned by the Graph API.

    Meta answers ``200`` for success and a JSON ``{"error": {...}}`` otherwise; ``code`` and
    ``error_subcode`` are what classification keys on, and ``fbtrace_id`` is what Meta support asks
    for, so it is preserved rather than flattened into the message.
    """

    def __init__(
        self,
        message: str,
        *,
        code: int | str | None = None,
        subcode: int | None = None,
        http_status: int | None = None,
        fbtrace_id: str | None = None,
        error_type: str | None = None,
    ) -> None:
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id
        self.error_type = error_type
        super().__init__(message, code=code, http_status=http_status)


#: Meta error code → failure class (Doc 06 §6.2). Curated, not exhaustive: an unmapped code falls
#: through to the HTTP-status rules below rather than being guessed at.
CODE_CLASS: dict[int, FailureClass] = {
    # Throttle — "we are pushing too hard"; back off and feed the rate gate (§5). Not a failure.
    4: FailureClass.THROTTLE,  # application request limit reached
    80007: FailureClass.THROTTLE,  # rate limit issues
    130429: FailureClass.THROTTLE,  # Cloud API message throughput limit
    131048: FailureClass.THROTTLE,  # spam rate limit hit
    131056: FailureClass.THROTTLE,  # (business, consumer) pair rate limit
    # Transient — Meta-side, usually clears.
    1: FailureClass.TRANSIENT,  # unknown API error
    2: FailureClass.TRANSIENT,  # temporary API service issue
    131000: FailureClass.TRANSIENT,  # generic "something went wrong"
    # Transient-media — refresh/retry the media prep, then the send (§6.2 media row).
    131053: FailureClass.TRANSIENT_MEDIA,  # media upload/download error
    # Terminal-data — the fix is the data, never a retry.
    131008: FailureClass.TERMINAL_DATA,  # required parameter missing
    131009: FailureClass.TERMINAL_DATA,  # parameter value invalid
    131021: FailureClass.TERMINAL_DATA,  # recipient cannot be the sender
    131026: FailureClass.TERMINAL_DATA,  # undeliverable / not a WhatsApp user
    131051: FailureClass.TERMINAL_DATA,  # unsupported message type
    # Terminal-policy — a compliance outcome, not a retry (Doc 01 CMP-03).
    131047: FailureClass.TERMINAL_POLICY,  # 24h window closed; needs a template
    131049: FailureClass.TERMINAL_POLICY,  # not delivered to maintain healthy ecosystem
    # Terminal-config — a whole-campaign blocker; pause + alert rather than retry.
    132015: FailureClass.TERMINAL_CONFIG,  # template paused
    132016: FailureClass.TERMINAL_CONFIG,  # template disabled
    133010: FailureClass.TERMINAL_CONFIG,  # phone number not registered
    # Template data errors — fix the template/params.
    132000: FailureClass.TERMINAL_DATA,  # param count mismatch
    132001: FailureClass.TERMINAL_DATA,  # template does not exist
    132005: FailureClass.TERMINAL_DATA,  # hydrated text too long
    132007: FailureClass.TERMINAL_DATA,  # format policy violation
    132012: FailureClass.TERMINAL_DATA,  # param format mismatch
}


def _from_status(http_status: int | None) -> FailureClass | None:
    """Fallback by HTTP shape when the code is unmapped (Doc 06 §6.2 rows 1–2)."""
    if http_status is None:
        return None
    if http_status == 429:
        return FailureClass.THROTTLE
    if http_status >= 500:
        return FailureClass.TRANSIENT
    if http_status in (401, 403):
        # Bad/expired token: retrying cannot fix it; an operator must.
        return FailureClass.TERMINAL_CONFIG
    if http_status >= 400:
        return FailureClass.TERMINAL
    return None


def classify_meta(exc: BaseException) -> FailureClass | None:
    """Classify a Meta failure, or return ``None`` to let the engine try other maps."""
    if isinstance(exc, ChannelTransportError):
        return FailureClass.TRANSIENT
    if isinstance(exc, ChannelAuthError):
        return FailureClass.TERMINAL_CONFIG
    if not isinstance(exc, MetaApiError):
        return None
    if isinstance(exc.code, int) and exc.code in CODE_CLASS:
        return CODE_CLASS[exc.code]
    return _from_status(exc.http_status) or FailureClass.UNKNOWN


def install() -> None:
    """Register the Meta map with the retry engine (Doc 06 §6.6). Idempotent."""
    register_error_map("meta", classify_meta)
