"""API tests for advanced contact search (Doc 04 §14.1, FR-CON-12) and attribute segments."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed(client, h) -> None:
    await client.post(
        "/api/v1/custom-attributes", headers=h,
        json={"key_name": "plan", "label": "Plan", "data_type": "enum",
              "enum_values": ["gold", "silver"]},
    )
    await client.post(
        "/api/v1/custom-attributes", headers=h,
        json={"key_name": "ltv", "label": "LTV", "data_type": "number"},
    )
    for phone, name, plan, ltv in (
        ("+14155550001", "Alice", "gold", 9000),
        ("+14155550002", "Bob", "silver", 100),
        ("+14155550003", "Carol", "gold", 100),
    ):
        contact = (
            await client.post(
                "/api/v1/contacts", headers=h,
                json={"phone_e164": phone, "full_name": name, "opt_in_status": "opted_in"},
            )
        ).json()
        await client.put(
            f"/api/v1/contacts/{contact['id']}/attributes", headers=h,
            json={"attributes": {"plan": plan, "ltv": ltv}},
        )


async def test_search_by_attribute_and_and_or(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed(client, h)

    # "plan = gold AND ltv > 5000" (Doc 03 §6.3 rationale)
    resp = await client.post(
        "/api/v1/contacts/search",
        headers=h,
        json={
            "match_type": "all",
            "rules": [
                {"group_index": 0, "field_source": "attribute", "field_key": "plan",
                 "operator": "eq", "value": "gold"},
                {"group_index": 0, "field_source": "attribute", "field_key": "ltv",
                 "operator": "gt", "value": 5000},
            ],
        },
    )
    assert resp.status_code == 200
    assert {c["full_name"] for c in resp.json()["data"]} == {"Alice"}
    assert resp.json()["page"]["total"] == 1

    # OR across groups
    any_resp = await client.post(
        "/api/v1/contacts/search",
        headers=h,
        json={
            "match_type": "any",
            "rules": [
                {"group_index": 0, "field_source": "attribute", "field_key": "plan",
                 "operator": "eq", "value": "silver"},
                {"group_index": 1, "field_source": "attribute", "field_key": "ltv",
                 "operator": "gte", "value": 9000},
            ],
        },
    )
    assert {c["full_name"] for c in any_resp.json()["data"]} == {"Alice", "Bob"}


async def test_search_mixed_sources_and_validation(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed(client, h)

    mixed = await client.post(
        "/api/v1/contacts/search",
        headers=h,
        json={
            "rules": [
                {"field_source": "contact", "field_key": "opt_in_status", "operator": "eq",
                 "value": "opted_in"},
                {"field_source": "attribute", "field_key": "plan", "operator": "in",
                 "value": ["gold"]},
            ]
        },
    )
    assert {c["full_name"] for c in mixed.json()["data"]} == {"Alice", "Carol"}

    # Unknown attribute / bad value / bad enum → 422
    for rule in (
        {"field_source": "attribute", "field_key": "nope", "operator": "eq", "value": "x"},
        {"field_source": "attribute", "field_key": "ltv", "operator": "eq", "value": "abc"},
        {"field_source": "attribute", "field_key": "plan", "operator": "eq", "value": "bronze"},
        {"field_source": "attribute", "field_key": "plan", "operator": "gt", "value": "gold"},
    ):
        resp = await client.post("/api/v1/contacts/search", headers=h, json={"rules": [rule]})
        assert resp.status_code == 422, rule


async def test_search_pagination_and_empty_rules(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed(client, h)

    # No rules → all contacts (an unconstrained search).
    every = await client.post("/api/v1/contacts/search", headers=h, json={"rules": []})
    assert every.json()["page"]["total"] == 3

    page1 = await client.post(
        "/api/v1/contacts/search", headers=h, json={"rules": [], "limit": 2}
    )
    assert len(page1.json()["data"]) == 2 and page1.json()["page"]["has_more"] is True
    page2 = await client.post(
        "/api/v1/contacts/search",
        headers=h,
        json={"rules": [], "limit": 2, "cursor": page1.json()["page"]["next_cursor"]},
    )
    ids1 = {c["id"] for c in page1.json()["data"]}
    assert ids1.isdisjoint({c["id"] for c in page2.json()["data"]})


async def test_saved_filter_compatibility(client, make_user) -> None:
    """The same rules produce identical results via POST /contacts/search and a segment."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _seed(client, h)
    rules = [
        {"field_source": "attribute", "field_key": "plan", "operator": "eq", "value": "gold"}
    ]

    search = await client.post("/api/v1/contacts/search", headers=h, json={"rules": rules})
    segment = (
        await client.post(
            "/api/v1/segments", headers=h, json={"name": "Gold", "rules": rules}
        )
    ).json()
    preview = await client.get(f"/api/v1/segments/{segment['id']}/contacts", headers=h)

    assert {c["id"] for c in search.json()["data"]} == {c["id"] for c in preview.json()["data"]}
    refreshed = await client.post(f"/api/v1/segments/{segment['id']}/refresh", headers=h)
    assert refreshed.json()["cached_count"] == search.json()["page"]["total"] == 2


async def test_search_permission_enforcement(client, make_user) -> None:
    await make_user(email="nobody@vi.co", password=PASSWORD)
    nobody_h = await _headers(client, "nobody@vi.co")
    assert (
        await client.post("/api/v1/contacts/search", headers=nobody_h, json={"rules": []})
    ).status_code == 403
    assert (await client.post("/api/v1/contacts/search", json={"rules": []})).status_code == 401
