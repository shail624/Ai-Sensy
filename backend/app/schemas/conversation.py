"""Conversation read schemas (Doc 04 §18.1) — Phase 7 Step 2.

The inbox list, detail and message history. Reads only: the collaboration writes (assign/status/
notes) live in :mod:`app.schemas.inbox`, and the send path in :mod:`app.schemas.message`.

Fields are denormalized where the frozen design says the list must render instantly
(``last_message_preview``/``unread_count``, Doc 03 §9.1; Doc 04 §18.2 performance note). This schema
surfaces those existing columns; it does not compute or reset them (read/unread state is a separate
milestone).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.api.pagination import Page
from app.channels.capabilities import CONNECTOR_META_CLOUD
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.tag import Tag
from app.schemas.message import MessageResponse
from app.schemas.tag import TagSummary


class ContactRef(BaseModel):
    """Who the conversation is with — enough to render an inbox row (Doc 05 B7 pane 2)."""

    id: str
    name: str | None
    phone: str


class WindowState(BaseModel):
    """The 24-hour customer-service window (Doc 03 §9.1; FR-WA-12).

    ``is_open`` is computed at read time, not read from the denormalized flag: a window closes by
    time passing, not by anything writing a row (Doc 03 §9.1).
    """

    is_open: bool
    expires_at: datetime | None
    last_inbound_at: datetime | None


class ConversationResponse(BaseModel):
    """A conversation as the inbox list and detail render it (Doc 04 §18.1)."""

    id: str
    type: str = "conversation"
    status: str
    channel_type: str
    #: Which provider owns this thread — ``"meta_cloud"`` or ``"waha"`` (QR-08). Display-only: the
    #: server derives it from the conversation's own durable ownership, never from a client hint.
    connector_type: str
    #: Assignee's public id, or ``null`` when unassigned.
    assigned_to: str | None
    contact: ContactRef | None
    #: Classification tags on the thread (Doc 04 §18.1 v1.3); ``[]`` when untagged.
    tags: list[TagSummary]
    #: The sending number's public id (the list's `number` filter groups by this). ``null`` for a
    #: channel-endpoint-owned (WAHA) thread (QR-08).
    phone_number_id: str | None
    last_message_at: datetime | None
    last_message_preview: str | None
    #: Denormalized on the row and maintained by the inbound path (Doc 03 §9.1); surfaced read-only.
    unread_count: int
    window: WindowState
    row_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_conversation(
        cls,
        conversation: Conversation,
        *,
        contact: Contact | None,
        phone_number_public_id: str | None,
        assigned_to: str | None,
        tags: list[Tag] | None = None,
        connector_type: str = CONNECTOR_META_CLOUD,
    ) -> ConversationResponse:
        return cls(
            id=conversation.public_id,
            status=conversation.status,
            channel_type=conversation.channel_type,
            connector_type=connector_type,
            assigned_to=assigned_to,
            tags=[TagSummary.from_tag(t) for t in (tags or [])],
            contact=(
                ContactRef(
                    id=contact.public_id,
                    name=contact.full_name or contact.profile_name,
                    phone=contact.phone_e164,
                )
                if contact is not None
                else None
            ),
            phone_number_id=phone_number_public_id,
            last_message_at=conversation.last_message_at,
            last_message_preview=conversation.last_message_preview,
            unread_count=conversation.unread_count,
            window=WindowState(
                # Computed at read time — a window closes by time passing (Doc 03 §9.1).
                is_open=conversation.window_is_open,
                expires_at=conversation.window_expires_at,
                last_inbound_at=conversation.last_inbound_at,
            ),
            row_version=conversation.row_version,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationsPage(BaseModel):
    """A page of the inbox list (Doc 04 §3 envelope)."""

    data: list[ConversationResponse]
    page: Page


class ConversationMessagesPage(BaseModel):
    """A page of a thread's message history (Doc 04 §18.1), newest first."""

    data: list[MessageResponse]
    page: Page
