"""CORE-02 API permissions, tenant isolation and OpenAPI contract tests."""

from __future__ import annotations

import uuid

import pytest

from app.core.security import hash_password
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.user import User

PASSWORD = "Sup3r-Secret-Pass!"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_reactivation_api_permissions_and_tenant_isolation(
    client, session_factory, organization, make_user
) -> None:
    agent = await make_user(email="core02-agent@vi.co", roles=("agent",))
    analyst = await make_user(email="core02-analyst@vi.co", roles=("analyst",))
    async with session_factory() as session:
        contact = Contact(
            organization_id=organization.id,
            wa_id="919811110001",
            phone_e164="+919811110001",
            full_name="API Vi Customer",
        )
        other_org = Organization(name="Other Tenant", slug="other-core02")
        session.add_all([contact, other_org])
        await session.flush()
        other_user = User(
            organization_id=other_org.id,
            email="other-core02@vi.co",
            password_hash=hash_password(PASSWORD),
            full_name="Other Tenant Owner",
            is_superuser=True,
        )
        session.add(other_user)
        await session.commit()

    agent_headers = await _headers(client, agent.user.email)
    response = await client.post(
        f"/api/v1/contacts/{contact.public_id}/reactivation-cases",
        headers=agent_headers,
        json={"idempotency_key": str(uuid.uuid4()), "source": "manual"},
    )
    assert response.status_code == 201, response.text
    case_id = response.json()["id"]

    pipeline = await client.get("/api/v1/reactivation-pipeline", headers=agent_headers)
    assert pipeline.status_code == 200
    assert pipeline.json()["total"] == 1
    assert pipeline.json()["data"][0]["contact_name"] == "API Vi Customer"
    assert pipeline.json()["data"][0]["available_transitions"] == [
        "follow_up",
        "not_interested",
    ]

    note = await client.post(
        f"/api/v1/reactivation-cases/{case_id}/notes",
        headers=agent_headers,
        json={"body": "Persisted case note"},
    )
    assert note.status_code == 201
    note_list = await client.get(
        f"/api/v1/reactivation-cases/{case_id}/notes", headers=agent_headers
    )
    assert note_list.status_code == 200
    assert note_list.json()["data"][0]["body"] == "Persisted case note"

    transitioned = await client.post(
        f"/api/v1/reactivation-cases/{case_id}/transition",
        headers=agent_headers,
        json={
            "idempotency_key": str(uuid.uuid4()),
            "expected_row_version": 0,
            "to_stage": "follow_up",
        },
    )
    assert transitioned.status_code == 200
    stale = await client.patch(
        f"/api/v1/reactivation-cases/{case_id}",
        headers=agent_headers,
        json={"expected_row_version": 0},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"

    analyst_headers = await _headers(client, analyst.user.email)
    assert (
        await client.get(f"/api/v1/reactivation-cases/{case_id}", headers=analyst_headers)
    ).status_code == 200
    forbidden = await client.post(
        f"/api/v1/contacts/{contact.public_id}/reactivation-cases",
        headers=analyst_headers,
        json={"idempotency_key": str(uuid.uuid4()), "source": "manual"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"

    approval_payload = {
        "idempotency_key": str(uuid.uuid4()),
        "expected_row_version": 0,
        "decision": "approved",
    }
    assert (
        await client.post(
            f"/api/v1/kyc-cases/{uuid.uuid4()}/approvals",
            headers=analyst_headers,
            json=approval_payload,
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/sim-orders/{uuid.uuid4()}/transition",
            headers=agent_headers,
            json={
                "idempotency_key": str(uuid.uuid4()),
                "expected_row_version": 0,
                "to_status": "approved",
            },
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/activation-records/{uuid.uuid4()}/approval",
            headers=agent_headers,
            json={
                "idempotency_key": str(uuid.uuid4()),
                "expected_row_version": 0,
                "to_status": "approved",
                "approval_reference": "MGR-TEST",
            },
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/sla/policies",
            headers=agent_headers,
            json={
                "domain": "reactivation",
                "trigger_name": "follow_up",
                "target_minutes": 60,
                "escalation_minutes": 90,
            },
        )
    ).status_code == 403

    other_headers = await _headers(client, "other-core02@vi.co")
    hidden = await client.get(f"/api/v1/reactivation-cases/{case_id}", headers=other_headers)
    assert hidden.status_code == 404
    hidden_pipeline = await client.get("/api/v1/reactivation-pipeline", headers=other_headers)
    assert hidden_pipeline.status_code == 200
    assert hidden_pipeline.json()["total"] == 0
    hidden_notes = await client.get(
        f"/api/v1/reactivation-cases/{case_id}/notes", headers=other_headers
    )
    assert hidden_notes.status_code == 404


@pytest.mark.asyncio
async def test_vi_openapi_exposes_typed_permission_scoped_foundation(client) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()
    expected = {
        "/api/v1/reactivation-cases/{case_id}/transition",
        "/api/v1/reactivation-cases/{case_id}/notes",
        "/api/v1/reactivation-pipeline",
        "/api/v1/kyc-cases/{kyc_id}/approvals",
        "/api/v1/kyc-operations",
        "/api/v1/kyc-cases/{kyc_id}/document-references",
        "/api/v1/kyc-cases/{kyc_id}/appointments",
        "/api/v1/sim-orders/{order_id}/transition",
        "/api/v1/activation-records/{activation_id}/approval",
        "/api/v1/sla/events",
    }
    assert expected <= set(schema["paths"])
    assert len(schema["paths"]) == 188
    assert "ReactivationCaseResponse" in schema["components"]["schemas"]
    assert "ActivationRecordResponse" in schema["components"]["schemas"]
    assert "KycOperationsResponse" in schema["components"]["schemas"]
    for immutable_path in (
        "/api/v1/eligibility-checks/{check_id}",
        "/api/v1/kyc-decisions/{decision_id}",
        "/api/v1/sim-order-events/{event_id}",
        "/api/v1/sla/events/{event_id}",
    ):
        assert "patch" not in schema["paths"][immutable_path]
        assert "delete" not in schema["paths"][immutable_path]
