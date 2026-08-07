"""Tests for the development-only Chat History preview fixture (`app.dev_fixtures`).

Hermetic — runs against the same in-memory SQLite database every other test uses
(`conftest.py`'s `session_factory`), never a real MySQL server. The safety guard itself is
dialect-independent, so this is exactly where it should be proven.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.cli import bootstrap_owner
from app.core.config import settings
from app.dev_fixtures import (
    FIXTURE_AGENT_EMAILS,
    FIXTURE_PHONE_META_IDS,
    FIXTURE_TAG_NAMES,
    FIXTURE_WABA_META_ID,
    SOURCE_DEV_FIXTURE,
    TOTAL_CONTACTS,
    TOTAL_CONVERSATIONS,
    DevFixturesNotAllowed,
    ensure_dev_fixtures_allowed,
    reset_chat_history_preview,
    seed_chat_history_preview,
)
from app.models.contact import Contact
from app.models.conversation import CONV_STATUSES, Conversation
from app.models.message import Message
from app.models.tag import Tag
from app.models.user import User
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository

OWNER_EMAIL = "owner@fixture-test.example"
OWNER_PASSWORD = "Fixture-Test-Owner-123"


async def _bootstrap(session_factory) -> None:
    await bootstrap_owner(
        session_factory, email=OWNER_EMAIL, full_name="Fixture Test Owner", password=OWNER_PASSWORD
    )


# --- 1. Production-like environments refuse execution ------------------------------------------


async def test_seed_refuses_in_production(session_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)  # even with the flag set
    with pytest.raises(DevFixturesNotAllowed, match="ENVIRONMENT"):
        await seed_chat_history_preview(session_factory)


async def test_seed_refuses_in_staging(session_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    with pytest.raises(DevFixturesNotAllowed, match="ENVIRONMENT"):
        await seed_chat_history_preview(session_factory)


async def test_seed_refuses_in_development_without_explicit_flag(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment alone is not enough — the flag defaults to False even in development."""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "allow_dev_fixtures", False)
    with pytest.raises(DevFixturesNotAllowed, match="ALLOW_DEV_FIXTURES"):
        await seed_chat_history_preview(session_factory)


async def test_reset_also_refuses_in_production(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    with pytest.raises(DevFixturesNotAllowed):
        await reset_chat_history_preview(session_factory)


def test_guard_function_directly_covers_all_four_combinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for environment, flag, should_pass in [
        ("production", True, False),
        ("staging", True, False),
        ("development", False, False),
        ("development", True, True),
        ("test", True, True),
    ]:
        monkeypatch.setattr(settings, "environment", environment)
        monkeypatch.setattr(settings, "allow_dev_fixtures", flag)
        if should_pass:
            ensure_dev_fixtures_allowed()  # must not raise
        else:
            with pytest.raises(DevFixturesNotAllowed):
                ensure_dev_fixtures_allowed()


# --- 2. Explicit development environment allows it --------------------------------------------


async def test_seed_succeeds_in_development_with_explicit_flag(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    summary = await seed_chat_history_preview(session_factory)

    assert summary.contacts_created == TOTAL_CONTACTS
    assert summary.conversations_created == TOTAL_CONVERSATIONS


async def test_seed_succeeds_in_test_environment_with_explicit_flag(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ENVIRONMENT=test is conftest's own default; only the flag needs setting here.
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    summary = await seed_chat_history_preview(session_factory)

    assert summary.contacts_created == TOTAL_CONTACTS


# --- 3. Rerunning is idempotent -----------------------------------------------------------------


async def test_seed_is_idempotent_on_rerun(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    first = await seed_chat_history_preview(session_factory)
    second = await seed_chat_history_preview(session_factory)

    assert first.contacts_created == TOTAL_CONTACTS
    assert first.conversations_created == TOTAL_CONVERSATIONS
    assert first.messages_created > 0
    # A rerun creates nothing new — every natural key already existed.
    assert second.contacts_created == 0
    assert second.conversations_created == 0
    assert second.messages_created == 0
    assert second.agents_created == 0
    assert second.waba_created is False
    assert second.phone_numbers_created == 0
    assert second.tags_created == 0

    async with session_factory() as session:
        contact_count = len(
            (await session.scalars(select(Contact.id).where(Contact.source == SOURCE_DEV_FIXTURE))).all()
        )
        assert contact_count == TOTAL_CONTACTS  # not doubled


async def test_seed_rerun_does_not_reset_operator_edits(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rerun must not clobber a status/assignment change an operator made in the meantime."""
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)
    await seed_chat_history_preview(session_factory)

    async with session_factory() as session:
        conversation = (await session.scalars(select(Conversation).limit(1))).first()
        assert conversation is not None
        conversation.status = "resolved"
        conversation.assigned_user_id = None
        await session.commit()
        edited_id = conversation.id

    await seed_chat_history_preview(session_factory)

    async with session_factory() as session:
        reloaded = await session.get(Conversation, edited_id)
        assert reloaded is not None
        assert reloaded.status == "resolved"
        assert reloaded.assigned_user_id is None


# --- 4. Fixture rows remain inside one organization --------------------------------------------


async def test_all_seeded_rows_are_scoped_to_one_organization(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)
    summary = await seed_chat_history_preview(session_factory)

    async with session_factory() as session:
        org = await OrganizationRepository(session).get_default()
        assert org is not None
        assert summary.organization_id == org.id

        for model in (Contact, Conversation, Message, PhoneNumber, WhatsAppBusinessAccount):
            org_ids = set(
                (await session.scalars(select(model.organization_id).distinct())).all()
            )
            assert org_ids <= {org.id}, f"{model.__name__} rows outside the single organization"

        agent_org_ids = set(
            (
                await session.scalars(
                    select(User.organization_id).where(User.email.in_(FIXTURE_AGENT_EMAILS))
                )
            ).all()
        )
        assert agent_org_ids == {org.id}


# --- 5. No provider/network send path is invoked ------------------------------------------------


async def test_seed_never_calls_the_channel_adapter(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fixture must never reach a provider adapter — there is no send path to invoke."""
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    with patch(
        "app.channels.base.get_adapter", side_effect=AssertionError("must never be called")
    ) as mock_get_adapter:
        await seed_chat_history_preview(session_factory)
        await reset_chat_history_preview(session_factory)

    mock_get_adapter.assert_not_called()


async def test_seed_opens_no_network_socket(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SQLite (file/memory) and Argon2 hashing need no socket — proves no network I/O occurs."""
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    def _refuse_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dev fixture seeding must never open a network socket")

    with patch.object(socket.socket, "connect", _refuse_connect):
        await seed_chat_history_preview(session_factory)


def test_dev_fixtures_module_never_imports_channel_adapters() -> None:
    """Static confirmation alongside the dynamic one above: no import-time coupling either."""
    import ast

    import app.dev_fixtures as module

    source = module.__file__
    assert source is not None
    with open(source, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(name == "app.channels" or name.startswith("app.channels.") for name in imported_modules)


# --- 6. Expected representative counts/statuses exist -------------------------------------------


async def test_representative_data_matches_the_required_minimums(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)
    await seed_chat_history_preview(session_factory)

    async with session_factory() as session:
        agents = (
            await session.scalars(select(User).where(User.email.in_(FIXTURE_AGENT_EMAILS)))
        ).all()
        assert len(agents) == 2

        numbers = (
            await session.scalars(
                select(PhoneNumber).where(PhoneNumber.phone_number_id.in_(FIXTURE_PHONE_META_IDS))
            )
        ).all()
        assert len(numbers) == 2

        conversations = (await session.scalars(select(Conversation))).all()
        assert len(conversations) >= 30

        statuses = {c.status for c in conversations}
        assert statuses == set(CONV_STATUSES)
        for status in CONV_STATUSES:
            assert sum(1 for c in conversations if c.status == status) >= 2

        assigned = [c for c in conversations if c.assigned_user_id is not None]
        unassigned = [c for c in conversations if c.assigned_user_id is None]
        assert assigned, "expected at least one assigned conversation"
        assert unassigned, "expected at least one unassigned conversation"

        tags = (await session.scalars(select(Tag).where(Tag.name.in_(FIXTURE_TAG_NAMES)))).all()
        assert len(tags) == 4

        # Conversation has no eager `tags` relationship; check via the junction table instead.
        from app.models.conversation_tag import conversation_tags as ct

        tagged_count = len(
            set((await session.scalars(select(ct.c.conversation_id).distinct())).all())
        )
        assert tagged_count >= 1

        contact_with_no_thread = await session.scalar(
            select(Contact).where(Contact.full_name == "Preview Customer NoThread")
        )
        assert contact_with_no_thread is not None
        no_thread_conversation = await session.scalar(
            select(Conversation).where(Conversation.contact_id == contact_with_no_thread.id)
        )
        assert no_thread_conversation is None

        flagship_contact = await session.scalar(
            select(Contact).where(Contact.full_name == "Preview Customer 01")
        )
        assert flagship_contact is not None
        flagship_conversation = await session.scalar(
            select(Conversation).where(Conversation.contact_id == flagship_contact.id)
        )
        assert flagship_conversation is not None
        flagship_message_count = len(
            (
                await session.scalars(
                    select(Message.id).where(Message.conversation_id == flagship_conversation.id)
                )
            ).all()
        )
        assert flagship_message_count > 50  # exceeds Chat History's message page size

        inbound_count = len(
            (await session.scalars(select(Message.id).where(Message.direction == "inbound"))).all()
        )
        outbound_count = len(
            (
                await session.scalars(select(Message.id).where(Message.direction == "outbound"))
            ).all()
        )
        assert inbound_count > 0
        assert outbound_count > 0


# --- 7. Existing unrelated rows are not deleted / 8. cleanup only removes fixture-owned data ----


async def test_reset_never_touches_unrelated_rows(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    async with session_factory() as session:
        org = await OrganizationRepository(session).get_default()
        assert org is not None
        real_contact = Contact(
            organization_id=org.id,
            wa_id="15550001234",
            phone_e164="+15550001234",
            full_name="A Real Customer",
            source="webhook",
        )
        session.add(real_contact)
        await session.flush()
        real_tag = Tag(organization_id=org.id, name="Genuinely Real Tag", color="#111111")
        session.add(real_tag)
        await session.commit()
        real_contact_id = real_contact.id
        real_tag_id = real_tag.id

    await seed_chat_history_preview(session_factory)
    reset_summary = await reset_chat_history_preview(session_factory)

    assert reset_summary.contacts_deleted == TOTAL_CONTACTS
    assert reset_summary.tags_deleted == 4

    async with session_factory() as session:
        assert await session.get(Contact, real_contact_id) is not None
        assert await session.get(Tag, real_tag_id) is not None
        owner = await UserRepository(session).get_by_email(OWNER_EMAIL)
        assert owner is not None

        remaining_fixture_contacts = (
            await session.scalars(select(Contact).where(Contact.source == SOURCE_DEV_FIXTURE))
        ).all()
        assert remaining_fixture_contacts == []

        remaining_waba = await session.scalar(
            select(WhatsAppBusinessAccount).where(
                WhatsAppBusinessAccount.waba_id == FIXTURE_WABA_META_ID
            )
        )
        assert remaining_waba is None

        remaining_agents = (
            await session.scalars(select(User).where(User.email.in_(FIXTURE_AGENT_EMAILS)))
        ).all()
        assert remaining_agents == []


async def test_reset_before_any_seed_is_a_safe_no_op(
    session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_dev_fixtures", True)
    await _bootstrap(session_factory)

    summary = await reset_chat_history_preview(session_factory)

    assert summary.contacts_deleted == 0
    assert summary.conversations_deleted == 0
    assert summary.agents_deleted == 0
