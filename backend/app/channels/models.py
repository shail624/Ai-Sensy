"""Canonical objects that cross the channel seam (Doc 07 §5.3).

These are the platform's own types: an adapter translates native payloads to and from them, so
**nothing channel-specific leaks past the adapter**. Frozen dataclasses (not Pydantic) because this
is an internal boundary, not the HTTP edge — matching ``StorageProvider``/``QueueSpec``.

Persistence is *not* modelled here: mapping these onto Doc 03's ``messages``/``conversations``
belongs to the modules that own those tables, not to the seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.channels.capabilities import Capability


class MessageType(StrEnum):
    """Canonical outbound message types (Doc 07 §5.2 "Outbound messaging")."""

    TEXT = "text"
    MEDIA = "media"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"


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
    MessageType.REACTION: Capability.REACTION,
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
class TemplateButtonValue:
    """A value bound to one of a template's buttons at send time.

    ``type`` is what the button *is* (``url`` suffix, ``quick_reply`` payload, ``copy_code``);
    ``value`` is the single datum that fills it. Which parameter shape a channel needs for each is
    the adapter's problem, not the caller's.
    """

    index: int
    type: str
    value: str


@dataclass(frozen=True, slots=True)
class TemplateContent:
    """A pre-approved template send, in the platform's own terms.

    Deliberately **variables, not components**: a template's variables are positional values the
    business layer knows (a name, an order number), while "components" is a provider's wire format.
    Handing the adapter values rather than a payload is what keeps Graph's shape behind the seam
    (Doc 07 §5.3) — and what lets a future channel bind the same template to a different format.
    """

    name: str
    language: str
    #: Positional ``{{1}}, {{2}}, …`` substitutions, in order.
    header: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    buttons: list[TemplateButtonValue] = field(default_factory=list)
    #: A media header's content, when the template declares one (Doc 03 ``has_media_header``).
    header_media: MediaContent | None = None


@dataclass(frozen=True, slots=True)
class ChannelTemplate:
    """A template as the channel holds it (Doc 03 §7.1's columns, canonicalised).

    ``components`` is the template's **definition** — the Doc 04 §15 structure the platform stores
    and renders — not a send payload.
    """

    name: str
    language: str
    category: str
    status: str
    components: list[dict[str, Any]] = field(default_factory=list)
    channel_template_id: str | None = None
    quality_score: str | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class InteractiveContent:
    """An interactive message (buttons/list). ``payload`` is the canonical interactive body."""

    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReactionContent:
    """A reaction to an existing message (Doc 04 §18.2 v1.4; Doc 07 §5.2a).

    ``message_id`` is the **target's channel id** (Meta's ``wamid``); ``emoji`` is a single emoji, or
    the empty string to remove a prior reaction. Canonicalised behind the seam (Doc 07 §5.3).
    """

    message_id: str
    emoji: str


Content = TextContent | MediaContent | TemplateContent | InteractiveContent | ReactionContent


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


class InboundEventType(StrEnum):
    """What an inbound event is (Doc 07 §5.2 "Inbound stream" — ``on_message``/``on_status``).

    Values match the vocabulary Doc 03 §9.4 gives ``webhook_events.object_type``. ``UNKNOWN`` is
    deliberate rather than a silent skip: Doc 06 §11.6 isolates an event of an unknown type to the
    dead-letter queue instead of dropping it, and that requires the adapter to *emit* it.
    """

    MESSAGES = "messages"
    STATUSES = "statuses"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class InboundEvent:
    """One event lifted out of a channel's inbound stream (Doc 07 §5.2/§18.2).

    Both channels normalize to this: Channel 1 from an official webhook delivery, a connector from
    its session stream — downstream there is no difference (decision CD14).

    ``payload`` is the event's **own** native fragment plus the delivery context it needs, so a
    stored event is independently replayable without the rest of its batch.
    """

    #: Dedup key (Doc 06 §11.4) — the channel's message id, plus the status for a status callback.
    #: ``None`` when the channel provides nothing stable to dedup on (Doc 03 §9.4 allows NULL).
    event_id: str | None
    type: InboundEventType
    #: The channel's own number id (Meta's ``phone_number_id``) — what routing resolves to a
    #: ``phone_numbers`` row (Doc 03 §5.2).
    channel_number_id: str
    payload: dict[str, Any]
    #: The channel's timestamp for the event; replay orders by it (Doc 04 §23.1).
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class InboundMessage:
    """A message a customer sent us, in the platform's own terms (Doc 07 §5.2 ``on_message``).

    The adapter has already translated the channel's payload: ``message_type`` and ``content`` use
    the vocabulary and shape of Doc 03's ``messages.message_type``/``content_json``, so the ledger
    stores what it is handed without ever knowing which channel produced it.
    """

    channel_message_id: str
    #: The channel's identifier for the sender (Meta's ``wa_id``).
    from_id: str
    message_type: str
    content: dict[str, Any]
    #: The sender's display name as the channel knows it (Doc 03 ``contacts.profile_name``).
    profile_name: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    """A delivery-state change for a message we sent (Doc 07 §5.2 ``on_status``).

    ``status`` is normalized to Doc 03's ``messages.status`` vocabulary — the platform's own
    delivery states, which the adapter maps the channel's names onto.
    """

    channel_message_id: str
    status: str
    recipient_id: str | None = None
    occurred_at: datetime | None = None
    error_code: str | None = None
    error_title: str | None = None
    error_detail: str | None = None


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
