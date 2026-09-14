"""Rotation of an API key's secret.

Rotation exists because the alternative — revoke then create — discards the key's name, scopes
and audit history and leaves a window with no working credential. These tests pin the properties
that make it worth having: the record survives, the secret does not, and a retired key cannot be
brought back to life.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditLog

PASSWORD = "Sup3r-Secret-Pass1"
KEYS_URL = "/api/v1/api-keys"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _owner(client, make_user) -> dict[str, str]:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    return await _headers(client, "owner@vi.co")


async def _create(client, headers, **overrides) -> dict:
    payload = {"name": "CI pipeline", "scopes": ["contacts:read"], **overrides}
    created = await client.post(KEYS_URL, headers=headers, json=payload)
    assert created.status_code == 201, created.text
    return created.json()


async def test_rotation_issues_a_new_secret_and_keeps_the_key(client, make_user) -> None:
    headers = await _owner(client, make_user)
    original = await _create(client, headers)

    rotated = await client.post(f"{KEYS_URL}/{original['id']}/rotate", headers=headers)

    assert rotated.status_code == 200, rotated.text
    body = rotated.json()
    assert body["secret"] != original["secret"]
    assert body["key_prefix"] == body["secret"][:12] != original["key_prefix"]
    # The point of rotation over revoke-and-create: identity, name and scopes all survive, so the
    # consumer keeps the permissions it was configured with.
    assert body["id"] == original["id"]
    assert body["name"] == original["name"]
    assert body["scopes"] == original["scopes"]
    assert body["is_active"] is True


async def test_the_listing_shows_the_new_prefix_and_never_a_secret(client, make_user) -> None:
    headers = await _owner(client, make_user)
    original = await _create(client, headers)

    rotated = (await client.post(f"{KEYS_URL}/{original['id']}/rotate", headers=headers)).json()

    listing = await client.get(KEYS_URL, headers=headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1, "rotation must not leave a second key behind"
    assert rows[0]["key_prefix"] == rotated["key_prefix"]
    assert "secret" not in rows[0]


async def test_a_revoked_key_cannot_be_rotated(client, make_user) -> None:
    """Reviving a retired credential would hand back a working secret for a key somebody
    deliberately turned off."""
    headers = await _owner(client, make_user)
    created = await _create(client, headers, name="temp")
    assert (await client.delete(f"{KEYS_URL}/{created['id']}", headers=headers)).status_code == 204

    rotated = await client.post(f"{KEYS_URL}/{created['id']}/rotate", headers=headers)

    assert rotated.status_code == 404


async def test_rotating_an_unknown_key_is_not_found(client, make_user) -> None:
    headers = await _owner(client, make_user)

    rotated = await client.post(
        f"{KEYS_URL}/00000000-0000-4000-8000-000000000000/rotate", headers=headers
    )

    assert rotated.status_code == 404


async def test_rotation_is_audited_without_recording_either_secret(
    client, make_user, session_factory
) -> None:
    headers = await _owner(client, make_user)
    original = await _create(client, headers)

    rotated = (await client.post(f"{KEYS_URL}/{original['id']}/rotate", headers=headers)).json()

    async with session_factory() as session:
        entries = (await session.scalars(select(AuditLog))).all()
    rotations = [e for e in entries if e.action == "api_key.rotated"]
    assert len(rotations) == 1
    entry = rotations[0]
    assert entry.before_json == {"key_prefix": original["key_prefix"]}
    assert entry.after_json == {"key_prefix": rotated["key_prefix"]}
    # Prefixes identify a key; the secrets themselves must never reach the audit trail.
    recorded = f"{entry.before_json}{entry.after_json}"
    assert original["secret"] not in recorded and rotated["secret"] not in recorded


async def test_rotation_requires_key_management_permission(client, make_user) -> None:
    headers = await _owner(client, make_user)
    created = await _create(client, headers)
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    agent = await _headers(client, "agent@vi.co")

    rotated = await client.post(f"{KEYS_URL}/{created['id']}/rotate", headers=agent)

    assert rotated.status_code == 403
