"""Campaign scheduling (Doc 03 §8.2; Doc 06 §10) — FR-CAM-03/04.

**The database is the schedule; Beat is only the heartbeat** (Doc 06 §10.2, D14). Beat embeds no
business schedule: it fires ``scheduler.tick`` on a short cadence, and the tick asks this service
what is due. That is what lets an operator create, edit or pause a schedule through the API with no
redeploy, and what lets schedules survive a restart.

Three shapes, **two rows** (Doc 03 §8.2's frozen ``ck_csched_type``):

* **one-time** — a ``run_at`` in UTC, fired once, then the row is spent.
* **recurring** — a cron read in an IANA zone; ``next_run_at`` is recomputed after each fire.
* **drip** — *not a third type*. A drip request is expanded here, at request time, into N
  ``one_time`` rows anchored on a start time (Doc 06 §10.3 — "the same mechanism"). The tick never
  learns the word: it sees ordinary one-time schedules, which is exactly the point.

Cron parsing and its field semantics are **Celery's** (:class:`celery.schedules.crontab`), already a
dependency. Only the walk to the next matching minute lives here, because the answer must be
computed in the schedule's own zone and stored as UTC (Doc 06 §10.4).
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    CAMPAIGN_DISPATCHABLE,
    CAMPAIGN_SCHEDULED,
    SCHEDULE_ONE_TIME,
    SCHEDULE_RECURRING,
    Campaign,
    CampaignSchedule,
)
from app.models.user import User
from app.repositories.campaign import CampaignRepository, CampaignScheduleRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.campaign_dispatch_service import (
    CampaignDispatchService,
    CampaignNotDispatchable,
)

logger = get_logger(__name__)

#: How far ahead the cron walk is willing to look before calling a schedule spent. Four years
#: covers every realistic cron (including Feb 29) without letting a pathological expression —
#: "Feb 30" — spin forever.
_HORIZON_DAYS = 366 * 4

#: Ceiling on a drip expansion. A drip is a marketing sequence, not a mail-merge loop; an
#: unbounded list would let one request write unbounded rows.
MAX_DRIP_STEPS = 50


class ScheduleInvalid(ValidationError):
    """The cron, the time or the drip shape cannot produce a fire (Doc 04 §17 → 422)."""

    code = "schedule_invalid"
    title = "Invalid Schedule"


class CampaignNotSchedulable(ConflictError):
    """The campaign is not in a state where scheduling it means anything (Doc 04 §17 → 409)."""

    code = "campaign_not_schedulable"
    title = "Campaign Not Schedulable"


def parse_cron(expr: str) -> crontab:
    """Celery's parser, with its errors turned into a 422 (Doc 04 §17).

    Standard five fields: ``minute hour day_of_month month_of_year day_of_week``. Delegated rather
    than reimplemented — ranges, steps, lists and names are semantics we should not own a second
    copy of.
    """
    fields = expr.split()
    if len(fields) != 5:
        raise ScheduleInvalid(
            f"A cron expression needs 5 fields (got {len(fields)}): "
            "minute hour day-of-month month day-of-week."
        )
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    try:
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )
    except (ValueError, KeyError) as exc:
        raise ScheduleInvalid(f"Invalid cron expression {expr!r}: {exc}") from exc


def load_timezone(name: str) -> ZoneInfo:
    """The schedule's IANA zone, or a 422 (Doc 06 §10.4)."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ScheduleInvalid(f"Unknown timezone {name!r}; use an IANA name.") from exc


def next_fire(
    expr: str,
    *,
    after: datetime,
    timezone: str,
    starts_on: date | None = None,
    ends_on: date | None = None,
) -> datetime | None:
    """The first cron match strictly after ``after``, as UTC — or ``None`` if the cron is spent.

    Computed in the schedule's zone and returned as UTC, which is what makes "every weekday at
    10:00 in Asia/Kolkata" survive DST and a server timezone change: the data is UTC, only the
    interpretation is local (Doc 03 §1.3; Doc 06 §10.4).

    Walks candidate days, then that day's matching hours and minutes, rather than every minute —
    ``ix_csched_next`` wants one answer, not a scan.
    """
    cron = parse_cron(expr)
    zone = load_timezone(timezone)

    # Naive means UTC here (Doc 03 §1.3, `utcnow`). Pinning that before any conversion matters:
    # `astimezone` on a naive value would silently read it as the *server's* local time, which is
    # the one interpretation that is never intended.
    after_utc = after.replace(tzinfo=_UTC) if after.tzinfo is None else after.astimezone(_UTC)
    local = after_utc.astimezone(zone)
    # Whole minutes only: cron has no finer resolution, and a stored microsecond would make a
    # fire land a hair early or late forever.
    cursor = local.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if starts_on is not None and cursor.date() < starts_on:
        cursor = datetime.combine(starts_on, time(0, 0), tzinfo=zone)

    hours = sorted(cron.hour)
    minutes = sorted(cron.minute)
    day = cursor.date()
    for offset in range(_HORIZON_DAYS):
        current = day + timedelta(days=offset)
        if ends_on is not None and current > ends_on:
            return None
        if not _day_matches(cron, current):
            continue
        for hh in hours:
            for mm in minutes:
                candidate = datetime.combine(current, time(hh, mm), tzinfo=zone)
                # Compare in UTC: a DST fold makes two local times share a wall clock, and only
                # the absolute instant orders them correctly.
                instant = candidate.astimezone(_UTC)
                if instant > after_utc:
                    return instant.replace(tzinfo=None)
    return None


_UTC = ZoneInfo("UTC")


def _day_matches(cron: crontab, day: date) -> bool:
    """Celery's day semantics: month, day-of-month and day-of-week are ANDed."""
    # Celery counts weekdays from Sunday=0; Python's isoweekday() is Monday=1…Sunday=7.
    dow = day.isoweekday() % 7
    return (
        day.month in cron.month_of_year
        and day.day in cron.day_of_month
        and dow in cron.day_of_week
    )


class CampaignScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._schedules = CampaignScheduleRepository(session)
        self._campaigns = CampaignRepository(session)
        self._users = UserRepository(session)
        self._dispatch = CampaignDispatchService(session)
        self._audit = AuditService(session)

    # --- Create (request path) ----------------------------------------------
    async def schedule(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        schedule_type: str,
        run_at: datetime | None = None,
        cron_expr: str | None = None,
        timezone: str = "UTC",
        starts_on: date | None = None,
        ends_on: date | None = None,
        starts_at: datetime | None = None,
        steps: list[int] | None = None,
    ) -> tuple[Campaign, list[CampaignSchedule]]:
        """Attach a schedule to a campaign and park it in ``scheduled`` (FR-CAM-03/04).

        Replaces rather than accumulates: re-scheduling retires the campaign's live rows, so the
        answer to "when does this fire" is always the last thing the operator said.
        """
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status not in CAMPAIGN_DISPATCHABLE:
            raise CampaignNotSchedulable(
                f"A {campaign.status} campaign cannot be scheduled."
            )

        now = utcnow()
        if schedule_type == SCHEDULE_ONE_TIME:
            rows = [self._one_time(campaign, run_at=run_at, timezone=timezone, now=now)]
        elif schedule_type == SCHEDULE_RECURRING:
            rows = [
                self._recurring(
                    campaign,
                    cron_expr=cron_expr,
                    timezone=timezone,
                    starts_on=starts_on,
                    ends_on=ends_on,
                    now=now,
                )
            ]
        elif schedule_type == "drip":
            rows = self._drip(
                campaign, starts_at=starts_at, steps=steps, timezone=timezone, now=now
            )
        else:
            raise ScheduleInvalid(f"Unknown schedule type {schedule_type!r}.")

        await self._schedules.deactivate_for_campaign(campaign.id)
        for row in rows:
            self._session.add(row)
        campaign.status = CAMPAIGN_SCHEDULED
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._schedules.flush()
        await self._audit.record(
            AuditAction.CAMPAIGN_SCHEDULED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            after={
                "schedule_type": schedule_type,
                "timezone": timezone,
                "fires": [r.next_run_at.isoformat() if r.next_run_at else None for r in rows],
            },
        )
        await self._session.commit()
        return campaign, rows

    def _one_time(
        self, campaign: Campaign, *, run_at: datetime | None, timezone: str, now: datetime
    ) -> CampaignSchedule:
        if run_at is None:
            raise ScheduleInvalid("A one-time schedule needs `run_at`.")
        load_timezone(timezone)
        fire = _naive_utc(run_at)
        if fire <= now:
            raise ScheduleInvalid("`run_at` must be in the future.")
        return CampaignSchedule(
            campaign_id=campaign.id,
            schedule_type=SCHEDULE_ONE_TIME,
            run_at=fire,
            timezone=timezone,
            next_run_at=fire,
            is_active=True,
        )

    def _recurring(
        self,
        campaign: Campaign,
        *,
        cron_expr: str | None,
        timezone: str,
        starts_on: date | None,
        ends_on: date | None,
        now: datetime,
    ) -> CampaignSchedule:
        if not cron_expr:
            raise ScheduleInvalid("A recurring schedule needs `cron_expr`.")
        if starts_on and ends_on and ends_on < starts_on:
            raise ScheduleInvalid("`ends_on` cannot precede `starts_on`.")
        upcoming = next_fire(
            cron_expr,
            after=now,
            timezone=timezone,
            starts_on=starts_on,
            ends_on=ends_on,
        )
        if upcoming is None:
            raise ScheduleInvalid(
                "That cron will never fire within its start/end window."
            )
        return CampaignSchedule(
            campaign_id=campaign.id,
            schedule_type=SCHEDULE_RECURRING,
            cron_expr=cron_expr,
            timezone=timezone,
            starts_on=starts_on,
            ends_on=ends_on,
            next_run_at=upcoming,
            is_active=True,
        )

    def _drip(
        self,
        campaign: Campaign,
        *,
        starts_at: datetime | None,
        steps: list[int] | None,
        timezone: str,
        now: datetime,
    ) -> list[CampaignSchedule]:
        """Expand a drip sequence into ordinary one-time steps (Doc 06 §10.3).

        The expansion is the whole feature. Storing a ``drip`` type would put sequence arithmetic
        in the tick's hot path and add a value the frozen ``ck_csched_type`` does not allow; doing
        it here leaves the scanner reading plain one-time rows.
        """
        if starts_at is None:
            raise ScheduleInvalid("A drip schedule needs `starts_at`.")
        if not steps:
            raise ScheduleInvalid("A drip schedule needs at least one step offset.")
        if len(steps) > MAX_DRIP_STEPS:
            raise ScheduleInvalid(f"A drip sequence is limited to {MAX_DRIP_STEPS} steps.")
        if any(offset < 0 for offset in steps):
            raise ScheduleInvalid("Drip step offsets cannot be negative.")
        if len(set(steps)) != len(steps):
            raise ScheduleInvalid("Drip step offsets must be distinct.")
        load_timezone(timezone)

        anchor = _naive_utc(starts_at)
        rows = []
        for offset in sorted(steps):
            fire = anchor + timedelta(minutes=offset)
            if fire <= now:
                raise ScheduleInvalid(
                    f"Drip step +{offset}m lands in the past; move `starts_at` forward."
                )
            rows.append(
                CampaignSchedule(
                    campaign_id=campaign.id,
                    schedule_type=SCHEDULE_ONE_TIME,
                    run_at=fire,
                    timezone=timezone,
                    next_run_at=fire,
                    is_active=True,
                )
            )
        return rows

    # --- Scan (scheduler.tick) ----------------------------------------------
    async def tick(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Fire everything due and report the campaigns to hand to the control lane (Doc 06 §10.2).

        Each schedule is claimed — advanced or retired, then committed — **before** its campaign is
        handed over, so an overlapping tick cannot fire the same slot twice.

        One campaign's problem is not the tick's: a campaign that will not start is recorded and
        stepped over, because the scan carries every other schedule in the system.
        """
        now = now or utcnow()
        due = await self._schedules.due(now, limit=settings.scheduler_tick_scan_limit)
        fired: list[int] = []
        skipped: list[int] = []
        missed: list[int] = []

        for schedule in due:
            slot = schedule.next_run_at
            # Read before firing: a campaign that declines makes `_fire` roll back, which expires
            # every object in the session — including this row.
            campaign_pk = schedule.campaign_id
            if schedule.schedule_type == SCHEDULE_ONE_TIME and self._too_late(slot, now):
                # A day-late blast is worse than no blast (Doc 06 §10.5, D15).
                schedule.is_active = False
                schedule.next_run_at = None
                await self._schedules.flush()
                await self._session.commit()
                missed.append(schedule.id)
                logger.error(
                    "campaign_schedule_missed",
                    extra={
                        "schedule": schedule.id,
                        "campaign": campaign_pk,
                        "due": slot.isoformat() if slot else None,
                        "grace_seconds": settings.scheduler_one_time_grace_seconds,
                    },
                )
                continue

            await self._claim(schedule, now=now)
            if await self._fire(schedule):
                fired.append(campaign_pk)
            else:
                skipped.append(campaign_pk)

        return {"fired": fired, "skipped": skipped, "missed": missed, "scanned": len(due)}

    def _too_late(self, slot: datetime | None, now: datetime) -> bool:
        if slot is None:
            return False
        grace = timedelta(seconds=settings.scheduler_one_time_grace_seconds)
        return now - slot > grace

    async def _claim(self, schedule: CampaignSchedule, *, now: datetime) -> None:
        """Advance the row past this slot, durably, before anything is enqueued."""
        schedule.last_run_at = now
        if schedule.schedule_type == SCHEDULE_ONE_TIME:
            schedule.next_run_at = None
            schedule.is_active = False
        else:
            # Recompute forward from now, not from the missed slot: a recurring schedule catches
            # up with a single fire and realigns, rather than replaying every slot it slept
            # through (Doc 06 §10.5, D15).
            upcoming = next_fire(
                schedule.cron_expr or "",
                after=now,
                timezone=schedule.timezone,
                starts_on=schedule.starts_on,
                ends_on=schedule.ends_on,
            )
            schedule.next_run_at = upcoming
            schedule.is_active = upcoming is not None
        await self._schedules.flush()
        await self._session.commit()

    async def _fire(self, schedule: CampaignSchedule) -> bool:
        """Hand one campaign to the send fabric, exactly as a manual dispatch would.

        Reuses :meth:`CampaignDispatchService.start` rather than repeating it: a scheduled fire is
        the same act as an operator pressing Send — same validation, same audit trail, same
        ``queued`` transition — and it is attributed to whoever created the campaign.
        """
        campaign = await self._campaigns.get_by_id(schedule.campaign_id)
        if campaign is None or campaign.deleted_at is not None:
            logger.warning(
                "campaign_schedule_orphaned",
                extra={"schedule": schedule.id, "campaign": schedule.campaign_id},
            )
            return False

        actor = (
            await self._users.get_by_id(campaign.created_by) if campaign.created_by else None
        )
        if actor is None:
            logger.error(
                "campaign_schedule_no_actor",
                extra={"schedule": schedule.id, "campaign": campaign.id},
            )
            return False

        try:
            await self._dispatch.start(
                organization_id=campaign.organization_id,
                actor=actor,
                public_id=uuidlib.UUID(bytes=campaign.uuid),
            )
        except CampaignNotDispatchable as exc:
            # Expected for a recurring occurrence whose campaign has already run: the frozen
            # design says the tick enqueues control and nothing more (Doc 06 §18.3), so an
            # occurrence with nothing owed is a no-op, not an error to retry.
            logger.info(
                "campaign_schedule_not_dispatchable",
                extra={
                    "schedule": schedule.id,
                    "campaign": campaign.id,
                    "status": campaign.status,
                    "reason": str(exc),
                },
            )
            await self._session.rollback()
            return False
        return True

    # --- Reads ---------------------------------------------------------------
    async def list_for_campaign(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> list[CampaignSchedule]:
        campaign = await self._campaign(organization_id, public_id)
        return await self._schedules.for_campaign(campaign.id)

    async def _campaign(self, organization_id: int, public_id: uuidlib.UUID) -> Campaign:
        campaign = await self._campaigns.get_active_by_uuid(organization_id, public_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign


def _naive_utc(value: datetime) -> datetime:
    """Store UTC, naive — the column is ``DATETIME(6)`` and every comparison here is UTC.

    An aware input is converted rather than trusted; a naive one is already taken to be UTC
    (Doc 03 §1.3: data is UTC, interpretation is tz-aware).
    """
    if value.tzinfo is None:
        return value.replace(microsecond=0)
    return value.astimezone(_UTC).replace(tzinfo=None, microsecond=0)
