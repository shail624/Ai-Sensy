"""API tests for role & permission management (Doc 04 §12.2) and RBAC enforcement."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _role_id(client, headers: dict[str, str], name: str) -> str:
    roles = (await client.get("/api/v1/roles", headers=headers)).json()
    return next(role["id"] for role in roles if role["name"] == name)


async def test_permissions_catalog_listed(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.get("/api/v1/permissions", headers=headers)
    assert resp.status_code == 200
    codes = {p["code"] for p in resp.json()}
    assert "users:manage" in codes and "auth:self" in codes


async def test_list_roles_returns_presets(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    roles = (await client.get("/api/v1/roles", headers=headers)).json()
    names = {r["name"] for r in roles}
    assert {"owner", "admin", "manager", "agent", "analyst"} <= names


async def test_roles_require_authentication(client, organization) -> None:
    assert (await client.get("/api/v1/roles")).status_code == 401


async def test_agent_forbidden_but_admin_allowed(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="admin@vi.co", password=PASSWORD, roles=("admin",))
    agent_headers = await _headers(client, "agent@vi.co")
    admin_headers = await _headers(client, "admin@vi.co")
    assert (await client.get("/api/v1/roles", headers=agent_headers)).status_code == 403
    assert (await client.get("/api/v1/roles", headers=admin_headers)).status_code == 200


async def test_role_crud_lifecycle(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": "reviewer", "description": "Reviews", "permissions": ["campaigns:read"]},
    )
    assert created.status_code == 201
    role = created.json()
    assert role["permissions"] == ["campaigns:read"] and role["is_system"] is False
    role_id = role["id"]

    got = await client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert got.status_code == 200 and got.json()["name"] == "reviewer"

    patched = await client.patch(
        f"/api/v1/roles/{role_id}", headers=headers, json={"description": "Updated"}
    )
    assert patched.status_code == 200 and patched.json()["description"] == "Updated"

    replaced = await client.put(
        f"/api/v1/roles/{role_id}/permissions",
        headers=headers,
        json={"permissions": ["analytics:read", "contacts:read"]},
    )
    assert replaced.status_code == 200
    assert set(replaced.json()["permissions"]) == {"analytics:read", "contacts:read"}

    assert (await client.delete(f"/api/v1/roles/{role_id}", headers=headers)).status_code == 204
    assert (await client.get(f"/api/v1/roles/{role_id}", headers=headers)).status_code == 404


async def test_create_role_unknown_permission_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": "broken", "permissions": ["nope:invalid"]},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


async def test_create_role_duplicate_name_409(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.post("/api/v1/roles", headers=headers, json={"name": "admin"})
    assert resp.status_code == 409


async def test_system_role_protected(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    admin_id = await _role_id(client, headers, "admin")

    renamed = await client.patch(
        f"/api/v1/roles/{admin_id}", headers=headers, json={"name": "root"}
    )
    assert renamed.status_code == 403
    deleted = await client.delete(f"/api/v1/roles/{admin_id}", headers=headers)
    assert deleted.status_code == 403
