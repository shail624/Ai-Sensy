"""Provider-native recipient identities for WAHA direct-message conversations.

WhatsApp phone JIDs and LIDs are routing addresses, not interchangeable Contact phone numbers.
This module validates the small direct-message vocabulary certified for WAHA and exposes the
canonical phone alias only when the provider actually supplied a phone-address form.
"""

from __future__ import annotations

import re

from app.channels.errors import ChannelError

_DIRECT_JID = re.compile(r"^(?P<digits>[1-9]\d{7,18})@(?P<domain>c\.us|s\.whatsapp\.net|lid)$")
_PHONE_DOMAINS = frozenset({"c.us", "s.whatsapp.net"})


def normalize_direct_jid(value: str | None) -> str:
    """Return a validated direct-message JID without changing its provider domain."""

    normalized = value.strip() if isinstance(value, str) else ""
    if not _DIRECT_JID.fullmatch(normalized):
        raise ChannelError("WAHA sender has no supported provider-native direct address")
    return normalized


def optional_direct_jid(value: str | None) -> str | None:
    """Validate an optional alternate JID; an invalid supplied value fails closed."""

    if value is None or not value.strip():
        return None
    return normalize_direct_jid(value)


def route_identity_namespace(address: str) -> str:
    """Use the governed LID namespace for LIDs and exact-JID vocabulary for phone JIDs."""

    match = _DIRECT_JID.fullmatch(address)
    if match is None:
        raise ChannelError("WAHA recipient address is not a supported direct JID")
    return "whatsapp_lid" if match.group("domain") == "lid" else "whatsapp_jid"


def phone_wa_id(*addresses: str | None) -> str | None:
    """Return digits only from an address that is factually a phone JID, never from a LID."""

    for address in addresses:
        if address is None:
            continue
        match = _DIRECT_JID.fullmatch(address)
        if match is not None and match.group("domain") in _PHONE_DOMAINS:
            digits = match.group("digits")
            # Contact phone identity is E.164-shaped; provider LIDs may be longer and never reach
            # this branch. Keep the canonical Contact constraint explicit at the adapter boundary.
            if 8 <= len(digits) <= 15:
                return digits
    return None
