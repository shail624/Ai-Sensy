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
from datetime import date as date_type
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

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
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportSchedulesResponse,
    ReportScheduleUpdate,
    ReportViewCreate,
    ReportViewResponse,
    ReportViewsResponse,
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
from app.services.chat_activity_service import ChatActivityService
from app.services.export_service import ExportService
from app.services.report_schedule_service import ReportScheduleService
from app.services.report_view_service import ReportViewService

router = APIRouter()

AnalyticsReader = Annotated[User, Depends(require_permissions("analytics:read"))]
AnalyticsExporter = Annotated[User, Depends(require_permissions("analytics:export"))]
#: Cost and the executive dashboard are commercially sensitive — a support agent or analyst has no
#: operational need for spend (Doc 15 §15).
AnalyticsExecutive = Annotated[User, Depends(require_permissions("analytics:executive"))]
AnalyticsScheduleManager = Annotated[
    User, Depends(require_permissions("analytics:export", "analytics:executive"))
]


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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
    )
    view = await AnalyticsQueryService(session).summary(
        organization_id=actor.organization_id, spec=spec, metrics=metrics
    )
    return AnalyticsSummaryResponse.of(view)


@router.get("/analytics/kpis", response_model=AnalyticsKpiResponse, summary="Derived KPIs only")
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
        compare=compare,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
        compare=compare,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
        compare=compare,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity=granularity,
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension=dimension,
        metrics=metrics,
        spec=spec,
        limit=limit,
        sort_by=sort_by,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="campaign_id",
        metrics=[
            "campaign_targeted",
            "campaign_sent",
            "campaign_delivered",
            "campaign_read",
            "campaign_failed",
            "campaign_skipped",
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="assigned_user_id",
        metrics=[
            "conversations_opened",
            "conversations_resolved",
            "outbound_messages",
            "conversations_handled",
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
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
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
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


# --- Saved report analysis views -------------------------------------------------------------------


@router.get(
    "/analytics/views",
    response_model=ReportViewsResponse,
    summary="List personal and team-shared Report views",
)
async def list_report_views(
    session: SessionDep,
    actor: AnalyticsReader,
) -> ReportViewsResponse:
    rows, can_manage_shared = await ReportViewService(session).list(actor)
    return ReportViewsResponse(
        data=[
            ReportViewResponse.from_view(
                row,
                actor_user_id=actor.id,
                can_manage_shared=can_manage_shared,
            )
            for row in rows
        ]
    )


@router.post(
    "/analytics/views",
    response_model=ReportViewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a personal or team-shared Report view",
)
async def create_report_view(
    payload: ReportViewCreate,
    session: SessionDep,
    actor: AnalyticsReader,
) -> ReportViewResponse:
    row = await ReportViewService(session).create(actor, payload)
    return ReportViewResponse.from_view(
        row,
        actor_user_id=actor.id,
        can_manage_shared=payload.visibility == "shared",
    )


@router.delete(
    "/analytics/views/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an owned personal or managed team Report view",
)
async def delete_report_view(
    view_id: uuidlib.UUID,
    session: SessionDep,
    actor: AnalyticsReader,
) -> None:
    await ReportViewService(session).delete(actor, view_id)


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


# --- Scheduled reports -----------------------------------------------------------------------------
@router.get(
    "/analytics/report-schedules",
    response_model=ReportSchedulesResponse,
    summary="List my scheduled reports",
)
async def list_report_schedules(
    session: SessionDep, actor: AnalyticsScheduleManager
) -> ReportSchedulesResponse:
    rows = await ReportScheduleService(session).list(actor)
    return ReportSchedulesResponse(data=[ReportScheduleResponse.from_schedule(row) for row in rows])


@router.post(
    "/analytics/report-schedules",
    response_model=ReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled report",
)
async def create_report_schedule(
    payload: ReportScheduleCreate, session: SessionDep, actor: AnalyticsScheduleManager
) -> ReportScheduleResponse:
    row = await ReportScheduleService(session).create(actor, payload)
    return ReportScheduleResponse.from_schedule(row)


@router.put(
    "/analytics/report-schedules/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="Replace a scheduled report",
)
async def update_report_schedule(
    schedule_id: uuidlib.UUID,
    payload: ReportScheduleUpdate,
    session: SessionDep,
    actor: AnalyticsScheduleManager,
) -> ReportScheduleResponse:
    row = await ReportScheduleService(session).update(actor, schedule_id, payload)
    return ReportScheduleResponse.from_schedule(row)


@router.delete(
    "/analytics/report-schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scheduled report",
)
async def delete_report_schedule(
    schedule_id: uuidlib.UUID,
    session: SessionDep,
    actor: AnalyticsScheduleManager,
    expected_row_version: Annotated[int, Query(ge=0)],
) -> None:
    await ReportScheduleService(session).delete(
        actor, schedule_id, expected_row_version=expected_row_version
    )


@router.get(
    "/analytics/task-productivity",
    response_model=AnalyticsBreakdownResponse,
    summary="Task productivity by teammate",
)
async def analytics_task_productivity(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """Completed/on-time/overdue task flow by assignee over the selected range."""
    spec = _spec(
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="assigned_agent_id",
        metrics=[
            "tasks_created",
            "tasks_completed",
            "tasks_completed_on_time",
            "tasks_overdue_entered",
        ],
        spec=spec,
        limit=limit,
        sort_by="tasks_completed",
    )


@router.get(
    "/analytics/reactivation-outcomes",
    response_model=AnalyticsBreakdownResponse,
    summary="Reactivation and eligibility outcomes",
)
async def analytics_reactivation_outcomes(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """Factual case creation, terminal outcomes and eligibility decisions by outcome."""
    spec = _spec(
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="outcome",
        metrics=[
            "reactivation_cases_created",
            "reactivation_stage_transitions",
            "reactivation_completed",
            "reactivation_not_required",
            "eligibility_decisions",
            "eligibility_eligible",
            "eligibility_not_eligible",
            "eligibility_review_required",
        ],
        spec=spec,
        limit=limit,
    )


@router.get(
    "/analytics/kyc-outcomes",
    response_model=AnalyticsBreakdownResponse,
    summary="KYC decision outcomes",
)
async def analytics_kyc_outcomes(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """Review and manager decisions with terminal approval/rejection truth."""
    spec = _spec(
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="outcome",
        metrics=["kyc_decisions", "kyc_approved", "kyc_rejected", "kyc_needs_information"],
        spec=spec,
        limit=limit,
    )


@router.get(
    "/analytics/service-levels",
    response_model=AnalyticsBreakdownResponse,
    summary="SLA and fulfilment outcomes",
)
async def analytics_service_levels(
    session: SessionDep,
    actor: AnalyticsReader,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    preset: Annotated[PresetLiteral | None, Query()] = None,
    timezone: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsBreakdownResponse:
    """SLA starts/breaches/resolutions plus SIM and activation terminal outcomes."""
    spec = _spec(
        actor,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        granularity="day",
        timezone=timezone,
    )
    return await _breakdown(
        session,
        actor,
        dimension="outcome",
        metrics=[
            "sla_started",
            "sla_breached",
            "sla_resolved",
            "sim_delivered",
            "sim_failed",
            "activations_completed",
            "activations_rejected",
        ],
        spec=spec,
        limit=limit,
    )


class ChatActivityDay(BaseModel):
    date: date_type
    user_messages: int
    business_messages: int
    chatbot_messages: int
    closed: int
    intervened: int


class ChatActivityResponse(BaseModel):
    timezone: str
    data: list[ChatActivityDay]


@router.get(
    "/analytics/chat-activity",
    response_model=ChatActivityResponse,
    summary="Messages and agent activity per day (Manage → Analytics)",
)
async def chat_activity(
    session: SessionDep,
    actor: AnalyticsReader,
    days: Annotated[int, Query(ge=1, le=31)] = 7,
    timezone: Annotated[str, Query(max_length=64)] = "Asia/Kolkata",
) -> ChatActivityResponse:
    """Customer, business and chatbot messages, plus chats closed and intervened, per day."""
    rows = await ChatActivityService(session).daily(
        organization_id=actor.organization_id, days=days, timezone=timezone
    )
    return ChatActivityResponse(
        timezone=timezone,
        data=[
            ChatActivityDay(
                date=row.day,
                user_messages=row.user_messages,
                business_messages=row.business_messages,
                chatbot_messages=row.chatbot_messages,
                closed=row.closed,
                intervened=row.intervened,
            )
            for row in rows
        ],
    )
