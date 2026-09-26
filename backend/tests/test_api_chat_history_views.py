"""Advanced Chat History filters and organization-shared saved-view contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the Meta adapter used by the inbound fixture
from app.models.audit import AuditLog
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.conversation_history_view import ConversationHistoryView
from app.models.message import Message
from app.models.organization import Organization
from app.models.template import MessageTemplate
from app.models.user import User
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from tests.test_api_conversations import _inbound
from tests.test_api_messages import _headers

CONVERSATIONS = "/api/v1/conversations"
VIEWS = "/api/v1/conversation-history/views"


async def _seed_filter_rows(client, make_user, session_factory, monkeypatch) -> tuple[str, str]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        organization = (await session.scalars(select(Organization))).one()
        waba = (await session.scalars(select(WhatsAppBusinessAccount))).one()
        number = (await session.scalars(select(PhoneNumber))).one()
        conversation = (await session.scalars(select(Conversation))).one()
        message = (await session.scalars(select(Message))).one()

        conversation.last_message_at = datetime(2026, 8, 10, 12, 0)
        template = MessageTemplate(
            organization_id=organization.id,
            waba_id=waba.id,
            name="history_filter_template",
            language="en",
            category="marketing",
            status="approved",
            components_json=[],
        )
        session.add(template)
        await session.flush()
        campaign = Campaign(
            organization_id=organization.id,
            name="August follow-up",
            phone_number_id=number.id,
            template_id=template.id,
            audience_type="list",
        )
        session.add(campaign)
        await session.flush()
        message.campaign_id = campaign.id
        # Message-ledger references are application-enforced because the table is partitioned.
        message.media_asset_id = 999
        session.add(
            AuditLog(
                organization_id=organization.id,
                actor_type="system",
                action="conversation.status_changed",
                entity_type="conversation",
                entity_id=conversation.id,
            )
        )

        other_contact = Contact(
            organization_id=organization.id,
            wa_id="919990000099",
            phone_e164="+919990000099",
            full_name="Older contact",
        )
        session.add(other_contact)
        await session.flush()
        session.add(
            Conversation(
                organization_id=organization.id,
                phone_number_id=number.id,
                contact_id=other_contact.id,
                channel_type="whatsapp",
                last_message_at=datetime(2026, 7, 1, 9, 0),
                last_message_preview="Older thread",
            )
        )
        await session.commit()
        return conversation.public_id, campaign.public_id


@pytest.mark.anyio
async def test_advanced_filters_compose_over_the_message_and_audit_ledgers(
    client, make_user, session_factory, monkeypatch, dispatched
):
    conversation_id, campaign_id = await _seed_filter_rows(
        client, make_user, session_factory, monkeypatch
    )
    owner = await _headers(
        client, make_user, email="history-owner@vi.co", is_superuser=True
    )

    response = await client.get(
        CONVERSATIONS,
        headers=owner,
        params={
            "from": "2026-08-01T00:00:00Z",
            "to": "2026-09-01T00:00:00Z",
            "campaign": campaign_id,
            "has_media": "true",
            "has_audit": "true",
        },
    )

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == [conversation_id]


@pytest.mark.anyio
async def test_activity_range_is_from_inclusive_and_to_exclusive(
    client, make_user, session_factory, monkeypatch, dispatched
):
    conversation_id, _ = await _seed_filter_rows(
        client, make_user, session_factory, monkeypatch
    )
    agent = await _headers(client, make_user, email="history-agent@vi.co", roles=("agent",))

    included = await client.get(
        CONVERSATIONS,
        headers=agent,
        params={"from": "2026-08-10T12:00:00Z", "to": "2026-08-11T00:00:00Z"},
    )
    excluded = await client.get(
        CONVERSATIONS,
        headers=agent,
        params={"to": "2026-08-10T12:00:00Z"},
    )

    assert [row["id"] for row in included.json()["data"]] == [conversation_id]
    assert conversation_id not in [row["id"] for row in excluded.json()["data"]]


@pytest.mark.anyio
async def test_invalid_range_and_campaign_identifiers_are_bounded_client_errors(
    client, make_user, session_factory, monkeypatch, dispatched
):
    await _seed_filter_rows(client, make_user, session_factory, monkeypatch)
    agent = await _headers(client, make_user, email="bounded@vi.co", roles=("agent",))

    invalid_range = await client.get(
        CONVERSATIONS,
        headers=agent,
        params={"from": "2026-08-11T00:00:00Z", "to": "2026-08-10T00:00:00Z"},
    )
    malformed = await client.get(CONVERSATIONS, headers=agent, params={"campaign": "not-a-uuid"})
    unknown = await client.get(
        CONVERSATIONS, headers=agent, params={"campaign": str(uuid.uuid4())}
    )

    assert invalid_range.status_code == 400
    assert malformed.status_code == 400
    assert unknown.status_code == 200 and unknown.json()["data"] == []


@pytest.mark.anyio
async def test_audit_filter_requires_audit_read(
    client, make_user, session_factory, monkeypatch, dispatched
):
    await _seed_filter_rows(client, make_user, session_factory, monkeypatch)
    agent = await _headers(client, make_user, email="no-audit@vi.co", roles=("agent",))

    response = await client.get(
        CONVERSATIONS, headers=agent, params={"has_audit": "true"}
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_manager_creates_a_team_shared_view_and_agent_can_apply_it(client, make_user):
    manager = await _headers(client, make_user, email="manager@vi.co", roles=("manager",))
    agent = await _headers(client, make_user, email="reader@vi.co", roles=("agent",))
    payload = {
        "name": "August media follow-up",
        "filters": {
            "status": "open",
            "from": "2026-08-01",
            "to": "2026-08-31",
            "has_media": True,
        },
    }

    created = await client.post(VIEWS, headers=manager, json=payload)
    listed = await client.get(VIEWS, headers=agent)

    assert created.status_code == 201, created.text
    assert created.json()["filters"]["from"] == "2026-08-01"
    assert listed.status_code == 200
    assert listed.json()["data"] == [created.json()]


@pytest.mark.anyio
async def test_shared_view_mutations_are_permission_scoped_and_names_are_unique(client, make_user):
    manager = await _headers(client, make_user, email="view-manager@vi.co", roles=("manager",))
    agent = await _headers(client, make_user, email="view-agent@vi.co", roles=("agent",))
    payload = {"name": "Needs review", "filters": {"status": "pending"}}

    assert (await client.post(VIEWS, headers=manager, json=payload)).status_code == 201
    duplicate = await client.post(
        VIEWS, headers=manager, json={"name": "needs REVIEW", "filters": {}}
    )
    forbidden = await client.post(
        VIEWS, headers=agent, json={"name": "Agent view", "filters": {}}
    )
    invalid_assignee = await client.post(
        VIEWS,
        headers=manager,
        json={"name": "Broken assignee", "filters": {"assignee": "someone"}},
    )

    assert duplicate.status_code == 409
    assert forbidden.status_code == 403
    assert invalid_assignee.status_code == 422


@pytest.mark.anyio
async def test_audit_scoped_shared_views_are_hidden_without_audit_permission(client, make_user):
    owner = await _headers(client, make_user, email="audit-owner@vi.co", is_superuser=True)
    agent = await _headers(client, make_user, email="plain-reader@vi.co", roles=("agent",))
    created = await client.post(
        VIEWS,
        headers=owner,
        json={"name": "Audited conversations", "filters": {"has_audit": True}},
    )

    assert created.status_code == 201
    assert (await client.get(VIEWS, headers=agent)).json()["data"] == []
    assert len((await client.get(VIEWS, headers=owner)).json()["data"]) == 1


@pytest.mark.anyio
async def test_shared_views_are_tenant_isolated(client, make_user, session_factory):
    manager = await _headers(client, make_user, email="tenant-manager@vi.co", roles=("manager",))
    created = await client.post(
        VIEWS, headers=manager, json={"name": "Our view", "filters": {}}
    )
    async with session_factory() as session:
        actor = (
            await session.scalars(select(User).where(User.email == "tenant-manager@vi.co"))
        ).one()
        foreign_org = Organization(name="Foreign", slug="foreign-history")
        session.add(foreign_org)
        await session.flush()
        session.add(
            ConversationHistoryView(
                organization_id=foreign_org.id,
                created_by_user_id=actor.id,
                name="Foreign view",
                filters_json={},
            )
        )
        await session.commit()

    rows = (await client.get(VIEWS, headers=manager)).json()["data"]
    assert created.status_code == 201
    assert [row["name"] for row in rows] == ["Our view"]


@pytest.mark.anyio
async def test_shared_view_delete_is_audited_and_foreign_ids_are_not_found(
    client, make_user, session_factory
):
    manager = await _headers(client, make_user, email="delete-manager@vi.co", roles=("manager",))
    created = await client.post(
        VIEWS, headers=manager, json={"name": "Temporary", "filters": {"has_media": True}}
    )

    missing = await client.delete(f"{VIEWS}/{uuid.uuid4()}", headers=manager)
    deleted = await client.delete(f"{VIEWS}/{created.json()['id']}", headers=manager)

    assert missing.status_code == 404
    assert deleted.status_code == 204
    assert (await client.get(VIEWS, headers=manager)).json()["data"] == []
    async with session_factory() as session:
        actions = [row.action for row in (await session.scalars(select(AuditLog))).all()]
    assert "conversation_history_view.created" in actions
    assert "conversation_history_view.deleted" in actions


def test_openapi_declares_advanced_filters_and_shared_view_operations():
    from app.main import create_app

    schema = create_app().openapi()
    parameters = schema["paths"][CONVERSATIONS]["get"]["parameters"]
    assert {"from", "to", "campaign", "has_media", "has_audit"} <= {
        parameter["name"] for parameter in parameters
    }
    assert {"get", "post"} <= set(schema["paths"][VIEWS])
    assert "delete" in schema["paths"][f"{VIEWS}/{{view_id}}"]
