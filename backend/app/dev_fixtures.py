"""Development-only representative preview fixtures for Chat History.

Not a product feature. A repository-controlled, opt-in local development aid that populates the
*existing* Chat History workspace with clearly fictional, deterministic data so the real
application can be run and its UI screenshotted end to end (Doc: MODULE_STATUS.md "Chat History"
— the populated-preview data blocker this module removes).

Reuses existing ORM models and the existing invariant-maintaining service (
:class:`~app.services.conversation_service.ConversationService`) exactly as the real
inbound/outbound paths do for window state, unread counts and last-message denormalization. It
never imports :mod:`app.channels` (the provider adapters), never opens a network connection, and
never constructs anything that looks like a provider webhook payload — there is no send path here
to invoke, real or fake.

Safety, enforced in code rather than only by convention:

- :func:`ensure_dev_fixtures_allowed` raises unless **both** ``settings.environment`` is
  ``development``/``test`` *and* ``settings.allow_dev_fixtures`` is explicitly ``True``. A
  production or staging-like configuration refuses to run any function in this module.
- Every seeded row is deterministically identified. Contacts carry
  ``source=SOURCE_DEV_FIXTURE``; the WABA, phone numbers, agent users and tags all use fixed,
  obviously-fictional natural keys (the ``FIXTURE_*`` constants below — country code ``999`` is
  unassigned by the ITU, the WhatsApp-number equivalent of the NANP's reserved ``555`` block).
  :func:`seed_chat_history_preview` looks each one up by that key before creating it, so the whole
  module is idempotent: re-running it changes nothing that already exists.
- :func:`reset_chat_history_preview` deletes only rows reachable from those markers — a contact
  fixture didn't create, or any row not descended from one, is never touched.

Everything here attaches to the single existing tenant organization created by
``python -m app.cli create-owner`` (Doc 03 §4.1, single-tenant deployment); this module never
creates a second organization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.security import hash_password, validate_password_policy
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_event import ContactEvent
from app.models.conversation import CONV_STATUSES, Conversation
from app.models.conversation_tag import conversation_tags
from app.models.message import (
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    MSG_DELIVERED,
    MSG_FAILED,
    MSG_READ,
    MSG_SENT,
    Message,
    MessageStatusHistory,
)
from app.models.tag import Tag, contact_tags
from app.models.user import User
from app.models.waba import WABA_ACTIVE, PhoneNumber, WhatsAppBusinessAccount
from app.rbac.catalog import ROLE_AGENT
from app.rbac.seeding import sync_permissions, sync_system_roles
from app.repositories._result import affected_rows
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.role import UserRoleRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.conversation_service import ConversationService

# --- Fixture identity markers -----------------------------------------------------------------
#: Root identification key: every fixture contact carries this in `contacts.source`, and
#: `reset_chat_history_preview` walks outward from contacts bearing it.
SOURCE_DEV_FIXTURE = "dev_fixture_chat_history_preview"

FIXTURE_WABA_META_ID = "PREVIEW-WABA-000001"
FIXTURE_WABA_NAME = "Preview WhatsApp Business Account (fixture)"
FIXTURE_PHONE_META_IDS: tuple[str, ...] = ("PREVIEW-PHONE-000001", "PREVIEW-PHONE-000002")
FIXTURE_PHONE_DISPLAY_NUMBERS: tuple[str, ...] = ("+999 5550 0001", "+999 5550 0002")
FIXTURE_PHONE_VERIFIED_NAMES: tuple[str, ...] = (
    "Preview Support Line (fixture)",
    "Preview Sales Line (fixture)",
)
#: ``.example`` is reserved by RFC 2606 specifically for documentation/example use and will never
#: resolve to a real registrable domain — unlike ``.invalid``, it also passes the same
#: `EmailStr`/`email-validator` syntax check the real login form runs (``.invalid``/``.test``/
#: ``.local``/``.localhost`` are all rejected as "special-use or reserved" before the password is
#: even checked), so these accounts can actually authenticate through the real UI.
FIXTURE_AGENT_EMAILS: tuple[str, ...] = (
    "agent.preview.one@fixture.example",
    "agent.preview.two@fixture.example",
)
FIXTURE_AGENT_NAMES: tuple[str, ...] = ("Preview Agent One", "Preview Agent Two")
#: A fixed, clearly-fictional password so a screenshot pass can actually log in as this account
#: through the real login form to demonstrate the audit-permission difference (Doc: RBAC preview).
#: Only ever valid when `ensure_dev_fixtures_allowed` would also allow seeding in the first place.
FIXTURE_AGENT_PASSWORD = "Preview-Fixture-Agent-Pass-1"  # noqa: S105 - fixture value, not a secret
FIXTURE_TAG_NAMES: tuple[str, ...] = (
    "VIP (Preview)",
    "Billing (Preview)",
    "Sales (Preview)",
    "Escalated (Preview)",
)

#: Country calling code 999 is unassigned by the ITU — an obviously-fictional block.
_FIXTURE_COUNTRY_CODE = "999"
TOTAL_CONTACTS = 31
#: The last contact intentionally has no conversation (Chat History no-results search target).
NO_THREAD_CONTACT_INDEX = TOTAL_CONTACTS  # 1-based; contact "31"
TOTAL_CONVERSATIONS = TOTAL_CONTACTS - 1  # 30
FLAGSHIP_CONTACT_INDEX = 1
FLAGSHIP_MESSAGE_COUNT = 60


class DevFixturesNotAllowed(RuntimeError):
    """Refused: this environment/configuration must never run the dev-fixture seeder."""


def ensure_dev_fixtures_allowed() -> None:
    """Fail closed unless this is an explicitly opted-in development/test environment.

    Two independent conditions must both hold — either alone is not enough:

    1. ``settings.environment`` is ``development`` or ``test`` (never ``staging``/``production``).
    2. ``settings.allow_dev_fixtures`` is explicitly ``True`` (defaults to ``False`` everywhere).
    """
    if settings.environment not in ("development", "test"):
        raise DevFixturesNotAllowed(
            f"refusing to run dev fixtures: ENVIRONMENT={settings.environment!r} "
            "(only 'development' or 'test' are allowed)"
        )
    if not settings.allow_dev_fixtures:
        raise DevFixturesNotAllowed(
            "refusing to run dev fixtures: ALLOW_DEV_FIXTURES is not set to true "
            "(explicit opt-in required even in a development environment)"
        )


@dataclass(frozen=True, slots=True)
class FixtureSummary:
    organization_id: int
    agents_created: int
    waba_created: bool
    phone_numbers_created: int
    tags_created: int
    contacts_created: int
    conversations_created: int
    messages_created: int
    agent_login_hint: str = field(default=FIXTURE_AGENT_PASSWORD)


@dataclass(frozen=True, slots=True)
class ResetSummary:
    contacts_deleted: int
    conversations_deleted: int
    messages_deleted: int
    tags_deleted: int
    phone_numbers_deleted: int
    waba_deleted: int
    agents_deleted: int


# --- Content pools (fictional, deterministic) -------------------------------------------------
# Cycled by index, never randomized — the same seed run always produces the same content, which
# is what makes `seed_chat_history_preview` safe to re-run and easy to reason about in a diff.

_INBOUND_TEXTS = (
    "Hi, I wanted to check the status of my last order.",
    "Is the Preview Store open this weekend?",
    "Can you send me the invoice again please?",
    "Thanks, that resolved it!",
    "I haven't received my delivery yet, can you check?",
    "What are your support hours?",
    "I'd like to update my billing address.",
    "Do you offer a preview/demo before purchase?",
)
_OUTBOUND_TEXTS = (
    "Hi! Thanks for reaching out — let me check that for you.",
    "Your order has been confirmed and is on its way.",
    "We're open Monday to Saturday, 9am to 6pm.",
    "I've resent the invoice to your registered email.",
    "Glad we could help — let us know if anything else comes up!",
    "Support is available 24/7 through this chat.",
    "Your billing address has been updated.",
    "Absolutely, happy to set up a preview for you.",
)


def _text_content(body: str) -> dict[str, Any]:
    return {"body": body}


def _media_content(index: int) -> tuple[str, dict[str, Any]]:
    kinds = ("image", "document")
    kind = kinds[index % len(kinds)]
    if kind == "image":
        return "image", {
            "media": {
                "kind": "image",
                "caption": "Preview product photo (fixture)",
                "filename": "preview-product.jpg",
                "mime_type": "image/jpeg",
                # Deliberately no `link` — metadata-only, no network fetch (Doc: preview fixture
                # safety — media must never point at a real or fake live provider URL).
            }
        }
    return "document", {
        "media": {
            "kind": "document",
            "caption": "Preview invoice (fixture)",
            "filename": "preview-invoice.pdf",
            "mime_type": "application/pdf",
        }
    }


def _template_content() -> dict[str, Any]:
    return {"template": {"name": "preview_order_confirmation", "language": "en_US"}}


def _location_content() -> dict[str, Any]:
    return {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "name": "Preview Store — fictional location",
        }
    }


# --- Idempotent get-or-create helpers -----------------------------------------------------------


async def _get_or_create_waba(
    session: AsyncSession, *, organization_id: int
) -> tuple[WhatsAppBusinessAccount, bool]:
    repo = WabaRepository(session)
    existing = await session.scalar(
        select(WhatsAppBusinessAccount).where(
            WhatsAppBusinessAccount.waba_id == FIXTURE_WABA_META_ID
        )
    )
    if existing is not None:
        return existing, False
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id,
        waba_id=FIXTURE_WABA_META_ID,
        business_name=FIXTURE_WABA_NAME,
        # A placeholder value run through the app's own local encryption utility — never a real
        # credential, never transmitted anywhere; it only satisfies the NOT NULL column.
        access_token_enc=encrypt("preview-fixture-not-a-real-token"),
        status=WABA_ACTIVE,
    )
    await repo.add(waba)
    return waba, True


async def _get_or_create_phone_numbers(
    session: AsyncSession, *, organization_id: int, waba_pk: int
) -> tuple[list[PhoneNumber], int]:
    repo = PhoneNumberRepository(session)
    numbers: list[PhoneNumber] = []
    created = 0
    for i, meta_id in enumerate(FIXTURE_PHONE_META_IDS):
        existing = await repo.get_by_meta_id(meta_id)
        if existing is not None:
            numbers.append(existing)
            continue
        number = PhoneNumber(
            organization_id=organization_id,
            waba_id=waba_pk,
            channel_type="whatsapp",
            phone_number_id=meta_id,
            display_number=FIXTURE_PHONE_DISPLAY_NUMBERS[i],
            verified_name=FIXTURE_PHONE_VERIFIED_NAMES[i],
            quality_rating="GREEN",
            status="connected",
            is_default=(i == 0),
        )
        await repo.add(number)
        numbers.append(number)
        created += 1
    return numbers, created


async def _get_or_create_agents(
    session: AsyncSession, *, organization_id: int
) -> tuple[list[User], int]:
    validate_password_policy(FIXTURE_AGENT_PASSWORD)
    users_repo = UserRepository(session)
    roles = await sync_system_roles(session, organization_id)
    agent_role = next(role for role in roles if role.name == ROLE_AGENT)
    user_roles = UserRoleRepository(session)

    agents: list[User] = []
    created = 0
    for email, name in zip(FIXTURE_AGENT_EMAILS, FIXTURE_AGENT_NAMES, strict=True):
        existing = await users_repo.get_by_email(email)
        if existing is not None:
            agents.append(existing)
            continue
        agent = User(
            organization_id=organization_id,
            email=email,
            password_hash=hash_password(FIXTURE_AGENT_PASSWORD),
            full_name=name,
            is_superuser=False,
        )
        await users_repo.add(agent)
        await user_roles.assign(agent.id, agent_role.id, assigned_by=None)
        agents.append(agent)
        created += 1
    return agents, created


async def _get_or_create_tags(
    session: AsyncSession, *, organization_id: int
) -> tuple[list[Tag], int]:
    repo = TagRepository(session)
    tags: list[Tag] = []
    created = 0
    palette = ("#7C3AED", "#0EA5E9", "#F59E0B", "#EF4444")
    for i, name in enumerate(FIXTURE_TAG_NAMES):
        existing = await repo.get_by_name(organization_id, name)
        if existing is not None:
            tags.append(existing)
            continue
        tag = Tag(organization_id=organization_id, name=name, color=palette[i % len(palette)])
        await repo.add(tag)
        tags.append(tag)
        created += 1
    return tags, created


def _contact_wa_id(index: int) -> str:
    return f"{_FIXTURE_COUNTRY_CODE}{index:07d}"


def _contact_name(index: int) -> str:
    if index == NO_THREAD_CONTACT_INDEX:
        return "Preview Customer NoThread"
    return f"Preview Customer {index:02d}"


async def _get_or_create_contacts(
    session: AsyncSession, *, organization_id: int
) -> tuple[list[Contact], int]:
    repo = ContactRepository(session)
    contacts: list[Contact] = []
    created = 0
    for index in range(1, TOTAL_CONTACTS + 1):
        wa_id = _contact_wa_id(index)
        existing = await repo.get_active_by_wa_id(organization_id, wa_id)
        if existing is not None:
            contacts.append(existing)
            continue
        contact = Contact(
            organization_id=organization_id,
            wa_id=wa_id,
            phone_e164=f"+{wa_id}",
            full_name=_contact_name(index),
            source=SOURCE_DEV_FIXTURE,
            opt_in_status="opted_in",
            opt_in_at=utcnow() - timedelta(days=30),
            is_active_on_wa=True,
        )
        await repo.add(contact)
        contacts.append(contact)
        created += 1
    return contacts, created


def _message_wamid(contact_index: int, message_index: int) -> str:
    return f"PREVIEW-MSG-{contact_index:03d}-{message_index:03d}"


async def _seed_thread(
    session: AsyncSession,
    *,
    conv_service: ConversationService,
    messages_repo: MessageRepository,
    organization_id: int,
    contact: Contact,
    contact_index: int,
    number: PhoneNumber,
    message_count: int,
) -> tuple[Conversation, int]:
    """Idempotently build one thread and its messages, returning (conversation, messages_created).

    Reuses :class:`ConversationService` for every state transition a real inbound/outbound message
    would trigger — window open/close, `unread_count`, `last_message_at`/`last_message_preview` —
    so the seeded rows obey exactly the invariants the application itself enforces.
    """
    now = utcnow()
    # Newer contacts (lower index) get more recent activity, so the default (unfiltered, newest-
    # first) list is naturally ordered contact 1..30 top to bottom — convenient for screenshots.
    thread_end = now - timedelta(hours=6 * (contact_index - 1))
    if message_count > 1:
        step = timedelta(hours=4) if message_count <= 8 else timedelta(hours=2)
    else:
        step = timedelta(0)

    conversation = await conv_service.thread_for(number=number, contact=contact)
    created_messages = 0

    for seq in range(1, message_count + 1):
        wamid = _message_wamid(contact_index, seq)
        if await messages_repo.get_by_wamid(wamid) is not None:
            continue  # already seeded on a prior run — idempotent

        occurred_at = thread_end - step * (message_count - seq)
        inbound = seq % 2 == 1  # thread opens with the customer, as a real one would

        if inbound:
            message_type, content = "text", _text_content(
                _INBOUND_TEXTS[(contact_index + seq) % len(_INBOUND_TEXTS)]
            )
            if seq % 9 == 0:
                message_type, content = _media_content(seq)
            conversation = await conv_service.open_for_inbound(
                number=number, contact=contact, occurred_at=occurred_at
            )
            stored = Message(
                organization_id=organization_id,
                conversation_id=conversation.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                direction=DIRECTION_INBOUND,
                wamid=wamid,
                message_type=message_type,
                content_json=content,
                status="accepted",
                created_at=occurred_at,
            )
            await messages_repo.add(stored)
            await conv_service.record_inbound_message(
                conversation,
                preview=ConversationService.preview_of(message_type, content),
                occurred_at=occurred_at,
            )
        else:
            message_type, content = "text", _text_content(
                _OUTBOUND_TEXTS[(contact_index + seq) % len(_OUTBOUND_TEXTS)]
            )
            if seq % 11 == 0:
                content = _template_content()
                message_type = "template"
            elif seq % 13 == 0:
                content = _location_content()
                message_type = "location"

            status = MSG_SENT
            sent_at: Any = occurred_at
            delivered_at = None
            read_at = None
            error_code = None
            if seq % 17 == 0:
                status, error_code = MSG_FAILED, "PREVIEW_UNDELIVERABLE"
            elif seq % 5 == 0:
                status = MSG_READ
                delivered_at = occurred_at + timedelta(minutes=1)
                read_at = occurred_at + timedelta(minutes=8)
            elif seq % 3 == 0:
                status = MSG_DELIVERED
                delivered_at = occurred_at + timedelta(minutes=1)

            stored = Message(
                organization_id=organization_id,
                conversation_id=conversation.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                direction=DIRECTION_OUTBOUND,
                wamid=wamid,
                message_type=message_type,
                content_json=content,
                status=status,
                error_code=error_code,
                sent_at=sent_at,
                delivered_at=delivered_at,
                read_at=read_at,
                created_at=occurred_at,
            )
            await messages_repo.add(stored)
            session.add(
                MessageStatusHistory(
                    message_id=stored.id,
                    wamid=wamid,
                    status=status,
                    error_code=error_code,
                    occurred_at=occurred_at,
                    created_at=occurred_at,
                )
            )
            await session.flush()
            await conv_service.record_outbound_message(
                conversation,
                contact=contact,
                preview=ConversationService.preview_of(message_type, content),
                occurred_at=occurred_at,
            )
        created_messages += 1

    return conversation, created_messages


async def seed_chat_history_preview(
    session_factory: async_sessionmaker[AsyncSession],
) -> FixtureSummary:
    """Populate Chat History with fictional, deterministic, idempotent preview data.

    Refuses immediately (before touching the database) unless
    :func:`ensure_dev_fixtures_allowed` passes. Attaches to the existing single-tenant
    organization created by ``python -m app.cli create-owner`` — raises if that hasn't run yet.
    """
    ensure_dev_fixtures_allowed()

    async with session_factory() as session:
        org_repo = OrganizationRepository(session)
        organization = await org_repo.get_default()
        if organization is None:
            raise DevFixturesNotAllowed(
                "no organization exists yet — run `python -m app.cli create-owner` first"
            )

        await sync_permissions(session)
        agents, agents_created = await _get_or_create_agents(
            session, organization_id=organization.id
        )
        waba, waba_created = await _get_or_create_waba(session, organization_id=organization.id)
        numbers, numbers_created = await _get_or_create_phone_numbers(
            session, organization_id=organization.id, waba_pk=waba.id
        )
        tags, tags_created = await _get_or_create_tags(session, organization_id=organization.id)
        contacts, contacts_created = await _get_or_create_contacts(
            session, organization_id=organization.id
        )

        conv_service = ConversationService(session)
        conversations_repo = ConversationRepository(session)
        messages_repo = MessageRepository(session)

        conversations_created = 0
        messages_created = 0

        for contact_index in range(1, TOTAL_CONVERSATIONS + 1):
            contact = contacts[contact_index - 1]
            number = numbers[contact_index % len(numbers)]
            message_count = (
                FLAGSHIP_MESSAGE_COUNT
                if contact_index == FLAGSHIP_CONTACT_INDEX
                else 3 + (contact_index % 4)
            )

            existing_conversation = await conversations_repo.get_for_number_contact(
                number.id, contact.id
            )
            is_new_conversation = existing_conversation is None

            conversation, created_count = await _seed_thread(
                session,
                conv_service=conv_service,
                messages_repo=messages_repo,
                organization_id=organization.id,
                contact=contact,
                contact_index=contact_index,
                number=number,
                message_count=message_count,
            )
            messages_created += created_count
            if is_new_conversation:
                conversations_created += 1
                # Status/assignment only set once, at creation — a rerun must not reset an
                # operator's later manual edits to a fixture conversation (idempotent, non-
                # destructive re-run).
                conversation.status = CONV_STATUSES[(contact_index - 1) % len(CONV_STATUSES)]
                assignment_cycle = [agents[0].id, agents[1].id, None]
                conversation.assigned_user_id = assignment_cycle[(contact_index - 1) % 3]
                await session.flush()

                if (contact_index - 1) % 2 == 0:
                    tag = tags[(contact_index - 1) % len(tags)]
                    existing_tag = await session.scalar(
                        select(conversation_tags.c.tag_id).where(
                            conversation_tags.c.conversation_id == conversation.id,
                            conversation_tags.c.tag_id == tag.id,
                        )
                    )
                    if existing_tag is None:
                        await session.execute(
                            conversation_tags.insert().values(
                                conversation_id=conversation.id,
                                tag_id=tag.id,
                                tagged_at=utcnow(),
                                tagged_by=agents[0].id,
                            )
                        )
                if contact_index == FLAGSHIP_CONTACT_INDEX:
                    # A second tag on the flagship thread only, for visual variety in the list.
                    second_tag = tags[1]
                    await session.execute(
                        conversation_tags.insert().values(
                            conversation_id=conversation.id,
                            tag_id=second_tag.id,
                            tagged_at=utcnow(),
                            tagged_by=agents[0].id,
                        )
                    )

        await session.commit()

        return FixtureSummary(
            organization_id=organization.id,
            agents_created=agents_created,
            waba_created=waba_created,
            phone_numbers_created=numbers_created,
            tags_created=tags_created,
            contacts_created=contacts_created,
            conversations_created=conversations_created,
            messages_created=messages_created,
        )


async def reset_chat_history_preview(
    session_factory: async_sessionmaker[AsyncSession],
) -> ResetSummary:
    """Delete only rows positively identified as fixture-owned by this module's own markers.

    Never touches a row that does not carry one of the ``FIXTURE_*``/``SOURCE_DEV_FIXTURE``
    markers — an operator's real data, or another test's data, is never at risk.
    """
    ensure_dev_fixtures_allowed()

    async with session_factory() as session:
        contact_ids = list(
            (
                await session.scalars(
                    select(Contact.id).where(Contact.source == SOURCE_DEV_FIXTURE)
                )
            ).all()
        )

        conversation_ids: list[int] = []
        if contact_ids:
            conversation_ids = list(
                (
                    await session.scalars(
                        select(Conversation.id).where(Conversation.contact_id.in_(contact_ids))
                    )
                ).all()
            )

        messages_deleted = 0
        if conversation_ids:
            # Captured before deleting the messages themselves, so the status-history cleanup
            # below can target exactly these ids — never a broader "whatever's now orphaned"
            # query, which could reach a row this fixture did not create.
            message_ids = list(
                (
                    await session.scalars(
                        select(Message.id).where(Message.conversation_id.in_(conversation_ids))
                    )
                ).all()
            )
            result = await session.execute(
                delete(Message).where(Message.conversation_id.in_(conversation_ids))
            )
            messages_deleted = affected_rows(result)
            if message_ids:
                await session.execute(
                    delete(MessageStatusHistory).where(
                        MessageStatusHistory.message_id.in_(message_ids)
                    )
                )
            await session.execute(
                delete(conversation_tags).where(
                    conversation_tags.c.conversation_id.in_(conversation_ids)
                )
            )

        conversations_deleted = 0
        if conversation_ids:
            result = await session.execute(
                delete(Conversation).where(Conversation.id.in_(conversation_ids))
            )
            conversations_deleted = affected_rows(result)

        contacts_deleted = 0
        if contact_ids:
            await session.execute(delete(contact_tags).where(contact_tags.c.contact_id.in_(contact_ids)))
            await session.execute(
                delete(ContactEvent).where(ContactEvent.contact_id.in_(contact_ids))
            )
            result = await session.execute(delete(Contact).where(Contact.id.in_(contact_ids)))
            contacts_deleted = affected_rows(result)

        result = await session.execute(delete(Tag).where(Tag.name.in_(FIXTURE_TAG_NAMES)))
        tags_deleted = affected_rows(result)

        result = await session.execute(
            delete(PhoneNumber).where(PhoneNumber.phone_number_id.in_(FIXTURE_PHONE_META_IDS))
        )
        phone_numbers_deleted = affected_rows(result)

        result = await session.execute(
            delete(WhatsAppBusinessAccount).where(
                WhatsAppBusinessAccount.waba_id == FIXTURE_WABA_META_ID
            )
        )
        waba_deleted = affected_rows(result)

        result = await session.execute(delete(User).where(User.email.in_(FIXTURE_AGENT_EMAILS)))
        agents_deleted = affected_rows(result)

        await session.commit()

        return ResetSummary(
            contacts_deleted=contacts_deleted,
            conversations_deleted=conversations_deleted,
            messages_deleted=messages_deleted,
            tags_deleted=tags_deleted,
            phone_numbers_deleted=phone_numbers_deleted,
            waba_deleted=waba_deleted,
            agents_deleted=agents_deleted,
        )
