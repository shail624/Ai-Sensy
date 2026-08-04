"""M13-02 exact identity, tenant, conflict, recommendation and no-merge acceptance tests."""

from __future__ import annotations

from sqlalchemy import select

from app.core.security import hash_password
from app.identity.domain import IdentityAssertion, IdentityNormalizerRegistry
from app.identity.flags import IDENTITY_RESOLUTION_FLAG
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.contact_event import ContactEvent
from app.models.contact_identity import ContactIdentity
from app.models.organization import Organization
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.identity_resolution_service import IdentityResolutionService

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _set_flag(session_factory, organization_id: int, enabled: bool = True) -> None:
    async with session_factory() as session:
        session.add(
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=organization_id,
                is_enabled=enabled,
            )
        )
        await session.commit()


def _phone_assertion(phone: str) -> dict[str, str]:
    return {
        "identity_namespace": "whatsapp_phone",
        "identity_scope": "global",
        "value": phone,
        "identity_kind": "provider",
        "source": "provider",
        "confidence": "authoritative",
    }


async def _create_contact(client, headers: dict[str, str], phone: str, name: str) -> dict:
    response = await client.post(
        "/api/v1/contacts",
        headers=headers,
        json={"phone_e164": phone, "full_name": name},
    )
    assert response.status_code == 201
    return response.json()


async def test_exact_phone_creates_one_canonical_contact_and_links_endpoint_aliases(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "assertions": [_phone_assertion("+14155552671")],
            "new_contact": {"full_name": "Canonical Customer"},
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "created"
    assert body["canonical_contact_id"]
    assert body["automatic_merge"] is False
    canonical_id = body["canonical_contact_id"]

    alias = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": canonical_id,
            "assertions": [
                {
                    "identity_namespace": "messenger_psid",
                    "identity_scope": "endpoint:page-1",
                    "value": "PSID-001",
                    "identity_kind": "endpoint",
                    "connector_type": "future_provider",
                    "connection_ref": "connection-1",
                    "endpoint_ref": "page-1",
                    "source": "provider",
                    "confidence": "verified",
                },
                {
                    "identity_namespace": "messenger_psid",
                    "identity_scope": "endpoint:page-2",
                    "value": "PSID-002",
                    "identity_kind": "endpoint",
                    "connector_type": "future_provider",
                    "connection_ref": "connection-1",
                    "endpoint_ref": "page-2",
                    "source": "provider",
                    "confidence": "verified",
                },
            ],
        },
    )
    assert alias.status_code == 200
    assert alias.json()["canonical_contact_id"] == canonical_id

    identities = await client.get(f"/api/v1/contacts/{canonical_id}/identities", headers=headers)
    assert identities.status_code == 200
    rows = identities.json()
    assert len(rows) == 3
    assert {row["contact_id"] for row in rows} == {canonical_id}
    assert {row["endpoint_ref"] for row in rows if row["endpoint_ref"]} == {
        "page-1",
        "page-2",
    }

    repeated = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "resolved"
    assert repeated.json()["canonical_contact_id"] == canonical_id
    assert len(repeated.json()["identities"]) == 1


async def test_conflict_queue_recommendation_approval_never_merges_or_moves_identity(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")
    primary = await _create_contact(client, headers, "+14155550001", "Primary")
    duplicate = await _create_contact(client, headers, "+14155550002", "Duplicate")

    linked = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": primary["id"],
            "assertions": [
                {
                    "identity_namespace": "instagram_user",
                    "identity_scope": "business:ig-1",
                    "value": "IG-USER-9",
                    "connector_type": "future_provider",
                }
            ],
        },
    )
    assert linked.status_code == 200
    identity_id = linked.json()["identities"][0]["id"]

    detected = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "contact_id": duplicate["id"],
            "assertions": [
                {
                    "identity_namespace": "instagram_user",
                    "identity_scope": "business:ig-1",
                    "value": "IG-USER-9",
                    "connector_type": "future_provider",
                }
            ],
        },
    )
    assert detected.status_code == 200
    conflict = detected.json()
    assert conflict["status"] == "conflict"
    assert conflict["canonical_contact_id"] is None
    conflict_id = conflict["conflict_id"]

    queue = await client.get("/api/v1/identity-conflicts?status=open", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    assert set(queue.json()["data"][0]["candidate_contact_ids"]) == {
        primary["id"],
        duplicate["id"],
    }

    recommendation = await client.post(
        f"/api/v1/identity-conflicts/{conflict_id}/recommendations",
        headers=headers,
        json={
            "primary_contact_id": primary["id"],
            "duplicate_contact_id": duplicate["id"],
            "confidence": "verified",
            "reason": "Operator reviewed exact provider evidence.",
        },
    )
    assert recommendation.status_code == 201
    rec = recommendation.json()
    assert rec["status"] == "pending" and rec["merge_executed"] is False

    approved = await client.post(
        f"/api/v1/identity-merge-recommendations/{rec['id']}/approve",
        headers=headers,
        json={"row_version": rec["row_version"], "note": "Approved for later merge workflow."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["merge_executed"] is False

    assert (
        await client.get(f"/api/v1/contacts/{primary['id']}", headers=headers)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/contacts/{duplicate['id']}", headers=headers)
    ).status_code == 200
    primary_identities = (
        await client.get(f"/api/v1/contacts/{primary['id']}/identities", headers=headers)
    ).json()
    duplicate_identities = (
        await client.get(f"/api/v1/contacts/{duplicate['id']}/identities", headers=headers)
    ).json()
    assert {row["id"] for row in primary_identities} == {identity_id}
    assert duplicate_identities == []

    async with session_factory() as session:
        identity = (await session.scalars(select(ContactIdentity))).one()
        primary_row = (
            await session.scalars(select(Contact).where(Contact.wa_id == "14155550001"))
        ).one()
        assert identity.contact_id == primary_row.id
        actions = set((await session.scalars(select(AuditLog.action))).all())
        assert AuditAction.IDENTITY_CONFLICT_DETECTED in actions
        assert AuditAction.IDENTITY_MERGE_RECOMMENDATION_CREATED in actions
        assert AuditAction.IDENTITY_MERGE_RECOMMENDATION_APPROVED in actions
        events = set((await session.scalars(select(ContactEvent.event_type))).all())
        assert "identity_conflict_detected" in events
        assert "identity_recommendation_approved" in events


async def test_non_phone_identity_without_authoritative_contact_requires_review_not_fuzzy_merge(
    client, make_user, session_factory, organization
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    await _set_flag(session_factory, organization.id)
    headers = await _headers(client, "owner@vi.co")
    await _create_contact(client, headers, "+14155550011", "Same Name")
    await _create_contact(client, headers, "+14155550012", "Same Name")

    result = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=headers,
        json={
            "new_contact": {"full_name": "Same Name"},
            "assertions": [
                {
                    "identity_namespace": "telegram_user",
                    "identity_scope": "provider:telegram",
                    "value": "tg-opaque-1",
                    "connector_type": "future_provider",
                }
            ],
        },
    )
    assert result.status_code == 200
    assert result.json()["status"] == "review_required"
    assert result.json()["canonical_contact_id"] is None
    listing = await client.get("/api/v1/contacts", headers=headers)
    assert listing.json()["page"]["total"] == 2


async def test_flag_and_rbac_fail_closed(client, make_user, session_factory, organization) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    owner_headers = await _headers(client, "owner@vi.co")
    disabled = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=owner_headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert disabled.status_code == 404

    await _set_flag(session_factory, organization.id)
    await make_user(email="restricted@vi.co", password=PASSWORD)
    restricted_headers = await _headers(client, "restricted@vi.co")
    denied = await client.post(
        "/api/v1/identity-resolution/resolve",
        headers=restricted_headers,
        json={"assertions": [_phone_assertion("+14155552671")]},
    )
    assert denied.status_code == 403


async def test_tenant_isolation_allows_same_exact_key_without_cross_tenant_resolution(
    db_session, session_factory, organization
) -> None:
    actor_one = User(
        organization_id=organization.id,
        email="one@vi.test",
        password_hash=hash_password(PASSWORD),
        full_name="One",
        is_superuser=True,
    )
    second_org = Organization(name="Second Org", slug="second-org")
    db_session.add_all([actor_one, second_org])
    await db_session.flush()
    actor_two = User(
        organization_id=second_org.id,
        email="two@vi.test",
        password_hash=hash_password(PASSWORD),
        full_name="Two",
        is_superuser=True,
    )
    db_session.add(actor_two)
    db_session.add_all(
        [
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=organization.id,
                is_enabled=True,
            ),
            FeatureFlag(
                key_name=IDENTITY_RESOLUTION_FLAG,
                organization_id=second_org.id,
                is_enabled=True,
            ),
        ]
    )
    await db_session.commit()

    assertion = IdentityAssertion(
        identity_namespace="whatsapp_phone",
        identity_scope="global",
        value="+14155552671",
    )
    first = await IdentityResolutionService(db_session).resolve(
        organization_id=organization.id,
        actor=actor_one,
        assertions=[assertion],
        contact_hint=None,
        new_contact_fields={"full_name": "One"},
    )
    second = await IdentityResolutionService(db_session).resolve(
        organization_id=second_org.id,
        actor=actor_two,
        assertions=[assertion],
        contact_hint=None,
        new_contact_fields={"full_name": "Two"},
    )
    assert first.contact is not None and second.contact is not None
    assert first.contact.public_id != second.contact.public_id
    identities = list((await db_session.scalars(select(ContactIdentity))).all())
    assert len(identities) == 2
    assert {row.organization_id for row in identities} == {organization.id, second_org.id}


async def test_future_namespace_registration_requires_no_resolver_architecture_change() -> None:
    registry = IdentityNormalizerRegistry()
    registry.register("future_network_user", lambda value: value.strip(), global_scope=False)
    normalized = registry.normalize(
        IdentityAssertion(
            identity_namespace="future_network_user",
            identity_scope="provider:future",
            value=" user-42 ",
            connector_type="future_provider",
        )
    )
    assert normalized.normalized_value == "user-42"
    assert normalized.key == ("future_network_user", "provider:future", "user-42")
