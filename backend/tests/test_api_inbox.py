"""Shared-inbox collaboration tests (Doc 04 §18.1; FR-INB) — Phase 7 Step 1.

The conversation is seeded through the real inbound path (``_inbound``), so these exercise the
collaboration layer over a genuine thread, not a hand-built row.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.audit import AuditLog
from app.models.conversation import (
    CONV_OPEN,
    CONV_PENDING,
    CONV_RESOLVED,
    CONV_SNOOZED,
    Conversation,
)
from app.models.internal_note import InternalNote
from app.models.user import User
from tests.test_api_conversations import _inbound
from tests.test_api_messages import _headers

CONVERSATIONS_URL = "/api/v1/conversations"


async def _conversation_id(session_factory) -> str:
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        return conv.public_id


async def _row_version(session_factory) -> int:
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        return conv.row_version


async def _user_id(session_factory, email: str) -> str:
    async with session_factory() as session:
        user = (await session.scalars(select(User).where(User.email == email))).first()
        return user.public_id


async def _deactivate(session_factory, email: str) -> None:
    async with session_factory() as session:
        user = (await session.scalars(select(User).where(User.email == email))).first()
        user.is_active = False
        await session.commit()


async def _seeded(client, make_user, session_factory, monkeypatch) -> tuple[dict, str]:
    """One inbound-seeded conversation and an agent (full inbox permissions)."""
    await _inbound(client, make_user, session_factory, monkeypatch)
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    return agent, await _conversation_id(session_factory)


async def _audit_actions(session_factory) -> list[str]:
    async with session_factory() as session:
        return [r.action for r in (await session.scalars(select(AuditLog))).all()]


# --- Assignment --------------------------------------------------------------
@pytest.mark.anyio
async def test_assign_sets_assignee(client, make_user, session_factory, monkeypatch, dispatched):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    assignee_id = await _user_id(session_factory, "agent@vi.co")
    before = await _row_version(session_factory)

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": assignee_id}
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assigned_to"] == assignee_id
    assert body["row_version"] == before + 1  # each write bumps the optimistic-lock counter
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        assert conv.assigned_user_id is not None
    assert "conversation.assigned" in await _audit_actions(session_factory)


@pytest.mark.anyio
async def test_reassign_changes_assignee(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    await _headers(client, make_user, email="second@vi.co", roles=("agent",))
    first = await _user_id(session_factory, "agent@vi.co")
    second = await _user_id(session_factory, "second@vi.co")

    first_resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": first}
    )
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": second}
    )

    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == second
    assert resp.json()["row_version"] == first_resp.json()["row_version"] + 1


@pytest.mark.anyio
async def test_assign_unknown_user_is_422(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign",
        headers=agent,
        json={"assignee_id": str(uuid.uuid4())},
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "assignee_invalid"


@pytest.mark.anyio
async def test_assign_inactive_user_is_422(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """A deactivated user cannot own a thread — assigning to one is invalid (Doc 04 §18.1)."""
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    await _headers(client, make_user, email="gone@vi.co", roles=("agent",))
    gone = await _user_id(session_factory, "gone@vi.co")
    await _deactivate(session_factory, "gone@vi.co")

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": gone}
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "assignee_invalid"


@pytest.mark.anyio
async def test_assign_requires_inbox_assign(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """A manager has inbox:read but not inbox:assign — assignment is forbidden."""
    _, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))
    assignee_id = await _user_id(session_factory, "mgr@vi.co")

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=manager, json={"assignee_id": assignee_id}
    )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_assign_unknown_conversation_is_404(client, make_user):
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{uuid.uuid4()}/assign",
        headers=agent,
        json={"assignee_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


# --- Status ------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("target", [CONV_PENDING, CONV_RESOLVED, CONV_SNOOZED, CONV_OPEN])
async def test_set_status(client, make_user, session_factory, monkeypatch, dispatched, target):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/status", headers=agent, json={"status": target}
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == target
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        assert conv.status == target
    assert "conversation.status_changed" in await _audit_actions(session_factory)


@pytest.mark.anyio
async def test_invalid_status_is_422(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/status", headers=agent, json={"status": "archived"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_status_requires_inbox_write(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """An analyst has no inbox permission at all — status changes are forbidden."""
    _, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/status", headers=analyst, json={"status": "resolved"}
    )
    assert resp.status_code == 403


# --- Notes -------------------------------------------------------------------
@pytest.mark.anyio
async def test_add_note(client, make_user, session_factory, monkeypatch, dispatched):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    author_id = await _user_id(session_factory, "agent@vi.co")

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent, json={"body": "Called back, VM."}
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["body"] == "Called back, VM."
    assert body["author"] == author_id
    async with session_factory() as session:
        assert len((await session.scalars(select(InternalNote))).all()) == 1
    assert "internal_note.added" in await _audit_actions(session_factory)


@pytest.mark.anyio
async def test_list_notes_oldest_first(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    for text in ("first", "second", "third"):
        await client.post(
            f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent, json={"body": text}
        )

    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent)

    assert resp.status_code == 200
    bodies = [n["body"] for n in resp.json()["data"]]
    assert bodies == ["first", "second", "third"]


@pytest.mark.anyio
async def test_delete_note_soft_deletes_and_hides(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    note_id = (
        await client.post(
            f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent, json={"body": "temp"}
        )
    ).json()["id"]

    resp = await client.delete(f"{CONVERSATIONS_URL}/{conv_id}/notes/{note_id}", headers=agent)

    assert resp.status_code == 204
    # Soft-deleted: the row survives for audit, the list read hides it.
    async with session_factory() as session:
        note = (await session.scalars(select(InternalNote))).first()
        assert note.deleted_at is not None
    listed = (await client.get(f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent)).json()
    assert listed["data"] == []
    assert "internal_note.deleted" in await _audit_actions(session_factory)


@pytest.mark.anyio
async def test_delete_unknown_note_is_404(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    resp = await client.delete(
        f"{CONVERSATIONS_URL}/{conv_id}/notes/{uuid.uuid4()}", headers=agent
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_empty_note_body_is_422(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=agent, json={"body": ""}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_add_note_requires_inbox_write(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """A manager can read the inbox but not write — listing notes is allowed, adding is not."""
    _, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))

    assert (await client.get(f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=manager)).status_code == 200
    post = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=manager, json={"body": "nope"}
    )
    assert post.status_code == 403


@pytest.mark.anyio
async def test_list_notes_requires_inbox_read(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """An analyst has no inbox:read — the notes list is forbidden."""
    _, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    resp = await client.get(f"{CONVERSATIONS_URL}/{conv_id}/notes", headers=analyst)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_notes_unknown_conversation_is_404(client, make_user):
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    resp = await client.get(f"{CONVERSATIONS_URL}/{uuid.uuid4()}/notes", headers=agent)
    assert resp.status_code == 404
