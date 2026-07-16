"""API tests for the authentication endpoints (Doc 04 §11)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _login(client, email: str, password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _headers(client, email: str, password: str = PASSWORD) -> dict[str, str]:
    resp = await _login(client, email, password)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_login_success_and_me(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    resp = await _login(client, "agent@vi.co")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"] and body["expires_in"] > 0
    assert body["user"]["email"] == "agent@vi.co"

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["roles"] == ["agent"]
    assert "auth:self" in me_body["permissions"]
    assert "inbox:read" in me_body["permissions"]


async def test_login_invalid_password_401(client, make_user) -> None:
    await make_user(email="u@vi.co", password=PASSWORD)
    resp = await _login(client, "u@vi.co", "wrong-password")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["code"] == "unauthorized"


async def test_login_unknown_email_is_generic_401(client, organization) -> None:
    resp = await _login(client, "ghost@vi.co")
    assert resp.status_code == 401


async def test_login_lockout_returns_423(client, make_user) -> None:
    await make_user(email="lock@vi.co", password=PASSWORD)
    for _ in range(4):
        assert (await _login(client, "lock@vi.co", "bad")).status_code == 401
    locked = await _login(client, "lock@vi.co", "bad")
    assert locked.status_code == 423
    assert locked.json()["code"] == "locked"
    # Correct password is still refused while locked.
    assert (await _login(client, "lock@vi.co")).status_code == 423


async def test_me_requires_authentication(client, organization) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_me_rejects_garbage_token(client, organization) -> None:
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


async def test_refresh_rotation_and_reuse_detection(client, make_user) -> None:
    await make_user(email="rot@vi.co", password=PASSWORD)
    login = (await _login(client, "rot@vi.co")).json()

    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != login["refresh_token"]

    # Reusing the original (already rotated) token is rejected.
    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert reuse.status_code == 401
    # And the family is burned — the rotated token no longer works either.
    dead = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert dead.status_code == 401


async def test_logout_revokes_refresh(client, make_user) -> None:
    await make_user(email="lo@vi.co", password=PASSWORD)
    login = (await _login(client, "lo@vi.co")).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert after.status_code == 401


async def test_logout_all(client, make_user) -> None:
    await make_user(email="la@vi.co", password=PASSWORD)
    login = (await _login(client, "la@vi.co")).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert (await client.post("/api/v1/auth/logout-all", headers=headers)).status_code == 204
    after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert after.status_code == 401


async def test_change_password_flow(client, make_user) -> None:
    await make_user(email="cp@vi.co", password=PASSWORD)
    login = (await _login(client, "cp@vi.co")).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Weak new password → 422 (policy).
    weak = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "short"},
    )
    assert weak.status_code == 422

    ok = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "Br4nd-New-Password"},
    )
    assert ok.status_code == 204
    # Old refresh token now invalid; new password logs in.
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    ).status_code == 401
    assert (await _login(client, "cp@vi.co", "Br4nd-New-Password")).status_code == 200


async def test_sessions_list_and_revoke(client, make_user) -> None:
    await make_user(email="se@vi.co", password=PASSWORD)
    login = (await _login(client, "se@vi.co")).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    listing = await client.get("/api/v1/auth/sessions", headers=headers)
    assert listing.status_code == 200
    sessions = listing.json()
    assert len(sessions) == 1

    revoke = await client.delete(f"/api/v1/auth/sessions/{sessions[0]['id']}", headers=headers)
    assert revoke.status_code == 204
    assert (await client.get("/api/v1/auth/sessions", headers=headers)).json() == []
