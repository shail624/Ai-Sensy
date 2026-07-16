"""API + service tests for job tracking and the DLQ (Doc 04 §22, Doc 06 §7)."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.job import JOB_SUCCESS
from app.services.job_service import DeadLetterService, JobService, fingerprint

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _job(session, task_id="t1", queue="default", **kw):
    service = JobService(session)
    job = await service.record_queued(
        task_id=task_id, task_name="app.tasks.demo", queue=queue, **kw
    )
    await session.commit()
    return job


# --- Job lifecycle ----------------------------------------------------------
async def test_job_lifecycle_tracking(db_session, organization) -> None:
    service = JobService(db_session)
    job = await _job(db_session)
    assert job.status == "queued" and job.attempts == 0

    await service.mark_started("t1")
    await db_session.commit()
    assert job.status == "started" and job.attempts == 1 and job.started_at is not None

    await service.mark_finished("t1", status=JOB_SUCCESS, result={"rows": 3})
    await db_session.commit()
    assert job.status == "success" and job.result_json == {"rows": 3}
    assert job.finished_at is not None and job.is_terminal is True


async def test_record_queued_is_idempotent(db_session, organization) -> None:
    first = await _job(db_session)
    second = await _job(db_session)  # redelivery must not duplicate the row
    assert first.id == second.id


async def test_mark_unknown_task_is_noop(db_session, organization) -> None:
    service = JobService(db_session)
    assert await service.mark_started("missing") is None
    assert await service.mark_finished("missing", status=JOB_SUCCESS) is None


async def test_cancel_job_revokes_and_audits(db_session, organization, make_user) -> None:
    actor = (await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)).user
    job = await _job(db_session)
    revoked: list[str] = []

    service = JobService(db_session)
    cancelled = await service.cancel_job(
        actor=actor, public_id=uuid.UUID(job.public_id), revoke=revoked.append
    )
    assert cancelled.status == "revoked" and revoked == ["t1"]

    # A terminal job cannot be cancelled again.
    with pytest.raises(ConflictError):
        await service.cancel_job(
            actor=actor, public_id=uuid.UUID(job.public_id), revoke=revoked.append
        )


async def test_get_unknown_job_404(db_session, organization) -> None:
    with pytest.raises(NotFoundError):
        await JobService(db_session).get_job(uuid.uuid4())


# --- Dead letter (Doc 06 §7) ------------------------------------------------
async def test_park_replay_and_discard(db_session, organization, make_user) -> None:
    actor = (await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)).user
    service = DeadLetterService(db_session)

    entry = await service.park(
        source_queue="webhooks.process",
        task_name="app.tasks.process",
        task_id="x1",
        payload={"args": [1], "kwargs": {}},
        error_class="unknown",
        error_detail="boom",
        attempts=5,
    )
    await db_session.commit()
    assert entry.status == "parked" and entry.fingerprint

    sent: list[tuple] = []
    replayed = await service.replay(
        actor=actor,
        public_id=uuid.UUID(entry.public_id),
        send=lambda name, payload, queue: sent.append((name, payload, queue)),
    )
    assert replayed.status == "replayed"
    assert sent == [("app.tasks.process", {"args": [1], "kwargs": {}}, "webhooks.process")]

    # Already-resolved entries cannot be replayed or discarded again.
    with pytest.raises(ConflictError):
        await service.discard(actor=actor, public_id=uuid.UUID(entry.public_id))


async def test_discard_marks_resolved(db_session, organization, make_user) -> None:
    actor = (await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)).user
    service = DeadLetterService(db_session)
    entry = await service.park(
        source_queue="default", task_name="t", task_id=None, payload=None,
        error_class="terminal", error_detail="bad",
    )
    await db_session.commit()
    discarded = await service.discard(actor=actor, public_id=uuid.UUID(entry.public_id))
    assert discarded.status == "discarded" and discarded.resolved_by == actor.id


def test_fingerprint_groups_same_root_cause() -> None:
    a = fingerprint("task", "transient", "Meta 500")
    b = fingerprint("task", "transient", "Meta 500")
    c = fingerprint("task", "terminal", "Meta 500")
    assert a == b and a != c  # one cause → one group (§7.4)


# --- API (Doc 04 §22) -------------------------------------------------------
async def test_jobs_api_list_get_and_filter(client, make_user, session_factory) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "ops@vi.co")
    async with session_factory() as session:
        await _job(session, task_id="a", queue="imports")
        await _job(session, task_id="b", queue="exports")

    listing = await client.get("/api/v1/jobs", headers=h)
    assert listing.status_code == 200 and listing.json()["page"]["total"] == 2

    filtered = await client.get("/api/v1/jobs?filter[queue][eq]=imports", headers=h)
    assert [j["queue"] for j in filtered.json()["data"]] == ["imports"]

    job_id = listing.json()["data"][0]["id"]
    assert (await client.get(f"/api/v1/jobs/{job_id}", headers=h)).status_code == 200
    assert (await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=h)).status_code == 404


async def test_jobs_permission_enforcement(client, make_user) -> None:
    # agent holds neither system:read nor system:manage
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    h = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/jobs", headers=h)).status_code == 403
    assert (await client.get("/api/v1/queues", headers=h)).status_code == 403
    assert (await client.get("/api/v1/jobs")).status_code == 401
