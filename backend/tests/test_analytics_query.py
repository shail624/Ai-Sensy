"""Analytics query service & schema tests (Doc 15 §10–§14, §21) — Phase 8 A6/A7.

The properties under test are the ones a dashboard's correctness rests on: the right stored grain
is chosen, UTC buckets fold into the caller's local periods, series are dense, ratios are derived
from summed components rather than averaged averages, comparison windows line up, and one
organization never sees another's numbers.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import BadRequestError
from app.models.analytics import GRAIN_DAY, GRAIN_HOUR, AnalyticsMessageRollup
from app.models.message import DIRECTION_OUTBOUND
from app.models.organization import Organization
from app.schemas.analytics import (
    AnalyticsComparisonResponse,
    AnalyticsFreshnessResponse,
    AnalyticsKpiResponse,
    AnalyticsRangeFilters,
    AnalyticsSeriesFilters,
    AnalyticsSeriesResponse,
    AnalyticsSummaryResponse,
    ReportExportRequest,
)
from app.services.analytics_query_service import (
    METRICS,
    AnalyticsQueryService,
    RangeSpec,
    comparison_window,
    dense_periods,
    derive_kpis,
    format_period,
    period_key,
    plan_grain,
    resolve_range,
    resolve_timezone,
)

NOW = datetime(2026, 7, 23, 14, 30, 0)
KOLKATA = "Asia/Kolkata"


def _spec(**overrides) -> RangeSpec:
    base = {
        "start": datetime(2026, 7, 20, 0, 0),
        "end": datetime(2026, 7, 23, 0, 0),
        "granularity": "day",
        "timezone": resolve_timezone("UTC"),
    }
    return RangeSpec(**{**base, **overrides})


# --- Range resolution (Doc 15 §14) ---------------------------------------------------------------
def test_explicit_range_is_accepted():
    spec = resolve_range(
        start=datetime(2026, 7, 1), end=datetime(2026, 7, 8), granularity="day", now=NOW
    )
    assert spec.start == datetime(2026, 7, 1)
    assert spec.end == datetime(2026, 7, 8)


def test_range_must_be_ordered():
    with pytest.raises(BadRequestError):
        resolve_range(start=datetime(2026, 7, 8), end=datetime(2026, 7, 1), now=NOW)


def test_range_requires_bounds_or_preset():
    with pytest.raises(BadRequestError):
        resolve_range(start=datetime(2026, 7, 1), now=NOW)


def test_future_range_is_truncated_not_rejected():
    """§14.3 — asking for tomorrow is a reasonable thing for a dashboard to do."""
    spec = resolve_range(
        start=datetime(2026, 7, 20), end=datetime(2026, 8, 30), granularity="day", now=NOW
    )
    assert spec.end <= datetime(2026, 7, 23, 15, 0)


def test_span_guard_rejects_an_unbounded_hourly_request():
    with pytest.raises(BadRequestError) as exc:
        resolve_range(
            start=datetime(2026, 6, 1), end=datetime(2026, 7, 23), granularity="hour", now=NOW
        )
    assert "at most 7 days" in str(exc.value)


def test_unknown_granularity_and_compare_are_rejected():
    with pytest.raises(BadRequestError):
        resolve_range(preset="today", granularity="fortnight", now=NOW)
    with pytest.raises(BadRequestError):
        resolve_range(preset="today", compare="last_decade", now=NOW)


def test_unknown_timezone_is_rejected():
    with pytest.raises(BadRequestError):
        resolve_timezone("Mars/Olympus_Mons")


@pytest.mark.parametrize(
    "preset", ["today", "yesterday", "last_7d", "last_30d", "this_month", "last_month", "this_quarter"]
)
def test_every_preset_resolves_to_a_window(preset):
    spec = resolve_range(preset=preset, timezone=KOLKATA, now=NOW)
    assert spec.start < spec.end


def test_presets_anchor_on_local_calendar_boundaries():
    """"Today" in Kolkata (+05:30) starts at 18:30 UTC the previous day."""
    spec = resolve_range(preset="today", timezone=KOLKATA, granularity="hour", now=NOW)
    assert spec.start == datetime(2026, 7, 22, 18, 30)


# --- Grain planning (Doc 15 §21.4) ---------------------------------------------------------------
def test_hour_granularity_always_uses_hourly_rows():
    assert plan_grain(_spec(granularity="hour"), NOW) == GRAIN_HOUR


def test_recent_day_range_prefers_hourly_for_exact_local_folding():
    assert plan_grain(_spec(granularity="day"), NOW) == GRAIN_HOUR


def test_range_past_hourly_retention_falls_back_to_daily():
    old = _spec(
        start=datetime(2026, 1, 1), end=datetime(2026, 1, 31), granularity="month"
    )
    assert plan_grain(old, NOW) == GRAIN_DAY


# --- Timezone folding (Doc 15 §10, §14.1) --------------------------------------------------------
def test_utc_bucket_folds_into_the_local_day():
    """20:00 UTC is already the next day in Kolkata — the fold must say so."""
    tz = resolve_timezone(KOLKATA)
    assert period_key(datetime(2026, 7, 22, 20, 0), "day", tz) == datetime(2026, 7, 23)
    assert period_key(datetime(2026, 7, 22, 10, 0), "day", tz) == datetime(2026, 7, 22)


def test_utc_fold_is_identity_in_utc():
    tz = resolve_timezone("UTC")
    assert period_key(datetime(2026, 7, 22, 20, 0), "day", tz) == datetime(2026, 7, 22)


def test_week_folds_to_monday():
    tz = resolve_timezone("UTC")
    # 2026-07-23 is a Thursday; its ISO week starts Monday the 20th.
    assert period_key(datetime(2026, 7, 23, 12, 0), "week", tz) == datetime(2026, 7, 20)


def test_month_folds_to_the_first():
    tz = resolve_timezone("UTC")
    assert period_key(datetime(2026, 7, 23, 12, 0), "month", tz) == datetime(2026, 7, 1)


def test_hour_labels_carry_the_hour_and_day_labels_do_not():
    assert format_period(datetime(2026, 7, 23, 9, 0), "hour") == "2026-07-23T09:00"
    assert format_period(datetime(2026, 7, 23), "day") == "2026-07-23"


# --- Dense buckets (Doc 15 §10) ------------------------------------------------------------------
def test_dense_periods_have_no_gaps():
    periods = dense_periods(_spec())
    assert periods == [datetime(2026, 7, 20), datetime(2026, 7, 21), datetime(2026, 7, 22)]


def test_dense_periods_at_hour_granularity():
    spec = _spec(
        start=datetime(2026, 7, 23, 8, 0), end=datetime(2026, 7, 23, 12, 0), granularity="hour"
    )
    assert len(dense_periods(spec)) == 4


def test_dense_periods_cross_a_month_boundary():
    spec = _spec(
        start=datetime(2026, 5, 15), end=datetime(2026, 7, 15), granularity="month"
    )
    assert dense_periods(spec) == [
        datetime(2026, 5, 1),
        datetime(2026, 6, 1),
        datetime(2026, 7, 1),
    ]


# --- Comparison windows (Doc 15 §14.2) -----------------------------------------------------------
def test_previous_period_shifts_by_the_range_length():
    spec = _spec(compare="previous_period")
    previous = comparison_window(spec)
    assert previous.start == datetime(2026, 7, 17)
    assert previous.end == datetime(2026, 7, 20)
    assert previous.end - previous.start == spec.end - spec.start


def test_previous_year_shifts_by_365_days():
    previous = comparison_window(_spec(compare="previous_year"))
    assert previous.start == datetime(2025, 7, 20)
    assert previous.end == datetime(2025, 7, 23)


def test_comparison_window_carries_no_further_comparison():
    assert comparison_window(_spec(compare="previous_period")).compare is None


# --- KPI derivation (Doc 15 §11, §6.2) -----------------------------------------------------------
def test_rates_are_derived_from_summed_components():
    kpis = derive_kpis({
        "messages_sent": 1000, "messages_delivered": 990, "messages_read": 500,
        "messages_failed": 10,
    })
    assert kpis["delivery_rate"] == 0.99
    assert kpis["read_rate"] == pytest.approx(0.505051, abs=1e-6)  # of delivered, not sent
    assert kpis["failure_rate"] == 0.01


def test_an_empty_denominator_yields_none_not_zero():
    """A rate over nothing is unknown; 0% would be a lie on an idle dashboard."""
    kpis = derive_kpis({"messages_sent": 0, "messages_delivered": 0})
    assert kpis["delivery_rate"] is None
    assert kpis["read_rate"] is None


def test_averages_use_stored_sum_and_count():
    kpis = derive_kpis({
        "delivery_latency_ms_sum": 9000, "delivery_latency_count": 3,
        "time_to_complete_seconds_sum": 7200, "time_to_complete_count": 2,
    })
    assert kpis["avg_delivery_latency_ms"] == 3000
    assert kpis["avg_time_to_complete_seconds"] == 3600


def test_task_and_customer_kpis():
    kpis = derive_kpis({
        "tasks_created": 20, "tasks_completed": 15, "tasks_completed_on_time": 12,
        "contacts_created": 100, "contacts_opted_in": 40, "contacts_opted_out": 10,
    })
    assert kpis["task_completion_rate"] == 0.75
    assert kpis["task_on_time_rate"] == 0.8
    assert kpis["net_opt_in_change"] == 30
    assert kpis["opt_out_rate"] == 0.1


def test_unavailable_latency_components_read_as_unknown():
    """first_response_*/resolution_* are still 0 from the rollup — they must not read as 0 s."""
    kpis = derive_kpis({"first_response_seconds_sum": 0, "first_response_count": 0})
    assert kpis["avg_first_response_seconds"] is None
    assert kpis["avg_resolution_seconds"] is None


# --- Metric catalogue -----------------------------------------------------------------------------
def test_active_customers_is_labelled_as_customer_hours():
    """Doc 15 §25 Q3 — the metric is honest about what summing it means."""
    assert METRICS["active_customer_hours"].label == "Active customer-hours"
    assert METRICS["active_customer_hours"].column == "active_count"


def test_every_metric_points_at_a_real_column():
    for key, spec in METRICS.items():
        assert hasattr(spec.model, spec.column), key


# --- Service reads --------------------------------------------------------------------------------
@pytest.fixture
async def seeded(db_session, organization):
    """Three hourly message buckets on 2026-07-22 (UTC), one of them after the Kolkata midnight."""
    rows = [
        (datetime(2026, 7, 22, 9, 0), 10, 9, 5, 1),
        (datetime(2026, 7, 22, 10, 0), 20, 18, 10, 2),
        (datetime(2026, 7, 22, 20, 0), 5, 5, 1, 0),  # 01:30 on 07-23 in Kolkata
    ]
    for bucket, accepted, delivered, read, failed in rows:
        db_session.add(
            AnalyticsMessageRollup(
                organization_id=organization.id,
                grain=GRAIN_HOUR,
                bucket_start=bucket,
                phone_number_id=1,
                direction=DIRECTION_OUTBOUND,
                message_type="text",
                accepted_count=accepted,
                sent_count=accepted,
                delivered_count=delivered,
                read_count=read,
                failed_count=failed,
            )
        )
    await db_session.commit()
    return organization.id


async def test_summary_sums_the_window(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="day", now=NOW
    )

    view = await service.summary(organization_id=seeded, spec=spec, metrics=["messages_accepted"])

    assert view.totals["messages_accepted"] == 35
    assert view.grain == GRAIN_HOUR


async def test_summary_derives_rates(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="day", now=NOW
    )

    view = await service.summary(
        organization_id=seeded, spec=spec, metrics=["messages_sent", "messages_delivered"]
    )

    assert view.kpis["delivery_rate"] == pytest.approx(32 / 35, abs=1e-6)


async def test_series_is_dense_over_an_empty_range(db_session, seeded):
    """Doc 15 §10 — hours with no activity return 0, never a gap."""
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22, 0, 0), end=datetime(2026, 7, 22, 6, 0),
        granularity="hour", now=NOW,
    )

    result = await service.series(
        organization_id=seeded, spec=spec, metrics=["messages_accepted"]
    )

    points = result.series[0].points
    assert len(points) == 6
    assert all(point.v == 0 for point in points)


async def test_series_folds_into_local_days(db_session, seeded):
    """The 20:00 UTC bucket belongs to 07-23 in Kolkata, not 07-22."""
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 21, 18, 30), end=datetime(2026, 7, 23, 18, 30),
        granularity="day", timezone=KOLKATA, now=NOW,
    )

    result = await service.series(
        organization_id=seeded, spec=spec, metrics=["messages_accepted"]
    )

    by_label = {point.t: point.v for point in result.series[0].points}
    assert by_label["2026-07-22"] == 30  # the 09:00 and 10:00 UTC buckets
    assert by_label["2026-07-23"] == 5   # the 20:00 UTC bucket


async def test_series_totals_match_the_points(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="hour", now=NOW
    )

    result = await service.series(
        organization_id=seeded, spec=spec, metrics=["messages_accepted"]
    )

    assert result.totals["messages_accepted"] == sum(p.v for p in result.series[0].points) == 35


async def test_series_with_comparison_returns_both_windows(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23),
        granularity="day", compare="previous_period", now=NOW,
    )

    result = await service.series(
        organization_id=seeded, spec=spec, metrics=["messages_accepted"]
    )

    assert result.totals["messages_accepted"] == 35
    assert len(result.comparison) == 1
    assert result.comparison_totals["messages_accepted"] == 0  # nothing seeded the day before


async def test_unknown_metric_is_rejected(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(preset="today", now=NOW)

    with pytest.raises(BadRequestError) as exc:
        await service.series(organization_id=seeded, spec=spec, metrics=["made_up"])
    assert "made_up" in str(exc.value)


async def test_series_requires_at_least_one_metric(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(preset="today", now=NOW)
    with pytest.raises(BadRequestError):
        await service.series(organization_id=seeded, spec=spec, metrics=[])


async def test_empty_dataset_yields_zero_totals_and_unknown_rates(db_session, organization):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="day", now=NOW
    )

    view = await service.summary(
        organization_id=organization.id, spec=spec, metrics=["messages_sent", "messages_delivered"]
    )

    assert view.totals == {"messages_sent": 0, "messages_delivered": 0}
    assert view.kpis["delivery_rate"] is None


async def test_organizations_are_isolated(db_session, seeded):
    other = Organization(name="Other Co", slug="other-co")
    db_session.add(other)
    await db_session.commit()
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="day", now=NOW
    )

    mine = await service.summary(organization_id=seeded, spec=spec, metrics=["messages_accepted"])
    theirs = await service.summary(
        organization_id=other.id, spec=spec, metrics=["messages_accepted"]
    )

    assert mine.totals["messages_accepted"] == 35
    assert theirs.totals["messages_accepted"] == 0


async def test_buckets_outside_the_range_are_excluded(db_session, seeded):
    """Boundary timestamps: the range is half-open, so the closing bound is not counted."""
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22, 9, 0), end=datetime(2026, 7, 22, 10, 0),
        granularity="hour", now=NOW,
    )

    view = await service.summary(organization_id=seeded, spec=spec, metrics=["messages_accepted"])

    assert view.totals["messages_accepted"] == 10  # only the 09:00 bucket


async def test_freshness_reports_lag_per_kind(db_session, organization):
    from app.models.analytics import AnalyticsRollupRun

    db_session.add(
        AnalyticsRollupRun(
            organization_id=organization.id,
            kind="messages",
            watermark_at=datetime(2026, 7, 23, 13, 0),
            last_run_at=datetime(2026, 7, 23, 14, 0),
            last_status="ok",
        )
    )
    await db_session.commit()

    rows = await AnalyticsQueryService(db_session).freshness(
        organization_id=organization.id, now=NOW
    )

    assert len(rows) == 1
    assert rows[0].kind == "messages"
    assert rows[0].lag_seconds == 5400  # 13:00 → 14:30


# --- Schema validation (Doc 15 §18) ----------------------------------------------------------------
def test_filters_accept_a_preset():
    filters = AnalyticsRangeFilters(preset="last_7d")
    assert filters.preset == "last_7d"
    assert filters.granularity == "day"


def test_filters_accept_an_explicit_range_by_alias():
    filters = AnalyticsRangeFilters.model_validate(
        {"from": "2026-07-01T00:00:00Z", "to": "2026-07-08T00:00:00Z"}
    )
    assert filters.from_ == datetime(2026, 7, 1)  # normalised to naive UTC


def test_filters_reject_a_range_with_neither_bound_nor_preset():
    with pytest.raises(ValidationError):
        AnalyticsRangeFilters()


def test_filters_reject_an_inverted_range():
    with pytest.raises(ValidationError):
        AnalyticsRangeFilters.model_validate(
            {"from": "2026-07-08T00:00:00Z", "to": "2026-07-01T00:00:00Z"}
        )


def test_filters_reject_an_unknown_granularity():
    with pytest.raises(ValidationError):
        AnalyticsRangeFilters(preset="today", granularity="fortnight")


def test_series_filters_require_metrics():
    with pytest.raises(ValidationError):
        AnalyticsSeriesFilters(preset="today", metrics=[])
    assert AnalyticsSeriesFilters(preset="today", metrics=["messages_sent"]).metrics == [
        "messages_sent"
    ]


def test_export_request_validates_report_and_format():
    request = ReportExportRequest(
        report="messages", format="csv", filters=AnalyticsRangeFilters(preset="last_30d")
    )
    assert request.report == "messages"
    with pytest.raises(ValidationError):
        ReportExportRequest(
            report="unicorns", format="csv", filters=AnalyticsRangeFilters(preset="today")
        )
    with pytest.raises(ValidationError):
        ReportExportRequest(
            report="messages", format="pdf", filters=AnalyticsRangeFilters(preset="today")
        )


def test_kpi_response_maps_every_derived_field():
    kpis = derive_kpis({"messages_sent": 100, "messages_delivered": 99})
    response = AnalyticsKpiResponse.of(kpis)
    assert response.delivery_rate == 0.99
    # 0 reads out of 99 delivered is a real 0%, not unknown — the denominator exists.
    assert response.read_rate == 0.0
    # Whereas a metric with no denominator at all stays unknown.
    assert response.avg_delivery_latency_ms is None


async def test_summary_response_serialises_from_the_view(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="day", now=NOW
    )
    view = await service.summary(organization_id=seeded, spec=spec, metrics=["messages_accepted"])

    payload = AnalyticsSummaryResponse.of(view).model_dump(by_alias=True)

    assert payload["from"] == datetime(2026, 7, 22)
    assert payload["totals"]["messages_accepted"] == 35
    assert "kpis" in payload and "grain" in payload


async def test_series_response_serialises_from_the_view(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23), granularity="hour", now=NOW
    )
    result = await service.series(
        organization_id=seeded, spec=spec, metrics=["messages_accepted"]
    )

    payload = AnalyticsSeriesResponse.of(result).model_dump(by_alias=True)

    assert payload["granularity"] == "hour"
    assert payload["grain"] == GRAIN_HOUR
    assert len(payload["series"][0]["points"]) == 24
    assert payload["timezone"] == "UTC"


async def test_comparison_response_carries_both_windows(db_session, seeded):
    service = AnalyticsQueryService(db_session)
    spec = resolve_range(
        start=datetime(2026, 7, 22), end=datetime(2026, 7, 23),
        granularity="day", compare="previous_period", now=NOW,
    )
    view = await service.summary(organization_id=seeded, spec=spec, metrics=["messages_accepted"])

    payload = AnalyticsComparisonResponse.of(view).model_dump(by_alias=True)

    assert payload["current"]["totals"]["messages_accepted"] == 35
    assert payload["previous_totals"]["messages_accepted"] == 0


async def test_freshness_response_serialises(db_session, organization):
    rows = await AnalyticsQueryService(db_session).freshness(
        organization_id=organization.id, now=NOW
    )
    assert AnalyticsFreshnessResponse.of(rows).model_dump() == {"data": []}
