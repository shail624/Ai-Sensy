"""Media validation (FR-MED-01..04, Doc 04 §16 → 413/415/422).

Every upload is validated against its declared media type before a byte is stored: allowed MIME
types and per-type size ceilings matching the WhatsApp Cloud API limits, so a file that the
platform would later fail to send is rejected at the door rather than stored and discovered
broken at send time.
"""

from __future__ import annotations

from dataclasses import dataclass

MEDIA_IMAGE = "image"
MEDIA_VIDEO = "video"
MEDIA_DOCUMENT = "document"
MEDIA_AUDIO = "audio"
MEDIA_STICKER = "sticker"
MEDIA_TYPES = (MEDIA_IMAGE, MEDIA_VIDEO, MEDIA_DOCUMENT, MEDIA_AUDIO, MEDIA_STICKER)

_MB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class MediaRule:
    """Allowed MIME types and size ceiling for one media type (WhatsApp Cloud API limits)."""

    mime_types: frozenset[str]
    max_bytes: int


RULES: dict[str, MediaRule] = {
    MEDIA_IMAGE: MediaRule(frozenset({"image/jpeg", "image/png"}), 5 * _MB),
    MEDIA_VIDEO: MediaRule(frozenset({"video/mp4", "video/3gpp"}), 16 * _MB),
    MEDIA_AUDIO: MediaRule(
        frozenset({"audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg"}), 16 * _MB
    ),
    MEDIA_DOCUMENT: MediaRule(
        frozenset(
            {
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-powerpoint",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "text/plain",
                "text/csv",
            }
        ),
        100 * _MB,
    ),
    MEDIA_STICKER: MediaRule(frozenset({"image/webp"}), 500 * 1024),
}


class UnsupportedMediaType(Exception):
    """MIME type is not allowed for the declared media type (→ 415)."""


class MediaTooLarge(Exception):
    """File exceeds the ceiling for its media type (→ 413)."""


class InvalidMedia(Exception):
    """The upload is structurally invalid (→ 422)."""


def validate(*, media_type: str, mime_type: str, byte_size: int) -> None:
    """Validate an upload; raises the exception matching the documented status code."""
    if media_type not in RULES:
        raise InvalidMedia(f"media_type must be one of {list(MEDIA_TYPES)}")
    if byte_size <= 0:
        raise InvalidMedia("file is empty")
    rule = RULES[media_type]
    if mime_type not in rule.mime_types:
        raise UnsupportedMediaType(
            f"{mime_type!r} is not allowed for {media_type!r}; allowed: {sorted(rule.mime_types)}"
        )
    if byte_size > rule.max_bytes:
        raise MediaTooLarge(
            f"{media_type!r} exceeds the {rule.max_bytes // _MB or 1}MB limit"
            if rule.max_bytes >= _MB
            else f"{media_type!r} exceeds the {rule.max_bytes} byte limit"
        )
