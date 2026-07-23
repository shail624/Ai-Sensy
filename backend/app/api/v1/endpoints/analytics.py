"""Analytics endpoints (Doc 15 §16, §17) — the read API over the rollups.

Three families, deliberately distinguished (Doc 15 §16):

1. ``/analytics/summary`` — scalar KPI cards for a range.
2. ``/analytics/series`` — the §10 time-series envelope; chart data.
3. ``/analytics/{failures,campaigns,agents,costs}`` — grouped tables, the entry point to
   drill-down.

Every read goes through :class:`~app.services.analytics_query_service.AnalyticsQueryService`, which
touches **only** the rollup tables. No endpoint here aggregates, and none re-implements an
operational list read: drilling into a row takes the caller to the owning module's endpoint
(Doc 15 AN-CD5). Live "right now" counters likewise stay on their own modules — ``/tasks/stats``
already serves them (AN-CD4).

Every query parameter is **declared**, so the contract can express the full filter surface — the
lesson of the Phase 7 inbox hardening (Doc 15 §18).
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.core.config import settings
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsBreakdownResponse,
    AnalyticsComparisonResponse,
    AnalyticsFreshnessResponse,
    AnalyticsKpiResponse,
    AnalyticsMetricsResponse,
    AnalyticsSeriesResponse,
    AnalyticsSummaryResponse,
    CompareLiteral,
    GranularityLiteral,
    MetricDescriptor,
    PresetLiteral,
    ReportExportRequest,
)
from app.schemas.export_job import ExportProgressResponse
from app.schemas.import_job import JobAcceptedResponse, JobEnvelope
from app.services.analytics_query_service import (
    DIMENSIONS,
    METRICS,
    AnalyticsQueryService,
    RangeSpec,
    resolve_range,
)
from app.services.export_service import ExportService

router = APIRouter()

AnalyticsReader = Annotated[User, Depends(require_permissions("analytics:read"))]
AnalyticsExporter = Annotated[User, Depends(require_permissions("analytics:export"))]
#: Cost and the executive dashboard are commercially sensitive — a support agent or analyst has no
#: operational need for spend (Doc 15 §15).
AnalyticsExecutive = Annotated[User, Depends(require_permissions("analytics:executive"))]


def _spec(
    actor: User,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    preset: str | None,
    granularity: str,
    timezone: str | None,
    compare: str | None = None,
) -> RangeSpec:
    """Resolve the window, applying the §14.1 timezone precedence: explicit → user → UTC."""
    return resolve_range(
        start=date_from,
        end=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone or actor.timezone,
        compare=compare,
    )


# --- Family 1: scalar summaries (Doc 15 §16) -----------------------------------------------------
@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Headline KPIs for a range",
)
async def analytics_summary(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    metrics: Annotated[list[str] | None, Query()] = None,
) -> AnalyticsSummaryResponse:
    """Range totals plus every derived KPI (Doc 15 §11), with the freshness of the answer."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone,
    )
    view = await AnalyticsQueryService(session).summary(
        organization_id=actor.organization_id, spec=spec, metrics=metrics
    )
    return AnalyticsSummaryResponse.of(view)


@router.get(
    "/analytics/kpis", response_model=AnalyticsKpiResponse, summary="Derived KPIs only"
)
async def analytics_kpis(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
) -> AnalyticsKpiResponse:
    """The §11 ratios and averages without the raw counters — the KPI-card payload."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone,
    )
    view = await AnalyticsQueryService(session).summary(
        organization_id=actor.organization_id, spec=spec
    )
    return AnalyticsKpiResponse.of(view.kpis)


@router.get(
    "/analytics/comparison",
    response_model=AnalyticsComparisonResponse,
    summary="A range beside its comparison window",
)
async def analytics_comparison(
    session: SessionDep,
    actor: AnalyticsReader,
    compare: Annotated[CompareLiteral, Query()] = "previous_period",
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    metrics: Annotated[list[str] | None, Query()] = None,
) -> AnalyticsComparisonResponse:
    """Current vs previous period or previous year, for delta display (Doc 15 §14.2)."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone, compare=compare,
    )
    view = await AnalyticsQueryService(session).summary(
        organization_id=actor.organization_id, spec=spec, metrics=metrics
    )
    return AnalyticsComparisonResponse.of(view)


# --- Family 2: time series (Doc 15 §10) ------------------------------------------------------------
@router.get(
    "/analytics/series",
    response_model=AnalyticsSeriesResponse,
    summary="Dense, timezone-folded time series",
)
async def analytics_series(
    session: SessionDep,
    actor: AnalyticsReader,
    metrics: Annotated[list[str], Query(min_length=1)],
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    compare: Annotated[CompareLiteral | None, Query()] = None,
) -> AnalyticsSeriesResponse:
    """One series per metric, dense across the range — no gaps for a chart to guess at."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone, compare=compare,
    )
    result = await AnalyticsQueryService(session).series(
        organization_id=actor.organization_id, spec=spec, metrics=metrics
    )
    return AnalyticsSeriesResponse.of(result)


@router.get(
    "/analytics/trends",
    response_model=AnalyticsSeriesResponse,
    summary="Trend series with its comparison window",
)
async def analytics_trends(
    session: SessionDep,
    actor: AnalyticsReader,
    metrics: Annotated[list[str], Query(min_length=1)],
    compare: Annotated[CompareLiteral, Query()] = "previous_period",
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
) -> AnalyticsSeriesResponse:
    """A series always paired with its comparison — the trend view of the same §10 envelope."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone, compare=compare,
    )
    result = await AnalyticsQueryService(session).series(
        organization_id=actor.organization_id, spec=spec, metrics=metrics
    )
    return AnalyticsSeriesResponse.of(result)


# --- Family 3: breakdowns (Doc 15 §16) -------------------------------------------------------------
async def _breakdown(
    session: SessionDep,
    actor: User,
    *,
    dimension: str,
    metrics: list[str] | None,
    spec: RangeSpec,
    limit: int,
    sort_by: str | None = None,
) -> AnalyticsBreakdownResponse:
    view = await AnalyticsQueryService(session).breakdown(
        organization_id=actor.organization_id,
        spec=spec,
        dimension=dimension,
        metrics=metrics,
        limit=limit,
        sort_by=sort_by,
    )
    return AnalyticsBreakdownResponse.of(view)


@router.get(
    "/analytics/breakdown",
    response_model=AnalyticsBreakdownResponse,
    summary="Group a range by any dimension",
)
async def analytics_breakdown(
    session: SessionDep,
    actor: AnalyticsReader,
    dimension: Annotated[str, Query()],
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    granularity: Annotated[GranularityLiteral, Query()] = "day",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    metrics: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    sort_by: Annotated[str | None, Query()] = None,
) -> AnalyticsBreakdownResponse:
    """The generic grouped table; the named endpoints below are presets over it."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity=granularity, timezone=timezone,
    )
    return await _breakdown(
        session, actor, dimension=dimension, metrics=metrics, spec=spec,
        limit=limit, sort_by=sort_by,
    )


@router.get(
    "/analytics/failures",
    response_model=AnalyticsBreakdownResponse,
    summary="Failures grouped by Meta error code",
)
async def analytics_failures(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """FR-AN-07 — the failure leaderboard; drill-down goes to the message list by error code."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity="day", timezone=timezone,
    )
    return await _breakdown(
        session, actor, dimension="error_code", metrics=["failures"], spec=spec, limit=limit
    )


@router.get(
    "/analytics/campaigns",
    response_model=AnalyticsBreakdownResponse,
    summary="Campaign performance table",
)
async def analytics_campaigns(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """FR-AN-02 — per-campaign funnel; campaign names resolve at read time (AN-CD2)."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity="day", timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="campaign_id",
        metrics=[
            "campaign_targeted", "campaign_sent", "campaign_delivered",
            "campaign_read", "campaign_failed", "campaign_skipped",
        ],
        spec=spec,
        limit=limit,
    )


@router.get(
    "/analytics/agents",
    response_model=AnalyticsBreakdownResponse,
    summary="Agent performance table",
)
async def analytics_agents(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """FR-AN-02/J6 — the agent is a *dimension* of the conversation rollup, not its own table."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity="day", timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="assigned_user_id",
        metrics=[
            "conversations_opened", "conversations_resolved",
            "outbound_messages", "conversations_handled",
        ],
        spec=spec,
        limit=limit,
    )


@router.get(
    "/analytics/costs",
    response_model=AnalyticsBreakdownResponse,
    summary="Spend breakdown (executive)",
)
async def analytics_costs(
    session: SessionDep,
    actor: AnalyticsExecutive,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """FR-AN-03 — spend by message type. Cost is copied from the ledger, never recomputed here."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity="day", timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="message_type",
        metrics=["cost_micros", "messages_delivered", "messages_sent"],
        spec=spec,
        limit=limit,
        sort_by="cost_micros",
    )


@router.get(
    "/analytics/executive",
    response_model=AnalyticsSummaryResponse,
    summary="Executive dashboard (executive)",
)
async def analytics_executive(
    session: SessionDep,
    actor: AnalyticsExecutive,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
) -> AnalyticsSummaryResponse:
    """Doc 15 §12 — a composition of existing metrics, including spend. No new measure."""
    spec = _spec(
        actor, date_from=date_from, date_to=date_to, preset=preset,
        granularity="day", timezone=timezone,
    )
    view = await AnalyticsQueryService(session).summary(
        organization_id=actor.organization_id, spec=spec
    )
    return AnalyticsSummaryResponse.of(view)


# --- Metadata & freshness --------------------------------------------------------------------------
@router.get(
    "/analytics/metrics",
    response_model=AnalyticsMetricsResponse,
    summary="The addressable metric catalogue",
)
async def analytics_metrics(actor: AnalyticsReader) -> AnalyticsMetricsResponse:
    """Lets a client build a metric picker from the contract rather than hard-coding keys."""
    return AnalyticsMetricsResponse(
        data=[MetricDescriptor(key=spec.key, label=spec.label) for spec in METRICS.values()]
    )


@router.get(
    "/analytics/dimensions",
    response_model=AnalyticsMetricsResponse,
    summary="The groupable dimensions",
)
async def analytics_dimensions(actor: AnalyticsReader) -> AnalyticsMetricsResponse:
    return AnalyticsMetricsResponse(
        data=[MetricDescriptor(key=name, label=name) for name in sorted(DIMENSIONS)]
    )


@router.get(
    "/analytics/freshness",
    response_model=AnalyticsFreshnessResponse,
    summary="Rollup watermarks — how stale the data is",
)
async def analytics_freshness(
    session: SessionDep, actor: AnalyticsReader
) -> AnalyticsFreshnessResponse:
    """A dashboard that cannot say how stale it is will eventually be trusted when it shouldn't."""
    rows = await AnalyticsQueryService(session).freshness(organization_id=actor.organization_id)
    return AnalyticsFreshnessResponse.of(rows)


# --- Report export (Doc 15 §19) ---------------------------------------------------------------------
@router.post(
    "/analytics/reports/export",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a report export (async)",
)
async def start_report_export(
    payload: ReportExportRequest, session: SessionDep, actor: AnalyticsExporter
) -> JobAcceptedResponse:
    """Always ``202`` — a large report is exactly the request that must not hold a worker.

    Reuses the frozen export system end to end: the ``exports`` row, the ``exports`` queue, the
    format writers and the signed-download flow. Only the ``entity`` and the row generator differ.
    """
    from app.analytics.tasks import run_report_export

    job = await ExportService(session).start_report(
        organization_id=actor.organization_id,
        actor=actor,
        report=payload.report,
        file_format=payload.format,
        filters=payload.filters.model_dump(mode="json", by_alias=True, exclude_none=True),
        dispatch=lambda export_id, task_id: run_report_export.apply_async(
            args=[export_id], task_id=task_id
        ),
    )
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job.public_id,
            type="export",
            status="queued",
            poll_url=f"{settings.api_v1_prefix}/analytics/reports/{job.public_id}",
        )
    )


@router.get(
    "/analytics/reports/{export_id}",
    response_model=ExportProgressResponse,
    summary="Report export progress + signed download link",
)
async def report_export_progress(
    export_id: uuidlib.UUID, session: SessionDep, actor: AnalyticsExporter
) -> ExportProgressResponse:
    """The same progress envelope contact exports use — one download flow for every artifact."""
    service = ExportService(session)
    job = await service.get(actor.organization_id, export_id)
    return ExportProgressResponse.from_job(job, await service.download_url(job))
