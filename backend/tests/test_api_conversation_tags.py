"""Conversation-tag tests (Doc 04 §18.1 v1.3; Doc 03 §9.7; FR-INB-07) — Phase 7 Step 5.

Add/remove classification tags, the additive `tags` array on list/detail reads, and the `tag`
filter. Conversations and tags are seeded directly (reusing the Step 2 read fixtures) so the
association behaviour is what these exercise.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.conversation_tag import conversation_tags
from app.models.tag import Tag
from tests.test_api_inbox_reads import _add_conv, _base
from tests.test_api_messages import _headers

CONVERSATIONS_URL = "/api/v1/conversations"


async def _add_tag(session_factory, org_id: int, *, name: str, color: str = "#22c55e") -> str:
    async with session_factory() as session:
        tag = Tag(organization_id=org_id, name=name, color=color)
        session.add(tag)
        await session.commit()
        return tag.public_id


async def _link_count(session_factory) -> int:
    async with session_factory() as session:
        return len((await session.execute(select(conversation_tags))).all())


# --- Add ---------------------------------------------------------------------
@pytest.mark.anyio
async def test_add_tags_returns_full_set(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955001")
    t1 = await _add_tag(session_factory, org, name="refund", color="#ef4444")
    t2 = await _add_tag(session_factory, org, name="vip", color="#22c55e")

    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1, t2]}
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert {t["name"] for t in data} == {"refund", "vip"}
    assert {t["id"] for t in data} == {t1, t2}
    assert all("color" in t for t in data)
    assert await _link_count(session_factory) == 2


@pytest.mark.anyio
async def test_add_is_idempotent(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955002")
    t1 = await _add_tag(session_factory, org, name="refund")

    await client.post(f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1]})
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1]}
    )

    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert await _link_count(session_factory) == 1  # re-add is a no-op


@pytest.mark.anyio
async def test_add_unknown_tag_is_422(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955003")
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [str(uuid.uuid4())]}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_add_empty_list_is_422(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955004")
    resp = await client.post(f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": []})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_add_over_limit_is_422(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955005")
    too_many = [str(uuid.uuid4()) for _ in range(51)]
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": too_many}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_add_requires_inbox_write(client, make_user, session_factory, monkeypatch, dispatched):
    _, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955006")
    t1 = await _add_tag(session_factory, org, name="refund")
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{conv}/tags", headers=manager, json={"tag_ids": [t1]}
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_add_unknown_conversation_is_404(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, *_ = await _base(client, make_user, session_factory, monkeypatch)
    t1 = await _add_tag(session_factory, org, name="refund")
    resp = await client.post(
        f"{CONVERSATIONS_URL}/{uuid.uuid4()}/tags", headers=agent, json={"tag_ids": [t1]}
    )
    assert resp.status_code == 404


# --- Remove ------------------------------------------------------------------
@pytest.mark.anyio
async def test_remove_tag(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955007")
    t1 = await _add_tag(session_factory, org, name="refund")
    await client.post(f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1]})

    resp = await client.delete(f"{CONVERSATIONS_URL}/{conv}/tags/{t1}", headers=agent)

    assert resp.status_code == 204
    assert await _link_count(session_factory) == 0


@pytest.mark.anyio
async def test_remove_unattached_tag_is_404(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955008")
    t1 = await _add_tag(session_factory, org, name="refund")  # exists but not attached
    resp = await client.delete(f"{CONVERSATIONS_URL}/{conv}/tags/{t1}", headers=agent)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_remove_requires_inbox_write(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955009")
    t1 = await _add_tag(session_factory, org, name="refund")
    await client.post(f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1]})
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))
    resp = await client.delete(f"{CONVERSATIONS_URL}/{conv}/tags/{t1}", headers=manager)
    assert resp.status_code == 403


# --- Tags in read responses --------------------------------------------------
@pytest.mark.anyio
async def test_list_and_detail_include_tags(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955010")
    t1 = await _add_tag(session_factory, org, name="refund", color="#ef4444")
    await client.post(f"{CONVERSATIONS_URL}/{conv}/tags", headers=agent, json={"tag_ids": [t1]})

    row = (await client.get(CONVERSATIONS_URL, headers=agent)).json()["data"][0]
    detail = (await client.get(f"{CONVERSATIONS_URL}/{conv}", headers=agent)).json()

    assert row["tags"] == [{"id": t1, "name": "refund", "color": "#ef4444"}]
    assert detail["tags"] == [{"id": t1, "name": "refund", "color": "#ef4444"}]


@pytest.mark.anyio
async def test_untagged_conversation_has_empty_tags(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    conv = await _add_conv(session_factory, org, number, name="A", phone="+1955011")
    detail = (await client.get(f"{CONVERSATIONS_URL}/{conv}", headers=agent)).json()
    assert detail["tags"] == []


# --- Filter ------------------------------------------------------------------
@pytest.mark.anyio
async def test_filter_by_tag(client, make_user, session_factory, monkeypatch, dispatched):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    tagged = await _add_conv(session_factory, org, number, name="Tagged", phone="+1955012")
    await _add_conv(session_factory, org, number, name="Plain", phone="+1955013")
    t1 = await _add_tag(session_factory, org, name="refund")
    await client.post(f"{CONVERSATIONS_URL}/{tagged}/tags", headers=agent, json={"tag_ids": [t1]})

    data = (await client.get(f"{CONVERSATIONS_URL}?tag={t1}", headers=agent)).json()["data"]

    assert [c["id"] for c in data] == [tagged]


@pytest.mark.anyio
async def test_filter_by_unknown_tag_is_empty(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, org, number = await _base(client, make_user, session_factory, monkeypatch)
    await _add_conv(session_factory, org, number, name="A", phone="+1955014")
    resp = await client.get(f"{CONVERSATIONS_URL}?tag={uuid.uuid4()}", headers=agent)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.anyio
async def test_filter_malformed_tag_is_400(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, *_ = await _base(client, make_user, session_factory, monkeypatch)
    resp = await client.get(f"{CONVERSATIONS_URL}?tag=not-a-uuid", headers=agent)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_multiple_tag_values_is_400(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, *_ = await _base(client, make_user, session_factory, monkeypatch)
    resp = await client.get(
        f"{CONVERSATIONS_URL}?tag={uuid.uuid4()}&tag={uuid.uuid4()}", headers=agent
    )
    assert resp.status_code == 400


# --- Build -------------------------------------------------------------------
def test_conversation_tag_endpoints_are_mounted() -> None:
    """Both tag routes are in the generated OpenAPI (build verification)."""
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert "post" in paths["/api/v1/conversations/{conversation_id}/tags"]
    assert "delete" in paths["/api/v1/conversations/{conversation_id}/tags/{tag_id}"]
