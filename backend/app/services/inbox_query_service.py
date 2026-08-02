"""Shared-inbox read service (Doc 04 §18.1) — Phase 7 Step 2.

The inbox's read side: list threads, open one, page its messages. Separate from
:class:`~app.services.inbox_service.InboxService` (the audited write side) because a read authorizes
nothing and records nothing — mixing them would put audit and mutation next to a plain query.

Filters and search are exactly what Doc 04 §18.1 freezes — status, assignee, number, ``q`` — and no
more. The list is keyed on ``last_message_at`` per the frozen contract; resolution of assignee and
number *public ids* to internal ids happens here so the repository speaks only ids.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tag import Tag
from app.models.user import User
from app.models.waba import PhoneNumber
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.conversation_tag import ConversationTagRepository
from app.repositories.message import MessageRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.repositories.waba import PhoneNumberRepository

#: Assignee-filter tokens for the two folders Doc 05 B7 makes first-class ("Mine" is the caller
#: passing their own id; "Unassigned" is this).
_UNASSIGNED_TOKENS = ("unassigned", "none")


@dataclass(slots=True)
class ConversationListResult:
    """A page of the inbox with everything the rows need resolved (Doc 04 §18.1)."""

    conversations: list[Conversation]
    contacts: dict[int, Contact]
    numbers: dict[int, str]
    assignees: dict[int, str]
    #: Active tags per conversation id (Doc 04 §18.1 v1.3), batch-resolved for the page.
    tags: dict[int, list[Tag]]
    has_more: bool


@dataclass(slots=True)
class ConversationDetail:
    """One thread, with the references its representation needs (Doc 04 §18.1)."""

    conversation: Conversation
    contact: Contact | None
    phone_number_public_id: str | None
    assigned_to: str | None
    #: Active tags on the thread (Doc 04 §18.1 v1.3).
    tags: list[Tag]


@dataclass(slots=True)
class MessagePage:
    """A page of a thread's messages (Doc 04 §18.1)."""

    conversation_public_id: str
    messages: list[Message]
    has_more: bool


class InboxQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._contacts = ContactRepository(session)
        self._messages = MessageRepository(session)
        self._users = UserRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._tags = TagRepository(session)
        self._conv_tags = ConversationTagRepository(session)

    # --- List ----------------------------------------------------------------
    async def list_conversations(
        self,
        *,
        organization_id: int,
        limit: int,
        cursor: tuple[datetime, int] | None,
        contact: str | None,
        status: str | None,
        assignee: str | None,
        number: str | None,
        tag: str | None,
        q: str | None,
    ) -> ConversationListResult:
        """The inbox list, filtered and searched as Doc 04 §18.1 defines, newest activity first."""
        assignee_id, unassigned, assignee_impossible = await self._resolve_assignee(
            organization_id, assignee
        )
        contact_id, contact_impossible = await self._resolve_contact(organization_id, contact)
        phone_number_id, number_impossible = await self._resolve_number(organization_id, number)
        tag_id, tag_impossible = await self._resolve_tag(organization_id, tag)

        # A filter that named a real-looking but non-existent assignee/number/tag matches nothing —
        # returned as an empty page, not an error: the query was valid, the target just isn't here.
        if contact_impossible or assignee_impossible or number_impossible or tag_impossible:
            return ConversationListResult([], {}, {}, {}, {}, has_more=False)

        conversations, has_more = await self._conversations.list_page(
            organization_id,
            contact_id=contact_id,
            status=status,
            assignee_id=assignee_id,
            unassigned=unassigned,
            phone_number_id=phone_number_id,
            tag_id=tag_id,
            q=q,
            limit=limit,
            cursor=cursor,
        )
        contacts = await self._contacts_for(conversations)
        numbers = await self._numbers_for(conversations)
        assignees = await self._assignees_for(conversations)
        tags = await self._conv_tags.tags_for_conversations([c.id for c in conversations])
        return ConversationListResult(conversations, contacts, numbers, assignees, tags, has_more)

    async def _resolve_contact(
        self, organization_id: int, contact: str | None
    ) -> tuple[int | None, bool]:
        """Resolve a public contact filter without exposing another tenant's identity."""
        if not contact:
            return None, False
        found = await self._contacts.get_active_by_uuid(
            organization_id, self._as_uuid(contact, "contact").bytes
        )
        if found is None:
            return None, True
        return found.id, False

    async def _resolve_assignee(
        self, organization_id: int, assignee: str | None
    ) -> tuple[int | None, bool, bool]:
        """(assignee_id, unassigned, impossible) for the assignee filter token."""
        if not assignee:
            return None, False, False
        if assignee.lower() in _UNASSIGNED_TOKENS:
            return None, True, False
        user = await self._users.get_by_uuid(self._as_uuid(assignee, "assignee"))
        if user is None or user.organization_id != organization_id:
            return None, False, True
        return user.id, False, False

    async def _resolve_number(
        self, organization_id: int, number: str | None
    ) -> tuple[int | None, bool]:
        """(phone_number_id, impossible) for the number filter."""
        if not number:
            return None, False
        found = await self._numbers.get_active_by_uuid(
            organization_id, self._as_uuid(number, "number").bytes
        )
        if found is None:
            return None, True
        return found.id, False

    async def _resolve_tag(
        self, organization_id: int, tag: str | None
    ) -> tuple[int | None, bool]:
        """(tag_id, impossible) for the by-tag filter (Doc 04 §18.1 v1.3).

        A malformed uuid is a 400 (via ``_as_uuid``); a well-formed but unknown/foreign tag is
        ``impossible`` — an empty page, exactly as the assignee/number filters behave.
        """
        if not tag:
            return None, False
        found = await self._tags.get_active_by_uuid(
            organization_id, self._as_uuid(tag, "tag").bytes
        )
        if found is None:
            return None, True
        return found.id, False

    @staticmethod
    def _as_uuid(value: str, field: str) -> uuidlib.UUID:
        try:
            return uuidlib.UUID(value)
        except ValueError as exc:
            raise BadRequestError(f"Invalid {field} filter; expected a UUID.") from exc

    # --- Detail --------------------------------------------------------------
    async def get_conversation(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> ConversationDetail:
        conversation = await self._conversation(organization_id, public_id)
        contact = await self._session.get(Contact, conversation.contact_id)
        number = await self._session.get(PhoneNumber, conversation.phone_number_id)
        assigned_to = await self._assignee_public_id(conversation)
        tags = (await self._conv_tags.tags_for_conversations([conversation.id])).get(
            conversation.id, []
        )
        return ConversationDetail(
            conversation=conversation,
            contact=contact,
            phone_number_public_id=number.public_id if number is not None else None,
            assigned_to=assigned_to,
            tags=tags,
        )

    # --- Message history -----------------------------------------------------
    async def list_messages(
        self,
        *,
        organization_id: int,
        public_id: uuidlib.UUID,
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> MessagePage:
        conversation = await self._conversation(organization_id, public_id)
        messages, has_more = await self._messages.list_for_conversation(
            conversation.id, limit=limit, cursor=cursor
        )
        return MessagePage(conversation.public_id, messages, has_more)

    # --- Batch resolution ----------------------------------------------------
    async def _contacts_for(
        self, conversations: list[Conversation]
    ) -> dict[int, Contact]:
        ids = {c.contact_id for c in conversations}
        if not ids:
            return {}
        rows = (await self._session.scalars(select(Contact).where(Contact.id.in_(ids)))).all()
        return {c.id: c for c in rows}

    async def _numbers_for(self, conversations: list[Conversation]) -> dict[int, str]:
        ids = {c.phone_number_id for c in conversations}
        if not ids:
            return {}
        rows = (
            await self._session.scalars(select(PhoneNumber).where(PhoneNumber.id.in_(ids)))
        ).all()
        return {n.id: n.public_id for n in rows}

    async def _assignees_for(self, conversations: list[Conversation]) -> dict[int, str]:
        ids = {c.assigned_user_id for c in conversations if c.assigned_user_id is not None}
        if not ids:
            return {}
        rows = (await self._session.scalars(select(User).where(User.id.in_(ids)))).all()
        return {u.id: u.public_id for u in rows}

    async def _assignee_public_id(self, conversation: Conversation) -> str | None:
        if conversation.assigned_user_id is None:
            return None
        user = await self._users.get_by_id(conversation.assigned_user_id)
        return user.public_id if user is not None else None

    async def _conversation(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> Conversation:
        conversation = await self._conversations.get_active_by_uuid(
            organization_id, public_id.bytes
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation
