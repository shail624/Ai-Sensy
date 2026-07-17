"""Messaging schemas (Doc 04 §18.2)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.channels.models import MessageType
from app.models.message import Message, MessageStatusHistory

#: The media kinds a send may carry (mirrors ``MediaKind``, Doc 07 §5.3).
MediaKindName = Literal["image", "video", "audio", "document", "sticker"]


class TextPayload(BaseModel):
    body: str = Field(min_length=1, max_length=4096)
    preview_url: bool = False


class MediaPayload(BaseModel):
    """Media to send. Exactly one source — the adapter can only attach one thing.

    ``media_asset_id`` is the platform's own stored asset (Doc 07 §17.3): it is uploaded to the
    channel on the send lane and the resulting id is cached, so the same file sent a hundred times
    is uploaded once. ``link``/``media_id`` hand a channel-side reference straight through.
    """

    kind: MediaKindName
    link: str | None = None
    media_id: str | None = None
    media_asset_id: uuidlib.UUID | None = None
    caption: str | None = Field(default=None, max_length=1024)
    filename: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _one_source(self) -> MediaPayload:
        sources = [bool(self.link), bool(self.media_id), bool(self.media_asset_id)]
        if sum(sources) != 1:
            raise ValueError("provide exactly one of link, media_id or media_asset_id")
        return self


class TemplateButtonPayload(BaseModel):
    """A value bound to one of the template's buttons (Doc 04 §18.2 `buttons[]`)."""

    index: int = Field(ge=0, le=9)
    type: Literal["url", "quick_reply", "copy_code"]
    value: str = Field(min_length=1, max_length=255)


class TemplateHeaderMedia(BaseModel):
    """The file filling a template's media header. Exactly one source, as for a media send."""

    kind: MediaKindName
    link: str | None = None
    media_id: str | None = None
    media_asset_id: uuidlib.UUID | None = None

    @model_validator(mode="after")
    def _one_source(self) -> TemplateHeaderMedia:
        if sum([bool(self.link), bool(self.media_id), bool(self.media_asset_id)]) != 1:
            raise ValueError("provide exactly one of link, media_id or media_asset_id")
        return self


class TemplatePayload(BaseModel):
    """A template send (Doc 04 §18.2).

    Values, not components: the caller names the template and supplies the positional variables it
    declares. Whether those are approved and correctly counted is the server's business, and what
    Graph wants them to look like is the adapter's.
    """

    id: uuidlib.UUID
    header: list[str] = Field(default_factory=list)
    body: list[str] = Field(default_factory=list)
    buttons: list[TemplateButtonPayload] = Field(default_factory=list)
    header_media: TemplateHeaderMedia | None = None


class MessageSendRequest(BaseModel):
    """A send (Doc 04 §18.2).

    ``type`` selects which payload is read; the others must be absent. Sending is deliberately not
    a discriminated union of free-form JSON: the ledger stores canonical content, so what a client
    may say is the same shape the adapter is handed.
    """

    phone_number_id: uuidlib.UUID
    to: str = Field(min_length=5, max_length=24, examples=["+14155552671"])
    type: Literal["text", "media", "interactive", "template"]
    text: TextPayload | None = None
    media: MediaPayload | None = None
    interactive: dict[str, Any] | None = None
    template: TemplatePayload | None = None

    @model_validator(mode="after")
    def _payload_matches_type(self) -> MessageSendRequest:
        supplied = {
            name for name in ("text", "media", "interactive", "template") if getattr(self, name)
        }
        if supplied != {self.type}:
            raise ValueError(f"type {self.type!r} requires exactly the {self.type!r} payload")
        return self

    def message_type(self) -> MessageType:
        return MessageType(self.type)

    def content(self) -> dict[str, Any]:
        """The canonical ``content_json`` for the ledger (Doc 03 §9.2)."""
        if self.text is not None:
            return {"body": self.text.body, "preview_url": self.text.preview_url}
        if self.media is not None:
            return {
                "media": {
                    "kind": self.media.kind,
                    # Named as the inbound path names it: one canonical media reference, whichever
                    # direction it travels.
                    "channel_media_id": self.media.media_id,
                    "link": self.media.link,
                    "media_asset_id": str(self.media.media_asset_id)
                    if self.media.media_asset_id
                    else None,
                    "caption": self.media.caption,
                    "filename": self.media.filename,
                }
            }
        if self.template is not None:
            return {"template": self._template_content()}
        return {"interactive": self.interactive or {}}

    def _template_content(self) -> dict[str, Any]:
        template = self.template
        assert template is not None  # noqa: S101 - guarded by `_payload_matches_type`
        content: dict[str, Any] = {
            # The public id is resolved to name/language when the send is accepted: a message must
            # record the template it was actually sent as, not a pointer that may later change.
            "id": str(template.id),
            "header": list(template.header),
            "body": list(template.body),
            "buttons": [b.model_dump() for b in template.buttons],
        }
        if template.header_media is not None:
            media = template.header_media
            content["header_media"] = {
                "kind": media.kind,
                "channel_media_id": media.media_id,
                "link": media.link,
                "media_asset_id": str(media.media_asset_id) if media.media_asset_id else None,
            }
        return content


class MessageAcceptedResponse(BaseModel):
    """The ``202`` a send answers with (Doc 04 §18.2)."""

    id: str
    status: str
    #: Always null here: only Meta issues a `wamid`, and it has not been asked yet.
    wamid: str | None = None
    conversation_id: str
    queued_at: datetime

    @classmethod
    def from_message(cls, message: Message, *, conversation_id: str) -> MessageAcceptedResponse:
        return cls(
            id=message.public_id,
            status=message.status,
            wamid=message.wamid,
            conversation_id=conversation_id,
            queued_at=message.created_at,
        )


class MessageResponse(BaseModel):
    id: str
    type: str = "message"
    conversation_id: str
    direction: str
    message_type: str
    status: str
    wamid: str | None
    content: dict[str, Any] | None
    error_code: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    @classmethod
    def from_message(cls, message: Message, *, conversation_id: str) -> MessageResponse:
        return cls(
            id=message.public_id,
            conversation_id=conversation_id,
            direction=message.direction,
            message_type=message.message_type,
            status=message.status,
            wamid=message.wamid,
            content=message.content_json,
            error_code=message.error_code,
            sent_at=message.sent_at,
            delivered_at=message.delivered_at,
            read_at=message.read_at,
            created_at=message.created_at,
        )


class StatusHistoryEntry(BaseModel):
    status: str
    occurred_at: datetime
    error_code: str | None = None
    error_title: str | None = None
    error_detail: str | None = None
    recipient_id: str | None = None

    @classmethod
    def from_entry(cls, entry: MessageStatusHistory) -> StatusHistoryEntry:
        return cls(
            status=entry.status,
            occurred_at=entry.occurred_at,
            error_code=entry.error_code,
            error_title=entry.error_title,
            error_detail=entry.error_detail,
            recipient_id=entry.recipient_id,
        )


class StatusHistoryResponse(BaseModel):
    data: list[StatusHistoryEntry]
