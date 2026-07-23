"""Analytics rollup service (Doc 15 §6–§8) — the write side of the analytics pipeline.

For each closed hourly bucket in a window, this service recomputes every fact table from the
operational sources (Doc 15 §5) and replaces that bucket's rows wholesale.

Three invariants govern the module:

* **Derived, never authoritative** (Doc 15 §4.1). A bucket's rows are a pure function of the source
  rows falling inside it, so the tables can be dropped and rebuilt at any time.
* **Additive measures only** (Doc 15 §6.2). Counts and sums are stored; every ratio is divided at
  read time, because a stored average cannot be re-aggregated.
* **Idempotent by re-derivation** (Doc 15 §6.3). Each bucket is *deleted and re-inserted* in one
  transaction, so re-running a window converges rather than double-counts.

**Concurrency — no lock.** Two overlapping runs may duplicate work and briefly contend on the same
rows, but neither can produce a wrong figure: both compute the same function of the same sources.
This is the strategy the campaign dispatcher already uses for the identical problem, and it is why
the platform needs no distributed-lock utility (Doc 15 §7).

**Late data** is absorbed by recomputing a *trailing window* rather than only the newest bucket: a
delivery receipt for a 10:59 send can arrive at 11:05, and the retry engine can deliver hours later
(Doc 15 §8.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.analytics import (
    GRAIN_DAY,
    GRAIN_HOUR,
    KIND_CAMPAIGNS,
    KIND_CONTACTS,
    KIND_CONVERSATIONS,
    KIND_FAILURES,
    KIND_MESSAGES,
    KIND_TASKS,
    ROLLUP_KINDS,
    RUN_FAILED,
    RUN_OK,
    AnalyticsCampaignRollup,
    AnalyticsContactRollup,
    AnalyticsConversationRollup,
    AnalyticsFailureRollup,
    AnalyticsMessageRollup,
    AnalyticsTaskRollup,
)
from app.models.campaign import (
    RECIPIENT_DELIVERED,
    RECIPIENT_FAILED,
    RECIPIENT_READ,
    RECIPIENT_SENT,
    RECIPIENT_SKIPPED,
    Campaign,
    CampaignRecipient,
)
from app.models.contact import OPT_IN_OPTED_IN, OPT_IN_OPTED_OUT, Contact
from app.models.conversation import CONV_RESOLVED, Conversation
from app.models.message import (
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    MSG_DELIVERED,
    MSG_FAILED,
    MSG_READ,
    MSG_SENT,
    Message,
)
from app.models.organization import Organization
from app.models.task import Task
from app.models.task_event import (
    TASK_EVENT_CANCELLED,
    TASK_EVENT_COMPLETED,
    TASK_EVENT_CREATED,
    TASK_EVENT_REOPENED,
    TASK_EVENT_SKIPPED,
    TaskEvent,
)
from app.repositories.analytics import AnalyticsRepository

logger = get_logger(__name__)

#: Doc 15 §8.1 — the incremental run recomputes this many trailing closed hours.
TRAILING_WINDOW_HOURS = 6
#: Doc 15 §8.1 — the nightly pass reaches further back, for data later than the trailing window.
NIGHTLY_WINDOW_HOURS = 48
#: Doc 15 §11.4 — inbound after this much silence counts as a reactivation.
REACTIVATION_SILENCE_DAYS = 30
#: Doc 15 §21.3 — retention: hourly rows 90 days, daily consolidation rows ~26 months.
HOURLY_RETENTION_DAYS = 90
DAILY_RETENTION_DAYS = 790
#: Cost is stored in micro-units of the organization's currency (Doc 15 §9.1).
COST_MICROS = 1_000_000

#: Dimension columns per fact table — drives both consolidation and the grain UNIQUE (Doc 15 §9).
_DIMENSIONS: dict[type, tuple[str, ...]] = {
    AnalyticsMessageRollup: ("phone_number_id", "direction", "message_type"),
    AnalyticsFailureRollup: ("phone_number_id", "error_code"),
    AnalyticsCampaignRollup: ("campaign_id",),
    AnalyticsConversationRollup: ("phone_number_id", "assigned_user_id"),
    AnalyticsTaskRollup: ("assigned_agent_id", "task_type"),
    AnalyticsContactRollup: (),
}
_NON_MEASURE = {"id", "organization_id", "grain", "bucket_start", "created_at", "updated_at"}


def floor_hour(moment: datetime) -> datetime:
    """The UTC hour bucket ``moment`` belongs to (Doc 15 §6.1)."""
    return moment.replace(minute=0, second=0, microsecond=0)


def floor_day(moment: datetime) -> datetime:
    """The UTC day bucket ``moment`` belongs to — the consolidation grain (Doc 15 §21.4)."""
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def hour_range(start: datetime, end: datetime) -> list[datetime]:
    """Every hour bucket in ``[start, end)``, oldest first."""
    buckets: list[datetime] = []
    cursor = floor_hour(start)
    while cursor < end:
        buckets.append(cursor)
        cursor += timedelta(hours=1)
    return buckets


def window_for(now: datetime, hours: int) -> tuple[datetime, datetime]:
    """The closed-bucket window ending at the last complete hour before ``now``.

    The *current* hour is deliberately excluded: it is still accumulating, and a partial bucket
    stored as if it were complete would read as a real dip in every chart.
    """
    end = floor_hour(now)
    return end - timedelta(hours=hours), end


def _micros(amount: Decimal | float | None) -> int:
    return 0 if amount is None else int(Decimal(str(amount)) * COST_MICROS)


def _count_if(condition: ColumnElement[bool]) -> ColumnElement[int]:
    """A dialect-neutral conditional count: 1 where the condition holds, else 0."""
    return func.sum(case((condition, 1), else_=0))


def _measures_of(model: type) -> tuple[str, ...]:
    dims = set(_DIMENSIONS[model])
    return tuple(
        column.name
        for column in model.__table__.columns
        if column.name not in _NON_MEASURE and column.name not in dims
    )


@dataclass(slots=True)
class RollupOutcome:
    """What one run did — returned to the task layer for logging and assertions."""

    organization_id: int
    kinds: tuple[str, ...]
    buckets: int
    rows_written: int
    window_start: datetime
    window_end: datetime


class AnalyticsRollupService:
    """Builds and maintains the pre-aggregated rollups (Doc 15 §6–§8)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AnalyticsRepository(session)

    # --- Entry points ---------------------------------------------------------------------------
    async def run_incremental(
        self, *, now: datetime | None = None, kinds: Sequence[str] | None = None
    ) -> list[RollupOutcome]:
        """Recompute the trailing 6 h for every organization (Doc 15 §8.1)."""
        start, end = window_for(now or utcnow(), TRAILING_WINDOW_HOURS)
        return await self._run_orgs(start, end, kinds)

    async def run_nightly(
        self, *, now: datetime | None = None, kinds: Sequence[str] | None = None
    ) -> list[RollupOutcome]:
        """Recompute the trailing 48 h, then write daily consolidation rows (§8.1, §21.4)."""
        start, end = window_for(now or utcnow(), NIGHTLY_WINDOW_HOURS)
        outcomes = await self._run_orgs(start, end, kinds)
        for outcome in outcomes:
            await self.consolidate_days(outcome.organization_id, start, end)
        return outcomes

    async def run_backfill(
        self,
        *,
        start: datetime,
        end: datetime,
        organization_id: int | None = None,
        kinds: Sequence[str] | None = None,
    ) -> list[RollupOutcome]:
        """Recompute an explicit range (Doc 15 §23.1 recovery).

        Safe at any time and any overlap: delete-then-insert makes a re-run converge rather than
        double-count, so a backfill needs no cleanup before or after.
        """
        return await self._run_orgs(
            floor_hour(start),
            floor_hour(end),
            kinds,
            organization_ids=[organization_id] if organization_id else None,
        )

    async def prune(self, *, now: datetime | None = None) -> int:
        """Drop rollup rows past retention (Doc 15 §21.3)."""
        moment = now or utcnow()
        cutoffs = (
            (GRAIN_HOUR, floor_hour(moment) - timedelta(days=HOURLY_RETENTION_DAYS)),
            (GRAIN_DAY, floor_day(moment) - timedelta(days=DAILY_RETENTION_DAYS)),
        )
        removed = 0
        for model in _DIMENSIONS:
            for grain, cutoff in cutoffs:
                removed += await self._repo.prune_before(model, grain, cutoff)
        await self._session.commit()
        return removed

    # --- Orchestration --------------------------------------------------------------------------
    async def _run_orgs(
        self,
        start: datetime,
        end: datetime,
        kinds: Sequence[str] | None,
        organization_ids: list[int] | None = None,
    ) -> list[RollupOutcome]:
        org_ids = organization_ids or await self._organization_ids()
        return [
            await self.rollup_organization(org_id, start, end, kinds) for org_id in org_ids
        ]

    async def rollup_organization(
        self,
        organization_id: int,
        start: datetime,
        end: datetime,
        kinds: Sequence[str] | None = None,
    ) -> RollupOutcome:
        """Recompute every bucket in ``[start, end)`` for one organization.

        Each bucket commits in its **own transaction**, so a failure part-way through leaves the
        buckets already done intact and the watermark honest about how far it got.
        """
        selected = tuple(kinds) if kinds else ROLLUP_KINDS
        buckets = hour_range(start, end)
        rows_written = 0

        for bucket in buckets:
            try:
                rows_written += await self._replace_bucket(organization_id, bucket, selected)
            except Exception as exc:  # noqa: BLE001 - record, then let the task layer classify
                await self._session.rollback()
                await self._record_run(
                    organization_id, selected, status=RUN_FAILED, error=str(exc)[:500]
                )
                logger.error(
                    "analytics_rollup_failed",
                    extra={"organization_id": organization_id, "bucket": bucket.isoformat()},
                )
                raise

        watermark = end - timedelta(hours=1) if buckets else None
        await self._record_run(organization_id, selected, status=RUN_OK, watermark=watermark)
        return RollupOutcome(
            organization_id=organization_id,
            kinds=selected,
            buckets=len(buckets),
            rows_written=rows_written,
            window_start=start,
            window_end=end,
        )

    async def _replace_bucket(
        self, organization_id: int, bucket: datetime, kinds: Sequence[str]
    ) -> int:
        """Delete-then-insert one hourly bucket, in one transaction (Doc 15 §6.3)."""
        upper = bucket + timedelta(hours=1)
        builders = {
            KIND_MESSAGES: (AnalyticsMessageRollup, self._build_messages),
            KIND_FAILURES: (AnalyticsFailureRollup, self._build_failures),
            KIND_CAMPAIGNS: (AnalyticsCampaignRollup, self._build_campaigns),
            KIND_CONVERSATIONS: (AnalyticsConversationRollup, self._build_conversations),
            KIND_TASKS: (AnalyticsTaskRollup, self._build_tasks),
            KIND_CONTACTS: (AnalyticsContactRollup, self._build_contacts),
        }
        written = 0
        for kind in kinds:
            model, build = builders[kind]
            await self._repo.clear_bucket(model, organization_id, GRAIN_HOUR, bucket)
            rows = await build(organization_id, bucket, upper)
            for row in rows:
                self._session.add(row)
            written += len(rows)
        await self._session.commit()
        return written

    # --- Aggregations (Doc 15 §9) ----------------------------------------------------------------
    async def _build_messages(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsMessageRollup]:
        """Volume, delivery outcome and cost by number × direction × type (§9.1, FR-AN-01)."""
        stmt = (
            select(
                Message.phone_number_id,
                Message.direction,
                Message.message_type,
                func.count().label("accepted"),
                _count_if(Message.status.in_((MSG_SENT, MSG_DELIVERED, MSG_READ))).label("sent"),
                _count_if(Message.status.in_((MSG_DELIVERED, MSG_READ))).label("delivered"),
                _count_if(Message.status == MSG_READ).label("read"),
                _count_if(Message.status == MSG_FAILED).label("failed"),
                func.sum(func.coalesce(Message.cost_amount, 0)).label("cost"),
            )
            .where(
                Message.organization_id == organization_id,
                Message.created_at >= lower,
                Message.created_at < upper,
            )
            .group_by(Message.phone_number_id, Message.direction, Message.message_type)
        )
        latencies = await self._delivery_latencies(organization_id, lower, upper)
        rows: list[AnalyticsMessageRollup] = []
        for row in (await self._session.execute(stmt)).all():
            key = (row.phone_number_id, row.direction, row.message_type)
            latency_sum, latency_count = latencies.get(key, (0, 0))
            rows.append(
                AnalyticsMessageRollup(
                    organization_id=organization_id,
                    grain=GRAIN_HOUR,
                    bucket_start=lower,
                    phone_number_id=row.phone_number_id,
                    direction=row.direction,
                    message_type=row.message_type,
                    accepted_count=int(row.accepted or 0),
                    sent_count=int(row.sent or 0),
                    delivered_count=int(row.delivered or 0),
                    read_count=int(row.read or 0),
                    failed_count=int(row.failed or 0),
                    cost_micros=_micros(row.cost),
                    delivery_latency_ms_sum=latency_sum,
                    delivery_latency_count=latency_count,
                )
            )
        return rows

    async def _delivery_latencies(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> dict[tuple[int | None, str, str], tuple[int, int]]:
        """Σ (delivered_at − sent_at) in ms and its denominator, per dimension.

        Differenced in Python rather than SQL because the epoch function differs between MySQL and
        SQLite and the per-hour row count is small. Only messages carrying *both* timestamps
        contribute, so the average covers messages that actually completed the transition.
        """
        stmt = select(
            Message.phone_number_id,
            Message.direction,
            Message.message_type,
            Message.sent_at,
            Message.delivered_at,
        ).where(
            Message.organization_id == organization_id,
            Message.created_at >= lower,
            Message.created_at < upper,
            Message.sent_at.is_not(None),
            Message.delivered_at.is_not(None),
        )
        totals: dict[tuple[int | None, str, str], tuple[int, int]] = {}
        for row in (await self._session.execute(stmt)).all():
            elapsed_ms = int((row.delivered_at - row.sent_at).total_seconds() * 1000)
            if elapsed_ms < 0:
                continue  # provider clock skew, not a measurement
            key = (row.phone_number_id, row.direction, row.message_type)
            carried_sum, carried_count = totals.get(key, (0, 0))
            totals[key] = (carried_sum + elapsed_ms, carried_count + 1)
        return totals

    async def _build_failures(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsFailureRollup]:
        """Failures grouped by Meta error code (§9.2, FR-AN-07)."""
        stmt = (
            select(
                Message.phone_number_id,
                Message.error_code,
                func.count().label("failures"),
            )
            .where(
                Message.organization_id == organization_id,
                Message.created_at >= lower,
                Message.created_at < upper,
                Message.status == MSG_FAILED,
                Message.error_code.is_not(None),
            )
            .group_by(Message.phone_number_id, Message.error_code)
        )
        return [
            AnalyticsFailureRollup(
                organization_id=organization_id,
                grain=GRAIN_HOUR,
                bucket_start=lower,
                phone_number_id=row.phone_number_id,
                error_code=row.error_code,
                failure_count=int(row.failures or 0),
            )
            for row in (await self._session.execute(stmt)).all()
        ]

    async def _build_campaigns(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsCampaignRollup]:
        """Per-campaign funnel and spend from the recipient log (§9.3, FR-AN-02/03).

        ``campaign_recipients`` carries no ``organization_id`` (it is scoped through its campaign),
        so the org filter is a join — not a column. ``click_count`` stays 0 until Phase 8b
        (Doc 15 §13); the column exists so the shape does not change when click tracking lands.
        """
        stmt = (
            select(
                CampaignRecipient.campaign_id,
                func.count().label("targeted"),
                _count_if(
                    CampaignRecipient.status.in_(
                        (RECIPIENT_SENT, RECIPIENT_DELIVERED, RECIPIENT_READ)
                    )
                ).label("sent"),
                _count_if(
                    CampaignRecipient.status.in_((RECIPIENT_DELIVERED, RECIPIENT_READ))
                ).label("delivered"),
                _count_if(CampaignRecipient.status == RECIPIENT_READ).label("read"),
                _count_if(CampaignRecipient.status == RECIPIENT_FAILED).label("failed"),
                _count_if(CampaignRecipient.status == RECIPIENT_SKIPPED).label("skipped"),
                func.sum(func.coalesce(CampaignRecipient.cost_amount, 0)).label("cost"),
            )
            .join(Campaign, Campaign.id == CampaignRecipient.campaign_id)
            .where(
                Campaign.organization_id == organization_id,
                CampaignRecipient.created_at >= lower,
                CampaignRecipient.created_at < upper,
            )
            .group_by(CampaignRecipient.campaign_id)
        )
        return [
            AnalyticsCampaignRollup(
                organization_id=organization_id,
                grain=GRAIN_HOUR,
                bucket_start=lower,
                campaign_id=row.campaign_id,
                targeted_count=int(row.targeted or 0),
                sent_count=int(row.sent or 0),
                delivered_count=int(row.delivered or 0),
                read_count=int(row.read or 0),
                failed_count=int(row.failed or 0),
                skipped_count=int(row.skipped or 0),
                click_count=0,
                cost_micros=_micros(row.cost),
            )
            for row in (await self._session.execute(stmt)).all()
        ]

    async def _build_conversations(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsConversationRollup]:
        """Inbox throughput by number × agent (§9.4, FR-AN-02/06).

        Message volume is attributed to the thread's *current* assignee, which is what "how much
        did this agent handle" means operationally.

        First-response and resolution latency (§11.2) need a per-thread walk of the ledger that the
        hourly bucket cannot see in isolation — a reply may answer an inbound from a previous hour.
        Their components are written as 0 here and are the first thing A6 needs; the columns exist
        so the schema does not change when that walk lands.
        """
        opened = await self._pairs(
            select(
                Conversation.phone_number_id,
                Conversation.assigned_user_id,
                func.count().label("n"),
            )
            .where(
                Conversation.organization_id == organization_id,
                Conversation.created_at >= lower,
                Conversation.created_at < upper,
            )
            .group_by(Conversation.phone_number_id, Conversation.assigned_user_id)
        )
        resolved = await self._pairs(
            select(
                Conversation.phone_number_id,
                Conversation.assigned_user_id,
                func.count().label("n"),
            )
            .where(
                Conversation.organization_id == organization_id,
                Conversation.status == CONV_RESOLVED,
                Conversation.updated_at >= lower,
                Conversation.updated_at < upper,
            )
            .group_by(Conversation.phone_number_id, Conversation.assigned_user_id)
        )

        volume_stmt = (
            select(
                Conversation.phone_number_id,
                Conversation.assigned_user_id,
                Message.direction,
                func.count().label("n"),
                func.count(func.distinct(Message.conversation_id)).label("threads"),
            )
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.organization_id == organization_id,
                Message.created_at >= lower,
                Message.created_at < upper,
            )
            .group_by(
                Conversation.phone_number_id, Conversation.assigned_user_id, Message.direction
            )
        )
        inbound: dict[tuple[int | None, int | None], int] = {}
        outbound: dict[tuple[int | None, int | None], int] = {}
        handled: dict[tuple[int | None, int | None], int] = {}
        for row in (await self._session.execute(volume_stmt)).all():
            key = (row.phone_number_id, row.assigned_user_id)
            if row.direction == DIRECTION_INBOUND:
                inbound[key] = inbound.get(key, 0) + int(row.n or 0)
            elif row.direction == DIRECTION_OUTBOUND:
                outbound[key] = outbound.get(key, 0) + int(row.n or 0)
                handled[key] = max(handled.get(key, 0), int(row.threads or 0))

        keys = set(opened) | set(resolved) | set(inbound) | set(outbound)
        return [
            AnalyticsConversationRollup(
                organization_id=organization_id,
                grain=GRAIN_HOUR,
                bucket_start=lower,
                phone_number_id=key[0],
                assigned_user_id=key[1],
                opened_count=opened.get(key, 0),
                resolved_count=resolved.get(key, 0),
                inbound_message_count=inbound.get(key, 0),
                outbound_message_count=outbound.get(key, 0),
                handled_count=handled.get(key, 0),
                first_response_seconds_sum=0,
                first_response_count=0,
                resolution_seconds_sum=0,
                resolution_count=0,
            )
            for key in sorted(keys, key=lambda k: (k[0] or 0, k[1] or 0))
        ]

    async def _build_tasks(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsTaskRollup]:
        """Follow-up metrics from the immutable task history (§9.5, redeeming Doc 14 §12).

        Read from ``task_events``, not ``tasks``: a task edited after the fact must not rewrite its
        own history, which is exactly the auditability Doc 14 §12 promised when it deferred these
        metrics to Phase 8.
        """
        stmt = (
            select(
                Task.assigned_agent_id,
                Task.task_type,
                TaskEvent.event_type,
                func.count().label("n"),
            )
            .join(Task, Task.id == TaskEvent.task_id)
            .where(
                TaskEvent.organization_id == organization_id,
                TaskEvent.created_at >= lower,
                TaskEvent.created_at < upper,
            )
            .group_by(Task.assigned_agent_id, Task.task_type, TaskEvent.event_type)
        )
        events: dict[tuple[int | None, str], dict[str, int]] = {}
        for row in (await self._session.execute(stmt)).all():
            bucket = events.setdefault((row.assigned_agent_id, row.task_type), {})
            bucket[row.event_type] = bucket.get(row.event_type, 0) + int(row.n or 0)

        completions = await self._task_completions(organization_id, lower, upper)
        overdue = await self._tasks_became_overdue(organization_id, lower, upper)
        keys = set(events) | set(completions) | set(overdue)

        return [
            AnalyticsTaskRollup(
                organization_id=organization_id,
                grain=GRAIN_HOUR,
                bucket_start=lower,
                assigned_agent_id=key[0],
                task_type=key[1],
                created_count=events.get(key, {}).get(TASK_EVENT_CREATED, 0),
                completed_count=events.get(key, {}).get(TASK_EVENT_COMPLETED, 0),
                completed_on_time_count=completions.get(key, (0, 0, 0))[0],
                skipped_count=events.get(key, {}).get(TASK_EVENT_SKIPPED, 0),
                cancelled_count=events.get(key, {}).get(TASK_EVENT_CANCELLED, 0),
                reopened_count=events.get(key, {}).get(TASK_EVENT_REOPENED, 0),
                overdue_entered_count=overdue.get(key, 0),
                time_to_complete_seconds_sum=completions.get(key, (0, 0, 0))[1],
                time_to_complete_count=completions.get(key, (0, 0, 0))[2],
            )
            for key in sorted(keys, key=lambda k: (k[0] or 0, k[1]))
        ]

    async def _task_completions(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> dict[tuple[int | None, str], tuple[int, int, int]]:
        """On-time count plus time-to-complete components, per agent × type (§11.3)."""
        stmt = select(
            Task.assigned_agent_id, Task.task_type, Task.due_at, Task.completed_at, Task.created_at
        ).where(
            Task.organization_id == organization_id,
            Task.completed_at.is_not(None),
            Task.completed_at >= lower,
            Task.completed_at < upper,
        )
        totals: dict[tuple[int | None, str], tuple[int, int, int]] = {}
        for row in (await self._session.execute(stmt)).all():
            key = (row.assigned_agent_id, row.task_type)
            on_time, elapsed_sum, elapsed_count = totals.get(key, (0, 0, 0))
            if row.due_at is not None and row.completed_at <= row.due_at:
                on_time += 1
            elapsed = int((row.completed_at - row.created_at).total_seconds())
            totals[key] = (on_time, elapsed_sum + max(elapsed, 0), elapsed_count + 1)
        return totals

    async def _tasks_became_overdue(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> dict[tuple[int | None, str], int]:
        """Open tasks whose ``due_at`` elapsed inside this bucket (§9.5)."""
        stmt = (
            select(Task.assigned_agent_id, Task.task_type, func.count().label("n"))
            .where(
                Task.organization_id == organization_id,
                Task.deleted_at.is_(None),
                Task.due_at >= lower,
                Task.due_at < upper,
                Task.completed_at.is_(None),
            )
            .group_by(Task.assigned_agent_id, Task.task_type)
        )
        return {
            (row.assigned_agent_id, row.task_type): int(row.n or 0)
            for row in (await self._session.execute(stmt)).all()
        }

    async def _build_contacts(
        self, organization_id: int, lower: datetime, upper: datetime
    ) -> list[AnalyticsContactRollup]:
        """Customer growth and opt-in health (§9.6, FR-AN-08)."""
        created = await self._scalar(
            select(func.count()).select_from(Contact).where(
                Contact.organization_id == organization_id,
                Contact.created_at >= lower,
                Contact.created_at < upper,
            )
        )
        opted_in = await self._scalar(
            select(func.count()).select_from(Contact).where(
                Contact.organization_id == organization_id,
                Contact.opt_in_status == OPT_IN_OPTED_IN,
                Contact.opt_in_at >= lower,
                Contact.opt_in_at < upper,
            )
        )
        opted_out = await self._scalar(
            select(func.count()).select_from(Contact).where(
                Contact.organization_id == organization_id,
                Contact.opt_in_status == OPT_IN_OPTED_OUT,
                Contact.opt_out_at >= lower,
                Contact.opt_out_at < upper,
            )
        )
        # Distinct contacts with any message this hour. Summed across buckets this is active
        # customer-*hours*, not unique customers (Doc 15 §11.4, Q3).
        active = await self._scalar(
            select(func.count(func.distinct(Message.contact_id))).where(
                Message.organization_id == organization_id,
                Message.created_at >= lower,
                Message.created_at < upper,
            )
        )
        reactivated = await self._scalar(
            select(func.count(func.distinct(Message.contact_id)))
            .join(Contact, Contact.id == Message.contact_id)
            .where(
                Message.organization_id == organization_id,
                Message.direction == DIRECTION_INBOUND,
                Message.created_at >= lower,
                Message.created_at < upper,
                Contact.last_contacted_at.is_not(None),
                Contact.last_contacted_at < lower - timedelta(days=REACTIVATION_SILENCE_DAYS),
            )
        )

        if not any((created, opted_in, opted_out, active, reactivated)):
            return []  # an empty hour writes no row; the read layer densifies (Doc 15 §10)
        return [
            AnalyticsContactRollup(
                organization_id=organization_id,
                grain=GRAIN_HOUR,
                bucket_start=lower,
                created_count=created,
                opted_in_count=opted_in,
                opted_out_count=opted_out,
                reactivated_count=reactivated,
                active_count=active,
            )
        ]

    # --- Daily consolidation (Doc 15 §21.4) ------------------------------------------------------
    async def consolidate_days(
        self, organization_id: int, start: datetime, end: datetime
    ) -> int:
        """Fold hourly rows into daily rows so long ranges survive the 90-day hourly prune.

        Same delete-then-insert discipline, one grain up. Because measures are additive (§6.2) a day
        is exactly the sum of its hours — the sources are never re-read.
        """
        days = sorted({floor_day(bucket) for bucket in hour_range(start, end)})
        written = 0
        for model in _DIMENSIONS:
            for day in days:
                await self._repo.clear_bucket(model, organization_id, GRAIN_DAY, day)
                written += await self._consolidate_one(model, organization_id, day)
        await self._session.commit()
        return written

    async def _consolidate_one(self, model: type, organization_id: int, day: datetime) -> int:
        """Sum one model's hourly rows for ``day`` into day-grain rows, grouped by its dimensions."""
        dimension_names = _DIMENSIONS[model]
        measures = _measures_of(model)
        dimensions = [getattr(model, name) for name in dimension_names]
        selected = [*dimensions, *[func.sum(getattr(model, m)).label(m) for m in measures]]
        stmt = select(*selected).where(
            model.organization_id == organization_id,
            model.grain == GRAIN_HOUR,
            model.bucket_start >= day,
            model.bucket_start < day + timedelta(days=1),
        )
        if dimensions:
            stmt = stmt.group_by(*dimensions)

        written = 0
        for row in (await self._session.execute(stmt)).all():
            values = row._mapping
            if all(int(values[m] or 0) == 0 for m in measures):
                continue
            self._session.add(
                model(
                    organization_id=organization_id,
                    grain=GRAIN_DAY,
                    bucket_start=day,
                    **{name: values[name] for name in dimension_names},
                    **{m: int(values[m] or 0) for m in measures},
                )
            )
            written += 1
        return written

    # --- Watermarks (Doc 15 §9.7, §23) -----------------------------------------------------------
    async def _record_run(
        self,
        organization_id: int,
        kinds: Sequence[str],
        *,
        status: str,
        watermark: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Advance (or fail) the per-kind watermark. A watermark never moves backwards."""
        now = utcnow()
        for kind in kinds:
            run = await self._repo.upsert_run(organization_id, kind)
            run.last_run_at = now
            run.last_status = status
            run.last_error = error
            if watermark is not None and (
                run.watermark_at is None or watermark > run.watermark_at
            ):
                run.watermark_at = watermark
        await self._session.commit()

    # --- Helpers ---------------------------------------------------------------------------------
    async def _scalar(self, stmt: Select) -> int:
        return int((await self._session.scalar(stmt)) or 0)

    async def _pairs(self, stmt: Select) -> dict[tuple[int | None, int | None], int]:
        return {
            (row[0], row[1]): int(row.n or 0)
            for row in (await self._session.execute(stmt)).all()
        }

    async def _organization_ids(self) -> list[int]:
        return list(
            (await self._session.scalars(select(Organization.id).order_by(Organization.id))).all()
        )
