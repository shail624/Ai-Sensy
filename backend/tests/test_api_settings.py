"""API tests for system settings & feature flags (Doc 04 §22)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_settings_get_empty_then_update(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    assert (await client.get("/api/v1/settings", headers=headers)).json() == []

    updated = await client.put(
        "/api/v1/settings",
        headers=headers,
        json={"values": {"business_hours": {"start": "09:00"}, "auto_reply": True}},
    )
    assert updated.status_code == 200
    by_key = {s["key"]: s for s in updated.json()}
    assert by_key["auto_reply"]["value"] is True
    assert by_key["auto_reply"]["value_type"] == "boolean"
    assert by_key["business_hours"]["value"] == {"start": "09:00"}


async def test_settings_upsert_is_idempotent_per_key(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 1}})
    second = await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 2}})
    values = {s["key"]: s["value"] for s in second.json()}
    assert values == {"k": 2}  # updated in place, not duplicated


async def test_settings_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/settings", headers=headers)).status_code == 403
    assert (
        await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 1}})
    ).status_code == 403
    assert (await client.get("/api/v1/settings")).status_code == 401


async def test_feature_flag_lifecycle(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    assert (await client.get("/api/v1/feature-flags", headers=headers)).json() == []

    created = await client.patch(
        "/api/v1/feature-flags/new_inbox",
        headers=headers,
        json={"is_enabled": True, "description": "New inbox UI", "rollout": {"percent": 50}},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["key"] == "new_inbox" and body["is_enabled"] is True
    assert body["rollout"] == {"percent": 50}

    listed = await client.get("/api/v1/feature-flags", headers=headers)
    assert [f["key"] for f in listed.json()] == ["new_inbox"]

    toggled = await client.patch(
        "/api/v1/feature-flags/new_inbox", headers=headers, json={"is_enabled": False}
    )
    assert toggled.json()["is_enabled"] is False
    assert toggled.json()["description"] == "New inbox UI"  # preserved


async def test_feature_flag_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/feature-flags", headers=headers)).status_code == 403
    assert (
        await client.patch("/api/v1/feature-flags/x", headers=headers, json={"is_enabled": True})
    ).status_code == 403


async def test_admin_can_manage_settings_and_flags(client, make_user) -> None:
    await make_user(email="admin@vi.co", password=PASSWORD, roles=("admin",))
    headers = await _headers(client, "admin@vi.co")
    assert (
        await client.put("/api/v1/settings", headers=headers, json={"values": {"k": "v"}})
    ).status_code == 200
    assert (
        await client.patch(
            "/api/v1/feature-flags/f", headers=headers, json={"is_enabled": True}
        )
    ).status_code == 200
