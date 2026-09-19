"""Governed campaign recipient-result exports and shared artifact delivery."""

from __future__ import annotations

import csv
import io
import uuid as uuidlib
from datetime import timedelta

import pytest
from anyio import Path
from sqlalchemy import select

from app.core.config import settings
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.campaign import Campaign, CampaignRecipient
from app.models.contact import Contact
from app.models.job import JobMetadata
from app.models.job_records import STATUS_READY, ExportJob
from app.services.export_service import ExportService
from tests.test_api_campaigns import CAMPAIGNS_URL, _body, _setup

PASSWORD = "Sup3r-Secret-Pass1"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _campaign(client, make_user, session_factory, monkeypatch) -> str:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    response = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, name="August recovery"),
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_campaign_export_requires_entitlement_and_enqueues_personal_job(
    client, make_user, session_factory, organization, monkeypatch
) -> None:
    campaign_id = await _campaign(client, make_user, session_factory, monkeypatch)
    manager = await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    await make_user(email="other@vi.co", password=PASSWORD, roles=("manager",))
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))

    import app.crm.tasks as tasks

    dispatched: list[tuple[list[str], str | None]] = []
    monkeypatch.setattr(
        tasks.run_campaign_results_export,
        "apply_async",
        lambda args, task_id=None: dispatched.append((args, task_id)),
    )
    endpoint = f"{CAMPAIGNS_URL}/{campaign_id}/exports"
    denied = await client.post(
        endpoint,
        headers=await _headers(client, "agent@vi.co"),
        json={"format": "csv"},
    )
    accepted = await client.post(
        endpoint,
        headers=await _headers(client, "manager@vi.co"),
        json={"format": "xlsx", "status": "failed"},
    )

    assert denied.status_code == 403
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["job"]["id"]
    assert accepted.json()["job"]["poll_url"] == f"{endpoint}/{job_id}"
    assert dispatched and dispatched[0][0] == [job_id]

    async with session_factory() as session:
        job = (await session.scalars(select(ExportJob))).one()
        metadata = (await session.scalars(select(JobMetadata))).one()
        assert job.organization_id == organization.id
        assert job.requested_by == manager.user.id
        assert job.entity == "campaign_results"
        assert job.filters_json == {
            "campaign_id": campaign_id,
            "campaign_name": "August recovery",
            "status": "failed",
        }
        assert metadata.task_name == "app.crm.tasks.run_campaign_results_export"
        assert metadata.queue == "exports"

    own = await client.get(f"{endpoint}/{job_id}", headers=await _headers(client, "manager@vi.co"))
    foreign = await client.get(f"{endpoint}/{job_id}", headers=await _headers(client, "other@vi.co"))
    assert own.status_code == 200 and own.json()["status"] == "pending"
    assert foreign.status_code == 404


async def test_campaign_export_validates_contract_and_tenant_scoped_campaign(
    client, make_user, session_factory, monkeypatch
) -> None:
    campaign_id = await _campaign(client, make_user, session_factory, monkeypatch)
    await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    headers = await _headers(client, "manager@vi.co")
    endpoint = f"{CAMPAIGNS_URL}/{campaign_id}/exports"

    invalid_format = await client.post(endpoint, headers=headers, json={"format": "xml"})
    invalid_status = await client.post(endpoint, headers=headers, json={"status": "opened"})
    unknown = await client.post(
        f"{CAMPAIGNS_URL}/{uuidlib.uuid4()}/exports",
        headers=headers,
        json={"format": "csv"},
    )

    assert invalid_format.status_code == 422
    assert invalid_status.status_code == 422
    assert unknown.status_code == 404


async def test_campaign_worker_streams_filtered_rows_and_redacts_internal_references(
    client, make_user, session_factory, organization, monkeypatch
) -> None:
    campaign_id = await _campaign(client, make_user, session_factory, monkeypatch)
    manager = await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    now = utcnow().replace(microsecond=0)

    async with session_factory() as session:
        campaign = (await session.scalars(select(Campaign))).one()
        campaign.cost_currency = "INR"
        recipients = list(
            (await session.scalars(select(CampaignRecipient).order_by(CampaignRecipient.id))).all()
        )
        contacts = list((await session.scalars(select(Contact).order_by(Contact.id))).all())
        contacts[0].full_name = "=HYPERLINK(\"https://invalid\")"
        for index, recipient in enumerate(recipients):
            recipient.created_at = now + timedelta(seconds=index)
            recipient.status = "failed" if index != 1 else "delivered"
            recipient.error_code = "131047" if recipient.status == "failed" else None
            recipient.error_detail = "PRIVATE INTERNAL DETAIL"
            recipient.wamid = "wamid.SECRET-PROVIDER-ID"
            recipient.message_id = 9000 + index
            recipient.variables_json = {"body": ["PRIVATE VARIABLE VALUE"]}
            recipient.retry_count = index
            recipient.cost_amount = "0.125000"
            recipient.queued_at = now + timedelta(seconds=index)
            recipient.failed_at = now + timedelta(minutes=1, seconds=index)
        await session.commit()

    monkeypatch.setattr("app.services.export_service._BATCH", 1)
    async with session_factory() as session:
        job = await ExportService(session).start_campaign_results(
            organization_id=organization.id,
            actor=manager.user,
            campaign_id=uuidlib.UUID(campaign_id),
            file_format="csv",
            recipient_status="failed",
            dispatch=lambda _export_id, _task_id: None,
        )
        export_id = job.public_id

    async with session_factory() as session:
        ready = await ExportService(session).run(export_id)
        assert ready.status == STATUS_READY
        assert ready.row_count == 2
        assert ready.storage_key is not None
        artifact = await Path(settings.storage_local_path, ready.storage_key).read_bytes()
        audits = list(
            (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action.in_(("export.started", "export.completed"))
                    )
                )
            ).all()
        )

    text = artifact.decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [row["recipient_status"] for row in rows] == ["failed", "failed"]
    assert rows[0]["contact_name_current"].startswith("'=")
    assert rows[0]["phone_e164_current"].startswith("+91")
    assert rows[0]["error_code"] == "131047"
    assert rows[0]["cost_currency"] == "INR"
    assert "wamid" not in rows[0]
    assert "message_id" not in rows[0]
    assert "variables" not in rows[0]
    assert "error_detail" not in rows[0]
    assert "PRIVATE INTERNAL DETAIL" not in text
    assert "PRIVATE VARIABLE VALUE" not in text
    assert "SECRET-PROVIDER-ID" not in text
    assert len(audits) == 2


async def test_campaign_progress_rejects_cross_campaign_job_substitution(
    client, make_user, session_factory, monkeypatch
) -> None:
    first_id = await _campaign(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, "mgr@vi.co")
    contacts = (await client.get("/api/v1/contacts", headers=headers)).json()["data"]
    campaigns = (await client.get(CAMPAIGNS_URL, headers=headers)).json()["data"]
    first = campaigns[0]
    second = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(
            first["phone_number_id"],
            first["template_id"],
            contacts[:1],
            name="Second campaign",
        ),
    )
    assert second.status_code == 201, second.text

    import app.crm.tasks as tasks

    monkeypatch.setattr(tasks.run_campaign_results_export, "apply_async", lambda *args, **kwargs: None)
    created = await client.post(
        f"{CAMPAIGNS_URL}/{first_id}/exports",
        headers=headers,
        json={"format": "csv"},
    )
    job_id = created.json()["job"]["id"]

    substituted = await client.get(
        f"{CAMPAIGNS_URL}/{second.json()['id']}/exports/{job_id}", headers=headers
    )
    assert substituted.status_code == 404


async def test_campaign_export_contract_is_published(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    schema = (await client.get("/api/v1/openapi.json")).json()
    assert "/api/v1/campaigns/{campaign_id}/exports" in schema["paths"]
    assert "/api/v1/campaigns/{campaign_id}/exports/{export_id}" in schema["paths"]
    request_schema = schema["components"]["schemas"]["CampaignResultsExportRequest"]
    assert set(request_schema["properties"]["format"]["enum"]) == {"pdf", "csv", "xlsx", "json"}

