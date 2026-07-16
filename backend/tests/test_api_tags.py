"""API tests for tags and contact tagging (Doc 04 §14.1/§14.2, FR-CON-09)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _contact(client, h, phone="+14155552671") -> dict:
    return (await client.post("/api/v1/contacts", headers=h, json={"phone_e164": phone})).json()


async def test_tag_crud(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/tags", headers=h, json={"name": "vip", "color": "#22c55e"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "vip" and body["color"] == "#22c55e" and body["usage_count"] == 0

    assert [t["name"] for t in (await client.get("/api/v1/tags", headers=h)).json()] == ["vip"]

    patched = await client.patch(
        f"/api/v1/tags/{body['id']}", headers=h, json={"name": "gold", "color": "#eab308"}
    )
    assert patched.status_code == 200 and patched.json()["name"] == "gold"

    assert (await client.delete(f"/api/v1/tags/{body['id']}", headers=h)).status_code == 204
    assert (await client.get("/api/v1/tags", headers=h)).json() == []


async def test_tag_validation_and_duplicates(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/tags", headers=h, json={"name": "vip"})
    assert (
        await client.post("/api/v1/tags", headers=h, json={"name": "vip"})
    ).status_code == 409
    assert (
        await client.post("/api/v1/tags", headers=h, json={"name": "x", "color": "green"})
    ).status_code == 422


async def test_attach_and_detach_tags(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    contact = await _contact(client, h)
    tag = (await client.post("/api/v1/tags", headers=h, json={"name": "vip"})).json()

    attached = await client.post(
        f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
    )
    assert attached.status_code == 200
    assert [t["name"] for t in attached.json()["tags"]] == ["vip"]
    # usage_count is maintained.
    assert (await client.get("/api/v1/tags", headers=h)).json()[0]["usage_count"] == 1

    # Idempotent: re-attaching does not double-count.
    await client.post(
        f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
    )
    assert (await client.get("/api/v1/tags", headers=h)).json()[0]["usage_count"] == 1

    removed = await client.delete(
        f"/api/v1/contacts/{contact['id']}/tags/{tag['id']}", headers=h
    )
    assert removed.status_code == 204
    fetched = await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)
    assert fetched.json()["tags"] == []
    assert (await client.get("/api/v1/tags", headers=h)).json()[0]["usage_count"] == 0


async def test_attach_unknown_tag_422_and_unknown_contact_404(client, make_user) -> None:
    import uuid

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    contact = await _contact(client, h)
    assert (
        await client.post(
            f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [str(uuid.uuid4())]}
        )
    ).status_code == 422
    tag = (await client.post("/api/v1/tags", headers=h, json={"name": "vip"})).json()
    assert (
        await client.post(
            f"/api/v1/contacts/{uuid.uuid4()}/tags", headers=h, json={"tags": [tag["id"]]}
        )
    ).status_code == 404


async def test_deleting_tag_detaches_from_contacts(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    contact = await _contact(client, h)
    tag = (await client.post("/api/v1/tags", headers=h, json={"name": "vip"})).json()
    await client.post(
        f"/api/v1/contacts/{contact['id']}/tags", headers=h, json={"tags": [tag["id"]]}
    )
    assert (await client.delete(f"/api/v1/tags/{tag['id']}", headers=h)).status_code == 204
    fetched = await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)
    assert fetched.json()["tags"] == []


async def test_tags_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="nobody@vi.co", password=PASSWORD)
    agent_h = await _headers(client, "agent@vi.co")
    nobody_h = await _headers(client, "nobody@vi.co")
    assert (await client.get("/api/v1/tags", headers=agent_h)).status_code == 200
    assert (
        await client.post("/api/v1/tags", headers=agent_h, json={"name": "x"})
    ).status_code == 403
    assert (await client.get("/api/v1/tags", headers=nobody_h)).status_code == 403
    assert (await client.get("/api/v1/tags")).status_code == 401
