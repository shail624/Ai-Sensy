"""API tests for API key management (Doc 04 §4.1, Doc 12 §58)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_create_key_returns_secret_once(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "CI pipeline", "scopes": ["contacts:read"]},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["secret"].startswith("sk_live_")
    assert body["key_prefix"] == body["secret"][:12]
    assert body["scopes"] == ["contacts:read"] and body["is_active"] is True

    # The secret is never returned again by list.
    listing = await client.get("/api/v1/api-keys", headers=headers)
    assert listing.status_code == 200
    row = listing.json()[0]
    assert "secret" not in row
    assert row["key_prefix"] == body["key_prefix"]


async def test_create_key_rejects_unknown_scope_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.post(
        "/api/v1/api-keys", headers=headers, json={"name": "bad", "scopes": ["nope:invalid"]}
    )
    assert resp.status_code == 422


async def test_revoke_key(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    created = (
        await client.post("/api/v1/api-keys", headers=headers, json={"name": "temp"})
    ).json()

    revoke = await client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers)
    assert revoke.status_code == 204
    # Revoking again → 404 (no longer active).
    assert (
        await client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers)
    ).status_code == 404
    # Listing still shows it, marked inactive.
    row = next(k for k in (await client.get("/api/v1/api-keys", headers=headers)).json())
    assert row["is_active"] is False and row["revoked_at"] is not None


async def test_apikeys_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/api-keys", headers=headers)).status_code == 403
    assert (
        await client.post("/api/v1/api-keys", headers=headers, json={"name": "x"})
    ).status_code == 403
    assert (await client.get("/api/v1/api-keys")).status_code == 401
