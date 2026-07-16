"""API tests for the media library (Doc 04 §16, FR-MED-05/06/09)."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.storage import scanning
from app.storage.scanning import ScanResult, VirusScanner

PASSWORD = "Sup3r-Secret-Pass1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    """Point the local backend at a temp dir and serve signed URLs from the test host."""
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider
    yield
    scanning.register_scanner(None)


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _upload(client, h, *, data=PNG, mime="image/png", media_type="image", name="a.png"):
    return await client.post(
        "/api/v1/media/upload",
        headers=h,
        files={"file": (name, data, mime)},
        data={"media_type": media_type},
    )


async def test_upload_list_get(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await _upload(client, h)
    assert created.status_code == 201
    body = created.json()
    assert body["media_type"] == "image" and body["mime_type"] == "image/png"
    assert body["byte_size"] == len(PNG) and len(body["sha256"]) == 64
    assert body["storage_backend"] == "local"

    listing = await client.get("/api/v1/media", headers=h)
    assert listing.status_code == 200 and listing.json()["total"] == 1
    assert (await client.get(f"/api/v1/media/{body['id']}", headers=h)).status_code == 200
    assert (await client.get(f"/api/v1/media/{uuid.uuid4()}", headers=h)).status_code == 404


async def test_upload_dedups_by_content_hash(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    first = (await _upload(client, h)).json()
    second = (await _upload(client, h, name="copy.png")).json()
    # Same bytes → one stored blob reused (FR-MED-05).
    assert first["id"] == second["id"] and first["sha256"] == second["sha256"]
    assert (await client.get("/api/v1/media", headers=h)).json()["total"] == 1


async def test_upload_validation_413_415_422(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    # wrong mime for declared type → 415
    assert (await _upload(client, h, mime="application/pdf")).status_code == 415
    # too large for image (5MB ceiling) → 413
    big = await _upload(client, h, data=b"0" * (6 * 1024 * 1024), name="big.png")
    assert big.status_code == 413
    # unknown media_type / empty file → 422
    assert (await _upload(client, h, media_type="hologram")).status_code == 422
    assert (await _upload(client, h, data=b"", name="empty.png")).status_code == 422


async def test_signed_url_download_roundtrip_and_tamper(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    asset = (await _upload(client, h)).json()

    content = await client.get(f"/api/v1/media/{asset['id']}/content", headers=h)
    assert content.status_code == 200
    url = content.json()["url"]
    assert content.json()["expires_in"] > 0

    # The signed URL needs no Bearer token — the signature is the credential.
    downloaded = await client.get(url)
    assert downloaded.status_code == 200 and downloaded.content == PNG

    # Tampered signature → 403; missing params → 400.
    assert (await client.get(url.replace("signature=", "signature=x"))).status_code == 403
    assert (await client.get(f"/api/v1/media/{asset['id']}/download")).status_code == 400


async def test_expired_signed_url_returns_410(client, make_user, monkeypatch) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    asset = (await _upload(client, h)).json()
    monkeypatch.setattr(settings, "storage_signed_url_ttl_seconds", -1)  # already expired
    url = (await client.get(f"/api/v1/media/{asset['id']}/content", headers=h)).json()["url"]
    assert (await client.get(url)).status_code == 410


async def test_delete_removes_asset_and_blob(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    asset = (await _upload(client, h)).json()
    assert (await client.delete(f"/api/v1/media/{asset['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/media/{asset['id']}", headers=h)).status_code == 404
    # Re-uploading the same bytes revives the asset rather than colliding on the unique hash.
    assert (await _upload(client, h)).status_code == 201


async def test_infected_upload_is_rejected(client, make_user) -> None:
    class _Infected(VirusScanner):
        name = "t"

        async def scan(self, data, *, file_name=None):
            return ScanResult(clean=False, signature="EICAR")

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    scanning.register_scanner(_Infected())
    resp = await _upload(client, h)
    assert resp.status_code == 422
    # Nothing was stored for a rejected file.
    assert (await client.get("/api/v1/media", headers=h)).json()["total"] == 0


async def test_media_permission_enforcement(client, make_user) -> None:
    # agent holds media:read but not media:write; a roleless user holds neither.
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="nobody@vi.co", password=PASSWORD)
    agent_h = await _headers(client, "agent@vi.co")
    nobody_h = await _headers(client, "nobody@vi.co")
    assert (await client.get("/api/v1/media", headers=agent_h)).status_code == 200
    assert (await _upload(client, agent_h)).status_code == 403
    assert (await client.get("/api/v1/media", headers=nobody_h)).status_code == 403
    assert (await client.get("/api/v1/media")).status_code == 401
