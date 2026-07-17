"""Quick-reply tests (Doc 04 §18.2; Doc 03 §9.5; FR-INB-04) — Phase 7 Step 4.

CRUD for personal/shared canned messages: visibility scoping, shortcut-uniqueness (409), soft
delete, and the inbox:read/inbox:write permission split. Users share one org (the ``organization``
fixture), so a second agent exercises the personal-vs-shared boundary.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.quick_reply import QuickReply
from tests.test_api_messages import _headers

QR_URL = "/api/v1/quick-replies"


async def _agent(client, make_user, email: str = "agent@vi.co") -> dict:
    return await _headers(client, make_user, email=email, roles=("agent",))


async def _create(
    client, headers, *, shortcut: str, title: str = "Greeting", body: str = "Hello!", shared: bool = False
):
    return await client.post(
        QR_URL,
        headers=headers,
        json={"shortcut": shortcut, "title": title, "body": body, "shared": shared},
    )


async def _shortcuts(client, headers) -> list[str]:
    data = (await client.get(QR_URL, headers=headers)).json()["data"]
    return [q["shortcut"] for q in data]


async def _row(session_factory, shortcut: str) -> QuickReply | None:
    async with session_factory() as session:
        return (
            await session.scalars(select(QuickReply).where(QuickReply.shortcut == shortcut))
        ).first()


# --- Create ------------------------------------------------------------------
@pytest.mark.anyio
async def test_create_personal_by_default(client, make_user, session_factory):
    agent = await _agent(client, make_user)

    resp = await _create(client, agent, shortcut="/hi", title="Hi", body="Hello there")

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["shortcut"] == "/hi"
    assert body["shared"] is False
    assert body["usage_count"] == 0
    assert "/hi" in await _shortcuts(client, agent)
    row = await _row(session_factory, "/hi")
    assert row.owner_user_id is not None and row.created_by == row.owner_user_id


@pytest.mark.anyio
async def test_create_shared(client, make_user):
    agent = await _agent(client, make_user)
    resp = await _create(client, agent, shortcut="/team", shared=True)
    assert resp.status_code == 201, resp.text
    assert resp.json()["shared"] is True


# --- Visibility --------------------------------------------------------------
@pytest.mark.anyio
async def test_list_shows_own_personal_and_all_shared(client, make_user):
    agent = await _agent(client, make_user, email="agent@vi.co")
    other = await _agent(client, make_user, email="other@vi.co")
    await _create(client, agent, shortcut="/mine")
    await _create(client, other, shortcut="/theirs")
    await _create(client, other, shortcut="/shared", shared=True)

    seen = await _shortcuts(client, agent)

    assert "/mine" in seen
    assert "/shared" in seen  # shared is visible to everyone
    assert "/theirs" not in seen  # another user's personal reply is invisible


# --- Shortcut uniqueness -----------------------------------------------------
@pytest.mark.anyio
async def test_duplicate_personal_shortcut_is_409(client, make_user):
    agent = await _agent(client, make_user)
    assert (await _create(client, agent, shortcut="/dup")).status_code == 201
    resp = await _create(client, agent, shortcut="/dup")
    assert resp.status_code == 409
    assert resp.json()["code"] == "quick_reply_shortcut_conflict"


@pytest.mark.anyio
async def test_duplicate_shared_shortcut_is_409(client, make_user):
    agent = await _agent(client, make_user)
    assert (await _create(client, agent, shortcut="/s", shared=True)).status_code == 201
    resp = await _create(client, agent, shortcut="/s", shared=True)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_personal_shortcut_is_per_user(client, make_user):
    """Two users may each own the same personal shortcut — scope is (org, owner)."""
    agent = await _agent(client, make_user, email="agent@vi.co")
    other = await _agent(client, make_user, email="other@vi.co")
    assert (await _create(client, agent, shortcut="/x")).status_code == 201
    assert (await _create(client, other, shortcut="/x")).status_code == 201


@pytest.mark.anyio
async def test_deleted_shortcut_can_be_reused(client, make_user):
    agent = await _agent(client, make_user)
    qr_id = (await _create(client, agent, shortcut="/reuse")).json()["id"]
    assert (await client.delete(f"{QR_URL}/{qr_id}", headers=agent)).status_code == 204
    assert (await _create(client, agent, shortcut="/reuse")).status_code == 201


# --- Update ------------------------------------------------------------------
@pytest.mark.anyio
async def test_update_edits_fields(client, make_user):
    agent = await _agent(client, make_user)
    qr_id = (await _create(client, agent, shortcut="/a", title="Old", body="old")).json()["id"]

    resp = await client.patch(
        f"{QR_URL}/{qr_id}", headers=agent, json={"title": "New", "body": "new"}
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "New"
    assert body["body"] == "new"
    assert body["shortcut"] == "/a"  # untouched


@pytest.mark.anyio
async def test_update_can_change_shortcut(client, make_user):
    agent = await _agent(client, make_user)
    qr_id = (await _create(client, agent, shortcut="/a")).json()["id"]
    resp = await client.patch(f"{QR_URL}/{qr_id}", headers=agent, json={"shortcut": "/z"})
    assert resp.status_code == 200
    assert resp.json()["shortcut"] == "/z"


@pytest.mark.anyio
async def test_update_shortcut_conflict_is_409(client, make_user):
    agent = await _agent(client, make_user)
    await _create(client, agent, shortcut="/a")
    qr_b = (await _create(client, agent, shortcut="/b")).json()["id"]

    resp = await client.patch(f"{QR_URL}/{qr_b}", headers=agent, json={"shortcut": "/a"})

    assert resp.status_code == 409
    assert resp.json()["code"] == "quick_reply_shortcut_conflict"


@pytest.mark.anyio
async def test_update_unknown_is_404(client, make_user):
    agent = await _agent(client, make_user)
    resp = await client.patch(f"{QR_URL}/{uuid.uuid4()}", headers=agent, json={"title": "x"})
    assert resp.status_code == 404


# --- Delete ------------------------------------------------------------------
@pytest.mark.anyio
async def test_delete_soft_deletes_and_hides(client, make_user, session_factory):
    agent = await _agent(client, make_user)
    qr_id = (await _create(client, agent, shortcut="/gone")).json()["id"]

    resp = await client.delete(f"{QR_URL}/{qr_id}", headers=agent)

    assert resp.status_code == 204
    assert "/gone" not in await _shortcuts(client, agent)
    row = await _row(session_factory, "/gone")
    assert row.deleted_at is not None  # soft-deleted, row retained


@pytest.mark.anyio
async def test_delete_unknown_is_404(client, make_user):
    agent = await _agent(client, make_user)
    resp = await client.delete(f"{QR_URL}/{uuid.uuid4()}", headers=agent)
    assert resp.status_code == 404


# --- Cross-user authorization ------------------------------------------------
@pytest.mark.anyio
async def test_cannot_manage_others_personal_reply(client, make_user):
    """Another user's personal reply is a 404 to edit or delete — existence never leaks."""
    agent = await _agent(client, make_user, email="agent@vi.co")
    other = await _agent(client, make_user, email="other@vi.co")
    qr_id = (await _create(client, agent, shortcut="/private")).json()["id"]

    assert (
        await client.patch(f"{QR_URL}/{qr_id}", headers=other, json={"title": "x"})
    ).status_code == 404
    assert (await client.delete(f"{QR_URL}/{qr_id}", headers=other)).status_code == 404


@pytest.mark.anyio
async def test_shared_reply_manageable_by_any_writer(client, make_user):
    """A shared reply is a team resource — another inbox:write member can edit and delete it."""
    agent = await _agent(client, make_user, email="agent@vi.co")
    other = await _agent(client, make_user, email="other@vi.co")
    qr_id = (await _create(client, agent, shortcut="/team", shared=True)).json()["id"]

    edit = await client.patch(f"{QR_URL}/{qr_id}", headers=other, json={"title": "Team edit"})
    assert edit.status_code == 200
    assert (await client.delete(f"{QR_URL}/{qr_id}", headers=other)).status_code == 204


# --- Permissions & validation ------------------------------------------------
@pytest.mark.anyio
async def test_write_requires_inbox_write(client, make_user):
    """A manager reads the inbox but cannot write — listing is allowed, creating is not."""
    await _agent(client, make_user)  # ensure the org exists with a seeded agent
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))

    assert (await client.get(QR_URL, headers=manager)).status_code == 200
    assert (await _create(client, manager, shortcut="/nope")).status_code == 403


@pytest.mark.anyio
async def test_list_requires_inbox_read(client, make_user):
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    assert (await client.get(QR_URL, headers=analyst)).status_code == 403


@pytest.mark.anyio
async def test_empty_shortcut_is_422(client, make_user):
    agent = await _agent(client, make_user)
    resp = await _create(client, agent, shortcut="")
    assert resp.status_code == 422


# --- Build -------------------------------------------------------------------
def test_quick_reply_endpoints_are_mounted() -> None:
    """All four routes are in the generated OpenAPI (build verification)."""
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert set(paths["/api/v1/quick-replies"]) >= {"get", "post"}
    assert set(paths["/api/v1/quick-replies/{quick_reply_id}"]) >= {"patch", "delete"}
