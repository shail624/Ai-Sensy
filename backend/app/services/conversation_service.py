"""Conversation & window service (Doc 03 §9.1; Doc 06 §2.3 ``inbound.process``) — FR-WA-09/12.

Owns everything an inbound message implies about the *thread*: who the customer is, that a thread
exists for them on this number, and that their message re-opened the 24-hour window.

Contact resolution lives here rather than in :mod:`app.services.contact_service` because the two
have opposite contracts. The API path is actor-driven and rejects a duplicate with ``409``; this
path is system-driven and **must** upsert — a customer messaging us twice is not a conflict, and
there is no user to attribute it to. The shared parts (the ``(organization_id, wa_id)`` key, the
timeline entry, the audit row) are reused rather than restated.

Nothing here commits: an inbound message and everything it implies is one transaction, owned by
:class:`~app.services.message_service.MessageService`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import ChannelType
from app.models.audit import ACTOR_SYSTEM
from app.models.contact import Contact
from app.models.contact_event import EVENT_CONTACT_CREATED
from app.models.conversation import PREVIEW_LENGTH, WINDOW, Conversation
from app.models.waba import PhoneNumber
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService

#: Doc 03 ``contacts.source`` — how this contact record came to exist.
SOURCE_WEBHOOK = "webhook"


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._contacts = ContactRepository(session)
        self._events = ContactEventService(session)
        self._audit = AuditService(session)

    async def _get_or_create_contact(
        self, *, organization_id: int, wa_id: str, source: str
    ) -> tuple[Contact, bool]:
        contact = await self._contacts.get_active_by_wa_id(organization_id, wa_id)
        if contact is not None:
            return contact, False
        contact = Contact(
            organization_id=organization_id,
            wa_id=wa_id,
            # The wa_id is a normalized E.164 without the '+'; the display form adds it back.
            phone_e164=f"+{wa_id}",
            source=source,
        )
        await self._contacts.add(contact)
        return contact, True

    async def resolve_contact(
        self,
        *,
        organization_id: int,
        wa_id: str,
        profile_name: str | None,
        occurred_at: datetime,
    ) -> Contact:
        """Find or create the customer behind an inbound message (FR-WA-09).

        Also the platform's **active detection**: a message can only arrive from a number that is
        live on WhatsApp, so receiving one is the proof `is_active_on_wa` records (Doc 03 §6.1).
        """
        contact, created = await self._get_or_create_contact(
            organization_id=organization_id, wa_id=wa_id, source=SOURCE_WEBHOOK
        )
        if profile_name:
            contact.profile_name = profile_name
        contact.is_active_on_wa = True
        # Monotonic: a replayed older message must not rewind the window (Doc 04 §23.1).
        if contact.last_inbound_at is None or occurred_at > contact.last_inbound_at:
            contact.last_inbound_at = occurred_at
        await self._contacts.flush()

        if created:
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_CONTACT_CREATED,
                payload={"source": SOURCE_WEBHOOK},
            )
            # A new person's PII entering the system is security-relevant, so it is audited on the
            # webhook path exactly as it is on the API path — with no actor, because there is none.
            await self._audit.record(
                AuditAction.CONTACT_CREATED,
                actor_type=ACTOR_SYSTEM,
                organization_id=organization_id,
                entity_type="contact",
                entity_id=contact.id,
                after={"wa_id": wa_id, "source": SOURCE_WEBHOOK},
            )
        return contact

    async def resolve_recipient(self, *, organization_id: int, wa_id: str, source: str) -> Contact:
        """Find or create the customer an **outbound** message is addressed to.

        Deliberately not :meth:`resolve_contact`: sending to someone proves nothing about them, so
        this records no `is_active_on_wa` and no `last_inbound_at` — those are facts only an
        inbound message establishes (FR-WA-09).
        """
        contact, created = await self._get_or_create_contact(
            organization_id=organization_id, wa_id=wa_id, source=source
        )
        await self._contacts.flush()
        if created:
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_CONTACT_CREATED,
                payload={"source": source},
            )
            await self._audit.record(
                AuditAction.CONTACT_CREATED,
                actor_type=ACTOR_SYSTEM,
                organization_id=organization_id,
                entity_type="contact",
                entity_id=contact.id,
                after={"wa_id": wa_id, "source": source},
            )
        return contact

    async def thread_for(self, *, number: PhoneNumber, contact: Contact) -> Conversation:
        """The thread for a (number, contact) pair, created if this is their first message.

        Touches no window state: only an inbound message opens a window (FR-WA-12).
        """
        conversation = await self._conversations.get_for_number_contact(number.id, contact.id)
        if conversation is None:
            conversation = Conversation(
                organization_id=number.organization_id,
                phone_number_id=number.id,
                contact_id=contact.id,
                channel_type=number.channel_type or ChannelType.WHATSAPP.value,
            )
            await self._conversations.add(conversation)
        elif conversation.deleted_at is not None:
            # A new message revives an archived thread rather than starting a second one.
            conversation.deleted_at = None
        await self._conversations.flush()
        return conversation

    async def open_for_inbound(
        self, *, number: PhoneNumber, contact: Contact, occurred_at: datetime
    ) -> Conversation:
        """The thread this message belongs to, with its window re-opened (FR-WA-12).

        Upsert, not create: ``uq_conv_number_contact`` means one thread per (number, contact), and
        every later message on it lands here again.
        """
        conversation = await self.thread_for(number=number, contact=contact)
        if conversation.last_inbound_at is None or occurred_at > conversation.last_inbound_at:
            conversation.last_inbound_at = occurred_at
            conversation.window_expires_at = occurred_at + WINDOW
        # Denormalized for `ix_conv_window`; `Conversation.window_is_open` is the read-time truth.
        conversation.is_window_open = conversation.window_is_open
        await self._conversations.flush()
        return conversation

    async def _touch_last_message(
        self, conversation: Conversation, *, preview: str, occurred_at: datetime
    ) -> None:
        if conversation.last_message_at is None or occurred_at >= conversation.last_message_at:
            # Only the newest message owns the preview; a replayed older one must not overwrite it.
            conversation.last_message_at = occurred_at
            conversation.last_message_preview = preview[:PREVIEW_LENGTH] or None
        conversation.row_version += 1
        await self._conversations.flush()

    async def record_inbound_message(
        self, conversation: Conversation, *, preview: str, occurred_at: datetime
    ) -> None:
        """Update the denormalized inbox columns for a newly stored inbound message.

        Called only when a message was actually inserted, so a redelivery can never inflate the
        unread badge (FR-WA-07).
        """
        conversation.unread_count += 1
        await self._touch_last_message(conversation, preview=preview, occurred_at=occurred_at)

    async def record_outbound_message(
        self, conversation: Conversation, *, contact: Contact, preview: str, occurred_at: datetime
    ) -> None:
        """Update the thread and the contact for a message **we** sent.

        No unread increment: unread counts what the customer said that nobody has read yet, and our
        own reply is neither.
        """
        contact.last_outbound_at = occurred_at
        contact.last_contacted_at = occurred_at
        await self._contacts.flush()
        await self._touch_last_message(conversation, preview=preview, occurred_at=occurred_at)

    @staticmethod
    def preview_of(message_type: str, content: dict[str, Any]) -> str:
        """What the inbox list shows for a message (Doc 03 §9.1 ``last_message_preview``).

        Reads the canonical content shape, never a channel's: a text body if there is one, a
        caption if the media carries one, and otherwise the type in brackets.
        """
        body = content.get("body")
        if isinstance(body, str) and body.strip():
            return body.strip()
        caption = (content.get("media") or {}).get("caption") if content else None
        if isinstance(caption, str) and caption.strip():
            return caption.strip()
        return f"[{message_type}]"
