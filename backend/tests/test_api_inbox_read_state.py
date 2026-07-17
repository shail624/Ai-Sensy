"""Shared-inbox read-state tests (Doc 04 §18.1; FR-INB) — Phase 7 Step 3.

``POST /conversations/{uuid}/read`` resets the shared ``unread_count`` (Doc 03 §9.1). The frozen
schema has no last-read marker, so read state is exactly the denormalized counter going to zero:
these assert the reset, its idempotence, permission scope and 404.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.conversation import Conversation
from tests.test_api_inbox_reads import _add_conv, _base
from tests.test_api_messages import _headers

CONVERSATIONS_URL = "/api/v1/conversations"


async def _set_unread(session_factory, count: int) -> None:
    """Seed the (single) conversation's denormalized unread counter, as the inbound path would."""
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        conv.unread_count = count
        await session.commit()


async def _state(session_factory) -> tuple[int, int]:
    """(unread_count, row_version) for the seeded conversation."""
    async with session_factory() as session:
        conv = (await session.scalars(select(Conversation))).first()
        return conv.unread_count, conv.row_version


# --- Reset -------------------------------------------------------------------
@pytest.mark.anyio
async def test_read_resets_unread(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1911001")
    await _set_unread(session_factory, 5)

    resp = await client.post(f"{CONVERSATIONS_URL}/{conv_id}/read", headers=agent)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == conv_id
    assert body["unread_count"] == 0
    assert body["row_version"] == 1  # a real reset bumps the optimistic-lock counter (was 0)
    assert await _state(session_factory) == (0, 1)


@pytest.mark.anyio
async def test_read_when_already_read_is_noop(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """An already-read thread returns 0 without churning row_version/updated_at (idempotent)."""
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1911002")
    # unread_count defaults to 0 — nothing to reset.

    resp = await client.post(f"{CONVERSATIONS_URL}/{conv_id}/read", headers=agent)

    assert resp.status_code == 200, resp.text
    assert resp.json()["unread_count"] == 0
    assert resp.json()["row_version"] == 0  # no write, so no version bump
    assert await _state(session_factory) == (0, 0)


@pytest.mark.anyio
async def test_read_is_idempotent_across_calls(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """Reset once, then a second read is a no-op — the counter stays 0 and the version doesn't move."""
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1911003")
    await _set_unread(session_factory, 3)

    first = await client.post(f"{CONVERSATIONS_URL}/{conv_id}/read", headers=agent)
    second = await client.post(f"{CONVERSATIONS_URL}/{conv_id}/read", headers=agent)

    assert first.json()["row_version"] == 1
    assert second.json()["row_version"] == 1  # second call changed nothing, so no further bump
    assert await _state(session_factory) == (0, 1)


# --- Permission & not-found --------------------------------------------------
@pytest.mark.anyio
async def test_read_requires_inbox_write(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """A manager can read the inbox but not write — marking read is forbidden (inbox:write)."""
    _, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv_id = await _add_conv(session_factory, org, number, name="A", phone="+1911004")
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))

    resp = await client.post(f"{CONVERSATIONS_URL}/{conv_id}/read", headers=manager)

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_read_unknown_conversation_is_404(client, make_user):
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    resp = await client.post(f"{CONVERSATIONS_URL}/{uuid.uuid4()}/read", headers=agent)
    assert resp.status_code == 404


# --- Build ------------------------------------------------------------------
def test_read_endpoint_is_mounted() -> None:
    """The route is in the generated OpenAPI (build verification)."""
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert "/api/v1/conversations/{conversation_id}/read" in paths
    assert "post" in paths["/api/v1/conversations/{conversation_id}/read"]
