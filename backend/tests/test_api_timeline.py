"""API tests for the contact activity timeline (Doc 03 §6.5, FR-CON-14)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_timeline_records_lifecycle_events(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    contact = (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).json()
    tag = (await client.post("/api/v1/tags", headers=h, json={"name": "vip"})).json()
    await client.post(
        f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
    )
    await client.patch(
        f"/api/v1/contacts/{contact['id']}",
        headers=h,
        json={"opt_in_status": "opted_in", "row_version": contact["row_version"]},
    )
    await client.delete(f"/api/v1/contacts/{contact['id']}/tags/{tag['id']}", headers=h)

    timeline = await client.get(f"/api/v1/contacts/{contact['id']}/timeline", headers=h)
    assert timeline.status_code == 200
    body = timeline.json()
    types = {e["event_type"] for e in body["data"]}
    assert {"contact_created", "tag_added", "optin_changed", "tag_removed"} <= types
    assert body["page"]["total"] >= 4
    # Newest first.
    assert body["data"][0]["event_type"] == "tag_removed"


async def test_timeline_filter_and_pagination(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    contact = (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).json()
    for i in range(3):
        tag = (await client.post("/api/v1/tags", headers=h, json={"name": f"t{i}"})).json()
        await client.post(
            f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
        )

    filtered = await client.get(
        f"/api/v1/contacts/{contact['id']}/timeline?filter[event_type][eq]=tag_added", headers=h
    )
    assert all(e["event_type"] == "tag_added" for e in filtered.json()["data"])
    assert filtered.json()["page"]["total"] == 3

    page1 = (
        await client.get(f"/api/v1/contacts/{contact['id']}/timeline?limit=2", headers=h)
    ).json()
    assert len(page1["data"]) == 2 and page1["page"]["has_more"] is True
    page2 = (
        await client.get(
            f"/api/v1/contacts/{contact['id']}/timeline?limit=2&cursor={page1['page']['next_cursor']}",
            headers=h,
        )
    ).json()
    assert {e["id"] for e in page1["data"]}.isdisjoint({e["id"] for e in page2["data"]})


async def test_timeline_404_and_permissions(client, make_user) -> None:
    import uuid

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="nobody@vi.co", password=PASSWORD)
    h = await _headers(client, "owner@vi.co")
    nobody_h = await _headers(client, "nobody@vi.co")
    assert (
        await client.get(f"/api/v1/contacts/{uuid.uuid4()}/timeline", headers=h)
    ).status_code == 404
    contact = (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).json()
    assert (
        await client.get(f"/api/v1/contacts/{contact['id']}/timeline", headers=nobody_h)
    ).status_code == 403
