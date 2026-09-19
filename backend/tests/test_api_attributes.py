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


# --- ATTR-01: required and retired --------------------------------------------------------------
async def test_a_new_definition_is_neither_required_nor_retired(client, make_user) -> None:
    """Both defaults preserve every existing definition's behaviour exactly."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    definition = await _define(client, h)

    assert definition["is_required"] is False
    assert definition["is_active"] is True


async def test_a_required_attribute_cannot_be_cleared(client, make_user) -> None:
    """Setting values is a *partial* update, so "required" means this one may not be emptied.

    It cannot mean "every write must carry it": this endpoint writes the keys it is given and
    deletes the ones passed as null, so demanding the key on every call would break every partial
    update and every import in the product.
    """
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    definition = await _define(client, h, is_required=True)
    contact = await _contact(client, h)

    stored = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": "gold"}},
    )
    assert stored.status_code == 200, stored.text

    cleared = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": None}},
    )

    assert cleared.status_code == 422, cleared.text
    assert cleared.json()["errors"][0]["code"] == "attribute_required"
    # The value it refused to clear is still there.
    fetched = await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)
    assert fetched.json()["attributes"] == {"plan": "gold"}
    assert definition["is_required"] is True


async def test_a_partial_update_that_omits_a_required_attribute_is_fine(client, make_user) -> None:
    """The distinction the rule above turns on, stated as its own case."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    await _define(client, h, is_required=True)
    await _define(client, h, key_name="city", label="City")
    contact = await _contact(client, h)

    response = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"city": "Delhi"}},
    )

    assert response.status_code == 200, response.text


async def test_a_retired_attribute_takes_no_new_value_but_can_still_be_tidied_up(
    client, make_user
) -> None:
    """Retiring is not deleting: the data stays readable, and stays removable."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    definition = await _define(client, h)
    contact = await _contact(client, h)
    await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": "gold"}},
    )

    retired = await client.patch(
        f"/api/v1/custom-attributes/{definition['id']}", headers=h, json={"is_active": False}
    )
    assert retired.status_code == 200 and retired.json()["is_active"] is False

    # The value written before it was retired is still readable.
    fetched = await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)
    assert fetched.json()["attributes"] == {"plan": "gold"}

    refused = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": "silver"}},
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["errors"][0]["code"] == "attribute_retired"

    # But it can still be cleared, so a field can be wound down rather than left half-used.
    cleaned = await client.put(
        f"/api/v1/contacts/{contact['id']}/attributes",
        headers=h,
        json={"attributes": {"plan": None}},
    )
    assert cleaned.status_code == 200, cleaned.text
    assert (await client.get(f"/api/v1/contacts/{contact['id']}", headers=h)).json()["attributes"] == {}


async def test_changing_either_flag_is_audited(client, make_user) -> None:
    """Retiring a field and making one mandatory both change what the team may record."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    definition = await _define(client, h)

    await client.patch(
        f"/api/v1/custom-attributes/{definition['id']}",
        headers=h,
        json={"is_required": True, "is_active": False},
    )

    trail = await client.get("/api/v1/audit-logs?filter[action][eq]=custom_attribute.updated", headers=h)
    entry = trail.json()["data"][0]
    assert entry["before"]["is_required"] is False and entry["before"]["is_active"] is True
    assert entry["after"]["is_required"] is True and entry["after"]["is_active"] is False
