"""API tests for contact CRUD (Doc 04 §14.1) — Module 2 foundation."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _phone(i: int) -> str:
    return f"+1415555{i:04d}"


async def test_create_get_contact(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/contacts",
        headers=h,
        json={"phone_e164": "+14155552671", "full_name": "Priya R",
              "email": "priya@x.com", "opt_in_status": "opted_in"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["type"] == "contact"
    assert body["wa_id"] == "14155552671" and body["phone_e164"] == "+14155552671"
    assert body["opt_in_status"] == "opted_in" and body["opt_in_at"] is not None
    assert body["source"] == "manual" and body["row_version"] == 0

    got = await client.get(f"/api/v1/contacts/{body['id']}", headers=h)
    assert got.status_code == 200 and got.json()["full_name"] == "Priya R"


async def test_create_duplicate_wa_id_409(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    dup = await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    assert dup.status_code == 409


async def test_create_validation_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    assert (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "not-a-phone"})
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/contacts", headers=h,
            json={"phone_e164": "+14155552671", "opt_in_status": "bogus"},
        )
    ).status_code == 422


async def test_update_optimistic_concurrency_and_optin(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    created = (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).json()
    cid, ver = created["id"], created["row_version"]

    patched = await client.patch(
        f"/api/v1/contacts/{cid}", headers=h,
        json={"full_name": "Updated", "opt_in_status": "opted_out", "row_version": ver},
    )
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "Updated"
    assert patched.json()["opt_in_status"] == "opted_out" and patched.json()["opt_out_at"] is not None

    stale = await client.patch(
        f"/api/v1/contacts/{cid}", headers=h, json={"full_name": "X", "row_version": ver}
    )
    assert stale.status_code == 409 and stale.json()["code"] == "version_conflict"


async def test_soft_delete_and_dedup(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    created = (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).json()

    assert (await client.delete(f"/api/v1/contacts/{created['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/contacts/{created['id']}", headers=h)).status_code == 404
    # wa_id remains reserved after soft delete (anonymization only on hard erase, Doc 3 §6.1).
    assert (
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": "+14155552671"})
    ).status_code == 409


async def test_list_search_filter_sort(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/contacts", headers=h,
                      json={"phone_e164": "+14155550001", "full_name": "Alice",
                            "opt_in_status": "opted_in"})
    await client.post("/api/v1/contacts", headers=h,
                      json={"phone_e164": "+14155550002", "full_name": "Bob", "source": "api"})

    listing = await client.get("/api/v1/contacts", headers=h)
    assert listing.status_code == 200 and listing.json()["page"]["total"] == 2

    by_q = await client.get("/api/v1/contacts?q=alice", headers=h)
    assert {c["full_name"] for c in by_q.json()["data"]} == {"Alice"}

    by_phone = await client.get("/api/v1/contacts?q=550002", headers=h)
    assert {c["full_name"] for c in by_phone.json()["data"]} == {"Bob"}

    by_optin = await client.get("/api/v1/contacts?filter[opt_in_status][eq]=opted_in", headers=h)
    assert {c["full_name"] for c in by_optin.json()["data"]} == {"Alice"}

    by_source = await client.get("/api/v1/contacts?filter[source][eq]=api", headers=h)
    assert {c["full_name"] for c in by_source.json()["data"]} == {"Bob"}

    by_name = await client.get("/api/v1/contacts?sort=full_name", headers=h)
    assert [c["full_name"] for c in by_name.json()["data"]] == ["Alice", "Bob"]


async def test_cursor_pagination_keyset(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    for i in range(5):
        await client.post("/api/v1/contacts", headers=h, json={"phone_e164": _phone(i)})

    page1 = (await client.get("/api/v1/contacts?limit=2", headers=h)).json()
    assert len(page1["data"]) == 2 and page1["page"]["has_more"] is True

    page2 = (
        await client.get(f"/api/v1/contacts?limit=2&cursor={page1['page']['next_cursor']}", headers=h)
    ).json()
    seen = {c["id"] for c in page1["data"]} | {c["id"] for c in page2["data"]}
    assert len(seen) == 4  # distinct across pages (keyset, no overlap)


async def test_cursor_pagination_nullable_sort(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    # Two named, two unnamed (full_name NULL → must sort last and page cleanly).
    await client.post("/api/v1/contacts", headers=h, json={"phone_e164": _phone(1), "full_name": "Ann"})
    await client.post("/api/v1/contacts", headers=h, json={"phone_e164": _phone(2), "full_name": "Bea"})
    await client.post("/api/v1/contacts", headers=h, json={"phone_e164": _phone(3)})
    await client.post("/api/v1/contacts", headers=h, json={"phone_e164": _phone(4)})

    collected: list = []
    url = "/api/v1/contacts?sort=full_name&limit=2"
    for _ in range(3):
        page = (await client.get(url, headers=h)).json()
        collected.extend(page["data"])
        if not page["page"]["next_cursor"]:
            break
        url = f"/api/v1/contacts?sort=full_name&limit=2&cursor={page['page']['next_cursor']}"
    assert len({c["id"] for c in collected}) == 4  # all pages, no dupes
    assert [c["full_name"] for c in collected[:2]] == ["Ann", "Bea"]  # non-null first


async def test_contacts_permission_enforcement(client, make_user) -> None:
    # agent has contacts:read but not contacts:write; roleless user has neither.
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="nobody@vi.co", password=PASSWORD)
    agent_h = await _headers(client, "agent@vi.co")
    nobody_h = await _headers(client, "nobody@vi.co")

    assert (await client.get("/api/v1/contacts", headers=agent_h)).status_code == 200
    assert (
        await client.post("/api/v1/contacts", headers=agent_h, json={"phone_e164": _phone(9)})
    ).status_code == 403
    assert (await client.get("/api/v1/contacts", headers=nobody_h)).status_code == 403
    assert (await client.get("/api/v1/contacts")).status_code == 401
