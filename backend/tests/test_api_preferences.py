"""API tests for user preferences (Doc 04 §12.1, settings user-scope)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_preferences_get_empty_then_set(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")

    assert (await client.get("/api/v1/users/me/preferences", headers=headers)).json() == {
        "preferences": {}
    }

    updated = await client.put(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"preferences": {"theme": "dark", "shortcuts": True}},
    )
    assert updated.status_code == 200
    assert updated.json()["preferences"] == {"theme": "dark", "shortcuts": True}

    # Persisted across requests.
    fetched = await client.get("/api/v1/users/me/preferences", headers=headers)
    assert fetched.json()["preferences"]["theme"] == "dark"


async def test_preferences_upsert_merges(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    await client.put(
        "/api/v1/users/me/preferences", headers=headers, json={"preferences": {"theme": "dark"}}
    )
    merged = await client.put(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"preferences": {"density": "compact"}},
    )
    assert merged.json()["preferences"] == {"theme": "dark", "density": "compact"}


async def test_preferences_are_per_user(client, make_user) -> None:
    await make_user(email="a@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="b@vi.co", password=PASSWORD, roles=("agent",))
    a_headers = await _headers(client, "a@vi.co")
    b_headers = await _headers(client, "b@vi.co")
    await client.put(
        "/api/v1/users/me/preferences", headers=a_headers, json={"preferences": {"theme": "dark"}}
    )
    assert (await client.get("/api/v1/users/me/preferences", headers=b_headers)).json() == {
        "preferences": {}
    }


async def test_preferences_require_auth(client, organization) -> None:
    assert (await client.get("/api/v1/users/me/preferences")).status_code == 401
