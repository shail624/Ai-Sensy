"""Message reaction tests (Doc 04 §18.2 v1.4; Doc 07 §5.2a) — Phase 7 Step 9.

An outbound reaction travels the send accept→deliver path: a ``reaction`` ledger row is written and
handed to ``sends.priority``; provider payload shaping stays in the Meta adapter. Reuses the Module 4
send fixtures (captured dispatch, in-memory idempotency) — the accept path never calls Meta.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import MagicMock

from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.channels.capabilities import Capability
from app.channels.meta.adapter import MetaChannelAdapter
from app.channels.models import MessageType, OutboundMessage, ReactionContent
from app.db.mixins import utcnow
from app.models.conversation import Conversation
from app.models.message import DIRECTION_INBOUND, Message
from tests.test_api_conversations import _rows
from tests.test_api_messages import _body, _headers, _key, _number_id, _open_window


def _react_url(message_uuid: str) -> str:
    return f"/api/v1/messages/{message_uuid}/reaction"


async def _agent(client, make_user, session_factory, monkeypatch) -> tuple[dict, Message]:
    """An open-window thread + the customer's inbound target message, and a sender's headers."""
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    target = next(
        m for m in await _rows(session_factory, Message) if m.direction == DIRECTION_INBOUND
    )
    assert target.wamid  # an inbound message always carries the channel's id
    return headers, target


async def _reactions(session_factory) -> list[Message]:
    return [m for m in await _rows(session_factory, Message) if m.message_type == "reaction"]


# --- Accept ------------------------------------------------------------------
async def test_react_accepts_and_queues(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)

    resp = await client.post(
        _react_url(target.public_id), headers=headers | _key(), json={"emoji": "👍"}
    )

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["wamid"] is None and body["conversation_id"]
    (reaction,) = await _reactions(session_factory)
    assert reaction.direction == "outbound"
    assert reaction.content_json == {"reaction": {"message_id": target.wamid, "emoji": "👍"}}
    assert sent == [reaction.id]  # handed to sends.priority


async def test_react_remove_with_empty_emoji(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        _react_url(target.public_id), headers=headers | _key(), json={"emoji": ""}
    )
    assert resp.status_code == 202, resp.text
    (reaction,) = await _reactions(session_factory)
    assert reaction.content_json["reaction"]["emoji"] == ""  # empty = remove


async def test_react_invalid_emoji_is_422(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        _react_url(target.public_id), headers=headers | _key(), json={"emoji": "hi"}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_emoji"


async def test_react_multiple_emoji_is_422(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        _react_url(target.public_id), headers=headers | _key(), json={"emoji": "👍👎"}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_emoji"


async def test_react_unknown_message_is_404(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, _ = await _agent(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        _react_url(str(uuid.uuid4())), headers=headers | _key(), json={"emoji": "👍"}
    )
    assert resp.status_code == 404


async def test_react_without_wamid_is_not_reactable(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, _ = await _agent(client, make_user, session_factory, monkeypatch)
    # An accepted outbound send has no wamid until the channel acknowledges it.
    await client.post("/api/v1/messages/send", headers=headers | _key(), json=_body(await _number_id(client, headers)))
    outbound = next(
        m
        for m in await _rows(session_factory, Message)
        if m.direction == "outbound" and m.wamid is None
    )
    resp = await client.post(
        _react_url(outbound.public_id), headers=headers | _key(), json={"emoji": "👍"}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "not_reactable"


async def test_react_window_closed_is_422(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        conv.window_expires_at = utcnow() - timedelta(hours=1)
        conv.is_window_open = False
        await session.commit()

    resp = await client.post(
        _react_url(target.public_id), headers=headers | _key(), json={"emoji": "👍"}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "window_closed"


# --- Permission & idempotency ------------------------------------------------
async def test_react_requires_messages_send(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    _, target = await _agent(client, make_user, session_factory, monkeypatch)
    viewer = await _headers(client, make_user, email="viewer@vi.co")  # no roles → no messages:send
    resp = await client.post(
        _react_url(target.public_id), headers=viewer | _key(), json={"emoji": "👍"}
    )
    assert resp.status_code == 403


async def test_react_requires_idempotency_key(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
):
    headers, target = await _agent(client, make_user, session_factory, monkeypatch)
    resp = await client.post(_react_url(target.public_id), headers=headers, json={"emoji": "👍"})
    assert resp.status_code == 422  # Idempotency-Key required (Doc 04 §8)


# --- Adapter (provider payload stays behind the seam) ------------------------
def test_meta_adapter_declares_reaction():
    assert Capability.REACTION in MetaChannelAdapter.capabilities


def test_meta_adapter_builds_reaction_payload():
    adapter = MetaChannelAdapter(client=MagicMock())
    payload = adapter._payload(
        OutboundMessage(
            to="15550001",
            type=MessageType.REACTION,
            content=ReactionContent(message_id="wamid.TARGET", emoji="👍"),
        )
    )
    assert payload["to"] == "15550001"
    assert payload["type"] == "reaction"
    assert payload["reaction"] == {"message_id": "wamid.TARGET", "emoji": "👍"}


def test_reaction_endpoint_is_mounted():
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert "post" in paths["/api/v1/messages/{message_id}/reaction"]
