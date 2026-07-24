"""Analytics schemas (Doc 15 §10, §14, §18) — request/response shapes for the read API.

Two conventions from the rest of the platform are load-bearing here:

* **Enums render as OpenAPI enums** via ``Literal``, kept in lockstep with the service constants
  (a test asserts equality), exactly as ``schemas/task.py`` does.
* **Every query parameter is declared.** The Phase 7 hardening milestone found the inbox reading
  filters off the raw request, which made them invisible to the contract; analytics has a large
  filter surface (§14) and declares all of it (Doc 15 §18).

Incoming datetimes are normalised to naive-UTC — the stored form (Doc 03 §1.3).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.services.analytics_query_service import (
    BreakdownResultView,
    BreakdownRowView,
    FreshnessView,
    SeriesResultView,
    SummaryView,
)

# --- Enumerations (mirror the service constants, Doc 15 §14.2) -----------------------------------
GranularityLiteral = Literal["hour", "day", "week", "month"]
PresetLiteral = Literal[
    "today", "yesterday", "last_7d", "last_30d", "this_month", "last_month", "this_quarter"
]
CompareLiteral = Literal["previous_period", "previous_year"]
ExportFormatLiteral = Literal["csv", "xlsx", "json"]
#: The report entities of Doc 15 §19 — new ``exports.entity`` values, not a new export system.
ReportLiteral = Literal[
    "messages", "failures", "campaigns", "conversations", "tasks", "customers", "costs"
]

MAX_METRICS = 24


def _to_naive_utc(value: datetime) -> datetime:
    """Normalise an (optionally tz-aware) datetime to naive-UTC for storage/comparison."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


NaiveUTC = Annotated[datetime, AfterValidator(_to_naive_utc)]


# --- Requests -------------------------------------------------------------------------------------
class AnalyticsRangeFilters(BaseModel):
    """The shared range/granularity/timezone filter set (Doc 15 §14.2).

    Endpoints declare these as query parameters; this model is the single definition of their
    types, defaults and mutual constraints.
    """

    from_: NaiveUTC | None = Field(default=None, alias="from")
    to: NaiveUTC | None = None
    preset: PresetLiteral | None = None
    granularity: GranularityLiteral = "day"
    timezone: str | None = Field(
        default=None, max_length=64, description="IANA name; defaults to the caller's, then the org's."
    )
    compare: CompareLiteral | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _range_is_addressable(self) -> AnalyticsRangeFilters:
        if self.preset is None and (self.from_ is None or self.to is None):
            raise ValueError("provide either 'preset' or both 'from' and 'to'")
        if self.from_ is not None and self.to is not None and self.from_ >= self.to:
            raise ValueError("'from' must be earlier than 'to'")
        return self


class AnalyticsSeriesFilters(AnalyticsRangeFilters):
    """Range filters plus the metrics to chart (Doc 15 §10)."""

    metrics: list[str] = Field(min_length=1, max_length=MAX_METRICS)


class ReportExportRequest(BaseModel):
    """``POST /analytics/reports/export`` — always async, always 202 (Doc 15 §19).

    The resolved range travels into ``exports.filters_json`` so an artifact is reproducible and
    self-describing. The response envelope is the frozen ``ExportProgressResponse``; a report is an
    export, not a second export system.
    """

    report: ReportLiteral
    format: ExportFormatLiteral = "csv"
    filters: AnalyticsRangeFilters


# --- Response building blocks (Doc 15 §10) ---------------------------------------------------------
class SeriesPoint(BaseModel):
    """One dense bucket. ``t`` is the **local** period label; the range bounds stay ISO-UTC."""

    t: str
    v: float


class Series(BaseModel):
    key: str
    label: str
    points: list[SeriesPoint]


class AnalyticsSeriesResponse(BaseModel):
    """The §10 envelope — one shape every chart in the frontend can render."""

    granularity: GranularityLiteral
    #: The stored grain actually read (``hour``/``day``). Past the hourly retention horizon a
    #: non-UTC "day" is a UTC day; surfacing the grain keeps that visible rather than implicit.
    grain: str
    from_: datetime = Field(serialization_alias="from")
    to: datetime
    timezone: str
    series: list[Series]
    #: Summed measures **and** the ratios derived from them (never summed per-bucket ratios).
    totals: dict[str, float | None]
    comparison: list[Series] = Field(default_factory=list)
    comparison_totals: dict[str, float | None] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @classmethod
    def of(cls, view: SeriesResultView) -> AnalyticsSeriesResponse:
        return cls(
            granularity=view.granularity,
            grain=view.grain,
            from_=view.start,
            to=view.end,
            timezone=view.timezone,
            series=[
                Series(
                    key=s.key,
                    label=s.label,
                    points=[SeriesPoint(t=p.t, v=p.v) for p in s.points],
                )
                for s in view.series
            ],
            totals=view.totals,
            comparison=[
                Series(
                    key=s.key,
                    label=s.label,
                    points=[SeriesPoint(t=p.t, v=p.v) for p in s.points],
                )
                for s in view.comparison
            ],
            comparison_totals=view.comparison_totals,
        )


class AnalyticsKpiResponse(BaseModel):
    """The derived ratios and averages of Doc 15 §11.

    Every field is nullable: a rate over an empty denominator is *unknown*, not zero, and a
    dashboard that shows 0% for "no messages sent" is lying.
    """

    delivery_rate: float | None = None
    read_rate: float | None = None
    failure_rate: float | None = None
    avg_delivery_latency_ms: float | None = None
    resolution_rate: float | None = None
    avg_first_response_seconds: float | None = None
    avg_resolution_seconds: float | None = None
    task_completion_rate: float | None = None
    task_on_time_rate: float | None = None
    avg_time_to_complete_seconds: float | None = None
    net_opt_in_change: float | None = None
    opt_out_rate: float | None = None
    campaign_delivery_rate: float | None = None
    campaign_click_through_rate: float | None = None
    cost_per_delivered_micros: float | None = None

    @classmethod
    def of(cls, kpis: dict[str, float | None]) -> AnalyticsKpiResponse:
        return cls(**{key: kpis.get(key) for key in cls.model_fields})


class AnalyticsSummaryResponse(BaseModel):
    """Scalar KPI cards for a range (Doc 15 §16, family 1)."""

    from_: datetime = Field(serialization_alias="from")
    to: datetime
    timezone: str
    grain: str
    totals: dict[str, int]
    kpis: AnalyticsKpiResponse
    #: How fresh the answer is — the stalest contributing watermark (Doc 15 §22).
    data_as_of: datetime | None = None

    model_config = {"populate_by_name": True}

    @classmethod
    def of(cls, view: SummaryView) -> AnalyticsSummaryResponse:
        return cls(
            from_=view.start,
            to=view.end,
            timezone=view.timezone,
            grain=view.grain,
            totals=view.totals,
            kpis=AnalyticsKpiResponse.of(view.kpis),
            data_as_of=view.data_as_of,
        )


class AnalyticsComparisonResponse(BaseModel):
    """A range beside its comparison window, for delta display (Doc 15 §14.2)."""

    current: AnalyticsSummaryResponse
    previous_totals: dict[str, int] = Field(default_factory=dict)
    previous_kpis: AnalyticsKpiResponse = Field(default_factory=AnalyticsKpiResponse)

    @classmethod
    def of(cls, view: SummaryView) -> AnalyticsComparisonResponse:
        return cls(
            current=AnalyticsSummaryResponse.of(view),
            previous_totals=view.comparison_totals,
            previous_kpis=AnalyticsKpiResponse.of(view.comparison_kpis),
        )


class BreakdownRow(BaseModel):
    """One dimension value with its summed measures and derived KPIs (Doc 15 §16, family 3)."""

    key: str
    label: str
    totals: dict[str, int]
    kpis: AnalyticsKpiResponse

    @classmethod
    def of(cls, view: BreakdownRowView) -> BreakdownRow:
        return cls(
            key=view.key,
            label=view.label,
            totals=view.totals,
            kpis=AnalyticsKpiResponse.of(view.kpis),
        )


class AnalyticsBreakdownResponse(BaseModel):
    """A grouped table — the entry point to drill-down (Doc 15 §16).

    Rows are a ranked leaderboard, not a dump: drilling into one takes the caller to the owning
    module's list endpoint, which analytics never re-implements.
    """

    dimension: str
    grain: str
    from_: datetime = Field(serialization_alias="from")
    to: datetime
    timezone: str
    data: list[BreakdownRow]
    totals: dict[str, int]

    model_config = {"populate_by_name": True}

    @classmethod
    def of(cls, view: BreakdownResultView) -> AnalyticsBreakdownResponse:
        return cls(
            dimension=view.dimension,
            grain=view.grain,
            from_=view.start,
            to=view.end,
            timezone=view.timezone,
            data=[BreakdownRow.of(row) for row in view.rows],
            totals=view.totals,
        )


class AnalyticsFreshnessRow(BaseModel):
    kind: str
    watermark_at: datetime | None
    last_run_at: datetime | None
    last_status: str | None
    lag_seconds: int | None

    @classmethod
    def of(cls, view: FreshnessView) -> AnalyticsFreshnessRow:
        return cls(
            kind=view.kind,
            watermark_at=view.watermark_at,
            last_run_at=view.last_run_at,
            last_status=view.last_status,
            lag_seconds=view.lag_seconds,
        )


class AnalyticsFreshnessResponse(BaseModel):
    """``GET /analytics/freshness`` — so a dashboard can state how stale it is (Doc 15 §17)."""

    data: list[AnalyticsFreshnessRow]

    @classmethod
    def of(cls, views: list[FreshnessView]) -> AnalyticsFreshnessResponse:
        return cls(data=[AnalyticsFreshnessRow.of(view) for view in views])


class MetricDescriptor(BaseModel):
    """One addressable metric — lets the frontend build a chart picker from the contract."""

    key: str
    label: str


class AnalyticsMetricsResponse(BaseModel):
    data: list[MetricDescriptor]
