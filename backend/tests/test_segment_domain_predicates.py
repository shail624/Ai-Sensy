"""Current, tenant-scoped Vi-domain predicates for saved Segments (GROW-03)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.contact import Contact
from app.models.contact_document import ContactDocument
from app.models.organization import Organization
from app.models.vi_domain import ActivationRecord, EligibilityCheck, KycCase, ReactivationCase

PASSWORD = "Sup3r-Secret-Pass1"
REQUEST_HASH = "0" * 64


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _contact(client, headers: dict[str, str], phone: str, name: str) -> dict:
    response = await client.post(
        "/api/v1/contacts",
        headers=headers,
        json={"phone_e164": phone, "full_name": name},
    )
    assert response.status_code == 201
    return response.json()


async def _matching_names(
    client,
    headers: dict[str, str],
    *,
    name: str,
    field_source: str,
    field_key: str,
    operator: str,
    value: object,
) -> set[str | None]:
    created = await client.post(
        "/api/v1/segments",
        headers=headers,
        json={
            "name": name,
            "rules": [
                {
                    "field_source": field_source,
                    "field_key": field_key,
                    "operator": operator,
                    "value": value,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    preview = await client.get(
        f"/api/v1/segments/{created.json()['id']}/contacts", headers=headers
    )
    assert preview.status_code == 200, preview.text
    return {contact["full_name"] for contact in preview.json()["data"]}


async def test_vi_domain_segment_predicates_use_current_tenant_truth(
    client, make_user, session_factory, organization
) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    contacts = [
        await _contact(client, headers, "+14155551001", "Eligible Alice"),
        await _contact(client, headers, "+14155551002", "KYC Bob"),
        await _contact(client, headers, "+14155551003", "Interested Carol"),
        await _contact(client, headers, "+14155551004", "Documents Dana"),
        await _contact(client, headers, "+14155551005", "Completed Eve"),
        await _contact(client, headers, "+14155551006", "Tenant Trap"),
    ]

    async with session_factory() as session:
        rows = list(
            await session.scalars(
                select(Contact).where(
                    Contact.uuid.in_([uuid.UUID(item["id"]).bytes for item in contacts])
                )
            )
        )
        by_name = {row.full_name: row for row in rows}
        cases: dict[str, ReactivationCase] = {}
        for name, stage in (
            ("Eligible Alice", "new_lead"),
            ("KYC Bob", "kyc_verification"),
            ("Interested Carol", "lead_confirmed"),
            ("Documents Dana", "documents_pending"),
            ("Completed Eve", "completed"),
            ("Tenant Trap", "kyc_verification"),
        ):
            contact = by_name[name]
            case = ReactivationCase(
                organization_id=organization.id,
                contact_id=contact.id,
                stage=stage,
                idempotency_key=uuid.uuid4().bytes,
                request_hash=REQUEST_HASH,
                created_by=owner.user.id,
                updated_by=owner.user.id,
            )
            session.add(case)
            cases[name] = case
        await session.flush()

        # Only the latest append-only eligibility decision is current.
        for name, statuses in (
            ("Eligible Alice", ("pending", "eligible")),
            ("KYC Bob", ("eligible", "not_eligible")),
        ):
            for status in statuses:
                session.add(
                    EligibilityCheck(
                        organization_id=organization.id,
                        case_id=cases[name].id,
                        contact_id=by_name[name].id,
                        status=status,
                        source="rules",
                        idempotency_key=uuid.uuid4().bytes,
                        request_hash=REQUEST_HASH,
                    )
                )

        session.add(
            KycCase(
                organization_id=organization.id,
                reactivation_case_id=cases["KYC Bob"].id,
                contact_id=by_name["KYC Bob"].id,
                status="under_review",
                idempotency_key=uuid.uuid4().bytes,
                request_hash=REQUEST_HASH,
            )
        )
        session.add(
            ContactDocument(
                organization_id=organization.id,
                contact_id=by_name["Documents Dana"].id,
                document_type="identity",
                title="Identity evidence",
                status="submitted",
                created_by=owner.user.id,
                updated_by=owner.user.id,
            )
        )
        session.add(
            ActivationRecord(
                organization_id=organization.id,
                reactivation_case_id=cases["Documents Dana"].id,
                contact_id=by_name["Documents Dana"].id,
                status="verification",
                idempotency_key=uuid.uuid4().bytes,
                request_hash=REQUEST_HASH,
            )
        )

        # A corrupt cross-tenant domain row must never make the current tenant's contact match.
        foreign = Organization(name="Foreign", slug="foreign-segment-domain")
        session.add(foreign)
        await session.flush()
        session.add(
            KycCase(
                organization_id=foreign.id,
                reactivation_case_id=cases["Tenant Trap"].id,
                contact_id=by_name["Tenant Trap"].id,
                status="under_review",
                idempotency_key=uuid.uuid4().bytes,
                request_hash=REQUEST_HASH,
            )
        )
        await session.commit()

    assert await _matching_names(
        client,
        headers,
        name="Eligible",
        field_source="reactivation",
        field_key="eligibility_status",
        operator="eq",
        value="eligible",
    ) == {"Eligible Alice"}
    assert await _matching_names(
        client,
        headers,
        name="KYC in progress",
        field_source="kyc",
        field_key="status",
        operator="in",
        value=["pending", "documents_pending", "under_review"],
    ) == {"KYC Bob"}
    assert await _matching_names(
        client,
        headers,
        name="Interested",
        field_source="reactivation",
        field_key="stage",
        operator="eq",
        value="lead_confirmed",
    ) == {"Interested Carol"}
    assert await _matching_names(
        client,
        headers,
        name="Documents",
        field_source="document",
        field_key="status",
        operator="eq",
        value="submitted",
    ) == {"Documents Dana"}
    assert await _matching_names(
        client,
        headers,
        name="Activation",
        field_source="activation",
        field_key="status",
        operator="in",
        value=["pending", "verification", "ready", "approved"],
    ) == {"Documents Dana"}
    assert await _matching_names(
        client,
        headers,
        name="Completed",
        field_source="reactivation",
        field_key="stage",
        operator="eq",
        value="completed",
    ) == {"Completed Eve"}


async def test_vi_domain_segment_rules_reject_unknown_fields_values_and_operators(
    client, make_user
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    invalid_rules = [
        {"field_source": "kyc", "field_key": "status", "operator": "eq", "value": "gone"},
        {
            "field_source": "reactivation",
            "field_key": "unknown",
            "operator": "eq",
            "value": "completed",
        },
        {
            "field_source": "document",
            "field_key": "status",
            "operator": "contains",
            "value": "submit",
        },
        {
            "field_source": "activation",
            "field_key": "status",
            "operator": "in",
            "value": [],
        },
        {
            "field_source": "kyc",
            "field_key": "status",
            "operator": "exists",
            "value": "yes",
        },
    ]
    for index, rule in enumerate(invalid_rules):
        response = await client.post(
            "/api/v1/segments",
            headers=headers,
            json={"name": f"Invalid {index}", "rules": [rule]},
        )
        assert response.status_code == 422, response.text
