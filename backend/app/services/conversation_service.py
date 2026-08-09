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
from app.db.mixins import utcnow
from app.identity.domain import IdentityAssertion, default_identity_normalizers
from app.models.audit import ACTOR_SYSTEM
from app.models.business_event import BUSINESS_EVENT_ACTOR_SYSTEM
from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.contact import Contact
from app.models.contact_event import (
    EVENT_CONTACT_CREATED,
    EVENT_IDENTITY_LINKED,
    REF_TYPE_CONTACT_IDENTITY,
)
from app.models.contact_identity import ContactIdentity
from app.models.conversation import PREVIEW_LENGTH, WINDOW, Conversation
from app.models.waba import PhoneNumber
from app.repositories.contact import ContactRepository
from app.repositories.contact_identity import ContactIdentityRepository
from app.repositories.conversation import ConversationRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.business_event_service import BusinessEventService
from app.services.contact_event_service import ContactEventService

#: Doc 03 ``contacts.source`` — how this contact record came to exist.
SOURCE_WEBHOOK = "webhook"


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._contacts = ContactRepository(session)
        self._identities = ContactIdentityRepository(session)
        self._events = ContactEventService(session)
        self._business_events = BusinessEventService(session)
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
        await self._observe_contact(contact, profile_name=profile_name, occurred_at=occurred_at)

        if created:
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_CONTACT_CREATED,
                payload={"source": SOURCE_WEBHOOK},
            )
            await self._business_events.record_contact_created(
                contact=contact,
                actor_type=BUSINESS_EVENT_ACTOR_SYSTEM,
                actor_id=None,
                occurred_at=occurred_at,
                source="conversations",
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

    async def _observe_contact(
        self, contact: Contact, *, profile_name: str | None, occurred_at: datetime
    ) -> None:
        if profile_name:
            contact.profile_name = profile_name
        contact.is_active_on_wa = True
        if contact.last_inbound_at is None or occurred_at > contact.last_inbound_at:
            contact.last_inbound_at = occurred_at
        await self._contacts.flush()

    async def resolve_endpoint_contact_identity(
        self,
        *,
        endpoint: ChannelEndpoint,
        connection: ChannelConnection,
        provider_address: str,
        route_namespace: str,
        phone_wa_id: str | None,
        profile_name: str | None,
        occurred_at: datetime,
    ) -> Contact:
        """Resolve one Contact without ever interpreting LID digits as a telephone identity."""

        self._require_owned_endpoint(endpoint, connection)
        route = await self._identities.get_exact(
            endpoint.organization_id,
            route_namespace,
            connection.public_id,
            provider_address,
        )
        contact = await self._identity_contact(endpoint.organization_id, route)

        if contact is None and phone_wa_id is not None:
            phone_identity = await self._identities.get_exact(
                endpoint.organization_id,
                "whatsapp_phone",
                "global",
                f"+{phone_wa_id}",
            )
            contact = await self._identity_contact(endpoint.organization_id, phone_identity)

        if contact is None:
            if phone_wa_id is None:
                raise ValueError(
                    "WAHA LID has no provider-supplied phone alias or existing identity owner"
                )
            contact = await self.resolve_contact(
                organization_id=endpoint.organization_id,
                wa_id=phone_wa_id,
                profile_name=profile_name,
                occurred_at=occurred_at,
            )
        else:
            await self._observe_contact(
                contact, profile_name=profile_name, occurred_at=occurred_at
            )

        await self.remember_endpoint_contact_identity(
            endpoint=endpoint,
            connection=connection,
            contact=contact,
            provider_address=provider_address,
            route_namespace=route_namespace,
            phone_wa_id=phone_wa_id,
            occurred_at=occurred_at,
        )
        return contact

    async def remember_endpoint_contact_identity(
        self,
        *,
        endpoint: ChannelEndpoint,
        connection: ChannelConnection,
        contact: Contact,
        provider_address: str,
        route_namespace: str,
        phone_wa_id: str | None,
        occurred_at: datetime,
    ) -> None:
        """Persist exact endpoint routing evidence on the existing Contact authority."""

        self._require_owned_endpoint(endpoint, connection)
        await self._link_provider_identity(
            contact=contact,
            assertion=IdentityAssertion(
                identity_namespace=route_namespace,
                identity_scope=connection.public_id,
                value=provider_address,
                connector_type=connection.connector_type,
                connection_ref=connection.public_id,
                endpoint_ref=endpoint.public_id,
            ),
            occurred_at=occurred_at,
        )
        if phone_wa_id is not None:
            await self._link_provider_identity(
                contact=contact,
                assertion=IdentityAssertion(
                    identity_namespace="whatsapp_phone",
                    identity_scope="global",
                    value=f"+{phone_wa_id}",
                    connector_type=connection.connector_type,
                    connection_ref=connection.public_id,
                    endpoint_ref=endpoint.public_id,
                ),
                occurred_at=occurred_at,
            )

    async def endpoint_reply_address(
        self,
        *,
        endpoint: ChannelEndpoint,
        connection: ChannelConnection,
        contact: Contact,
    ) -> str | None:
        """Return the latest provider-observed route for this Contact and owned endpoint."""

        self._require_owned_endpoint(endpoint, connection)
        identity = await self._identities.latest_routing_identity(
            organization_id=endpoint.organization_id,
            contact_id=contact.id,
            connector_type=connection.connector_type,
            endpoint_ref=endpoint.public_id,
        )
        return identity.normalized_value if identity is not None else None

    async def _identity_contact(
        self, organization_id: int, identity: ContactIdentity | None
    ) -> Contact | None:
        if identity is None:
            return None
        contact = await self._contacts.get_by_id(identity.contact_id)
        if (
            contact is None
            or contact.organization_id != organization_id
            or contact.deleted_at is not None
        ):
            raise ValueError("provider identity points to an unavailable Contact")
        return contact

    async def _link_provider_identity(
        self,
        *,
        contact: Contact,
        assertion: IdentityAssertion,
        occurred_at: datetime,
    ) -> ContactIdentity:
        identity = default_identity_normalizers.normalize(assertion)
        current = await self._identities.get_exact(contact.organization_id, *identity.key)
        if current is not None:
            if current.contact_id != contact.id:
                raise ValueError("provider identity is already owned by another Contact")
            if current.verified_at is None or occurred_at > current.verified_at:
                current.verified_at = occurred_at
            return current

        row = ContactIdentity(
            organization_id=contact.organization_id,
            contact_id=contact.id,
            identity_namespace=identity.identity_namespace,
            identity_scope=identity.identity_scope,
            normalized_value=identity.normalized_value,
            identity_kind=identity.identity_kind.value,
            connector_type=identity.connector_type,
            connection_ref=identity.connection_ref,
            endpoint_ref=identity.endpoint_ref,
            source=identity.source.value,
            confidence=identity.confidence.value,
            verified_at=occurred_at,
            evidence_json={"normalization": "exact", "purpose": "reply_routing"},
        )
        await self._identities.add(row)
        await self._events.record(
            organization_id=contact.organization_id,
            contact_id=contact.id,
            event_type=EVENT_IDENTITY_LINKED,
            ref_type=REF_TYPE_CONTACT_IDENTITY,
            ref_id=row.id,
            payload={
                "identity_namespace": identity.identity_namespace,
                "identity_scope": identity.identity_scope,
                "source": identity.source.value,
                "confidence": identity.confidence.value,
            },
        )
        await self._audit.record(
            AuditAction.CONTACT_IDENTITY_LINKED,
            actor_type=ACTOR_SYSTEM,
            organization_id=contact.organization_id,
            entity_type="contact_identity",
            entity_id=row.id,
            after={
                "contact_id": contact.public_id,
                "identity_namespace": identity.identity_namespace,
                "identity_scope": identity.identity_scope,
                "normalized_value": identity.normalized_value,
                "confidence": identity.confidence.value,
            },
        )
        return row

    @staticmethod
    def _require_owned_endpoint(
        endpoint: ChannelEndpoint, connection: ChannelConnection
    ) -> None:
        if (
            endpoint.connection_id != connection.id
            or endpoint.organization_id != connection.organization_id
        ):
            raise ValueError("channel endpoint does not belong to the resolved connection")

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
            await self._business_events.record_contact_created(
                contact=contact,
                actor_type=BUSINESS_EVENT_ACTOR_SYSTEM,
                actor_id=None,
                occurred_at=utcnow(),
                source="conversations",
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

    # --- Provider-neutral (channel-endpoint-owned, e.g. WAHA) analogues (QR-08) -----------------
    #
    # Kept as their own straight-line methods rather than unifying `number`/`endpoint` behind one
    # signature: ADR-0020 asks for independent failure domains between providers, and the two owner
    # columns (`phone_number_id` / `channel_endpoint_id`) are already mutually exclusive at the
    # database level (`ck_conv_endpoint_owner`) — a shared method would only reintroduce, in code,
    # the ambiguity the schema was built to rule out.

    async def thread_for_endpoint(
        self, *, endpoint: ChannelEndpoint, contact: Contact
    ) -> Conversation:
        """The thread for a (channel endpoint, contact) pair, created on first contact."""
        conversation = await self._conversations.get_for_endpoint_contact(endpoint.id, contact.id)
        if conversation is None:
            conversation = Conversation(
                organization_id=endpoint.organization_id,
                channel_endpoint_id=endpoint.id,
                contact_id=contact.id,
                channel_type=ChannelType.WHATSAPP.value,
            )
            await self._conversations.add(conversation)
        elif conversation.deleted_at is not None:
            conversation.deleted_at = None
        await self._conversations.flush()
        return conversation

    async def open_for_inbound_endpoint(
        self, *, endpoint: ChannelEndpoint, contact: Contact, occurred_at: datetime
    ) -> Conversation:
        """The provider-neutral analogue of :meth:`open_for_inbound`.

        Still records ``last_inbound_at``/``window_expires_at`` — an honest fact about when the
        contact last wrote in, useful in the Inbox UI regardless of provider — but nothing in the
        WAHA send path *enforces* the Meta-only 24-hour customer-service-window rule those fields
        back; WhatsApp Multi-Device carries no such restriction.
        """
        conversation = await self.thread_for_endpoint(endpoint=endpoint, contact=contact)
        if conversation.last_inbound_at is None or occurred_at > conversation.last_inbound_at:
            conversation.last_inbound_at = occurred_at
            conversation.window_expires_at = occurred_at + WINDOW
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
