"""API tests for segments / saved filters (Doc 04 §14.3, Doc 03 §6.4, FR-CON-10)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _contact(client, h, phone: str, **fields) -> dict:
    return (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": phone, **fields})
    ).json()


async def test_segment_crud_with_rules(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/segments",
        headers=h,
        json={
            "name": "Opted-in",
            "description": "Reachable contacts",
            "match_type": "all",
            "rules": [
                {"field_source": "contact", "field_key": "opt_in_status", "operator": "eq",
                 "value": "opted_in"}
            ],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["type"] == "segment" and body["match_type"] == "all"
    assert body["is_dynamic"] is True and body["cached_count"] is None
    assert len(body["rules"]) == 1

    assert [s["name"] for s in (await client.get("/api/v1/segments", headers=h)).json()] == [
        "Opted-in"
    ]
    got = await client.get(f"/api/v1/segments/{body['id']}", headers=h)
    assert got.status_code == 200 and got.json()["rules"][0]["field_key"] == "opt_in_status"

    patched = await client.patch(
        f"/api/v1/segments/{body['id']}", headers=h, json={"name": "Reachable"}
    )
    assert patched.json()["name"] == "Reachable"

    assert (await client.delete(f"/api/v1/segments/{body['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/segments/{body['id']}", headers=h)).status_code == 404


async def test_segment_duplicate_name_409(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/segments", headers=h, json={"name": "S1", "rules": []})
    assert (
        await client.post("/api/v1/segments", headers=h, json={"name": "S1", "rules": []})
    ).status_code == 409


async def test_segment_rule_validation_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    def rule(**kw):
        base = {"field_source": "contact", "field_key": "full_name", "operator": "eq",
                "value": "x"}
        base.update(kw)
        return {"name": "bad", "rules": [base]}

    # Unknown field
    assert (
        await client.post("/api/v1/segments", headers=h, json=rule(field_key="nope"))
    ).status_code == 422
    # Operator not allowed for the field type
    assert (
        await client.post("/api/v1/segments", headers=h, json=rule(operator="between"))
    ).status_code == 422
    # attribute rules need custom attributes (not built yet)
    assert (
        await client.post(
            "/api/v1/segments", headers=h, json=rule(field_source="attribute", field_key="plan")
        )
    ).status_code == 422
    # between needs exactly two values
    assert (
        await client.post(
            "/api/v1/segments",
            headers=h,
            json=rule(field_key="created_at", operator="between", value=["2026-01-01T00:00:00"]),
        )
    ).status_code == 422
    # invalid match_type
    assert (
        await client.post(
            "/api/v1/segments", headers=h, json={"name": "x", "match_type": "some", "rules": []}
        )
    ).status_code == 422


async def test_segment_preview_and_cached_count(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _contact(client, h, "+14155550001", full_name="Alice", opt_in_status="opted_in")
    await _contact(client, h, "+14155550002", full_name="Bob", opt_in_status="opted_out")
    await _contact(client, h, "+14155550003", full_name="Carol", opt_in_status="opted_in")

    segment = (
        await client.post(
            "/api/v1/segments",
            headers=h,
            json={
                "name": "Opted-in",
                "rules": [
                    {"field_source": "contact", "field_key": "opt_in_status", "operator": "eq",
                     "value": "opted_in"}
                ],
            },
        )
    ).json()

    preview = await client.get(f"/api/v1/segments/{segment['id']}/contacts", headers=h)
    assert preview.status_code == 200
    assert {c["full_name"] for c in preview.json()["data"]} == {"Alice", "Carol"}
    assert preview.json()["page"]["total"] == 2

    # cached_count is only populated by refresh.
    assert segment["cached_count"] is None
    refreshed = await client.post(f"/api/v1/segments/{segment['id']}/refresh", headers=h)
    assert refreshed.status_code == 200
    assert refreshed.json()["cached_count"] == 2
    assert refreshed.json()["last_evaluated_at"] is not None

    # Changing rules invalidates the cached size.
    updated = await client.patch(
        f"/api/v1/segments/{segment['id']}",
        headers=h,
        json={
            "rules": [
                {"field_source": "contact", "field_key": "opt_in_status", "operator": "eq",
                 "value": "opted_out"}
            ]
        },
    )
    assert updated.json()["cached_count"] is None


async def test_segment_match_any_and_groups(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _contact(client, h, "+14155550001", full_name="Alice", opt_in_status="opted_in")
    await _contact(client, h, "+14155550002", full_name="Bob", source="api")

    # Two groups OR-ed at the top level (match_type=any).
    segment = (
        await client.post(
            "/api/v1/segments",
            headers=h,
            json={
                "name": "Either",
                "match_type": "any",
                "rules": [
                    {"group_index": 0, "field_source": "contact", "field_key": "opt_in_status",
                     "operator": "eq", "value": "opted_in"},
                    {"group_index": 1, "field_source": "contact", "field_key": "source",
                     "operator": "eq", "value": "api"},
                ],
            },
        )
    ).json()
    preview = await client.get(f"/api/v1/segments/{segment['id']}/contacts", headers=h)
    assert {c["full_name"] for c in preview.json()["data"]} == {"Alice", "Bob"}

    # Same rules ANDed → no contact satisfies both.
    both = await client.patch(
        f"/api/v1/segments/{segment['id']}", headers=h, json={"match_type": "all"}
    )
    assert both.json()["match_type"] == "all"
    preview2 = await client.get(f"/api/v1/segments/{segment['id']}/contacts", headers=h)
    assert preview2.json()["page"]["total"] == 0


async def test_segment_tag_rule(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    contact = await _contact(client, h, "+14155550001", full_name="Alice")
    await _contact(client, h, "+14155550002", full_name="Bob")
    tag = (await client.post("/api/v1/tags", headers=h, json={"name": "vip"})).json()
    await client.post(
        f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
    )

    segment = (
        await client.post(
            "/api/v1/segments",
            headers=h,
            json={
                "name": "VIPs",
                "rules": [
                    {"field_source": "tag", "field_key": "tags", "operator": "has_tag",
                     "value": "vip"}
                ],
            },
        )
    ).json()
    preview = await client.get(f"/api/v1/segments/{segment['id']}/contacts", headers=h)
    assert {c["full_name"] for c in preview.json()["data"]} == {"Alice"}


async def test_segment_preview_pagination(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    for i in range(5):
        await _contact(client, h, f"+1415555{i:04d}", opt_in_status="opted_in")
    segment = (
        await client.post(
            "/api/v1/segments",
            headers=h,
            json={
                "name": "All opted-in",
                "rules": [
                    {"field_source": "contact", "field_key": "opt_in_status", "operator": "eq",
                     "value": "opted_in"}
                ],
            },
        )
    ).json()
    page1 = (
        await client.get(f"/api/v1/segments/{segment['id']}/contacts?limit=2", headers=h)
    ).json()
    assert len(page1["data"]) == 2 and page1["page"]["has_more"] is True and page1["page"]["total"] == 5
    page2 = (
        await client.get(
            f"/api/v1/segments/{segment['id']}/contacts?limit=2&cursor={page1['page']['next_cursor']}",
            headers=h,
        )
    ).json()
    assert {c["id"] for c in page1["data"]}.isdisjoint({c["id"] for c in page2["data"]})


async def test_segments_permission_enforcement(client, make_user) -> None:
    # analyst holds segments:read but not segments:write; agent holds neither.
    await make_user(email="analyst@vi.co", password=PASSWORD, roles=("analyst",))
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    analyst_h = await _headers(client, "analyst@vi.co")
    agent_h = await _headers(client, "agent@vi.co")

    assert (await client.get("/api/v1/segments", headers=analyst_h)).status_code == 200
    assert (
        await client.post("/api/v1/segments", headers=analyst_h, json={"name": "x", "rules": []})
    ).status_code == 403
    assert (await client.get("/api/v1/segments", headers=agent_h)).status_code == 403
    assert (await client.get("/api/v1/segments")).status_code == 401
