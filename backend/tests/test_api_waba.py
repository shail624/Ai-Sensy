"""WABA & phone-number tests (Doc 04 §13.2/§13.3, FR-WA-01..04/13) — M4 Step 2.

No network: Meta is reached only through the adapter, whose transport is an ``httpx.MockTransport``.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.core.crypto import decrypt, encrypt
from app.models.waba import WhatsAppBusinessAccount
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.waba_service import WabaService

PASSWORD = "Sup3r-Secret-Pass1"
TOKEN = "system-user-token-abc123"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _owner(client, make_user) -> dict[str, str]:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    return await _headers(client, "owner@vi.co")


async def _connect(client, h, **overrides) -> dict:
    body = {
        "waba_id": "waba-100",
        "business_name": "Vi Reactivation",
        "access_token": TOKEN,
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }
    body.update(overrides)
    resp = await client.post("/api/v1/waba", headers=h, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _numbers_response(*nodes: dict) -> httpx.Response:
    return httpx.Response(200, json={"data": list(nodes)})


def _node(number_id: str, display: str, **extra) -> dict:
    node = {
        "id": number_id,
        "display_phone_number": display,
        "verified_name": "Vi Team",
        "quality_rating": "GREEN",
        "messaging_limit_tier": "TIER_100K",
        "throughput": {"level": "STANDARD"},
        "status": "connected",
    }
    node.update(extra)
    return node


@pytest.fixture
def meta(monkeypatch):
    """Bind every adapter this test creates to a mock transport."""
    state: dict = {"handler": lambda request: _numbers_response(), "calls": []}
    real = WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        def handler(request: httpx.Request) -> httpx.Response:
            state["calls"].append(str(request.url))
            return state["handler"](request)

        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter.client._owns_http = True
        return adapter

    monkeypatch.setattr(WabaService, "adapter_for", _adapter_for)
    return state


# --- WABA CRUD (Doc 04 §13.2) ------------------------------------------------
async def test_connect_waba_stores_token_encrypted_and_never_returns_it(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    body = await _connect(client, h)

    assert body["waba_id"] == "waba-100" and body["token_set"] is True
    assert body["phone_number_count"] == 0
    # The single most sensitive field must not appear anywhere in the response.
    assert TOKEN not in str(body) and "access_token" not in body

    async with session_factory() as session:
        waba = await WabaRepository(session).get_by_uuid(uuid.UUID(body["id"]))
        assert waba.access_token_enc != TOKEN.encode()
        assert decrypt(waba.access_token_enc) == TOKEN


async def test_connecting_the_same_waba_twice_is_409(client, make_user) -> None:
    h = await _owner(client, make_user)
    await _connect(client, h)
    resp = await client.post(
        "/api/v1/waba",
        headers=h,
        json={"waba_id": "waba-100", "business_name": "Dup", "access_token": TOKEN},
    )
    assert resp.status_code == 409, resp.text


async def test_list_and_get_waba(client, make_user) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    listing = (await client.get("/api/v1/waba", headers=h)).json()["data"]
    assert [w["id"] for w in listing] == [created["id"]]

    fetched = (await client.get(f"/api/v1/waba/{created['id']}", headers=h)).json()
    assert fetched["business_name"] == "Vi Reactivation" and fetched["token_set"] is True
    assert (await client.get(f"/api/v1/waba/{uuid.uuid4()}", headers=h)).status_code == 404


async def test_update_waba_rotates_token_without_exposing_it(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)

    resp = await client.patch(
        f"/api/v1/waba/{created['id']}",
        headers=h,
        json={"business_name": "Renamed", "access_token": "rotated-token-xyz"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["business_name"] == "Renamed"
    assert "rotated-token-xyz" not in str(resp.json())

    async with session_factory() as session:
        waba = await WabaRepository(session).get_by_uuid(uuid.UUID(created["id"]))
        assert decrypt(waba.access_token_enc) == "rotated-token-xyz"


async def test_update_waba_rejects_bad_status_and_stale_version(client, make_user) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    bad = await client.patch(
        f"/api/v1/waba/{created['id']}", headers=h, json={"status": "nonsense"}
    )
    assert bad.status_code == 422
    stale = await client.patch(
        f"/api/v1/waba/{created['id']}", headers=h, json={"business_name": "X", "row_version": 99}
    )
    assert stale.status_code == 409


async def test_disconnect_waba_refuses_while_numbers_remain(
    client, make_user, session_factory, meta
) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(_node("pn-1", "+14155550001"))
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])

    blocked = await client.delete(f"/api/v1/waba/{created['id']}", headers=h)
    assert blocked.status_code == 409, blocked.text

    # Removing the number (Meta no longer reports it) releases the WABA.
    meta["handler"] = lambda request: _numbers_response()
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])
    assert (await client.delete(f"/api/v1/waba/{created['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/waba/{created['id']}", headers=h)).status_code == 404


async def test_waba_permission_enforcement(client, make_user) -> None:
    await make_user(email="viewer@vi.co", password=PASSWORD, roles=("viewer",))
    h = await _headers(client, "viewer@vi.co")
    assert (await client.post("/api/v1/waba", headers=h, json={})).status_code == 403
    assert (await client.get("/api/v1/waba")).status_code == 401


# --- Sync (Doc 04 §13.2 — 202 + job) ----------------------------------------
async def test_sync_returns_202_and_enqueues_without_calling_meta(
    client, make_user, meta
) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)

    dispatched: list = []
    import app.channels.tasks as tasks

    tasks.run_waba_sync.apply_async = lambda args, task_id: dispatched.append((args, task_id))

    resp = await client.post(f"/api/v1/waba/{created['id']}/sync", headers=h)
    assert resp.status_code == 202, resp.text
    job = resp.json()["job"]
    assert job["type"] == "waba_sync" and job["status"] == "queued"
    assert job["poll_url"] == f"/api/v1/jobs/{job['id']}"
    assert dispatched and dispatched[0][0] == [created["id"]]
    # Nothing was pulled on the request path.
    assert meta["calls"] == []


async def test_run_sync_creates_updates_and_removes_numbers(
    client, make_user, session_factory, meta
) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)

    meta["handler"] = lambda request: _numbers_response(
        _node("pn-1", "+14155550001"), _node("pn-2", "+14155550002", quality_rating="YELLOW")
    )
    async with session_factory() as session:
        result = await WabaService(session).run_sync(created["id"])
    assert result == {"created": 2, "updated": 0, "removed": 0}

    numbers = (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"]
    assert {n["display_number"] for n in numbers} == {"+14155550001", "+14155550002"}
    first = next(n for n in numbers if n["phone_number_id"] == "pn-1")
    assert first["quality_rating"] == "GREEN" and first["messaging_tier"] == "TIER_100K"
    assert first["throughput_level"] == "STANDARD" and first["mps_limit"] == 80
    assert first["waba_id"] == created["id"] and first["last_synced_at"] is not None

    # Second sync: pn-1 changes, pn-2 disappears.
    meta["handler"] = lambda request: _numbers_response(
        _node("pn-1", "+14155550001", quality_rating="RED")
    )
    async with session_factory() as session:
        result = await WabaService(session).run_sync(created["id"])
    assert result == {"created": 0, "updated": 1, "removed": 1}

    numbers = (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"]
    assert [n["phone_number_id"] for n in numbers] == ["pn-1"]
    assert numbers[0]["quality_rating"] == "RED"


async def test_run_sync_is_idempotent(client, make_user, session_factory, meta) -> None:
    """Redelivery updates in place rather than duplicating (Doc 06 §8)."""
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(_node("pn-1", "+14155550001"))

    async with session_factory() as session:
        assert (await WabaService(session).run_sync(created["id"]))["created"] == 1
    async with session_factory() as session:
        assert (await WabaService(session).run_sync(created["id"]))["updated"] == 1

    assert len((await client.get("/api/v1/phone-numbers", headers=h)).json()["data"]) == 1


async def test_sync_preserves_operator_owned_fields(
    client, make_user, session_factory, meta
) -> None:
    """Meta owns quality/tier; the operator owns mps_limit and is_default."""
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(_node("pn-1", "+14155550001"))
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])

    number = (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"][0]
    await client.patch(
        f"/api/v1/phone-numbers/{number['id']}",
        headers=h,
        json={"mps_limit": 20, "is_default": True},
    )
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])

    after = (await client.get(f"/api/v1/phone-numbers/{number['id']}", headers=h)).json()
    assert after["mps_limit"] == 20 and after["is_default"] is True


# --- Phone numbers (Doc 04 §13.3) -------------------------------------------
async def _synced_number(client, h, session_factory, meta) -> dict:
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(_node("pn-1", "+14155550001"))
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])
    return (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"][0]


async def test_list_numbers_filters(client, make_user, session_factory, meta) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(
        _node("pn-1", "+14155550001"), _node("pn-2", "+14155550002", quality_rating="RED")
    )
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])

    green = await client.get(
        "/api/v1/phone-numbers?filter[quality_rating][eq]=GREEN", headers=h
    )
    assert [n["phone_number_id"] for n in green.json()["data"]] == ["pn-1"]

    by_waba = await client.get(f"/api/v1/phone-numbers?waba={created['id']}", headers=h)
    assert len(by_waba.json()["data"]) == 2

    missing = await client.get(f"/api/v1/phone-numbers?waba={uuid.uuid4()}", headers=h)
    assert missing.status_code == 404


async def test_default_number_is_exclusive(client, make_user, session_factory, meta) -> None:
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    meta["handler"] = lambda request: _numbers_response(
        _node("pn-1", "+14155550001"), _node("pn-2", "+14155550002")
    )
    async with session_factory() as session:
        await WabaService(session).run_sync(created["id"])
    numbers = (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"]

    for number in numbers:
        resp = await client.patch(
            f"/api/v1/phone-numbers/{number['id']}", headers=h, json={"is_default": True}
        )
        assert resp.status_code == 200, resp.text

    after = (await client.get("/api/v1/phone-numbers", headers=h)).json()["data"]
    assert [n["is_default"] for n in after].count(True) == 1
    assert next(n for n in after if n["is_default"])["id"] == numbers[-1]["id"]


async def test_health_reads_stored_state(client, make_user, session_factory, meta) -> None:
    h = await _owner(client, make_user)
    number = await _synced_number(client, h, session_factory, meta)
    before = len(meta["calls"])

    health = (
        await client.get(f"/api/v1/phone-numbers/{number['id']}/health", headers=h)
    ).json()
    assert health["quality_rating"] == "GREEN" and health["healthy"] is True
    assert health["messaging_tier"] == "TIER_100K" and health["mps_limit"] == 80
    # Reading health must not hit Meta.
    assert len(meta["calls"]) == before


async def test_refresh_repulls_health_from_meta(client, make_user, session_factory, meta) -> None:
    h = await _owner(client, make_user)
    number = await _synced_number(client, h, session_factory, meta)

    meta["handler"] = lambda request: httpx.Response(
        200,
        json={
            "quality_rating": "RED",
            "messaging_limit_tier": "TIER_1K",
            "throughput": {"level": "NOT_APPLICABLE"},
            "verified_name": "Vi Team",
        },
    )
    resp = await client.post(f"/api/v1/phone-numbers/{number['id']}/refresh", headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["quality_rating"] == "RED" and resp.json()["healthy"] is False
    assert resp.json()["messaging_tier"] == "TIER_1K"

    stored = (await client.get(f"/api/v1/phone-numbers/{number['id']}", headers=h)).json()
    assert stored["quality_rating"] == "RED"


async def test_refresh_surfaces_channel_failure_as_502(
    client, make_user, session_factory, meta
) -> None:
    h = await _owner(client, make_user)
    number = await _synced_number(client, h, session_factory, meta)
    meta["handler"] = lambda request: httpx.Response(
        500, json={"error": {"message": "meta is down", "code": 2}}
    )
    resp = await client.post(f"/api/v1/phone-numbers/{number['id']}/refresh", headers=h)
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "channel_error"


async def test_number_permission_enforcement(client, make_user, session_factory, meta) -> None:
    h = await _owner(client, make_user)
    number = await _synced_number(client, h, session_factory, meta)
    await make_user(email="viewer@vi.co", password=PASSWORD, roles=("viewer",))
    viewer = await _headers(client, "viewer@vi.co")
    assert (await client.get("/api/v1/phone-numbers", headers=viewer)).status_code == 403
    assert (
        await client.post(f"/api/v1/phone-numbers/{number['id']}/refresh", headers=viewer)
    ).status_code == 403


async def test_unknown_number_is_404(client, make_user) -> None:
    h = await _owner(client, make_user)
    assert (
        await client.get(f"/api/v1/phone-numbers/{uuid.uuid4()}", headers=h)
    ).status_code == 404


# --- Token encryption at rest (FR-WA-03) ------------------------------------
def test_encrypt_roundtrip_and_tamper_detection() -> None:
    sealed = encrypt("secret-token")
    assert sealed != b"secret-token" and decrypt(sealed) == "secret-token"
    # Each encryption uses a fresh nonce, so ciphertexts differ.
    assert encrypt("secret-token") != sealed

    from app.core.crypto import EncryptionError

    tampered = bytearray(sealed)
    tampered[-1] ^= 0x01
    with pytest.raises(EncryptionError, match="authentication"):
        decrypt(bytes(tampered))
    with pytest.raises(EncryptionError):
        decrypt(b"")


async def test_token_is_never_written_to_the_audit_trail(
    client, make_user, session_factory
) -> None:
    h = await _owner(client, make_user)
    await _connect(client, h)
    entries = (await client.get("/api/v1/audit-logs?filter[action][eq]=waba.connected", headers=h))
    assert TOKEN not in entries.text


async def test_repository_lookup_by_meta_id(client, make_user, session_factory, meta) -> None:
    """The key inbound webhook routing will use (Doc 03 §5.2)."""
    h = await _owner(client, make_user)
    await _synced_number(client, h, session_factory, meta)
    async with session_factory() as session:
        found = await PhoneNumberRepository(session).get_by_meta_id("pn-1")
        assert found is not None and found.display_number == "+14155550001"
        assert await PhoneNumberRepository(session).get_by_meta_id("nope") is None


async def test_adapter_is_resolved_from_the_registry_with_waba_credentials(
    client, make_user, session_factory
) -> None:
    """Meta is reached through the registry, bound to that WABA's own token (Doc 07 §5.4)."""
    h = await _owner(client, make_user)
    created = await _connect(client, h)
    async with session_factory() as session:
        waba = await WabaRepository(session).get_by_uuid(uuid.UUID(created["id"]))
        adapter = WabaService(session).adapter_for(waba, phone_number_id="pn-9")
        assert adapter.connector_type == "meta_cloud"
        assert adapter.client.credentials.access_token == TOKEN
        assert adapter.client.credentials.waba_id == "waba-100"
        assert adapter.client.credentials.phone_number_id == "pn-9"
        await adapter.close()


def test_waba_model_never_renders_its_token() -> None:
    waba = WhatsAppBusinessAccount(
        organization_id=1, waba_id="w", business_name="b", access_token_enc=encrypt("tok")
    )
    assert "tok" not in repr(waba)
