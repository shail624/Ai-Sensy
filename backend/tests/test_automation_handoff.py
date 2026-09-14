"""Published automation human-handoff contract into the existing Live Chat lifecycle."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.audit import AuditLog
from app.models.business_event import (
    BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED,
    BusinessEvent,
)
from app.models.conversation import CONV_OPEN, CONV_PENDING, CONV_RESOLVED, Conversation
from app.models.user import User
from tests.test_api_conversations import _inbound

PASSWORD = "Sup3r-Secret-Pass1"
AUTOMATIONS = "/api/v1/automations"


async def _headers(client, make_user, *, email: str, **kwargs) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kwargs)
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _handoff_graph() -> dict:
    return {
        "nodes": [
            {
                "id": "trigger-1",
                "kind": "trigger",
                "config": {"event": "message.received"},
            },
            {
                "id": "handoff-1",
                "kind": "handoff",
                "label": "Talk to a person",
                "config": {"reason": "Customer requested a human agent"},
            },
        ],
        "edges": [{"id": "edge-1", "source": "trigger-1", "target": "handoff-1"}],
    }


async def _seed(client, make_user, session_factory, monkeypatch) -> tuple[dict[str, str], str]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@vi.co", "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    owner = {"Authorization": f"Bearer {login.json()['access_token']}"}
    async with session_factory() as session:
        conversation = (await session.scalars(select(Conversation))).one()
        return owner, conversation.public_id


async def _published(client, owner: dict[str, str]) -> dict:
    created = await client.post(
        AUTOMATIONS,
        headers=owner,
        json={"name": "Human support", "graph": _handoff_graph()},
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"{AUTOMATIONS}/{created.json()['id']}/publish",
        headers=owner,
        json={"expected_row_version": created.json()["row_version"]},
    )
    assert published.status_code == 200, published.text
    return published.json()


def _execute_headers(owner: dict[str, str], key: uuid.UUID) -> dict[str, str]:
    return {**owner, "Idempotency-Key": str(key)}


async def test_published_handoff_requests_live_chat_once_and_replays_safely(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, conversation_id = await _seed(client, make_user, session_factory, monkeypatch)
    flow = await _published(client, owner)
    publisher = await _headers(
        client, make_user, email="handoff-publisher@example.com", roles=("manager",)
    )
    key = uuid.uuid4()
    path = f"{AUTOMATIONS}/{flow['id']}/handoffs"
    payload = {"conversation_id": conversation_id, "node_id": "handoff-1"}

    requested = await client.post(
        path, headers=_execute_headers(publisher, key), json=payload
    )
    replayed = await client.post(
        path, headers=_execute_headers(publisher, key), json=payload
    )

    assert requested.status_code == 201, requested.text
    assert requested.json()["outcome"] == "requested"
    assert requested.json()["replayed"] is False
    assert requested.json()["reason"] == "Customer requested a human agent"
    assert requested.json()["conversation"]["status"] == CONV_PENDING
    assert requested.json()["conversation"]["assigned_to"] is None
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["event_id"] == requested.json()["event_id"]
    assert replayed.json()["replayed"] is True
    assert replayed.json()["conversation"]["row_version"] == requested.json()["conversation"][
        "row_version"
    ]

    dirty = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}",
        headers=owner,
        json={"name": "Later draft edit", "expected_row_version": flow["row_version"]},
    )
    assert dirty.status_code == 200, dirty.text
    replay_after_edit = await client.post(
        path, headers=_execute_headers(publisher, key), json=payload
    )
    assert replay_after_edit.status_code == 200
    assert replay_after_edit.json()["event_id"] == requested.json()["event_id"]
    assert replay_after_edit.json()["replayed"] is True

    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(BusinessEvent)
                .where(
                    BusinessEvent.event_type
                    == BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED
                )
            )
            == 1
        )
        handoff_audits = await session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "automation.handoff_requested")
        )
        assert handoff_audits == 1
        event = (
            await session.scalars(
                select(BusinessEvent).where(
                    BusinessEvent.event_type
                    == BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED
                )
            )
        ).one()
        assert event.payload_json == {
            "automation_id": flow["id"],
            "version_no": 1,
            "node_id": "handoff-1",
            "reason": "Customer requested a human agent",
            "outcome": "requested",
        }


async def test_old_replay_never_requeues_an_intervened_chat(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, conversation_id = await _seed(client, make_user, session_factory, monkeypatch)
    flow = await _published(client, owner)
    first_key = uuid.uuid4()
    path = f"{AUTOMATIONS}/{flow['id']}/handoffs"
    payload = {"conversation_id": conversation_id, "node_id": "handoff-1"}
    await client.post(path, headers=_execute_headers(owner, first_key), json=payload)
    agent = await _headers(
        client, make_user, email="handoff-agent@example.com", roles=("agent",)
    )
    claimed = await client.post(
        f"/api/v1/conversations/{conversation_id}/intervene", headers=agent
    )
    assert claimed.status_code == 200, claimed.text

    replayed = await client.post(
        path, headers=_execute_headers(owner, first_key), json=payload
    )
    new_request = await client.post(
        path, headers=_execute_headers(owner, uuid.uuid4()), json=payload
    )

    assert replayed.status_code == 200
    assert replayed.json()["conversation"]["status"] == CONV_OPEN
    assert replayed.json()["conversation"]["assigned_to"] == claimed.json()["assigned_to"]
    assert new_request.status_code == 201
    assert new_request.json()["outcome"] == "already_intervened"
    assert new_request.json()["conversation"]["status"] == CONV_OPEN
    assert new_request.json()["conversation"]["assigned_to"] == claimed.json()["assigned_to"]


async def test_handoff_reopens_resolved_thread_and_clears_historical_owner(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, conversation_id = await _seed(client, make_user, session_factory, monkeypatch)
    flow = await _published(client, owner)
    async with session_factory() as session:
        owner_user = (await session.scalars(select(User).where(User.email == "owner@vi.co"))).one()
        owner_id = owner_user.public_id
    assert (
        await client.post(
            f"/api/v1/conversations/{conversation_id}/assign",
            headers=owner,
            json={"assignee_id": owner_id},
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/api/v1/conversations/{conversation_id}/status",
            headers=owner,
            json={"status": CONV_RESOLVED},
        )
    ).status_code == 200

    response = await client.post(
        f"{AUTOMATIONS}/{flow['id']}/handoffs",
        headers=_execute_headers(owner, uuid.uuid4()),
        json={"conversation_id": conversation_id, "node_id": "handoff-1"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["outcome"] == "requested"
    assert response.json()["conversation"]["status"] == CONV_PENDING
    assert response.json()["conversation"]["assigned_to"] is None


async def test_handoff_requires_publisher_and_clean_active_node(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, conversation_id = await _seed(client, make_user, session_factory, monkeypatch)
    flow = await _published(client, owner)
    agent = await _headers(
        client, make_user, email="handoff-no-publish@example.com", roles=("agent",)
    )
    path = f"{AUTOMATIONS}/{flow['id']}/handoffs"
    payload = {"conversation_id": conversation_id, "node_id": "handoff-1"}
    assert (
        await client.post(
            path, headers=_execute_headers(agent, uuid.uuid4()), json=payload
        )
    ).status_code == 403

    wrong_node = await client.post(
        path,
        headers=_execute_headers(owner, uuid.uuid4()),
        json={**payload, "node_id": "trigger-1"},
    )
    assert wrong_node.status_code == 422
    assert wrong_node.json()["code"] == "automation_handoff_invalid"

    dirty = await client.patch(
        f"{AUTOMATIONS}/{flow['id']}",
        headers=owner,
        json={"name": "Unpublished handoff change", "expected_row_version": flow["row_version"]},
    )
    assert dirty.status_code == 200, dirty.text
    blocked = await client.post(
        path, headers=_execute_headers(owner, uuid.uuid4()), json=payload
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "automation_handoff_conflict"
