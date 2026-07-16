"""API tests for custom attributes (Doc 04 §14.1/§14.4, Doc 03 §6.3, FR-CON-11)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _define(client, h, **kw) -> dict:
    body = {"key_name": "plan", "label": "Plan", "data_type": "string"}
    body.update(kw)
    return (await client.post("/api/v1/custom-attributes", headers=h, json=body)).json()


async def _contact(client, h, phone="+14155552671") -> dict:
    return (await client.post("/api/v1/contacts", headers=h, json={"phone_e164": phone})).json()


async def test_definition_crud(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/custom-attributes",
        headers=h,
        json={"key_name": "plan", "label": "Plan", "data_type": "enum",
              "enum_values": ["gold", "silver"], "is_indexed": True},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["data_type"] == "enum" and body["enum_values"] == ["gold", "silver"]

    assert [d["key_name"] for d in (await client.get("/api/v1/custom-attributes", headers=h)).json()] == ["plan"]

    patched = await client.patch(
        f"/api/v1/custom-attributes/{body['id']}",
        headers=h,
        json={"label": "Plan Tier", "enum_values": ["gold", "silver", "bronze"]},
    )
    assert patched.json()["label"] == "Plan Tier"
    assert patched.json()["enum_values"] == ["gold", "silver", "bronze"]

    assert (
        await client.delete(f"/api/v1/custom-attributes/{body['id']}", headers=h)
    ).status_code == 204
    assert (await client.get("/api/v1/custom-attributes", headers=h)).json() == []


async def test_definition_validation(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    # unknown data_type
    assert (
        await client.post(
            "/api/v1/custom-attributes",
            headers=h,
            json={"key_name": "x", "label": "X", "data_type": "blob"},
        )
    ).status_code == 422
    # enum without values
    assert (
        await client.post(
            "/api/v1/custom-attributes",
            headers=h,
            json={"key_name": "y", "label": "Y", "data_type": "enum"},
        )
    ).status_code == 422
    # duplicate key
    await _define(client, h)
    assert (
        await client.post(
            "/api/v1/custom-attributes",
            headers=h,
            json={"key_name": "plan", "label": "Dup", "data_type": "string"},
        )
    ).status_code == 409


async def test_set_values_typed_and_validated(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _define(client, h, key_name="plan", data_type="enum", enum_values=["gold", "silver"])
    await _define(client, h, key_name="ltv", label="LTV", data_type="number")
    await _define(client, h, key_name="vip", label="VIP", data_type="boolean")
    await _define(client, h, key_name="joined", label="Joined", data_type="datetime")
    contact = await _contact(client, h)

    ok = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": "gold", "ltv": 5400.5, "vip": True,
                             "joined": "2026-06-01T10:00:00"}},
    )
    assert ok.status_code == 200
    attrs = ok.json()["attributes"]
    assert attrs["plan"] == "gold" and attrs["ltv"] == 5400.5 and attrs["vip"] is True
    assert attrs["joined"].startswith("2026-06-01T10:00:00")

    # Type mismatches → 422 (Doc 04 §14.1)
    for bad in ({"ltv": "not-a-number"}, {"vip": "yes"}, {"plan": "bronze"},
                {"joined": "nope"}, {"missing": 1}):
        resp = await client.put(
            f"/api/v1/contacts/{contact['id']}/attributes", headers=h, json={"attributes": bad}
        )
        assert resp.status_code == 422, bad


async def test_values_upsert_and_clear(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _define(client, h, key_name="plan", data_type="string")
    contact = await _contact(client, h)

    await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes", headers=h,
        json={"attributes": {"plan": "gold"}},
    )
    updated = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes", headers=h,
        json={"attributes": {"plan": "silver"}},
    )
    assert updated.json()["attributes"] == {"plan": "silver"}  # upsert, not duplicate

    cleared = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes", headers=h,
        json={"attributes": {"plan": None}},
    )
    assert cleared.json()["attributes"] == {}


async def test_indexed_attribute_mirrors_into_cache(client, make_user, session_factory) -> None:
    from sqlalchemy import select

    from app.models.contact import Contact

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _define(client, h, key_name="plan", data_type="string", is_indexed=True)
    await _define(client, h, key_name="notes", label="Notes", data_type="string")
    contact = await _contact(client, h)
    await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": "gold", "notes": "cold"}},
    )
    async with session_factory() as session:
        row = (await session.scalars(select(Contact))).first()
        # Only is_indexed attributes are mirrored (Doc 03 §6.3).
        assert row.attributes_cache == {"plan": "gold"}


async def test_deleting_definition_removes_values(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    definition = await _define(client, h, key_name="plan", data_type="string")
    contact = await _contact(client, h)
    await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes", headers=h,
        json={"attributes": {"plan": "gold"}},
    )
    await client.delete(f"/api/v1/custom-attributes/{definition['id']}", headers=h)
    fetched = await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)
    assert fetched.json()["attributes"] == {}


async def test_attributes_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    agent_h = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/custom-attributes", headers=agent_h)).status_code == 200
    assert (
        await client.post(
            "/api/v1/custom-attributes", headers=agent_h,
            json={"key_name": "x", "label": "X", "data_type": "string"},
        )
    ).status_code == 403
    assert (await client.get("/api/v1/custom-attributes")).status_code == 401
