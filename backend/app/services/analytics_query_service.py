"""Analytics query service (Doc 15 §10–§14) — the read side of the pipeline.

Resolves a date range, picks a stored grain, folds UTC buckets into the caller's timezone, emits
**dense** series with no gaps, and computes every ratio at read time from the stored additive
components (Doc 15 §6.2, §11).

It reads **only** the rollup tables — never a partitioned operational source — which is what makes
the §22 latency targets reachable against a 10M+ row ledger. Live "right now" counters stay on
their owning modules (Doc 15 §8.3, AN-CD4); this service never re-implements an operational list
read, and it never re-derives a rollup.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.db.mixins import utcnow
from app.models.analytics import (
    GRAIN_DAY,
    GRAIN_HOUR,
    AnalyticsCampaignRollup,
    AnalyticsContactRollup,
    AnalyticsConversationRollup,
    AnalyticsFailureRollup,
    AnalyticsMessageRollup,
    AnalyticsTaskRollup,
)
from app.models.campaign import Campaign
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository
from app.services.analytics_rollup_service import (
    HOURLY_RETENTION_DAYS,
    floor_day,
    floor_hour,
)

# --- Granularity & presets (Doc 15 §14.2) --------------------------------------------------------
GRANULARITY_HOUR = "hour"
GRANULARITY_DAY = "day"
GRANULARITY_WEEK = "week"
GRANULARITY_MONTH = "month"
GRANULARITIES: tuple[str, ...] = (
    GRANULARITY_HOUR,
    GRANULARITY_DAY,
    GRANULARITY_WEEK,
    GRANULARITY_MONTH,
)

PRESETS: tuple[str, ...] = (
    "today",
    "yesterday",
    "last_7d",
    "last_30d",
    "this_month",
    "last_month",
    "this_quarter",
)

COMPARE_PREVIOUS_PERIOD = "previous_period"
COMPARE_PREVIOUS_YEAR = "previous_year"
COMPARISONS: tuple[str, ...] = (COMPARE_PREVIOUS_PERIOD, COMPARE_PREVIOUS_YEAR)

#: Doc 15 §14.3 — maximum span per granularity, so one request is always bounded work.
MAX_SPAN_DAYS: dict[str, int] = {
    GRANULARITY_HOUR: 7,
    GRANULARITY_DAY: 400,
    GRANULARITY_WEEK: 365 * 3,
    GRANULARITY_MONTH: 365 * 5,
}

_UTC = ZoneInfo("UTC")

#: Groupable dimensions → the fact table that carries them (Doc 15 §16, family 3).
DIMENSIONS: dict[str, type] = {
    "error_code": AnalyticsFailureRollup,
    "campaign_id": AnalyticsCampaignRollup,
    "assigned_user_id": AnalyticsConversationRollup,
    "assigned_agent_id": AnalyticsTaskRollup,
    "task_type": AnalyticsTaskRollup,
    "direction": AnalyticsMessageRollup,
    "message_type": AnalyticsMessageRollup,
    "phone_number_id": AnalyticsMessageRollup,
}
#: A breakdown is a leaderboard, not a dump — drill-down goes to the operational list endpoints.
MAX_BREAKDOWN_ROWS = 200
#: A NULL dimension is a real cohort (the unassigned backlog), not an absence.
UNASSIGNED_LABEL = "Unassigned"


def resolve_timezone(name: str | None) -> ZoneInfo:
    """Resolve an IANA name, falling back to UTC (Doc 15 §14.1).

    The caller is expected to have already applied the precedence chain (explicit → user → org);
    this is the single place that turns a name into a zone.
    """
    if not name:
        return _UTC
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BadRequestError(f"Unknown timezone {name!r}.") from exc


# --- Metric catalogue (Doc 15 §11) ---------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class MetricSpec:
    """One additive measure, addressable by key. Never a ratio — ratios are derived (§6.2)."""

    key: str
    label: str
    model: type
    column: str


def _metric(key: str, label: str, model: type, column: str) -> MetricSpec:
    return MetricSpec(key=key, label=label, model=model, column=column)


METRICS: dict[str, MetricSpec] = {
    spec.key: spec
    for spec in (
        # Messaging & delivery (§11.1)
        _metric("messages_accepted", "Messages accepted", AnalyticsMessageRollup, "accepted_count"),
        _metric("messages_sent", "Messages sent", AnalyticsMessageRollup, "sent_count"),
        _metric("messages_delivered", "Delivered", AnalyticsMessageRollup, "delivered_count"),
        _metric("messages_read", "Read", AnalyticsMessageRollup, "read_count"),
        _metric("messages_failed", "Failed", AnalyticsMessageRollup, "failed_count"),
        _metric("cost_micros", "Spend (micros)", AnalyticsMessageRollup, "cost_micros"),
        _metric(
            "delivery_latency_ms_sum", "Delivery latency Σ (ms)",
            AnalyticsMessageRollup, "delivery_latency_ms_sum",
        ),
        _metric(
            "delivery_latency_count", "Delivery latency n",
            AnalyticsMessageRollup, "delivery_latency_count",
        ),
        # Failures (§11.1 / FR-AN-07)
        _metric("failures", "Failures", AnalyticsFailureRollup, "failure_count"),
        # Conversations & agents (§11.2)
        _metric("conversations_opened", "Opened", AnalyticsConversationRollup, "opened_count"),
        _metric("conversations_resolved", "Resolved", AnalyticsConversationRollup, "resolved_count"),
        _metric(
            "inbound_messages", "Inbound messages",
            AnalyticsConversationRollup, "inbound_message_count",
        ),
        _metric(
            "outbound_messages", "Outbound messages",
            AnalyticsConversationRollup, "outbound_message_count",
        ),
        _metric("conversations_handled", "Handled", AnalyticsConversationRollup, "handled_count"),
        _metric(
            "first_response_seconds_sum", "First response Σ (s)",
            AnalyticsConversationRollup, "first_response_seconds_sum",
        ),
        _metric(
            "first_response_count", "First response n",
            AnalyticsConversationRollup, "first_response_count",
        ),
        _metric(
            "resolution_seconds_sum", "Resolution Σ (s)",
            AnalyticsConversationRollup, "resolution_seconds_sum",
        ),
        _metric(
            "resolution_count", "Resolution n",
            AnalyticsConversationRollup, "resolution_count",
        ),
        # Tasks (§11.3)
        _metric("tasks_created", "Tasks created", AnalyticsTaskRollup, "created_count"),
        _metric("tasks_completed", "Tasks completed", AnalyticsTaskRollup, "completed_count"),
        _metric(
            "tasks_completed_on_time", "Completed on time",
            AnalyticsTaskRollup, "completed_on_time_count",
        ),
        _metric("tasks_skipped", "Tasks skipped", AnalyticsTaskRollup, "skipped_count"),
        _metric("tasks_cancelled", "Tasks cancelled", AnalyticsTaskRollup, "cancelled_count"),
        _metric("tasks_reopened", "Tasks reopened", AnalyticsTaskRollup, "reopened_count"),
        _metric(
            "tasks_overdue_entered", "Became overdue",
            AnalyticsTaskRollup, "overdue_entered_count",
        ),
        _metric(
            "time_to_complete_seconds_sum", "Time to complete Σ (s)",
            AnalyticsTaskRollup, "time_to_complete_seconds_sum",
        ),
        _metric(
            "time_to_complete_count", "Time to complete n",
            AnalyticsTaskRollup, "time_to_complete_count",
        ),
        # Customers (§11.4)
        _metric("contacts_created", "New customers", AnalyticsContactRollup, "created_count"),
        _metric("contacts_opted_in", "Opted in", AnalyticsContactRollup, "opted_in_count"),
        _metric("contacts_opted_out", "Opted out", AnalyticsContactRollup, "opted_out_count"),
        _metric("contacts_reactivated", "Reactivated", AnalyticsContactRollup, "reactivated_count"),
        # Doc 15 §25 Q3, resolved: the public metric is `active_customer_hours`. The rollup
        # de-duplicates contacts per bucket only, so summing buckets counts a customer once per
        # active hour. `active_customers` is deliberately **not** exposed — it would read as a
        # unique-customer count the stored measure cannot support.
        _metric("active_customer_hours", "Active customer-hours", AnalyticsContactRollup, "active_count"),
        # Campaigns (§11.5)
        _metric("campaign_targeted", "Targeted", AnalyticsCampaignRollup, "targeted_count"),
        _metric("campaign_sent", "Sent", AnalyticsCampaignRollup, "sent_count"),
        _metric("campaign_delivered", "Delivered", AnalyticsCampaignRollup, "delivered_count"),
        _metric("campaign_read", "Read", AnalyticsCampaignRollup, "read_count"),
        _metric("campaign_failed", "Failed", AnalyticsCampaignRollup, "failed_count"),
        _metric("campaign_skipped", "Skipped", AnalyticsCampaignRollup, "skipped_count"),
        _metric("campaign_clicks", "Clicks", AnalyticsCampaignRollup, "click_count"),
        _metric("campaign_cost_micros", "Campaign spend (micros)", AnalyticsCampaignRollup, "cost_micros"),
    )
}


def _ratio(numerator: int, denominator: int) -> float | None:
    """A rate, or ``None`` when there is nothing to divide — never a misleading zero."""
    return None if denominator <= 0 else round(numerator / denominator, 6)


def _mean(total: int, count: int) -> float | None:
    return None if count <= 0 else round(total / count, 3)


def derive_kpis(totals: dict[str, int]) -> dict[str, float | None]:
    """Every ratio and average of Doc 15 §11, computed from summed components (§6.2).

    Deriving here — rather than storing — is what makes an arbitrary range correct: the mean of
    hourly means is not the daily mean.
    """
    get = lambda key: int(totals.get(key, 0))  # noqa: E731 - local alias keeps the table readable
    return {
        # §11.1 messaging
        "delivery_rate": _ratio(get("messages_delivered"), get("messages_sent")),
        # Read rate divides by *delivered*: a message that never arrived cannot be read.
        "read_rate": _ratio(get("messages_read"), get("messages_delivered")),
        "failure_rate": _ratio(get("messages_failed"), get("messages_sent")),
        "avg_delivery_latency_ms": _mean(
            get("delivery_latency_ms_sum"), get("delivery_latency_count")
        ),
        # §11.2 conversations
        "resolution_rate": _ratio(get("conversations_resolved"), get("conversations_opened")),
        "avg_first_response_seconds": _mean(
            get("first_response_seconds_sum"), get("first_response_count")
        ),
        "avg_resolution_seconds": _mean(get("resolution_seconds_sum"), get("resolution_count")),
        # §11.3 tasks
        "task_completion_rate": _ratio(get("tasks_completed"), get("tasks_created")),
        "task_on_time_rate": _ratio(get("tasks_completed_on_time"), get("tasks_completed")),
        "avg_time_to_complete_seconds": _mean(
            get("time_to_complete_seconds_sum"), get("time_to_complete_count")
        ),
        # §11.4 customers
        "net_opt_in_change": float(get("contacts_opted_in") - get("contacts_opted_out")),
        "opt_out_rate": _ratio(get("contacts_opted_out"), get("contacts_created")),
        # §11.5 campaigns
        "campaign_delivery_rate": _ratio(get("campaign_delivered"), get("campaign_sent")),
        "campaign_click_through_rate": _ratio(get("campaign_clicks"), get("campaign_delivered")),
        "cost_per_delivered_micros": _mean(get("cost_micros"), get("messages_delivered")),
    }


# --- Range & grain planning ----------------------------------------------------------------------
@dataclass(slots=True)
class RangeSpec:
    """A resolved, validated query window (Doc 15 §14)."""

    start: datetime          # naive UTC, inclusive
    end: datetime            # naive UTC, exclusive
    granularity: str
    timezone: ZoneInfo
    compare: str | None = None

    @property
    def timezone_name(self) -> str:
        return str(self.timezone)


def resolve_preset(preset: str, tz: ZoneInfo, now: datetime) -> tuple[datetime, datetime]:
    """Turn a preset into a half-open UTC window, anchored on local calendar boundaries."""
    local_now = now.replace(tzinfo=UTC).astimezone(tz)
    local_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    if preset == "today":
        start_local, end_local = local_today, local_today + timedelta(days=1)
    elif preset == "yesterday":
        start_local, end_local = local_today - timedelta(days=1), local_today
    elif preset == "last_7d":
        start_local, end_local = local_today - timedelta(days=7), local_today + timedelta(days=1)
    elif preset == "last_30d":
        start_local, end_local = local_today - timedelta(days=30), local_today + timedelta(days=1)
    elif preset == "this_month":
        start_local = local_today.replace(day=1)
        end_local = local_today + timedelta(days=1)
    elif preset == "last_month":
        first_this = local_today.replace(day=1)
        start_local = (first_this - timedelta(days=1)).replace(day=1)
        end_local = first_this
    elif preset == "this_quarter":
        quarter_first_month = 3 * ((local_today.month - 1) // 3) + 1
        start_local = local_today.replace(month=quarter_first_month, day=1)
        end_local = local_today + timedelta(days=1)
    else:
        raise BadRequestError(f"preset must be one of {sorted(PRESETS)}")

    return _to_naive_utc(start_local), _to_naive_utc(end_local)


def _to_naive_utc(moment: datetime) -> datetime:
    return moment.astimezone(_UTC).replace(tzinfo=None)


def _normalise(moment: datetime | None) -> datetime | None:
    """Accept an aware or naive datetime, store naive-UTC (Doc 03 §1.3).

    Clients legitimately send ISO instants with an offset (``...Z``, ``+05:30``); everything below
    this boundary compares naive UTC, so the conversion happens once, here.
    """
    if moment is None or moment.tzinfo is None:
        return moment
    return _to_naive_utc(moment)


def resolve_range(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    preset: str | None = None,
    granularity: str = GRANULARITY_DAY,
    timezone: str | None = None,
    compare: str | None = None,
    now: datetime | None = None,
) -> RangeSpec:
    """Validate and normalise a query window (Doc 15 §14.2/§14.3)."""
    if granularity not in GRANULARITIES:
        raise BadRequestError(f"granularity must be one of {sorted(GRANULARITIES)}")
    if compare is not None and compare not in COMPARISONS:
        raise BadRequestError(f"compare must be one of {sorted(COMPARISONS)}")

    tz = resolve_timezone(timezone)
    moment = now or utcnow()
    start, end = _normalise(start), _normalise(end)

    if preset:
        start, end = resolve_preset(preset, tz, moment)
    if start is None or end is None:
        raise BadRequestError("Provide either 'preset' or both 'from' and 'to'.")
    if start >= end:
        raise BadRequestError("'from' must be earlier than 'to'.")

    # A range extending past now is truncated rather than rejected (§14.3) — asking for tomorrow
    # is a reasonable thing for a dashboard to do.
    end = min(end, floor_hour(moment) + timedelta(hours=1))
    if start >= end:
        raise BadRequestError("The requested range has not started yet.")

    span_days = (end - start).total_seconds() / 86400
    limit = MAX_SPAN_DAYS[granularity]
    if span_days > limit:
        raise BadRequestError(
            f"A '{granularity}' range may span at most {limit} days; {span_days:.0f} requested."
        )

    return RangeSpec(start=start, end=end, granularity=granularity, timezone=tz, compare=compare)


def plan_grain(spec: RangeSpec, now: datetime | None = None) -> str:
    """Pick the stored grain that answers this range (Doc 15 §21.4).

    Hourly rows fold exactly into any timezone, so they are preferred whenever they still exist.
    Past the 90-day hourly retention only daily rows remain; those are **UTC-midnight aligned**, so
    for a non-UTC timezone a "day" then means a UTC day. That approximation is inherent to
    consolidation and is surfaced to the caller as ``grain`` on the response.
    """
    if spec.granularity == GRANULARITY_HOUR:
        return GRAIN_HOUR
    hourly_cutoff = floor_hour(now or utcnow()) - timedelta(days=HOURLY_RETENTION_DAYS)
    return GRAIN_HOUR if spec.start >= hourly_cutoff else GRAIN_DAY


# --- Bucket folding (Doc 15 §10) ------------------------------------------------------------------
def period_key(bucket_start: datetime, granularity: str, tz: ZoneInfo) -> datetime:
    """The **local** period a UTC bucket belongs to, as a local-naive datetime.

    This is the one place UTC storage becomes local presentation; everything downstream works in
    local period keys.
    """
    local = bucket_start.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
    if granularity == GRANULARITY_HOUR:
        return floor_hour(local)
    if granularity == GRANULARITY_DAY:
        return floor_day(local)
    if granularity == GRANULARITY_WEEK:
        day = floor_day(local)
        return day - timedelta(days=day.weekday())  # ISO weeks start Monday
    return floor_day(local).replace(day=1)


def dense_periods(spec: RangeSpec) -> list[datetime]:
    """Every local period in the range, with no gaps (Doc 15 §10).

    Charts must never have to guess whether a missing bucket means zero or missing data, so the
    series is generated from the calendar and then filled — not from whatever rows exist.
    """
    tz = spec.timezone
    end_local = spec.end.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)

    cursor = period_key(spec.start, spec.granularity, tz)
    periods: list[datetime] = []
    # The span guards of §14.3 already bound this; the counter is a belt-and-braces stop so a
    # malformed granularity can never spin.
    while cursor < end_local and len(periods) < 100_000:
        periods.append(cursor)
        cursor = _advance(cursor, spec.granularity)
    return periods


def _advance(period: datetime, granularity: str) -> datetime:
    if granularity == GRANULARITY_HOUR:
        return period + timedelta(hours=1)
    if granularity == GRANULARITY_DAY:
        return period + timedelta(days=1)
    if granularity == GRANULARITY_WEEK:
        return period + timedelta(weeks=1)
    year, month = divmod(period.month, 12)
    return period.replace(year=period.year + year, month=month + 1, day=1)


def format_period(period: datetime, granularity: str) -> str:
    """The ``t`` label of a series point (Doc 15 §10)."""
    if granularity == GRANULARITY_HOUR:
        return period.strftime("%Y-%m-%dT%H:00")
    return period.strftime("%Y-%m-%d")


# --- Views ----------------------------------------------------------------------------------------
@dataclass(slots=True)
class SeriesPointView:
    t: str
    v: float


@dataclass(slots=True)
class SeriesView:
    key: str
    label: str
    points: list[SeriesPointView]


@dataclass(slots=True)
class SeriesResultView:
    """The §10 envelope, plus the grain actually used so staleness is never implicit."""

    granularity: str
    grain: str
    start: datetime
    end: datetime
    timezone: str
    series: list[SeriesView]
    totals: dict[str, float | None]
    comparison: list[SeriesView] = field(default_factory=list)
    comparison_totals: dict[str, float | None] = field(default_factory=dict)


@dataclass(slots=True)
class SummaryView:
    """Scalar KPI cards for a range (Doc 15 §16, family 1)."""

    start: datetime
    end: datetime
    timezone: str
    grain: str
    totals: dict[str, int]
    kpis: dict[str, float | None]
    comparison_totals: dict[str, int] = field(default_factory=dict)
    comparison_kpis: dict[str, float | None] = field(default_factory=dict)
    data_as_of: datetime | None = None


@dataclass(slots=True)
class BreakdownRowView:
    """One dimension value with its summed measures and derived KPIs (Doc 15 §16, family 3)."""

    key: str
    label: str
    totals: dict[str, int]
    kpis: dict[str, float | None]


@dataclass(slots=True)
class BreakdownResultView:
    dimension: str
    grain: str
    start: datetime
    end: datetime
    timezone: str
    rows: list[BreakdownRowView]
    totals: dict[str, int]


@dataclass(slots=True)
class FreshnessView:
    """How stale each rollup kind is (Doc 15 §17 ``/analytics/freshness``, §22)."""

    kind: str
    watermark_at: datetime | None
    last_run_at: datetime | None
    last_status: str | None
    lag_seconds: int | None


class AnalyticsQueryService:
    """Serves KPI summaries and time series from the rollups (Doc 15 §10–§14)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AnalyticsRepository(session)

    # --- Public reads ------------------------------------------------------------------------
    async def summary(
        self,
        *,
        organization_id: int,
        spec: RangeSpec,
        metrics: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> SummaryView:
        """Range totals plus every derived KPI (Doc 15 §11)."""
        keys = self._validate_metrics(metrics)
        grain = plan_grain(spec, now)
        totals = await self._totals(organization_id, spec.start, spec.end, grain, keys)

        comparison_totals: dict[str, int] = {}
        comparison_kpis: dict[str, float | None] = {}
        if spec.compare:
            previous = comparison_window(spec)
            comparison_totals = await self._totals(
                organization_id, previous.start, previous.end, plan_grain(previous, now), keys
            )
            comparison_kpis = derive_kpis(comparison_totals)

        return SummaryView(
            start=spec.start,
            end=spec.end,
            timezone=spec.timezone_name,
            grain=grain,
            totals=totals,
            kpis=derive_kpis(totals),
            comparison_totals=comparison_totals,
            comparison_kpis=comparison_kpis,
            data_as_of=await self._data_as_of(organization_id),
        )

    async def series(
        self,
        *,
        organization_id: int,
        spec: RangeSpec,
        metrics: Sequence[str],
        now: datetime | None = None,
    ) -> SeriesResultView:
        """A dense, timezone-folded time series per metric (Doc 15 §10)."""
        keys = self._validate_metrics(metrics, required=True)
        grain = plan_grain(spec, now)
        series, totals = await self._series_for(organization_id, spec, grain, keys)

        comparison: list[SeriesView] = []
        comparison_totals: dict[str, float | None] = {}
        if spec.compare:
            previous = comparison_window(spec)
            comparison, previous_totals = await self._series_for(
                organization_id, previous, plan_grain(previous, now), keys
            )
            comparison_totals = {**previous_totals, **derive_kpis(
                {k: int(v or 0) for k, v in previous_totals.items()}
            )}

        return SeriesResultView(
            granularity=spec.granularity,
            grain=grain,
            start=spec.start,
            end=spec.end,
            timezone=spec.timezone_name,
            series=series,
            totals={**totals, **derive_kpis({k: int(v or 0) for k, v in totals.items()})},
            comparison=comparison,
            comparison_totals=comparison_totals,
        )

    async def breakdown(
        self,
        *,
        organization_id: int,
        spec: RangeSpec,
        dimension: str,
        metrics: Sequence[str] | None = None,
        limit: int = 50,
        sort_by: str | None = None,
        now: datetime | None = None,
    ) -> BreakdownResultView:
        """Group a range by one dimension — the entry point to drill-down (Doc 15 §16, family 3).

        Reads the same rollup rows as :meth:`summary`, grouped by a dimension column instead of
        folded into periods. No aggregation logic is duplicated: measures are summed and every
        ratio goes through :func:`derive_kpis`, exactly as the scalar path does.

        High-cardinality dimension values are internal ids; display names are resolved from the
        operational tables at read time (Doc 15 AN-CD2 — the platform's own tables *are* its
        conformed dimensions). That is a label lookup, never an aggregation.
        """
        model = DIMENSIONS.get(dimension)
        if model is None:
            raise BadRequestError(f"dimension must be one of {sorted(DIMENSIONS)}")
        if limit < 1 or limit > MAX_BREAKDOWN_ROWS:
            raise BadRequestError(f"limit must be between 1 and {MAX_BREAKDOWN_ROWS}.")

        keys = [key for key in self._validate_metrics(metrics) if METRICS[key].model is model]
        if not keys:
            raise BadRequestError(f"No metrics of dimension {dimension!r} were requested.")

        grain = plan_grain(spec, now)
        rows = await self._repo.fetch_range(model, organization_id, grain, spec.start, spec.end)

        grouped: dict[object, dict[str, int]] = {}
        for row in rows:
            bucket = grouped.setdefault(getattr(row, dimension), dict.fromkeys(keys, 0))
            for key in keys:
                bucket[key] += int(getattr(row, METRICS[key].column) or 0)

        sort_key = sort_by if sort_by in keys else keys[0]
        ordered = sorted(grouped.items(), key=lambda item: item[1][sort_key], reverse=True)[:limit]
        labels = await self._resolve_labels(dimension, [value for value, _ in ordered])

        totals = dict.fromkeys(keys, 0)
        for _, measures in grouped.items():
            for key in keys:
                totals[key] += measures[key]

        return BreakdownResultView(
            dimension=dimension,
            grain=grain,
            start=spec.start,
            end=spec.end,
            timezone=spec.timezone_name,
            rows=[
                BreakdownRowView(
                    key="" if value is None else str(value),
                    label=labels.get(value, UNASSIGNED_LABEL if value is None else str(value)),
                    totals=measures,
                    kpis=derive_kpis(measures),
                )
                for value, measures in ordered
            ],
            totals=totals,
        )

    async def _resolve_labels(self, dimension: str, values: Sequence[object]) -> dict[object, str]:
        """Display names for a dimension's values (Doc 15 AN-CD2 — read-time resolution).

        Only the entity dimensions need a lookup; ``error_code``, ``task_type``, ``direction`` and
        ``message_type`` are already human-readable.
        """
        ids = [value for value in values if isinstance(value, int)]
        if not ids:
            return {}
        if dimension in ("assigned_user_id", "assigned_agent_id"):
            stmt = select(User.id, User.full_name).where(User.id.in_(ids))
        elif dimension == "campaign_id":
            stmt = select(Campaign.id, Campaign.name).where(Campaign.id.in_(ids))
        else:
            return {}
        return {row[0]: row[1] for row in (await self._session.execute(stmt)).all()}

    async def freshness(self, *, organization_id: int, now: datetime | None = None) -> list[FreshnessView]:
        """Rollup watermarks — the honest "data as of" of Doc 15 §22."""
        moment = now or utcnow()
        return [
            FreshnessView(
                kind=run.kind,
                watermark_at=run.watermark_at,
                last_run_at=run.last_run_at,
                last_status=run.last_status,
                lag_seconds=(
                    int((moment - run.watermark_at).total_seconds())
                    if run.watermark_at is not None
                    else None
                ),
            )
            for run in await self._repo.runs_for(organization_id)
        ]

    # --- Internals ---------------------------------------------------------------------------
    async def _totals(
        self,
        organization_id: int,
        start: datetime,
        end: datetime,
        grain: str,
        keys: Sequence[str],
    ) -> dict[str, int]:
        """Sum each metric over the window. Additive measures make this a plain sum (§6.2)."""
        totals = dict.fromkeys(keys, 0)
        for model, model_keys in self._by_model(keys).items():
            rows = await self._repo.fetch_range(model, organization_id, grain, start, end)
            for row in rows:
                for key in model_keys:
                    totals[key] += int(getattr(row, METRICS[key].column) or 0)
        return totals

    async def _series_for(
        self,
        organization_id: int,
        spec: RangeSpec,
        grain: str,
        keys: Sequence[str],
    ) -> tuple[list[SeriesView], dict[str, float | None]]:
        periods = dense_periods(spec)
        buckets: dict[str, dict[datetime, int]] = {key: dict.fromkeys(periods, 0) for key in keys}
        totals: dict[str, float | None] = dict.fromkeys(keys, 0)

        for model, model_keys in self._by_model(keys).items():
            rows = await self._repo.fetch_range(model, organization_id, grain, spec.start, spec.end)
            for row in rows:
                period = period_key(row.bucket_start, spec.granularity, spec.timezone)
                for key in model_keys:
                    value = int(getattr(row, METRICS[key].column) or 0)
                    if period in buckets[key]:
                        buckets[key][period] += value
                    totals[key] = int(totals[key] or 0) + value

        series = [
            SeriesView(
                key=key,
                label=METRICS[key].label,
                points=[
                    SeriesPointView(
                        t=format_period(period, spec.granularity), v=buckets[key][period]
                    )
                    for period in periods
                ],
            )
            for key in keys
        ]
        return series, totals

    async def _data_as_of(self, organization_id: int) -> datetime | None:
        """The oldest watermark across kinds — a summary is only as fresh as its stalest input."""
        runs = await self._repo.runs_for(organization_id)
        watermarks = [run.watermark_at for run in runs if run.watermark_at is not None]
        return min(watermarks) if watermarks else None

    @staticmethod
    def _validate_metrics(
        metrics: Sequence[str] | None, *, required: bool = False
    ) -> tuple[str, ...]:
        if not metrics:
            if required:
                raise BadRequestError("At least one metric is required.")
            return tuple(METRICS)
        unknown = [key for key in metrics if key not in METRICS]
        if unknown:
            raise BadRequestError(f"Unknown metric(s): {', '.join(sorted(unknown))}.")
        return tuple(dict.fromkeys(metrics))  # de-duplicate, preserve order

    @staticmethod
    def _by_model(keys: Iterable[str]) -> dict[type, list[str]]:
        """Group metric keys by their fact table, so each table is read once."""
        grouped: dict[type, list[str]] = {}
        for key in keys:
            grouped.setdefault(METRICS[key].model, []).append(key)
        return grouped


def comparison_window(spec: RangeSpec) -> RangeSpec:
    """The window ``compare`` asks for (Doc 15 §14.2).

    ``previous_period`` shifts back by the range's own length, so a 7-day range compares against
    the 7 days before it. ``previous_year`` shifts back 365 days, keeping the same span.
    """
    shift = (
        timedelta(days=365)
        if spec.compare == COMPARE_PREVIOUS_YEAR
        else spec.end - spec.start
    )
    return RangeSpec(
        start=spec.start - shift,
        end=spec.end - shift,
        granularity=spec.granularity,
        timezone=spec.timezone,
        compare=None,
    )
