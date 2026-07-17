"""Shared-inbox read tests (Doc 04 §18.1; FR-INB) — Phase 7 Step 2.

Conversations are seeded directly so ordering, filtering and search are deterministic — the read
side is what these exercise, not the inbound path (covered elsewhere).
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.conversation import (
    CONV_OPEN,
    CONV_PENDING,
    CONV_RESOLVED,
    Conversation,
)
from app.models.message import DIRECTION_INBOUND, DIRECTION_OUTBOUND, MSG_SENT, Message
from app.models.user import User
from app.models.waba import PhoneNumber
from tests.test_api_messages import _headers
from tests.test_api_webhooks import _seed_number

CONVERSATIONS_URL = "/api/v1/conversations"


async def _base(client, make_user, session_factory, monkeypatch) -> tuple[dict, int, int]:
    """A synced number + an agent; returns (agent headers, org id, number id)."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    async with session_factory() as session:
        number = (await session.scalars(select(PhoneNumber))).first()
        return agent, number.organization_id, number.id


async def _user_pk_and_uuid(session_factory, email: str) -> tuple[int, str]:
    async with session_factory() as session:
        user = (await session.scalars(select(User).where(User.email == email))).first()
        return user.id, user.public_id


async def _add_conv(
    session_factory,
    org_id: int,
    number_id: int,
    *,
    name: str,
    phone: str,
    status: str = CONV_OPEN,
    assigned_user_id: int | None = None,
    minutes_ago: int = 0,
    preview: str = "hello",
    inbound_minutes_ago: int | None = None,
) -> str:
    async with session_factory() as session:
        contact = Contact(
            organization_id=org_id,
            wa_id=phone.lstrip("+"),
            phone_e164=phone,
            full_name=name,
            source="manual",
        )
        session.add(contact)
        await session.flush()
        last_inbound = (
            None if inbound_minutes_ago is None else utcnow() - timedelta(minutes=inbound_minutes_ago)
        )
        conv = Conversation(
            organization_id=org_id,
            phone_number_id=number_id,
            contact_id=contact.id,
            status=status,
            assigned_user_id=assigned_user_id,
            last_message_at=utcnow() - timedelta(minutes=minutes_ago),
            last_message_preview=preview,
            last_inbound_at=last_inbound,
            window_expires_at=(last_inbound + timedelta(hours=24)) if last_inbound else None,
        )
        session.add(conv)
        await session.commit()
        return conv.public_id


# --- List: ordering & pagination ---------------------------------------------
@pytest.mark.anyio
async def test_list_orders_by_recent_activity(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="Old", phone="+15550001", minutes_ago=60)
    await _add_conv(session_factory, org, number, name="New", phone="+15550002", minutes_ago=1)
    await _add_conv(session_factory, org, number, name="Mid", phone="+15550003", minutes_ago=30)

    resp = await client.get(CONVERSATIONS_URL, headers=agent)

    assert resp.status_code == 200, resp.text
    names = [c["contact"]["name"] for c in resp.json()["data"]]
    assert names == ["New", "Mid", "Old"]


@pytest.mark.anyio
async def test_list_paginates_with_cursor(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    for i in range(5):
        await _add_conv(
            session_factory, org, number, name=f"C{i}", phone=f"+1666000{i}", minutes_ago=i
        )

    first = (await client.get(f"{CONVERSATIONS_URL}?limit=2", headers=agent)).json()
    assert len(first["data"]) == 2
    assert first["page"]["has_more"] is True
    cursor = first["page"]["next_cursor"]
    assert cursor

    second = (
        await client.get(f"{CONVERSATIONS_URL}?limit=2&cursor={cursor}", headers=agent)
    ).json()
    assert len(second["data"]) == 2
    # No overlap between pages.
    assert {c["id"] for c in first["data"]}.isdisjoint({c["id"] for c in second["data"]})


# --- List: filters -----------------------------------------------------------
@pytest.mark.anyio
async def test_filter_by_status(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="A", phone="+1777001", status=CONV_OPEN)
    await _add_conv(session_factory, org, number, name="B", phone="+1777002", status=CONV_RESOLVED)
    await _add_conv(session_factory, org, number, name="C", phone="+1777003", status=CONV_PENDING)

    resp = await client.get(f"{CONVERSATIONS_URL}?status={CONV_RESOLVED}", headers=agent)

    data = resp.json()["data"]
    assert [c["contact"]["name"] for c in data] == ["B"]
    assert data[0]["status"] == CONV_RESOLVED


@pytest.mark.anyio
async def test_filter_by_assignee_and_unassigned(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    agent_pk, agent_uuid = await _user_pk_and_uuid(session_factory, "agent@vi.co")
    await _add_conv(
        session_factory, org, number, name="Mine", phone="+1788001", assigned_user_id=agent_pk
    )
    await _add_conv(session_factory, org, number, name="Free", phone="+1788002")

    mine = (await client.get(f"{CONVERSATIONS_URL}?assignee={agent_uuid}", headers=agent)).json()
    assert [c["contact"]["name"] for c in mine["data"]] == ["Mine"]
    assert mine["data"][0]["assigned_to"] == agent_uuid

    free = (await client.get(f"{CONVERSATIONS_URL}?assignee=unassigned", headers=agent)).json()
    assert [c["contact"]["name"] for c in free["data"]] == ["Free"]
    assert free["data"][0]["assigned_to"] is None


@pytest.mark.anyio
async def test_unknown_assignee_returns_empty(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """A real-looking but absent assignee matches nothing — an empty page, not an error."""
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="A", phone="+1799001")

    resp = await client.get(f"{CONVERSATIONS_URL}?assignee={uuid.uuid4()}", headers=agent)

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.anyio
async def test_malformed_assignee_is_400(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    resp = await client.get(f"{CONVERSATIONS_URL}?assignee=not-a-uuid", headers=agent)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_filter_by_number(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="A", phone="+1811001")
    async with session_factory() as session:
        number_uuid = (await session.scalars(select(PhoneNumber))).first().public_id

    resp = await client.get(f"{CONVERSATIONS_URL}?number={number_uuid}", headers=agent)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["phone_number_id"] == number_uuid


# --- List: search ------------------------------------------------------------
@pytest.mark.anyio
async def test_search_by_contact_name_and_phone(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="Priya Raman", phone="+14150000001")
    await _add_conv(session_factory, org, number, name="John Doe", phone="+14150000002")

    by_name = (await client.get(f"{CONVERSATIONS_URL}?q=priya", headers=agent)).json()
    assert [c["contact"]["name"] for c in by_name["data"]] == ["Priya Raman"]

    by_phone = (await client.get(f"{CONVERSATIONS_URL}?q=0000002", headers=agent)).json()
    assert [c["contact"]["name"] for c in by_phone["data"]] == ["John Doe"]


# --- List: permission & content ----------------------------------------------
@pytest.mark.anyio
async def test_list_requires_inbox_read(
    client, make_user, session_factory, monkeypatch, dispatched
):
    await _base(client, make_user, session_factory, monkeypatch)
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    resp = await client.get(CONVERSATIONS_URL, headers=analyst)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_list_row_surfaces_unread_and_window(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """The denormalized unread_count is surfaced read-only, and window state is computed."""
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(
        session_factory, org, number, name="A", phone="+1822001", inbound_minutes_ago=60
    )

    row = (await client.get(CONVERSATIONS_URL, headers=agent)).json()["data"][0]

    assert "unread_count" in row
    assert row["window"]["is_open"] is True  # inbound 60m ago → still inside the 24h window
    assert row["window"]["expires_at"] is not None


# --- Detail ------------------------------------------------------------------
@pytest.mark.anyio
async def test_detail_returns_window_and_refs(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(
        session_factory, org, number, name="Ada", phone="+1833001", inbound_minutes_ago=1
    )

    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}", headers=agent)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == conv_id
    assert body["contact"]["name"] == "Ada"
    assert body["phone_number_id"] is not None
    assert body["window"]["is_open"] is True


@pytest.mark.anyio
async def test_detail_unknown_is_404(client, make_user, session_factory, monkeypatch, dispatched):
    agent, *_ = await _base(client, make_user, session_factory, monkeypatch)
    resp = await client.get(f"{CONVERSATIONS_URL}/{uuid.uuid4()}", headers=agent)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_detail_requires_inbox_read(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1844001")
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}", headers=analyst)
    assert resp.status_code == 403


# --- Message history ---------------------------------------------------------
async def _add_message(
    session_factory, conv, *, direction: str, body: str, minutes_ago: int
) -> None:
    async with session_factory() as session:
        c = (
            await session.scalars(
                select(Conversation).where(Conversation.uuid == uuid.UUID(conv).bytes)
            )
        ).first()
        session.add(
            Message(
                organization_id=c.organization_id,
                conversation_id=c.id,
                phone_number_id=c.phone_number_id,
                contact_id=c.contact_id,
                direction=direction,
                message_type="text",
                status=MSG_SENT,
                content_json={"body": body},
                created_at=utcnow() - timedelta(minutes=minutes_ago),
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_messages_newest_first(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1855001")
    await _add_message(session_factory, conv_id, direction=DIRECTION_INBOUND, body="first", minutes_ago=10)
    await _add_message(session_factory, conv_id, direction=DIRECTION_OUTBOUND, body="reply", minutes_ago=5)
    await _add_message(session_factory, conv_id, direction=DIRECTION_INBOUND, body="latest", minutes_ago=1)

    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}/messages", headers=agent)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert [m["content"]["body"] for m in data] == ["latest", "reply", "first"]
    assert all(m["conversation_id"] == conv_id for m in data)


@pytest.mark.anyio
async def test_messages_paginate(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1866001")
    for i in range(4):
        await _add_message(
            session_factory, conv_id, direction=DIRECTION_INBOUND, body=f"m{i}", minutes_ago=i
        )

    first = (
        await client.get(f"{CONVERSATIONS_URL}/{conv_id}/messages?limit=2", headers=agent)
    ).json()
    assert len(first["data"]) == 2
    assert first["page"]["has_more"] is True
    cursor = first["page"]["next_cursor"]
    second = (
        await client.get(
            f"{CONVERSATIONS_URL}/{conv_id}/messages?limit=2&cursor={cursor}", headers=agent
        )
    ).json()
    assert len(second["data"]) == 2
    assert {m["id"] for m in first["data"]}.isdisjoint({m["id"] for m in second["data"]})


@pytest.mark.anyio
async def test_messages_unknown_conversation_is_404(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, *_ = await _base(client, make_user, session_factory, monkeypatch)
    resp = await client.get(f"{CONVERSATIONS_URL}/{uuid.uuid4()}/messages", headers=agent)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_messages_requires_inbox_read(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1877001")
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}/messages", headers=analyst)
    assert resp.status_code == 403
