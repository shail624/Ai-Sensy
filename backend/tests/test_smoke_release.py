"""RC1 end-to-end smoke test — the release gate, exercised in one flow.

Walks the path an operator actually takes on day one: seed customers, produce message traffic,
roll it up, read the dashboard, export a report, download it, and open the CSV. Each step asserts
the *observable* outcome rather than an internal call, so this fails if any seam between the
modules breaks — which is what a smoke test is for.

Deliberately covers the two defects production hardening fixed (formula neutralisation, report
column shape) and the two isolation guarantees the platform sells (cross-org, executive-only).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.analytics import GRAIN_HOUR, AnalyticsMessageRollup, AnalyticsRollupRun
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.job_records import STATUS_READY, ExportJob
from app.models.message import DIRECTION_OUTBOUND, MSG_DELIVERED, MSG_READ, Message
from app.models.organization import Organization
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.services.analytics_rollup_service import AnalyticsRollupService, window_for
from app.services.export_service import ExportService

PASSWORD = "Sup3r-Secret-Pass1"
BASE = "/api/v1/analytics"

#: One closed hour inside the incremental window, so the rollup has something to find.
NOW = utcnow().replace(minute=30, second=0, microsecond=0)
BUCKET = NOW.replace(minute=0) - timedelta(hours=1)
RANGE = {
    "from": (BUCKET - timedelta(hours=1)).isoformat() + "Z",
    "to": (BUCKET + timedelta(hours=2)).isoformat() + "Z",
}

#: A WhatsApp profile name is attacker-controllable, so it is the realistic injection vector.
HOSTILE_NAME = "=cmd|' /C calc'!A0"


async def _login(client, make_user, *, email: str, **kw) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def seeded(session_factory, organization):
    """Steps 1–2: sample customers and the message traffic a campaign would produce."""
    async with session_factory() as session:
        waba = WhatsAppBusinessAccount(
            organization_id=organization.id, waba_id="WABA-RC1",
            business_name="Vi", access_token_enc=b"cipher",
        )
        session.add(waba)
        await session.flush()
        number = PhoneNumber(
            organization_id=organization.id, waba_id=waba.id,
            phone_number_id="PN-RC1", display_number="+911111111111",
        )
        session.add(number)
        await session.flush()

        contacts = [
            Contact(
                organization_id=organization.id,
                wa_id=f"91999000000{i}",
                phone_e164=f"+91999000000{i}",
                # One customer carries a hostile display name (step 8).
                full_name=HOSTILE_NAME if i == 0 else f"Customer {i}",
                created_at=BUCKET + timedelta(minutes=1),
            )
            for i in range(3)
        ]
        session.add_all(contacts)
        await session.flush()

        conversation = Conversation(
            organization_id=organization.id,
            phone_number_id=number.id,
            contact_id=contacts[0].id,
        )
        session.add(conversation)
        await session.flush()

        # Step 2: a campaign's worth of outbound traffic, with a realistic delivery mix.
        for index, contact in enumerate(contacts):
            session.add(
                Message(
                    organization_id=organization.id,
                    conversation_id=conversation.id,
                    phone_number_id=number.id,
                    contact_id=contact.id,
                    direction=DIRECTION_OUTBOUND,
                    message_type="text",
                    status=MSG_READ if index == 0 else MSG_DELIVERED,
                    cost_amount=0.01,
                    sent_at=BUCKET + timedelta(minutes=2),
                    delivered_at=BUCKET + timedelta(minutes=2, seconds=3),
                    created_at=BUCKET + timedelta(minutes=2),
                )
            )
        await session.commit()
    return organization.id


async def test_release_smoke_flow(client, make_user, session_factory, seeded, monkeypatch):
    """Steps 1–8: seed → roll up → dashboard → export → download → open the CSV."""
    owner = await _login(client, make_user, email="owner@vi.co", is_superuser=True)

    # --- Step 3: execute the rollup exactly as the beat-scheduled task does -----------------
    async with session_factory() as session:
        start, end = window_for(NOW, 6)
        outcome = await AnalyticsRollupService(session).rollup_organization(seeded, start, end)
    assert outcome.rows_written > 0, "the rollup found no source rows to aggregate"

    async with session_factory() as session:
        watermark = (
            await session.scalars(
                select(AnalyticsRollupRun).where(AnalyticsRollupRun.kind == "messages")
            )
        ).first()
    assert watermark is not None and watermark.last_status == "ok"

    # --- Step 4: the dashboard reads what the rollup wrote -----------------------------------
    summary = await client.get(f"{BASE}/summary", params=RANGE, headers=owner)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["totals"]["messages_sent"] == 3
    assert body["totals"]["messages_delivered"] == 3
    assert body["kpis"]["delivery_rate"] == 1.0
    assert body["data_as_of"] is not None, "the dashboard must state how fresh it is"

    freshness = await client.get(f"{BASE}/freshness", headers=owner)
    assert any(row["kind"] == "messages" for row in freshness.json()["data"])

    # --- Step 5: generate a report ------------------------------------------------------------
    import app.analytics.tasks as tasks

    monkeypatch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
    created = await client.post(
        f"{BASE}/reports/export",
        headers=owner,
        json={"report": "messages", "format": "csv", "filters": {**RANGE, "granularity": "hour"}},
    )
    assert created.status_code == 202, created.text
    export_id = created.json()["job"]["id"]

    # The worker body — the same call the exports queue makes.
    async with session_factory() as session:
        job = await ExportService(session).run(export_id)
    assert job.status == STATUS_READY
    assert job.storage_key and job.row_count == 3

    # --- Step 6: download the artifact --------------------------------------------------------
    progress = await client.get(f"{BASE}/reports/{export_id}", headers=owner)
    assert progress.status_code == 200
    assert progress.json()["status"] == STATUS_READY

    async with session_factory() as session:
        stored = (
            await session.scalars(select(ExportJob).where(ExportJob.entity == "report:messages"))
        ).first()
    assert stored is not None

    # --- Step 7: open the exported CSV --------------------------------------------------------
    from app.core.config import settings
    from app.storage.base import get_provider

    raw = await get_provider(settings.storage_backend).get(job.storage_key)
    lines = raw.decode("utf-8").splitlines()
    assert lines[0].startswith("period,messages_"), "report CSV must carry the report columns"
    assert "phone_e164" not in lines[0], "report CSV must not carry the contacts shape"
    assert len(lines) == 4, "header + three hourly buckets"


async def test_contact_export_neutralizes_a_hostile_name(
    client, make_user, session_factory, seeded, monkeypatch
):
    """Step 8: a WhatsApp profile name must not execute when the CSV is opened in Excel."""
    import app.crm.tasks as crm_tasks

    monkeypatch.setattr(crm_tasks.run_contact_export, "apply_async", lambda args, task_id=None: None)
    owner = await _login(client, make_user, email="owner@vi.co", is_superuser=True)

    created = await client.post(
        "/api/v1/contacts/export", headers=owner, json={"format": "csv", "rules": []}
    )
    assert created.status_code == 202, created.text
    export_id = created.json()["job"]["id"]

    async with session_factory() as session:
        job = await ExportService(session).run(export_id)

    from app.core.config import settings
    from app.storage.base import get_provider

    body = (await get_provider(settings.storage_backend).get(job.storage_key)).decode("utf-8")

    assert f"'{HOSTILE_NAME}" in body, "a leading '=' must be neutralised (CWE-1236)"
    assert f",{HOSTILE_NAME}" not in body, "the raw formula must not reach the file"
    # The same pass must not corrupt E.164 numbers, which legitimately start with '+'.
    assert "+919990000001" in body
    assert "'+919990000001" not in body


async def test_cross_organization_isolation(client, make_user, session_factory, seeded):
    """Step 9: one organization's rollups must never reach another's dashboard."""
    async with session_factory() as session:
        other = Organization(name="Other Co", slug="other-co")
        session.add(other)
        await session.flush()
        session.add(
            AnalyticsMessageRollup(
                organization_id=other.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=99, direction=DIRECTION_OUTBOUND, message_type="text",
                accepted_count=9_999, sent_count=9_999,
            )
        )
        await session.commit()

    owner = await _login(client, make_user, email="owner@vi.co", is_superuser=True)
    async with session_factory() as session:
        start, end = window_for(NOW, 6)
        await AnalyticsRollupService(session).rollup_organization(seeded, start, end)

    body = (await client.get(f"{BASE}/summary", params=RANGE, headers=owner)).json()
    assert body["totals"]["messages_sent"] == 3, "another org's 9,999 must not leak in"


async def test_executive_only_metrics_are_gated(client, make_user, seeded):
    """Step 10: spend is commercially sensitive — read access is not enough."""
    await _login(client, make_user, email="owner@vi.co", is_superuser=True)
    analyst = await _login(client, make_user, email="analyst@vi.co", roles=("analyst",))

    assert (await client.get(f"{BASE}/summary", params=RANGE, headers=analyst)).status_code == 200
    assert (await client.get(f"{BASE}/costs", params=RANGE, headers=analyst)).status_code == 403
    assert (
        await client.get(f"{BASE}/executive", params=RANGE, headers=analyst)
    ).status_code == 403


def test_beat_schedule_is_registered_and_utc() -> None:
    """The four periodic entries exist, in UTC, with no duplicates (Doc 15 §8.1)."""
    from app.queue.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    tasks = {entry["task"] for entry in schedule.values()}
    assert tasks == {
        "app.crm.campaign_tasks.scheduler_tick",
        "app.analytics.tasks.rollup_incremental",
        "app.analytics.tasks.rollup_nightly",
        "app.analytics.tasks.rollup_prune",
    }
    # Entry names are the dedupe key: one entry per task, so a restart cannot accumulate them.
    assert len(schedule) == len(tasks)
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True

    incremental = schedule["analytics-rollup-incremental"]["schedule"]
    assert incremental.minute == {0, 15, 30, 45}
    nightly = schedule["analytics-rollup-nightly"]["schedule"]
    assert (nightly.hour, nightly.minute) == ({2}, {15})
    prune = schedule["analytics-rollup-prune"]["schedule"]
    assert (prune.hour, prune.minute) == ({3}, {0})
