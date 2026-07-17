"""Canonical objects that cross the channel seam (Doc 07 §5.3).

These are the platform's own types: an adapter translates native payloads to and from them, so
**nothing channel-specific leaks past the adapter**. Frozen dataclasses (not Pydantic) because this
is an internal boundary, not the HTTP edge — matching ``StorageProvider``/``QueueSpec``.

Persistence is *not* modelled here: mapping these onto Doc 03's ``messages``/``conversations``
belongs to the modules that own those tables, not to the seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.channels.capabilities import Capability


class MessageType(StrEnum):
    """Canonical outbound message types (Doc 07 §5.2 "Outbound messaging")."""

    TEXT = "text"
    MEDIA = "media"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"


class MediaKind(StrEnum):
    """Canonical media kinds — the platform's own vocabulary, not a provider's."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"


#: Which capability a message type requires before an adapter may be asked to send it.
CAPABILITY_FOR_TYPE: dict[MessageType, Capability] = {
    MessageType.TEXT: Capability.TEXT,
    MessageType.MEDIA: Capability.MEDIA,
    MessageType.INTERACTIVE: Capability.INTERACTIVE,
    MessageType.TEMPLATE: Capability.TEMPLATE,
}


@dataclass(frozen=True, slots=True)
class TextContent:
    body: str
    preview_url: bool = False


@dataclass(frozen=True, slots=True)
class MediaContent:
    """Media to send. Exactly one of ``media_id`` (already uploaded) or ``link`` is used."""

    kind: MediaKind
    media_id: str | None = None
    link: str | None = None
    caption: str | None = None
    filename: str | None = None


@dataclass(frozen=True, slots=True)
class TemplateContent:
    """A pre-approved template send. ``components`` carries the variable substitutions."""

    name: str
    language: str
    components: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InteractiveContent:
    """An interactive message (buttons/list). ``payload`` is the canonical interactive body."""

    payload: dict[str, Any]


Content = TextContent | MediaContent | TemplateContent | InteractiveContent


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    """One message to deliver to ``to`` (a channel-native recipient id, e.g. a ``wa_id``)."""

    to: str
    type: MessageType
    content: Content


@dataclass(frozen=True, slots=True)
class SendResult:
    """The channel's acknowledgement of a send.

    ``channel_message_id`` is the provider's id (Meta's ``wamid``) — the value Doc 06 §2.3 names as
    the send idempotency key and Doc 03 stores on ``messages``.
    """

    to: str
    channel_message_id: str | None
    accepted: bool = True
    raw: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class Attachment:
    """A media object held by the channel (Doc 07 §5.2 "Media")."""

    media_id: str
    mime_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    filename: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadedAttachment:
    """Bytes fetched from the channel plus what the channel said they are."""

    content: bytes
    mime_type: str | None = None
    sha256: str | None = None
    byte_size: int | None = None


@dataclass(frozen=True, slots=True)
class ChannelStatus:
    """Session/auth state (Doc 07 §5.2 "Session/auth" — ``status``)."""

    connected: bool
    identity: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ChannelPhoneNumber:
    """A number the channel says an account owns (Doc 03 §5.2 fields, canonicalised).

    Provisioning, not messaging: only channels that own numbers report these, so this crosses the
    seam as its own type rather than joining the §5.2 messaging operations.
    """

    phone_number_id: str
    display_number: str
    verified_name: str | None = None
    quality_rating: str | None = None
    messaging_tier: str | None = None
    throughput_level: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class HealthSignal:
    """Channel health (Doc 07 §5.2 "Health").

    For Meta this is number quality/tier (Doc 06 §28); for a connector it is session health — the
    caller reads the same canonical shape either way.
    """

    healthy: bool
    quality_rating: str | None = None
    messaging_tier: str | None = None
    throughput_limit: str | None = None
    detail: str | None = None
