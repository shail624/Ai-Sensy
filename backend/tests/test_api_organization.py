"""API tests for organization management (Doc 04 §13.1)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_get_organization(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.get("/api/v1/organization", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "vi-reactivation"
    assert body["type"] == "organization"
    assert body["row_version"] == 0


async def test_update_organization(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.patch(
        "/api/v1/organization",
        headers=headers,
        json={
            "name": "Vi Reactivation (Updated)",
            "timezone": "Asia/Kolkata",
            "default_locale": "hi",
            "settings": {"brand_color": "#611f69"},
            "row_version": 0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Vi Reactivation (Updated)"
    assert body["timezone"] == "Asia/Kolkata"
    assert body["default_locale"] == "hi"
    assert body["settings"] == {"brand_color": "#611f69"}
    assert body["row_version"] == 1


async def test_update_optimistic_concurrency(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    stale = await client.patch(
        "/api/v1/organization", headers=headers, json={"name": "X", "row_version": 99}
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"


async def test_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    # Agent lacks settings:read / settings:manage.
    assert (await client.get("/api/v1/organization", headers=headers)).status_code == 403
    assert (
        await client.patch("/api/v1/organization", headers=headers, json={"name": "X"})
    ).status_code == 403
    # Unauthenticated.
    assert (await client.get("/api/v1/organization")).status_code == 401


async def test_admin_can_read_and_manage(client, make_user) -> None:
    # The admin preset holds settings:read + settings:manage (Doc 12 §58).
    await make_user(email="admin@vi.co", password=PASSWORD, roles=("admin",))
    headers = await _headers(client, "admin@vi.co")
    assert (await client.get("/api/v1/organization", headers=headers)).status_code == 200
    updated = await client.patch(
        "/api/v1/organization", headers=headers, json={"name": "Admin Renamed"}
    )
    assert updated.status_code == 200 and updated.json()["name"] == "Admin Renamed"
