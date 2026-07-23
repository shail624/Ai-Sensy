"""Analytics API & report-export tests (Doc 15 §16–§19) — Phase 8 A8/A9.

Covers the transport contract: the three-way permission split (read / export / executive),
organization isolation, parameter validation as RFC 7807 problems, breakdown and comparison
shapes, and the report export reusing the frozen export system end to end.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.db.mixins import utcnow
from app.models.analytics import (
    GRAIN_HOUR,
    AnalyticsCampaignRollup,
    AnalyticsContactRollup,
    AnalyticsFailureRollup,
    AnalyticsMessageRollup,
)
from app.models.message import DIRECTION_OUTBOUND
from app.models.organization import Organization

PASSWORD = "Sup3r-Secret-Pass1"
BASE = "/api/v1/analytics"
PROBLEM = "application/problem+json"

#: Buckets are seeded "yesterday" so every preset-free range in these tests is closed and stable.
BUCKET = (utcnow() - timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
RANGE = {
    "from": (BUCKET - timedelta(hours=1)).isoformat() + "Z",
    "to": (BUCKET + timedelta(hours=2)).isoformat() + "Z",
}


async def _headers(client, make_user, *, email: str, **kw) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _owner(client, make_user, email: str = "owner@vi.co") -> dict[str, str]:
    return await _headers(client, make_user, email=email, is_superuser=True)


def _assert_problem(resp, status: int) -> dict:
    assert resp.status_code == status, resp.text
    assert resp.headers["content-type"].startswith(PROBLEM)
    body = resp.json()
    assert body["status"] == status
    return body


@pytest.fixture
async def seeded(session_factory, organization):
    """Rollup rows across four fact tables, so every endpoint family has something to read."""
    async with session_factory() as session:
        session.add_all([
            AnalyticsMessageRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=1, direction=DIRECTION_OUTBOUND, message_type="text",
                accepted_count=100, sent_count=100, delivered_count=90, read_count=45,
                failed_count=10, cost_micros=250_000,
            ),
            AnalyticsMessageRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=1, direction=DIRECTION_OUTBOUND, message_type="template",
                accepted_count=40, sent_count=40, delivered_count=38, read_count=20,
                failed_count=2, cost_micros=900_000,
            ),
            AnalyticsFailureRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=1, error_code="131047", failure_count=8,
            ),
            AnalyticsFailureRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=1, error_code="470", failure_count=4,
            ),
            AnalyticsCampaignRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                campaign_id=1, targeted_count=500, sent_count=480, delivered_count=460,
                read_count=200, failed_count=20, cost_micros=1_200_000,
            ),
            AnalyticsContactRollup(
                organization_id=organization.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                created_count=12, opted_in_count=9, opted_out_count=3, active_count=40,
            ),
        ])
        await session.commit()
    return organization.id


# --- Authorization (Doc 15 §15) -------------------------------------------------------------------
async def test_analytics_requires_authentication(client):
    _assert_problem(await client.get(f"{BASE}/summary", params=RANGE), 401)


async def test_agent_has_no_analytics_access(client, make_user):
    """The Agent bundle deliberately carries no analytics permission."""
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    _assert_problem(await client.get(f"{BASE}/summary", params=RANGE, headers=agent), 403)


async def test_analyst_can_read_but_not_see_spend(client, make_user):
    """Analyst holds read+export; cost and the executive dashboard are executive-only."""
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))

    assert (await client.get(f"{BASE}/summary", params=RANGE, headers=analyst)).status_code == 200
    _assert_problem(await client.get(f"{BASE}/costs", params=RANGE, headers=analyst), 403)
    _assert_problem(await client.get(f"{BASE}/executive", params=RANGE, headers=analyst), 403)


async def test_manager_can_read_and_export_but_not_executive(client, make_user):
    manager = await _headers(client, make_user, email="mgr@vi.co", roles=("manager",))

    assert (await client.get(f"{BASE}/series", headers=manager,
                             params={**RANGE, "metrics": ["messages_sent"]})).status_code == 200
    _assert_problem(await client.get(f"{BASE}/costs", params=RANGE, headers=manager), 403)


async def test_owner_reaches_the_executive_surfaces(client, make_user, seeded):
    owner = await _owner(client, make_user)

    assert (await client.get(f"{BASE}/costs", params=RANGE, headers=owner)).status_code == 200
    assert (await client.get(f"{BASE}/executive", params=RANGE, headers=owner)).status_code == 200


# --- Summary, KPIs, comparison --------------------------------------------------------------------
async def test_summary_returns_totals_kpis_and_freshness(client, make_user, seeded):
    owner = await _owner(client, make_user)

    resp = await client.get(f"{BASE}/summary", params=RANGE, headers=owner)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["messages_sent"] == 140
    assert body["kpis"]["delivery_rate"] == pytest.approx(128 / 140, abs=1e-6)
    assert "from" in body and "grain" in body and "data_as_of" in body


async def test_summary_can_select_metrics(client, make_user, seeded):
    owner = await _owner(client, make_user)

    resp = await client.get(
        f"{BASE}/summary", headers=owner, params={**RANGE, "metrics": ["messages_failed"]}
    )

    assert resp.json()["totals"] == {"messages_failed": 12}


async def test_kpis_endpoint_returns_only_derived_values(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/kpis", params=RANGE, headers=owner)).json()

    assert "delivery_rate" in body
    assert "totals" not in body


async def test_comparison_returns_both_windows(client, make_user, seeded):
    owner = await _owner(client, make_user)

    resp = await client.get(
        f"{BASE}/comparison", headers=owner, params={**RANGE, "compare": "previous_period"}
    )

    body = resp.json()
    assert body["current"]["totals"]["messages_sent"] == 140
    assert body["previous_totals"]["messages_sent"] == 0  # nothing seeded before the window


# --- Series & trends -------------------------------------------------------------------------------
async def test_series_is_dense_and_totals_match(client, make_user, seeded):
    owner = await _owner(client, make_user)

    resp = await client.get(
        f"{BASE}/series", headers=owner,
        params={**RANGE, "metrics": ["messages_sent"], "granularity": "hour"},
    )

    body = resp.json()
    points = body["series"][0]["points"]
    assert len(points) == 3  # the range spans three hours; empty ones are zero-filled
    assert sum(p["v"] for p in points) == 140
    assert body["totals"]["messages_sent"] == 140


async def test_series_requires_at_least_one_metric(client, make_user, seeded):
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{BASE}/series", params=RANGE, headers=owner), 422)


async def test_trends_always_carry_a_comparison(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(
        f"{BASE}/trends", headers=owner, params={**RANGE, "metrics": ["messages_sent"]}
    )).json()

    assert body["comparison"] and body["comparison"][0]["key"] == "messages_sent"


# --- Breakdowns ------------------------------------------------------------------------------------
async def test_failures_breakdown_ranks_error_codes(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/failures", params=RANGE, headers=owner)).json()

    assert body["dimension"] == "error_code"
    assert [row["key"] for row in body["data"]] == ["131047", "470"]  # ranked by count
    assert body["data"][0]["totals"]["failures"] == 8


async def test_campaigns_breakdown_returns_the_funnel(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/campaigns", params=RANGE, headers=owner)).json()

    assert body["dimension"] == "campaign_id"
    row = body["data"][0]
    assert row["totals"]["campaign_delivered"] == 460
    assert row["kpis"]["campaign_delivery_rate"] == pytest.approx(460 / 480, abs=1e-6)


async def test_agents_breakdown_labels_the_unassigned_cohort(client, make_user, seeded):
    """A NULL assignee is a real cohort — the unassigned backlog, not an absence."""
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/agents", params=RANGE, headers=owner)).json()

    assert body["dimension"] == "assigned_user_id"
    assert isinstance(body["data"], list)


async def test_costs_breakdown_ranks_by_spend(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/costs", params=RANGE, headers=owner)).json()

    assert [row["key"] for row in body["data"]] == ["template", "text"]  # 0.9 > 0.25
    assert body["totals"]["cost_micros"] == 1_150_000


async def test_generic_breakdown_accepts_any_declared_dimension(client, make_user, seeded):
    owner = await _owner(client, make_user)

    body = (await client.get(
        f"{BASE}/breakdown", headers=owner,
        params={**RANGE, "dimension": "message_type", "metrics": ["messages_sent"]},
    )).json()

    assert {row["key"] for row in body["data"]} == {"text", "template"}


async def test_unknown_dimension_is_a_problem(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/breakdown", headers=owner, params={**RANGE, "dimension": "phase_of_moon"}
    )
    _assert_problem(resp, 400)


async def test_breakdown_limit_is_bounded(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/breakdown", headers=owner,
        params={**RANGE, "dimension": "message_type", "limit": 5000},
    )
    _assert_problem(resp, 422)


# --- Parameter validation (Doc 15 §14.3) ------------------------------------------------------------
async def test_range_without_bounds_or_preset_is_rejected(client, make_user, seeded):
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{BASE}/summary", headers=owner), 400)


async def test_inverted_range_is_rejected(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/summary", headers=owner,
        params={"from": "2026-07-20T00:00:00Z", "to": "2026-07-10T00:00:00Z"},
    )
    _assert_problem(resp, 400)


async def test_hourly_span_guard_is_enforced(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/summary", headers=owner,
        params={"from": "2026-01-01T00:00:00Z", "to": "2026-06-01T00:00:00Z",
                "granularity": "hour"},
    )
    body = _assert_problem(resp, 400)
    assert "7 days" in body["detail"]


async def test_unknown_granularity_is_a_validation_problem(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/summary", headers=owner, params={**RANGE, "granularity": "fortnight"}
    )
    _assert_problem(resp, 422)


async def test_unknown_timezone_is_rejected(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/summary", headers=owner, params={**RANGE, "timezone": "Mars/Olympus_Mons"}
    )
    _assert_problem(resp, 400)


async def test_unknown_metric_is_rejected(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(
        f"{BASE}/series", headers=owner, params={**RANGE, "metrics": ["made_up"]}
    )
    body = _assert_problem(resp, 400)
    assert "made_up" in body["detail"]


async def test_preset_resolves_without_explicit_bounds(client, make_user, seeded):
    owner = await _owner(client, make_user)
    resp = await client.get(f"{BASE}/summary", headers=owner, params={"preset": "last_7d"})
    assert resp.status_code == 200


# --- Empty datasets & isolation ---------------------------------------------------------------------
async def test_empty_dataset_returns_zeros_and_unknown_rates(client, make_user):
    owner = await _owner(client, make_user)

    body = (await client.get(f"{BASE}/summary", params=RANGE, headers=owner)).json()

    assert body["totals"]["messages_sent"] == 0
    assert body["kpis"]["delivery_rate"] is None


async def test_empty_breakdown_returns_an_empty_table(client, make_user):
    owner = await _owner(client, make_user)
    body = (await client.get(f"{BASE}/failures", params=RANGE, headers=owner)).json()
    assert body["data"] == []


async def test_organizations_are_isolated(client, make_user, seeded, session_factory):
    """A second org's rollups must never reach this org's dashboard."""
    async with session_factory() as session:
        other = Organization(name="Other Co", slug="other-co")
        session.add(other)
        await session.flush()
        session.add(
            AnalyticsMessageRollup(
                organization_id=other.id, grain=GRAIN_HOUR, bucket_start=BUCKET,
                phone_number_id=9, direction=DIRECTION_OUTBOUND, message_type="text",
                accepted_count=9999, sent_count=9999,
            )
        )
        await session.commit()

    owner = await _owner(client, make_user)
    body = (await client.get(f"{BASE}/summary", params=RANGE, headers=owner)).json()

    assert body["totals"]["messages_sent"] == 140  # not 10139


async def test_freshness_is_readable_and_empty_before_any_rollup(client, make_user, seeded):
    owner = await _owner(client, make_user)
    body = (await client.get(f"{BASE}/freshness", headers=owner)).json()
    assert body == {"data": []}


async def test_metric_and_dimension_catalogues_are_published(client, make_user, seeded):
    owner = await _owner(client, make_user)

    metrics = (await client.get(f"{BASE}/metrics", headers=owner)).json()["data"]
    dimensions = (await client.get(f"{BASE}/dimensions", headers=owner)).json()["data"]

    keys = {m["key"] for m in metrics}
    assert "messages_sent" in keys
    # Doc 15 §25 Q3 resolved: the honest name is published, the misleading one is not.
    assert "active_customer_hours" in keys
    assert "active_customers" not in keys
    assert {d["key"] for d in dimensions} >= {"error_code", "campaign_id", "assigned_user_id"}


# --- Report export (Doc 15 §19) ----------------------------------------------------------------------
async def test_export_requires_the_export_permission(client, make_user, seeded):
    """A reader may look but not export."""
    await _owner(client, make_user)  # ensure the org exists
    reader = await _headers(client, make_user, email="reader@vi.co", roles=("agent",))

    resp = await client.post(
        f"{BASE}/reports/export", headers=reader,
        json={"report": "messages", "format": "csv", "filters": {"preset": "last_7d"}},
    )
    _assert_problem(resp, 403)


async def test_export_is_accepted_and_queued(client, make_user, seeded, monkeypatch):
    """202 always — a large report must never hold a worker on the request path."""
    dispatched: list[str] = []
    import app.analytics.tasks as tasks

    monkeypatch.setattr(
        tasks.run_report_export, "apply_async",
        lambda args, task_id=None: dispatched.append(args[0]),
    )
    owner = await _owner(client, make_user)

    resp = await client.post(
        f"{BASE}/reports/export", headers=owner,
        json={"report": "messages", "format": "csv", "filters": {"preset": "last_7d"}},
    )

    assert resp.status_code == 202, resp.text
    job = resp.json()["job"]
    assert job["type"] == "export" and job["status"] == "queued"
    assert job["poll_url"].endswith(f"/analytics/reports/{job['id']}")
    assert dispatched == [job["id"]]


async def test_export_records_a_report_entity(client, make_user, seeded, monkeypatch, session_factory):
    """Doc 15 §19 — a report is a new ``exports.entity`` value, not a new table."""
    from sqlalchemy import select

    import app.analytics.tasks as tasks
    from app.models.job_records import ExportJob

    monkeypatch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
    owner = await _owner(client, make_user)

    await client.post(
        f"{BASE}/reports/export", headers=owner,
        json={"report": "tasks", "format": "json", "filters": {"preset": "last_30d"}},
    )

    async with session_factory() as session:
        job = (await session.scalars(select(ExportJob))).first()
    assert job.entity == "report:tasks"
    assert job.format == "json"
    assert job.filters_json["preset"] == "last_30d"


async def test_export_rejects_an_unknown_report_and_format(client, make_user, seeded):
    owner = await _owner(client, make_user)

    _assert_problem(
        await client.post(
            f"{BASE}/reports/export", headers=owner,
            json={"report": "unicorns", "format": "csv", "filters": {"preset": "today"}},
        ),
        422,
    )
    _assert_problem(
        await client.post(
            f"{BASE}/reports/export", headers=owner,
            json={"report": "messages", "format": "pdf", "filters": {"preset": "today"}},
        ),
        422,
    )


async def test_export_generates_rows_from_the_rollups(client, make_user, seeded, session_factory):
    """The worker body streams from rollups — never the ledger (Doc 15 §19)."""
    from sqlalchemy import select

    from app.models.job_records import STATUS_READY, ExportJob
    from app.services.export_service import ExportService

    owner = await _owner(client, make_user)
    with pytest.MonkeyPatch.context() as patch:
        import app.analytics.tasks as tasks

        patch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
        created = await client.post(
            f"{BASE}/reports/export", headers=owner,
            json={
                "report": "messages", "format": "csv",
                "filters": {**RANGE, "granularity": "hour"},
            },
        )
    export_id = created.json()["job"]["id"]

    async with session_factory() as session:
        job = await ExportService(session).run(export_id)

    assert job.status == STATUS_READY
    assert job.row_count == 3  # one row per hourly bucket in the range
    assert job.storage_key and job.storage_key.endswith(".csv")

    async with session_factory() as session:
        stored = (await session.scalars(select(ExportJob))).first()
    assert stored.entity == "report:messages"


async def test_export_progress_is_readable(client, make_user, seeded, monkeypatch):
    import app.analytics.tasks as tasks

    monkeypatch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
    owner = await _owner(client, make_user)
    created = await client.post(
        f"{BASE}/reports/export", headers=owner,
        json={"report": "messages", "format": "csv", "filters": {"preset": "today"}},
    )
    export_id = created.json()["job"]["id"]

    resp = await client.get(f"{BASE}/reports/{export_id}", headers=owner)

    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == export_id
    assert resp.json()["type"] == "export"


async def test_export_of_another_org_is_not_found(client, make_user, seeded, monkeypatch):
    import app.analytics.tasks as tasks

    monkeypatch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
    owner = await _owner(client, make_user)
    _assert_problem(await client.get(f"{BASE}/reports/{uuid.uuid4()}", headers=owner), 404)


# --- Build ------------------------------------------------------------------------------------------
def test_every_analytics_route_is_mounted() -> None:
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/analytics/summary", "/api/v1/analytics/kpis", "/api/v1/analytics/comparison",
        "/api/v1/analytics/series", "/api/v1/analytics/trends", "/api/v1/analytics/breakdown",
        "/api/v1/analytics/failures", "/api/v1/analytics/campaigns", "/api/v1/analytics/agents",
        "/api/v1/analytics/costs", "/api/v1/analytics/executive", "/api/v1/analytics/metrics",
        "/api/v1/analytics/dimensions", "/api/v1/analytics/freshness",
        "/api/v1/analytics/reports/export", "/api/v1/analytics/reports/{export_id}",
    }
    assert expected <= set(paths)


async def test_report_artifact_contains_the_rollup_rows(client, make_user, seeded, session_factory):
    """The artifact itself must carry the report columns, not a contacts header with blank rows.

    A9's row-count assertion could not see this: `row_count` is computed before writing.
    """
    import app.analytics.tasks as tasks
    from app.crm.formats import export_writer
    from app.services.export_service import REPORT_METRICS, ExportService

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(tasks.run_report_export, "apply_async", lambda args, task_id=None: None)
        created = await client.post(
            f"{BASE}/reports/export",
            headers=await _owner(client, make_user),
            json={
                "report": "messages", "format": "csv",
                "filters": {**RANGE, "granularity": "hour"},
            },
        )
    export_id = created.json()["job"]["id"]

    captured: dict[str, bytes] = {}
    real_writer = export_writer

    def capturing_writer(fmt: str, columns=None):
        writer = real_writer(fmt, columns) if columns else real_writer(fmt)
        original_finish = writer.finish

        def finish() -> bytes:
            captured["body"] = original_finish()
            return captured["body"]

        writer.finish = finish  # type: ignore[method-assign]
        return writer

    with pytest.MonkeyPatch.context() as patch:
        import app.services.export_service as export_module

        patch.setattr(export_module, "export_writer", capturing_writer)
        async with session_factory() as session:
            await ExportService(session).run(export_id)

    body = captured["body"].decode("utf-8")
    header = body.splitlines()[0]
    assert header == ",".join(("period", *REPORT_METRICS["messages"]))
    assert "phone_e164" not in header          # not the contacts shape
    assert "messages_sent" in header
    assert len(body.splitlines()) == 4         # header + three hourly buckets
