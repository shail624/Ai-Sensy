"""API tests for user management (Doc 04 §12.1)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str, password: str = PASSWORD) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_create_list_get_user(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "newbie@vi.co",
            "full_name": "New Bie",
            "password": PASSWORD,
            "roles": ["agent"],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["email"] == "newbie@vi.co" and body["roles"] == ["agent"]
    assert body["is_active"] is True and body["is_superuser"] is False
    user_id = body["id"]

    listing = await client.get("/api/v1/users", headers=headers)
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["page"]["total"] == 2  # owner + newbie
    assert {u["email"] for u in payload["data"]} == {"owner@vi.co", "newbie@vi.co"}

    got = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert got.status_code == 200 and got.json()["full_name"] == "New Bie"


async def test_create_user_duplicate_email_409(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post(
        "/api/v1/users",
        headers=headers,
        json={"email": "dup@vi.co", "full_name": "Dup", "password": PASSWORD},
    )
    again = await client.post(
        "/api/v1/users",
        headers=headers,
        json={"email": "dup@vi.co", "full_name": "Dup2", "password": PASSWORD},
    )
    assert again.status_code == 409


async def test_create_user_unknown_role_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.post(
        "/api/v1/users",
        headers=headers,
        json={"email": "x@vi.co", "full_name": "X", "password": PASSWORD, "roles": ["ghost"]},
    )
    assert resp.status_code == 422


async def test_update_user_roles_and_optimistic_concurrency(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    created = (
        await client.post(
            "/api/v1/users",
            headers=headers,
            json={"email": "u@vi.co", "full_name": "U", "password": PASSWORD, "roles": ["agent"]},
        )
    ).json()
    user_id, version = created["id"], created["row_version"]

    patched = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"full_name": "Updated", "roles": ["manager"], "row_version": version},
    )
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "Updated" and patched.json()["roles"] == ["manager"]

    # Stale version → 409 version_conflict.
    stale = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"full_name": "Again", "row_version": version},
    )
    assert stale.status_code == 409 and stale.json()["code"] == "version_conflict"


async def test_deactivate_revokes_sessions(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    target = await make_user(email="target@vi.co", password=PASSWORD, roles=("agent",))
    owner_headers = await _headers(client, "owner@vi.co")
    target_login = (
        await client.post(
            "/api/v1/auth/login", json={"email": "target@vi.co", "password": PASSWORD}
        )
    ).json()

    deactivate = await client.post(
        f"/api/v1/users/{target.user.public_id}/deactivate", headers=owner_headers
    )
    assert deactivate.status_code == 200 and deactivate.json()["is_active"] is False
    # Target's refresh token is revoked, and they can no longer log in.
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": target_login["refresh_token"]}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": "target@vi.co", "password": PASSWORD}
        )
    ).status_code == 401

    reactivate = await client.post(
        f"/api/v1/users/{target.user.public_id}/activate", headers=owner_headers
    )
    assert reactivate.status_code == 200 and reactivate.json()["is_active"] is True


async def test_cannot_delete_or_deactivate_self(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    assert (
        await client.delete(f"/api/v1/users/{owner.user.public_id}", headers=headers)
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/users/{owner.user.public_id}/deactivate", headers=headers
        )
    ).status_code == 409


async def test_delete_user_soft_deletes(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    target = await make_user(email="gone@vi.co", password=PASSWORD)
    headers = await _headers(client, "owner@vi.co")
    assert (
        await client.delete(f"/api/v1/users/{target.user.public_id}", headers=headers)
    ).status_code == 204
    assert (
        await client.get(f"/api/v1/users/{target.user.public_id}", headers=headers)
    ).status_code == 404


async def test_users_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/users", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/users")).status_code == 401


async def test_list_filter_and_search(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="alice@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="bob@vi.co", password=PASSWORD, roles=("manager",))
    headers = await _headers(client, "owner@vi.co")

    by_role = await client.get("/api/v1/users?filter[role][eq]=manager", headers=headers)
    assert {u["email"] for u in by_role.json()["data"]} == {"bob@vi.co"}

    by_q = await client.get("/api/v1/users?q=alice", headers=headers)
    assert {u["email"] for u in by_q.json()["data"]} == {"alice@vi.co"}
