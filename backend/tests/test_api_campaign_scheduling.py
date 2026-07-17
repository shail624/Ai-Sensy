"""Campaign scheduling tests (Doc 03 §8.2, Doc 04 §17, Doc 06 §10) — FR-CAM-03/04.

No broker and no clock games: the tick is driven directly and ``now`` is injected, so a test for
"fires when due" does not wait for a due date to arrive.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.db.mixins import utcnow
from app.models.campaign import (
    CAMPAIGN_QUEUED,
    CAMPAIGN_SCHEDULED,
    SCHEDULE_ONE_TIME,
    SCHEDULE_RECURRING,
    Campaign,
    CampaignSchedule,
)
from app.services.campaign_schedule_service import CampaignScheduleService, next_fire
from tests.test_api_campaign_dispatch import _approved_campaign
from tests.test_api_campaigns import CAMPAIGNS_URL
from tests.test_api_conversations import _rows


def _url(campaign_id: str) -> str:
    return f"{CAMPAIGNS_URL}/{campaign_id}/schedule"


async def _campaign_pk(session_factory) -> int:
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        return campaign.id


# --- next_fire: the cron walk ------------------------------------------------
def test_next_fire_respects_timezone() -> None:
    """10:00 in Asia/Kolkata is 04:30 UTC — the zone is what the cron means (Doc 06 §10.4)."""
    after = datetime(2026, 7, 17, 0, 0)
    fire = next_fire("0 10 * * *", after=after, timezone="Asia/Kolkata")
    assert fire == datetime(2026, 7, 17, 4, 30)


def test_next_fire_crosses_dst() -> None:
    """A US spring-forward moves the UTC instant, not the local wall clock."""
    # 2026-03-08 is the US DST transition. 09:00 New York is 14:00 UTC before, 13:00 after.
    before = next_fire("0 9 * * *", after=datetime(2026, 3, 6, 20, 0), timezone="America/New_York")
    after_dst = next_fire("0 9 * * *", after=datetime(2026, 3, 9, 0, 0), timezone="America/New_York")
    assert before == datetime(2026, 3, 7, 14, 0)
    assert after_dst == datetime(2026, 3, 9, 13, 0)


def test_next_fire_weekday_only() -> None:
    """`mon-fri` skips the weekend — Celery's field semantics, not ours."""
    # 2026-07-18 is a Saturday; the next weekday fire is Monday the 20th.
    fire = next_fire("0 9 * * mon-fri", after=datetime(2026, 7, 18, 0, 0), timezone="UTC")
    assert fire == datetime(2026, 7, 20, 9, 0)


def test_next_fire_is_strictly_after() -> None:
    """A fire exactly at `after` is the slot we just ran; the next one is tomorrow."""
    fire = next_fire("0 9 * * *", after=datetime(2026, 7, 17, 9, 0), timezone="UTC")
    assert fire == datetime(2026, 7, 18, 9, 0)


def test_next_fire_returns_none_past_ends_on() -> None:
    fire = next_fire(
        "0 9 * * *",
        after=datetime(2026, 7, 17, 12, 0),
        timezone="UTC",
        ends_on=date(2026, 7, 17),
    )
    assert fire is None


# --- POST /campaigns/{uuid}/schedule ----------------------------------------
@pytest.mark.anyio
async def test_schedule_one_time(client, make_user, session_factory, monkeypatch) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(hours=2)

    response = await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == CAMPAIGN_SCHEDULED
    assert len(body["schedules"]) == 1
    entry = body["schedules"][0]
    assert entry["schedule_type"] == SCHEDULE_ONE_TIME
    assert entry["is_active"] is True
    assert entry["next_run_at"] is not None


@pytest.mark.anyio
async def test_schedule_recurring_computes_next_run(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)

    response = await client.post(
        _url(created["id"]),
        headers=headers,
        json={
            "schedule_type": "recurring",
            "cron_expr": "0 10 * * mon-fri",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 200
    entry = response.json()["schedules"][0]
    assert entry["schedule_type"] == SCHEDULE_RECURRING
    assert entry["cron_expr"] == "0 10 * * mon-fri"
    # 10:00 Kolkata is 04:30 UTC, and next_run_at is stored UTC (Doc 03 §1.3).
    assert entry["next_run_at"].endswith("04:30:00")


@pytest.mark.anyio
async def test_drip_expands_into_one_time_rows(
    client, make_user, session_factory, monkeypatch
) -> None:
    """A drip is N one-time rows, never a third schedule_type (Doc 06 §10.3)."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    anchor = utcnow() + timedelta(hours=1)

    response = await client.post(
        _url(created["id"]),
        headers=headers,
        json={
            "schedule_type": "drip",
            "starts_at": anchor.isoformat(),
            "steps": [0, 1440, 4320],
        },
    )

    assert response.status_code == 200
    schedules = response.json()["schedules"]
    assert len(schedules) == 3
    assert {s["schedule_type"] for s in schedules} == {SCHEDULE_ONE_TIME}
    fires = [datetime.fromisoformat(s["next_run_at"]) for s in schedules]
    # Anchored on starts_at, one step per offset, in order.
    assert fires[1] - fires[0] == timedelta(days=1)
    assert fires[2] - fires[0] == timedelta(days=3)


@pytest.mark.anyio
async def test_reschedule_replaces_previous_rows(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The last thing the operator said is the schedule; earlier rows are retired, not stacked."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    first = utcnow() + timedelta(hours=2)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": first.isoformat()},
    )
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": (first + timedelta(days=1)).isoformat()},
    )

    rows = await _rows(session_factory, CampaignSchedule)
    active = [r for r in rows if r.is_active]
    assert len(rows) == 2
    assert len(active) == 1
    assert active[0].next_run_at is not None


# --- Validation (422) --------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"schedule_type": "one_time"}, id="one_time-without-run_at"),
        pytest.param({"schedule_type": "recurring"}, id="recurring-without-cron"),
        pytest.param(
            {"schedule_type": "recurring", "cron_expr": "not a cron"}, id="unparseable-cron"
        ),
        pytest.param(
            {"schedule_type": "recurring", "cron_expr": "99 10 * * *"}, id="out-of-range-cron"
        ),
        pytest.param(
            {"schedule_type": "recurring", "cron_expr": "0 10 * * *", "timezone": "Mars/Olympus"},
            id="unknown-timezone",
        ),
        pytest.param({"schedule_type": "drip", "steps": [0]}, id="drip-without-anchor"),
    ],
)
async def test_invalid_schedule_is_422(
    client, make_user, session_factory, monkeypatch, payload: dict
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    response = await client.post(_url(created["id"]), headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_past_run_at_is_422(client, make_user, session_factory, monkeypatch) -> None:
    """A schedule in the past would fire instantly — that is a mistake, not an instruction."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    response = await client.post(
        _url(created["id"]),
        headers=headers,
        json={
            "schedule_type": "one_time",
            "run_at": (utcnow() - timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_schedule_unknown_campaign_is_404(client, make_user) -> None:
    from tests.test_api_messages import _headers

    headers = await _headers(client, make_user, email="sched@vi.co", is_superuser=True)
    response = await client.post(
        _url(str(uuid.uuid4())),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": (utcnow() + timedelta(hours=1)).isoformat()},
    )
    assert response.status_code == 404


# --- scheduler.tick ----------------------------------------------------------
@pytest.mark.anyio
async def test_tick_fires_due_one_time_and_spends_it(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The due row hands its campaign to the control lane, then is spent (Doc 06 §18.3)."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(minutes=30)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat()},
    )

    async with session_factory() as session:
        result = await CampaignScheduleService(session).tick(now=run_at + timedelta(seconds=30))

    assert result["fired"] == [await _campaign_pk(session_factory)]
    assert result["missed"] == []
    (schedule,) = await _rows(session_factory, CampaignSchedule)
    assert schedule.is_active is False
    assert schedule.next_run_at is None
    assert schedule.last_run_at is not None
    # The fire is the same act as a manual dispatch: validated, audited, queued.
    (campaign,) = await _rows(session_factory, Campaign)
    assert campaign.status == CAMPAIGN_QUEUED


@pytest.mark.anyio
async def test_tick_ignores_schedules_not_yet_due(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(hours=5)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat()},
    )

    async with session_factory() as session:
        result = await CampaignScheduleService(session).tick(now=utcnow())

    assert result["scanned"] == 0
    assert result["fired"] == []
    (campaign,) = await _rows(session_factory, Campaign)
    assert campaign.status == CAMPAIGN_SCHEDULED


@pytest.mark.anyio
async def test_tick_skips_one_time_past_grace(
    client, make_user, session_factory, monkeypatch
) -> None:
    """A day-late blast is worse than no blast: past grace it is marked missed (Doc 06 §10.5)."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(minutes=10)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat()},
    )

    async with session_factory() as session:
        result = await CampaignScheduleService(session).tick(now=run_at + timedelta(days=1))

    assert result["fired"] == []
    assert len(result["missed"]) == 1
    (schedule,) = await _rows(session_factory, CampaignSchedule)
    assert schedule.is_active is False
    assert schedule.last_run_at is None  # it never ran
    (campaign,) = await _rows(session_factory, Campaign)
    assert campaign.status == CAMPAIGN_SCHEDULED  # untouched; nothing was sent


@pytest.mark.anyio
async def test_tick_recurring_fires_once_and_realigns(
    client, make_user, session_factory, monkeypatch
) -> None:
    """Downtime costs one catch-up fire, not a thundering herd of every missed slot (D15)."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "recurring", "cron_expr": "0 * * * *", "timezone": "UTC"},
    )

    # Wake up three days late: many hourly slots were missed.
    late = utcnow() + timedelta(days=3)
    async with session_factory() as session:
        result = await CampaignScheduleService(session).tick(now=late)

    assert len(result["fired"]) == 1  # exactly one catch-up, not 72
    (schedule,) = await _rows(session_factory, CampaignSchedule)
    assert schedule.is_active is True
    # Realigned forward from now, not replaying the backlog.
    assert schedule.next_run_at > late.replace(tzinfo=None)


@pytest.mark.anyio
async def test_tick_deactivates_recurring_past_ends_on(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    tomorrow = (utcnow() + timedelta(days=1)).date()
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={
            "schedule_type": "recurring",
            "cron_expr": "0 * * * *",
            "ends_on": tomorrow.isoformat(),
        },
    )

    async with session_factory() as session:
        await CampaignScheduleService(session).tick(now=utcnow() + timedelta(days=1, hours=23))

    (schedule,) = await _rows(session_factory, CampaignSchedule)
    assert schedule.is_active is False
    assert schedule.next_run_at is None


@pytest.mark.anyio
async def test_tick_drip_fires_each_step_in_turn(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The tick sees ordinary one-time rows; the drip is already expanded (Doc 06 §10.3)."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    anchor = utcnow() + timedelta(minutes=10)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "drip", "starts_at": anchor.isoformat(), "steps": [0, 60]},
    )

    async with session_factory() as session:
        first = await CampaignScheduleService(session).tick(now=anchor + timedelta(seconds=30))
    assert len(first["fired"]) == 1

    rows = await _rows(session_factory, CampaignSchedule)
    assert sorted(r.is_active for r in rows) == [False, True]

    # The second step is still pending until its own offset arrives.
    async with session_factory() as session:
        second = await CampaignScheduleService(session).tick(now=anchor + timedelta(minutes=61))
    assert second["scanned"] == 1
    rows = await _rows(session_factory, CampaignSchedule)
    assert all(r.is_active is False for r in rows)


@pytest.mark.anyio
async def test_tick_is_idempotent_across_overlapping_runs(
    client, make_user, session_factory, monkeypatch
) -> None:
    """A row is claimed before its campaign is handed over, so a second tick re-fires nothing."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(minutes=5)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat()},
    )

    fire_time = run_at + timedelta(seconds=1)
    async with session_factory() as session:
        first = await CampaignScheduleService(session).tick(now=fire_time)
    async with session_factory() as session:
        second = await CampaignScheduleService(session).tick(now=fire_time)

    assert len(first["fired"]) == 1
    assert second["fired"] == []
    assert second["scanned"] == 0


@pytest.mark.anyio
async def test_tick_task_enqueues_fired_campaigns(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The task is the thin adapter: the service decides, the broker hand-off happens here."""
    import app.crm.campaign_tasks as tasks

    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    run_at = utcnow() + timedelta(minutes=5)
    await client.post(
        _url(created["id"]),
        headers=headers,
        json={"schedule_type": "one_time", "run_at": run_at.isoformat()},
    )

    enqueued: list[int] = []
    monkeypatch.setattr(
        tasks.dispatch_campaign, "apply_async", lambda args: enqueued.append(args[0])
    )
    async with session_factory() as session:
        result = await CampaignScheduleService(session).tick(now=run_at + timedelta(seconds=1))
    for campaign_pk in result["fired"]:
        tasks.dispatch_campaign.apply_async(args=[campaign_pk])

    assert enqueued == [await _campaign_pk(session_factory)]


@pytest.mark.anyio
async def test_scheduler_tick_is_registered_on_its_queue() -> None:
    """The tick belongs to `scheduler.tick` — P0/control, per the registry (Doc 06 §2.3)."""
    from app.crm.campaign_tasks import scheduler_tick
    from app.queue.registry import SCHEDULER_TICK

    assert scheduler_tick.queue_name == SCHEDULER_TICK
