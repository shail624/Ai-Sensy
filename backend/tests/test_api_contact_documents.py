"""HTTP contract tests for governed customer documents (Design Book 19, Phase 4A)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.db.mixins import utcnow
from app.models.organization import Organization
from app.models.user import User
from app.storage import scanning

PASSWORD = "Sup3r-Secret-Pass1"
PNG = b"\x89PNG\r\n\x1a\n" + b"d" * 64
DOCS = "/api/v1/documents"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401

    yield
    scanning.register_scanner(None)


async def _headers(client, make_user, *, email: str, **kwargs) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kwargs)
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _login(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _contact(client, headers, phone: str = "+919991000001") -> str:
    response = await client.post(
        "/api/v1/contacts", headers=headers, json={"phone_e164": phone, "full_name": "Asha"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _media(client, headers, *, data: bytes = PNG, name: str = "identity.png") -> str:
    response = await client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": (name, data, "image/png")},
        data={"media_type": "image"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create(client, headers, contact_id: str, media_id: str, **overrides):
    body = {
        "document_type": "identity",
        "title": "Aadhaar card",
        "media_asset_id": media_id,
        "note": "Collected at onboarding",
    }
    body.update(overrides)
    return await client.post(f"/api/v1/contacts/{contact_id}/documents", headers=headers, json=body)


def _assert_problem(response, status: int, code: str | None = None) -> None:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status
    if code is not None:
        assert body["code"] == code


async def test_create_list_and_detail_include_safe_version_metadata(client, make_user) -> None:
    owner = await _headers(client, make_user, email="owner@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)

    response = await _create(client, owner, contact_id, media_id)

    assert response.status_code == 201, response.text
    document = response.json()
    assert document["contact_id"] == contact_id
    assert document["status"] == "submitted"
    assert document["version_count"] == 1
    assert document["current_version"]["media_asset_id"] == media_id
    assert document["current_version"]["file_name"] == "identity.png"
    assert "storage_key" not in document["current_version"]
    uuid.UUID(document["id"])
    uuid.UUID(document["current_version"]["id"])

    listing = await client.get(f"/api/v1/contacts/{contact_id}/documents", headers=owner)
    detail = await client.get(f"{DOCS}/{document['id']}", headers=owner)
    assert listing.status_code == 200 and listing.json()["total"] == 1
    assert detail.status_code == 200 and detail.json()["id"] == document["id"]


async def test_version_reopens_verified_document_and_preserves_history(client, make_user) -> None:
    owner = await _headers(client, make_user, email="version@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    first_media = await _media(client, owner)
    document = (await _create(client, owner, contact_id, first_media)).json()
    verified = await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "verified", "expected_row_version": document["row_version"]},
    )
    second_media = await _media(
        client, owner, data=b"\x89PNG\r\n\x1a\n" + b"v" * 64, name="identity-v2.png"
    )

    response = await client.post(
        f"{DOCS}/{document['id']}/versions",
        headers=owner,
        json={"media_asset_id": second_media, "note": "Clearer scan"},
    )

    assert verified.status_code == 200, verified.text
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "submitted"
    assert [version["version_no"] for version in body["versions"]] == [1, 2]
    history = await client.get(f"{DOCS}/{document['id']}/history", headers=owner)
    assert [event["event_type"] for event in history.json()["data"]] == [
        "created",
        "verified",
        "version_added",
    ]


async def test_verification_rejection_expiry_and_archive_transitions(client, make_user) -> None:
    owner = await _headers(client, make_user, email="states@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)
    document = (
        await _create(
            client,
            owner,
            contact_id,
            media_id,
            expires_at=(utcnow() - timedelta(days=1)).isoformat() + "Z",
        )
    ).json()

    missing_reason = await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "rejected"},
    )
    assert missing_reason.status_code == 422

    verified = await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "verified"},
    )
    expired = await client.post(f"{DOCS}/{document['id']}/expire", headers=owner, json={})
    archived = await client.post(f"{DOCS}/{document['id']}/archive", headers=owner, json={})

    assert verified.json()["status"] == "verified" and verified.json()["verified_by_name"]
    assert expired.json()["status"] == "expired"
    assert archived.json()["status"] == "archived" and archived.json()["archived_at"]
    _assert_problem(
        await client.post(
            f"{DOCS}/{document['id']}/verification",
            headers=owner,
            json={"decision": "verified"},
        ),
        409,
        "document_state",
    )


async def test_rejection_records_reason_and_actor(client, make_user) -> None:
    owner = await _headers(client, make_user, email="reject@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    document = (await _create(client, owner, contact_id, await _media(client, owner))).json()

    response = await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "rejected", "reason": "The image is unreadable"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["rejection_reason"] == "The image is unreadable"
    history = (await client.get(f"{DOCS}/{document['id']}/history", headers=owner)).json()["data"]
    assert history[-1]["reason"] == "The image is unreadable"
    assert history[-1]["actor_name"] == "Test User"
    uuid.UUID(history[-1]["actor_user_id"])


async def test_signed_preview_download_and_media_retention(client, make_user) -> None:
    owner = await _headers(client, make_user, email="content@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)
    document = (await _create(client, owner, contact_id, media_id)).json()
    version_id = document["current_version"]["id"]

    content = await client.get(
        f"{DOCS}/{document['id']}/versions/{version_id}/content", headers=owner
    )
    assert content.status_code == 200, content.text
    assert (await client.get(content.json()["url"])).content == PNG
    _assert_problem(await client.delete(f"/api/v1/media/{media_id}", headers=owner), 409)


async def test_stale_version_and_duplicate_media_are_conflicts(client, make_user) -> None:
    owner = await _headers(client, make_user, email="conflict@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)
    document = (await _create(client, owner, contact_id, media_id)).json()
    await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "verified", "expected_row_version": 0},
    )

    stale = await client.post(
        f"{DOCS}/{document['id']}/archive",
        headers=owner,
        json={"expected_row_version": 0},
    )
    duplicate = await client.post(
        f"{DOCS}/{document['id']}/versions",
        headers=owner,
        json={"media_asset_id": media_id},
    )
    _assert_problem(stale, 409, "version_conflict")
    _assert_problem(duplicate, 409, "conflict")


async def test_permissions_split_agent_write_manager_verify_analyst_none(client, make_user) -> None:
    owner = await _headers(client, make_user, email="rbac-owner@docs.co", is_superuser=True)
    agent = await _headers(client, make_user, email="agent@docs.co", roles=("agent",))
    manager = await _headers(client, make_user, email="manager@docs.co", roles=("manager",))
    analyst = await _headers(client, make_user, email="analyst@docs.co", roles=("analyst",))
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)

    created = await _create(client, agent, contact_id, media_id)
    assert created.status_code == 201, created.text
    _assert_problem(
        await client.post(
            f"{DOCS}/{created.json()['id']}/verification",
            headers=agent,
            json={"decision": "verified"},
        ),
        403,
        "forbidden",
    )
    assert (
        await client.post(
            f"{DOCS}/{created.json()['id']}/verification",
            headers=manager,
            json={"decision": "verified"},
        )
    ).status_code == 200
    _assert_problem(
        await client.get(f"/api/v1/contacts/{contact_id}/documents", headers=analyst),
        403,
        "forbidden",
    )


async def test_foreign_tenant_document_is_hidden(
    client, make_user, session_factory, organization
) -> None:
    owner = await _headers(client, make_user, email="tenant-one@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    document = (await _create(client, owner, contact_id, await _media(client, owner))).json()

    async with session_factory() as session:
        other_org = Organization(name="Other", slug="other-docs")
        session.add(other_org)
        await session.flush()
        other = User(
            organization_id=other_org.id,
            email="tenant-two@docs.co",
            password_hash=hash_password(PASSWORD),
            full_name="Other Owner",
            is_active=True,
            is_superuser=True,
        )
        session.add(other)
        await session.commit()
    other_headers = await _login(client, "tenant-two@docs.co")

    _assert_problem(await client.get(f"{DOCS}/{document['id']}", headers=other_headers), 404)


async def test_document_lifecycle_projects_to_contact_timeline(client, make_user) -> None:
    owner = await _headers(client, make_user, email="timeline@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    document = (await _create(client, owner, contact_id, await _media(client, owner))).json()
    await client.post(
        f"{DOCS}/{document['id']}/verification",
        headers=owner,
        json={"decision": "verified"},
    )

    timeline = await client.get(f"/api/v1/contacts/{contact_id}/timeline", headers=owner)
    events = timeline.json()["data"]
    assert {"document_created", "document_verified"} <= {event["event_type"] for event in events}
    created = next(event for event in events if event["event_type"] == "document_created")
    assert created["ref_type"] == "contact_document"
    assert created["payload"]["title"] == "Aadhaar card"


def test_openapi_mounts_every_document_operation() -> None:
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/contacts/{contact_id}/documents": {"get", "post"},
        "/api/v1/documents/{document_id}": {"get"},
        "/api/v1/documents/{document_id}/versions": {"post"},
        "/api/v1/documents/{document_id}/verification": {"post"},
        "/api/v1/documents/{document_id}/expire": {"post"},
        "/api/v1/documents/{document_id}/archive": {"post"},
        "/api/v1/documents/{document_id}/history": {"get"},
        "/api/v1/documents/{document_id}/versions/{version_id}/content": {"get"},
    }
    for path, methods in expected.items():
        assert methods <= set(paths[path])
    assert sum(len(methods) for methods in expected.values()) == 9


# --- DOC-01: the document is the only door to the document ---------------------------------------
async def _custom_role(client, owner, name: str, permissions: list[str]) -> None:
    role = await client.post("/api/v1/roles", headers=owner, json={"name": name})
    assert role.status_code == 201, role.text
    granted = await client.put(
        f"/api/v1/roles/{role.json()['id']}/permissions",
        headers=owner,
        json={"permissions": permissions},
    )
    assert granted.status_code == 200, granted.text


async def test_media_read_alone_cannot_reach_a_customers_identity_document(
    client, make_user
) -> None:
    """A document is *built on* a media asset and shares the upload endpoint.

    So one row in `media_assets` holds either a campaign image or somebody's Aadhaar scan, and
    `documents:read` guarded the document routes while guarding nothing on the media routes. No
    shipped role has `media:read` without `documents:read`, so nothing was exposed as installed —
    but custom roles are a supported feature, and the moment somebody builds "Media librarian" the
    second door opens onto every customer's identity file. Splitting the two permissions means
    nothing if either one reaches the same bytes.
    """
    owner = await _headers(client, make_user, email="owner@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner, name="aadhaar.png")
    document = (await _create(client, owner, contact_id, media_id)).json()

    await _custom_role(client, owner, "media-librarian", ["media:read"])
    created = await client.post(
        "/api/v1/users",
        headers=owner,
        json={
            "email": "librarian@docs.co",
            "full_name": "Media Librarian",
            "password": PASSWORD,
            "roles": ["media-librarian"],
        },
    )
    assert created.status_code == 201, created.text
    librarian = await _login(client, "librarian@docs.co")

    # The front door is shut, and always was.
    assert (await client.get(f"{DOCS}/{document['id']}", headers=librarian)).status_code == 403

    # The back door is shut too: not in the library, and not fetchable by id.
    listed = await client.get("/api/v1/media", headers=librarian)
    assert listed.status_code == 200
    assert [asset["file_name"] for asset in listed.json()["data"]] == []
    assert (await client.get(f"/api/v1/media/{media_id}", headers=librarian)).status_code == 403
    refused = await client.get(f"/api/v1/media/{media_id}/content", headers=librarian)
    assert refused.status_code == 403, refused.text
    assert "url" not in refused.text


async def test_the_owner_still_reads_the_document_through_the_document(client, make_user) -> None:
    """The guard refuses a route, not a person: the governed path is unchanged."""
    owner = await _headers(client, make_user, email="owner@docs.co", is_superuser=True)
    contact_id = await _contact(client, owner)
    media_id = await _media(client, owner)
    document = (await _create(client, owner, contact_id, media_id)).json()

    response = await client.get(
        f"{DOCS}/{document['id']}/versions/{document['current_version']['id']}/content",
        headers=owner,
    )

    assert response.status_code == 200, response.text
    assert response.json()["url"]


async def test_reading_a_document_is_recorded_with_who_what_and_where(
    client, make_user, session_factory
) -> None:
    """Every change to a document was audited and every read was not.

    That is the wrong way round for somebody's Aadhaar: "who altered this record" is rarely the
    question a compliance review opens with, and "who looked at this customer's identity document,
    from where, and when" had no answer at all.
    """
    from sqlalchemy import select

    from app.models.audit import AuditLog

    owner = await _headers(client, make_user, email="owner@docs.co", is_superuser=True)
    headers = owner | {"User-Agent": "ViDesk/3.0 (Windows)"}
    contact_id = await _contact(client, headers)
    media_id = await _media(client, headers, name="aadhaar.png")
    document = (await _create(client, headers, contact_id, media_id)).json()

    fetched = await client.get(
        f"{DOCS}/{document['id']}/versions/{document['current_version']['id']}/content",
        headers=headers,
    )
    assert fetched.status_code == 200, fetched.text

    async with session_factory() as session:
        rows = list((await session.scalars(select(AuditLog))).all())
    entry = next(row for row in rows if row.action == "contact_document.accessed")

    assert entry.entity_type == "contact_document"
    assert entry.metadata_json == {
        "document_type": "identity",
        "version_no": 1,
        "file_name": "aadhaar.png",
    }
    assert entry.user_agent == "ViDesk/3.0 (Windows)"
    assert entry.ip_address is not None
    # A signed URL is a credential for the bytes; recording it would make the trail a second copy
    # of the thing it is protecting.
    assert fetched.json()["url"] not in str(entry.metadata_json)
