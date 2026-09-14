"""Scheduled Analytics reports: governed CRUD, heartbeat dispatch and ready delivery."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.job_records import STATUS_READY, ExportJob
from app.models.notification import Notification
from app.models.report_schedule import ReportSchedule
from app.models.user import User
from app.services.export_service import ExportService
from app.services.report_schedule_service import ReportScheduleService

PASSWORD = "Sup3r-Secret-Pass1"
BASE = "/api/v1/analytics/report-schedules"


async def _login(client, make_user, *, email: str, is_superuser: bool = False, roles=()):
    created = await make_user(
        email=email, password=PASSWORD, is_superuser=is_superuser, roles=roles
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    return created, {"Authorization": f"Bearer {response.json()['access_token']}"}


def _payload(**changes):
    return {
        "name": "Monday leadership pack",
        "report": "messages",
        "format": "pdf",
        "preset": "last_30d",
        "granularity": "day",
        "cadence": "weekly",
        "timezone": "Asia/Kolkata",
        "local_time": "09:00",
        "weekday": "monday",
        "month_day": None,
        "is_active": True,
        **changes,
    }


async def test_schedule_crud_is_personal_and_requires_export_plus_executive(
    client, make_user
):
    _, owner = await _login(client, make_user, email="schedule-owner@vi.co", is_superuser=True)
    _, other = await _login(client, make_user, email="other-owner@vi.co", is_superuser=True)
    _, analyst = await _login(client, make_user, email="schedule-analyst@vi.co", roles=("analyst",))

    assert (await client.get(BASE, headers=analyst)).status_code == 403
    created = await client.post(BASE, headers=owner, json=_payload())
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["next_run_at"] is not None
    assert row["row_version"] == 0
    assert (await client.get(BASE, headers=other)).json() == {"data": []}

    duplicate = await client.post(BASE, headers=owner, json=_payload())
    assert duplicate.status_code == 409

    updated_payload = _payload(
        name="Daily delivery pack",
        cadence="daily",
        weekday=None,
        local_time="08:15",
        expected_row_version=row["row_version"],
    )
    updated = await client.put(f"{BASE}/{row['id']}", headers=owner, json=updated_payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["row_version"] == 1
    assert updated.json()["cadence"] == "daily"

    stale = await client.put(f"{BASE}/{row['id']}", headers=owner, json=updated_payload)
    assert stale.status_code == 409
    deleted = await client.delete(
        f"{BASE}/{row['id']}",
        headers=owner,
        params={"expected_row_version": 1},
    )
    assert deleted.status_code == 204
    assert (await client.get(BASE, headers=owner)).json() == {"data": []}


async def test_schedule_shape_and_timezone_are_validated(client, make_user):
    _, owner = await _login(client, make_user, email="schedule-validation@vi.co", is_superuser=True)

    missing_weekday = await client.post(BASE, headers=owner, json=_payload(weekday=None))
    assert missing_weekday.status_code == 422
    unknown_timezone = await client.post(
        BASE, headers=owner, json=_payload(timezone="Mars/Olympus")
    )
    assert unknown_timezone.status_code == 422
    invalid_month = await client.post(
        BASE,
        headers=owner,
        json=_payload(cadence="monthly", weekday=None, month_day=31),
    )
    assert invalid_month.status_code == 422


async def test_personal_schedule_limit_is_enforced(client, make_user):
    _, owner = await _login(client, make_user, email="schedule-limit@vi.co", is_superuser=True)
    for index in range(25):
        response = await client.post(
            BASE, headers=owner, json=_payload(name=f"Leadership pack {index + 1}")
        )
        assert response.status_code == 201, response.text

    overflow = await client.post(BASE, headers=owner, json=_payload(name="One too many"))
    assert overflow.status_code == 422
    assert "at most 25" in overflow.json()["detail"]


async def test_due_schedule_creates_one_shared_export_and_ready_notification(
    client, make_user, session_factory
):
    created_user, headers = await _login(
        client, make_user, email="scheduled-export@vi.co", is_superuser=True
    )
    response = await client.post(
        BASE,
        headers=headers,
        json=_payload(
            report="team_productivity", format="csv", preset="last_7d", timezone="UTC"
        ),
    )
    assert response.status_code == 201, response.text
    schedule_id = response.json()["id"]
    now = utcnow().replace(second=0, microsecond=0)
    dispatched: list[tuple[str, str]] = []

    async with session_factory() as session:
        schedule = (await session.scalars(select(ReportSchedule))).one()
        schedule.next_run_at = now - timedelta(minutes=1)
        await session.commit()

    async with session_factory() as session:
        result = await ReportScheduleService(session).tick(
            now=now,
            dispatch=lambda export_id, task_id: dispatched.append((export_id, task_id)),
        )
    assert result["scanned"] == 1
    assert len(result["fired"]) == 1
    assert [item[0] for item in dispatched] == result["fired"]

    async with session_factory() as session:
        again = await ReportScheduleService(session).tick(
            now=now,
            dispatch=lambda export_id, task_id: dispatched.append((export_id, task_id)),
        )
        job = (await session.scalars(select(ExportJob))).one()
        schedule = (await session.scalars(select(ReportSchedule))).one()
        export_id = job.public_id
        assert again == {"scanned": 0, "fired": [], "disabled": []}
        assert job.entity == "report:team_productivity"
        assert job.requested_by == created_user.user.id
        assert job.filters_json["_report_schedule_id"] == schedule_id
        assert schedule.last_run_at == now
        assert schedule.next_run_at and schedule.next_run_at > now

    async with session_factory() as session:
        ready = await ExportService(session).run(export_id)
        assert ready.status == STATUS_READY

    async with session_factory() as session:
        notification = (await session.scalars(select(Notification))).one()
        assert notification.notification_type == "report_ready"
        assert notification.recipient_user_id == created_user.user.id
        assert notification.dedup_key == f"report-export-ready:{export_id}"

    center = await client.get("/api/v1/notifications?type=report_ready", headers=headers)
    assert center.status_code == 200, center.text
    assert center.json()["data"][0]["action_url"] == "/downloads?category=analytics&status=ready"


async def test_tick_disables_schedule_when_owner_is_inactive(client, make_user, session_factory):
    _, headers = await _login(
        client, make_user, email="inactive-schedule-owner@vi.co", is_superuser=True
    )
    assert (await client.post(BASE, headers=headers, json=_payload(timezone="UTC"))).status_code == 201
    now = utcnow().replace(second=0, microsecond=0)

    async with session_factory() as session:
        user = (
            await session.scalars(select(User).where(User.email == "inactive-schedule-owner@vi.co"))
        ).one()
        schedule = (await session.scalars(select(ReportSchedule))).one()
        user.is_active = False
        schedule.next_run_at = now - timedelta(minutes=1)
        await session.commit()

    dispatched: list[str] = []
    async with session_factory() as session:
        result = await ReportScheduleService(session).tick(
            now=now,
            dispatch=lambda export_id, task_id: dispatched.append(export_id),
        )
        schedule = (await session.scalars(select(ReportSchedule))).one()
        assert schedule.is_active is False
        assert schedule.next_run_at is None

    assert result["scanned"] == 1
    assert len(result["disabled"]) == 1
    assert dispatched == []
