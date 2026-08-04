"""Channel identity & capability vocabulary (Doc 07 §5.2).

Capabilities are the mechanism behind the abstraction: the CRM offers an action only when the
adapter **declares** it (e.g. "Broadcast" appears only for a channel with :attr:`Capability.CAMPAIGNS`,
"Call" only with :attr:`Capability.CALLS`). Branching on capability rather than channel identity is
what lets a new channel slot in without touching the engine (§5.2/§5.4, decision CD1).
"""

from __future__ import annotations

from enum import StrEnum


class ChannelType(StrEnum):
    """Canonical channel identifier — the value persisted on Doc 03's ``channel_type`` columns.

    ``whatsapp`` matches the frozen default on ``phone_numbers``/``conversations``/``messages``
    (Doc 03 §6/§9). Future channels (Instagram, Messenger, SMS…) are added here as data.
    """

    WHATSAPP = "whatsapp"


#: Connector type of the official Meta Cloud API adapter (Channel 1, Doc 07 §5.2 "Identity").
CONNECTOR_META_CLOUD = "meta_cloud"


class Capability(StrEnum):
    """What an adapter can do (Doc 07 §5.2).

    Names follow the doc's operation groups. ``*``-flagged rows there (template, reaction, calls…)
    are exactly the ones an adapter may omit — the platform must check before offering them.
    """

    # Outbound messaging
    TEXT = "text"
    MEDIA = "media"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    LOCATION = "location"
    CONTACT = "contact"
    REACTION = "reaction"
    #: Throughput sending — the flag Doc 07 §5.2 uses to distinguish Meta from a manual connector.
    BULK = "bulk"
    #: Drives whether the CRM offers Broadcast at all (§5.2).
    CAMPAIGNS = "campaigns"
    # Inbound stream (§5.2) — how a channel delivers messages/statuses back to us.
    #: Signature-verified provider callbacks (Doc 07 §4.2 lists this on Channel 1). A connector
    #: that pushes events over its own session stream declares its own flag instead.
    OFFICIAL_WEBHOOKS = "official_webhooks"
    # Media
    MEDIA_UPLOAD = "media_upload"
    MEDIA_DOWNLOAD = "media_download"
    # Calls (Business Calling API where enabled / connector call metadata)
    CALLS = "calls"
    # Provider runtime / pairing (Module 13; capability-gated, provider-neutral)
    QR_AUTH = "qr_auth"
    SESSION_STREAM = "session_stream"
    SESSION_RECONNECT = "session_reconnect"
    SESSION_LOGOUT = "session_logout"
    # Health
    HEALTH = "health"
