"""A user's sign-in history (Team Management: login history; Audit Timeline: login evidence).

The audit trail already records successes, rejected passwords and lockouts with their source
address. This endpoint reads that rather than keeping a second copy, so these tests are mostly
about what is *included* and who is allowed to see it.
"""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"
USERS_URL = "/api/v1/users"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _history(client, headers, user_id: str, **params):
    return await client.get(f"{USERS_URL}/{user_id}/login-history", headers=headers, params=params)


async def test_a_successful_sign_in_appears_with_its_outcome(client, make_user) -> None:
    created = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    body = (await _history(client, headers, created.user.public_id)).json()

    assert [entry["action"] for entry in body["data"]] == ["user.login"]


async def test_failures_are_included_not_just_successes(client, make_user) -> None:
    """The reason this endpoint is worth having.

    A list of successes answers "when did they last sign in". Only the failures answer "is somebody
    trying to get in" — so a history that quietly dropped them would look healthy during an attack.
    """
    created = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    for _ in range(2):
        await client.post(
            "/api/v1/auth/login", json={"email": "owner@vi.co", "password": "wrong-password"}
        )

    body = (await _history(client, headers, created.user.public_id)).json()

    actions = [entry["action"] for entry in body["data"]]
    assert actions.count("user.login_failed") == 2
    assert "user.login" in actions


async def test_entries_carry_the_time_and_source_address(client, make_user) -> None:
    created = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    entry = (await _history(client, headers, created.user.public_id)).json()["data"][0]

    assert entry["created_at"]
    # The column is nullable and the test client has no real peer address, so the key must exist
    # even when the value does not — a missing key would break the caller, a null is honest.
    assert "ip_address" in entry


async def test_only_the_named_user_is_reported(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "owner@vi.co")
    await _headers(client, "agent@vi.co")  # the agent signs in too

    body = (await _history(client, headers, owner.user.public_id)).json()

    # Every entry belongs to the requested user, not to whoever else signed in meanwhile.
    assert {entry["actor"] for entry in body["data"]} == {owner.user.public_id}


async def test_unrelated_actions_are_excluded(client, make_user) -> None:
    created = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "auditable"})

    body = (await _history(client, headers, created.user.public_id)).json()

    assert all(entry["action"].startswith("user.login") for entry in body["data"])


async def test_pagination_is_declared_and_bounded(client, make_user) -> None:
    created = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    for _ in range(3):
        await client.post(
            "/api/v1/auth/login", json={"email": "owner@vi.co", "password": "wrong-password"}
        )

    first = (await _history(client, headers, created.user.public_id, limit=2)).json()

    assert len(first["data"]) == 2 and first["page"]["has_more"] is True
    second = await _history(
        client, headers, created.user.public_id, cursor=first["page"]["next_cursor"], limit=2
    )
    assert second.status_code == 200
    assert (await _history(client, headers, created.user.public_id, limit=0)).status_code == 422


async def test_an_unknown_user_is_not_found(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    missing = await _history(client, headers, "00000000-0000-4000-8000-000000000000")

    assert missing.status_code == 404


async def test_reading_a_history_requires_user_read_permission(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="nobody@vi.co", password=PASSWORD)
    nobody = await _headers(client, "nobody@vi.co")

    denied = await _history(client, nobody, owner.user.public_id)

    assert denied.status_code == 403
