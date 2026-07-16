"""API tests for the audit-log read endpoint (Doc 04 §22)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_audit_log_captures_actions_and_lists(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    # Generate an auditable action.
    await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})

    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"]["total"] >= 1
    actions = {e["action"] for e in body["data"]}
    assert "role.created" in actions
    # login also audited, with the actor resolved to the owner's UUID.
    login_entry = next((e for e in body["data"] if e["action"] == "user.login"), None)
    assert login_entry is not None
    assert login_entry["actor"] == owner.user.public_id


async def test_audit_filters_by_action_and_entity(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "r1"})

    by_action = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=role.created", headers=headers
    )
    assert all(e["action"] == "role.created" for e in by_action.json()["data"])

    by_entity = await client.get(
        "/api/v1/audit-logs?filter[entity][eq]=role", headers=headers
    )
    assert all(e["entity_type"] == "role" for e in by_entity.json()["data"])


async def test_audit_filter_by_actor_and_pagination(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    for i in range(3):
        await client.post("/api/v1/roles", headers=headers, json={"name": f"role{i}"})

    page1 = await client.get(
        f"/api/v1/audit-logs?filter[actor][eq]={owner.user.public_id}&limit=2", headers=headers
    )
    body1 = page1.json()
    assert len(body1["data"]) == 2 and body1["page"]["has_more"] is True

    page2 = await client.get(
        f"/api/v1/audit-logs?cursor={body1['page']['next_cursor']}&limit=2", headers=headers
    )
    assert page2.status_code == 200
    # Distinct entries across pages (keyset).
    ids1 = {e["id"] for e in body1["data"]}
    ids2 = {e["id"] for e in page2.json()["data"]}
    assert ids1.isdisjoint(ids2)


async def test_audit_unknown_actor_returns_empty(client, make_user) -> None:
    import uuid

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.get(
        f"/api/v1/audit-logs?filter[actor][eq]={uuid.uuid4()}", headers=headers
    )
    assert resp.status_code == 200 and resp.json()["data"] == []


async def test_audit_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/audit-logs", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/audit-logs")).status_code == 401
