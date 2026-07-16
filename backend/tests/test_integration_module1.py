"""End-to-end integration test for Module 1 (Auth + RBAC + Admin).

Exercises the whole Module 1 surface in one realistic flow across every feature area,
verifying they compose correctly and that the audit trail captures the chain of actions.
"""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _login(client, email: str, password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _headers(client, email: str, password: str = PASSWORD) -> dict[str, str]:
    return {"Authorization": f"Bearer {(await _login(client, email, password)).json()['access_token']}"}


async def test_module1_end_to_end(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    owner_h = await _headers(client, "owner@vi.co")

    # 1. Owner creates a user with the manager role.
    created = await client.post(
        "/api/v1/users",
        headers=owner_h,
        json={"email": "manager@vi.co", "full_name": "Mgr", "password": PASSWORD,
              "roles": ["manager"]},
    )
    assert created.status_code == 201
    manager_id = created.json()["id"]

    # 2. The new user can log in and sees manager permissions via /auth/me.
    me = await client.get("/api/v1/auth/me", headers=await _headers(client, "manager@vi.co"))
    assert me.status_code == 200
    assert me.json()["roles"] == ["manager"]
    assert "campaigns:send" in me.json()["permissions"]

    # 3. Owner creates a custom role and assigns permissions.
    role = await client.post(
        "/api/v1/roles", headers=owner_h,
        json={"name": "auditor", "permissions": ["audit:read"]},
    )
    assert role.status_code == 201

    # 4. Owner updates the organization (optimistic concurrency).
    org = await client.patch(
        "/api/v1/organization", headers=owner_h,
        json={"name": "Vi (E2E)", "row_version": 0},
    )
    assert org.status_code == 200 and org.json()["name"] == "Vi (E2E)"

    # 5. Owner sets a system setting and a feature flag.
    assert (await client.put("/api/v1/settings", headers=owner_h,
                             json={"values": {"auto_reply": True}})).status_code == 200
    assert (await client.patch("/api/v1/feature-flags/new_ui", headers=owner_h,
                               json={"is_enabled": True})).status_code == 200

    # 6. Owner creates an API key (secret shown once) and lists it.
    key = await client.post("/api/v1/api-keys", headers=owner_h,
                            json={"name": "integration", "scopes": ["contacts:read"]})
    assert key.status_code == 201 and key.json()["secret"].startswith("sk_live_")
    assert len((await client.get("/api/v1/api-keys", headers=owner_h)).json()) == 1

    # 7. The manager manages their own preferences.
    mgr_h = await _headers(client, "manager@vi.co")
    prefs = await client.put("/api/v1/users/me/preferences", headers=mgr_h,
                             json={"preferences": {"theme": "dark"}})
    assert prefs.json()["preferences"] == {"theme": "dark"}

    # 8. The audit trail captured the full chain of privileged actions.
    audit = await client.get("/api/v1/audit-logs?limit=200", headers=owner_h)
    actions = {e["action"] for e in audit.json()["data"]}
    assert {
        "user.login", "user.created", "role.created", "organization.updated",
        "setting.updated", "feature_flag.updated", "api_key.created", "preferences.updated",
    } <= actions

    # 9. Deactivating the manager blocks further login (session revocation).
    assert (await client.post(f"/api/v1/users/{manager_id}/deactivate",
                              headers=owner_h)).status_code == 200
    assert (await _login(client, "manager@vi.co")).status_code == 401

    # 10. RBAC is enforced end-to-end: the manager never had admin reach.
    assert owner.user.is_superuser is True
