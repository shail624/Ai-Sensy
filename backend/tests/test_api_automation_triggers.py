"""Durable business-event and automation trigger receipt contracts (Design Book 24)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.automation import AutomationTriggerReceipt
from app.models.business_event import BUSINESS_EVENT_ACTOR_USER, BusinessEvent
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.user import User
from app.services.business_event_service import BusinessEventService

PASSWORD = "Sup3r-Secret-Pass1"
AUTOMATIONS = "/api/v1/automations"


async def _headers(client, make_user, *, email: str, **kwargs) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kwargs)
    return await _login(client, email)


async def _login(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _graph(event: str = "contact.created") -> dict:
    return {
        "nodes": [{"id": "trigger-1", "kind": "trigger", "config": {"event": event}}],
        "edges": [],
    }


async def _published(client, headers, name: str, event: str = "contact.created") -> dict:
    created = await client.post(
        AUTOMATIONS,
        headers=headers,
        json={"name": name, "graph": _graph(event)},
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"{AUTOMATIONS}/{created.json()['id']}/publish", headers=headers, json={}
    )
    assert published.status_code == 200, published.text
    return published.json()


async def test_contact_created_records_safe_idempotent_receipt(
    client, make_user, session_factory
) -> None:
    owner = await _headers(client, make_user, email="trigger-owner@example.com", is_superuser=True)
    flow = await _published(client, owner, "New contact intake")

    created = await client.post(
        "/api/v1/contacts",
        headers=owner,
        json={
            "phone_e164": "+14155550131",
            "full_name": "Receipt Privacy Check",
            "opt_in_status": "opted_in",
        },
    )
    assert created.status_code == 201, created.text

    response = await client.get(f"{AUTOMATIONS}/{flow['id']}/trigger-receipts", headers=owner)
    assert response.status_code == 200, response.text
    receipts = response.json()["data"]
    assert len(receipts) == 1
    assert receipts[0]["event_type"] == "contact.created"
    assert receipts[0]["event_version"] == receipts[0]["version_no"] == 1
    assert receipts[0]["status"] == "received"
    assert receipts[0]["source"] == "contacts"

    async with session_factory() as session:
        event = (await session.scalars(select(BusinessEvent))).one()
        contact = (await session.scalars(select(Contact))).one()
        assert event.payload_json == {
            "contact_id": created.json()["id"],
            "source": "manual",
            "opt_in_status": "opted_in",
        }
        serialized = str(event.payload_json)
        assert "+14155550131" not in serialized
        assert "Receipt Privacy Check" not in serialized

        await BusinessEventService(session).record_contact_created(
            contact=contact,
            actor_type=BUSINESS_EVENT_ACTOR_USER,
            actor_id=None,
            occurred_at=event.occurred_at,
            source="contacts",
        )
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(BusinessEvent)) == 1
        assert await session.scalar(select(func.count()).select_from(AutomationTriggerReceipt)) == 1


async def test_only_enabled_clean_matching_publications_receive_events(client, make_user) -> None:
    owner = await _headers(client, make_user, email="trigger-filter@example.com", is_superuser=True)
    clean = await _published(client, owner, "Clean contact flow")
    wrong = await _published(client, owner, "Inbound message flow", "message.received")
    disabled = await _published(client, owner, "Disabled contact flow")
    dirty = await _published(client, owner, "Dirty contact flow")

    disabled_response = await client.post(
        f"{AUTOMATIONS}/{disabled['id']}/disable",
        headers=owner,
        json={"expected_row_version": disabled["row_version"]},
    )
    assert disabled_response.status_code == 200, disabled_response.text
    dirty_response = await client.patch(
        f"{AUTOMATIONS}/{dirty['id']}",
        headers=owner,
        json={
            "name": "Dirty unpublished name",
            "expected_row_version": dirty["row_version"],
        },
    )
    assert dirty_response.status_code == 200, dirty_response.text

    created = await client.post(
        "/api/v1/contacts",
        headers=owner,
        json={"phone_e164": "+14155550132"},
    )
    assert created.status_code == 201, created.text

    async def receipt_count(flow_id: str) -> int:
        response = await client.get(f"{AUTOMATIONS}/{flow_id}/trigger-receipts", headers=owner)
        assert response.status_code == 200, response.text
        return len(response.json()["data"])

    assert await receipt_count(clean["id"]) == 1
    assert await receipt_count(wrong["id"]) == 0
    assert await receipt_count(disabled["id"]) == 0
    assert await receipt_count(dirty["id"]) == 0


async def test_receipt_history_is_read_only_and_tenant_scoped(
    client, make_user, session_factory
) -> None:
    manager = await _headers(
        client, make_user, email="trigger-manager@example.com", roles=("manager",)
    )
    analyst = await _headers(
        client, make_user, email="trigger-analyst@example.com", roles=("analyst",)
    )
    nobody = await _headers(client, make_user, email="trigger-nobody@example.com")
    flow = await _published(client, manager, "Tenant receipt flow")
    assert (
        await client.post(
            "/api/v1/contacts",
            headers=manager,
            json={"phone_e164": "+14155550133"},
        )
    ).status_code == 201
    assert (
        await client.get(f"{AUTOMATIONS}/{flow['id']}/trigger-receipts", headers=analyst)
    ).status_code == 200
    assert (
        await client.get(f"{AUTOMATIONS}/{flow['id']}/trigger-receipts", headers=nobody)
    ).status_code == 403

    async with session_factory() as session:
        other_org = Organization(name="Other trigger tenant", slug="other-trigger")
        session.add(other_org)
        await session.flush()
        session.add(
            User(
                organization_id=other_org.id,
                email="trigger-other@example.com",
                password_hash=hash_password(PASSWORD),
                full_name="Other Owner",
                is_active=True,
                is_superuser=True,
            )
        )
        await session.commit()
    other = await _login(client, "trigger-other@example.com")
    assert (
        await client.get(f"{AUTOMATIONS}/{flow['id']}/trigger-receipts", headers=other)
    ).status_code == 404


def test_openapi_mounts_trigger_receipt_history() -> None:
    from app.main import create_app

    assert "/api/v1/automations/{automation_id}/trigger-receipts" in create_app().openapi()["paths"]
