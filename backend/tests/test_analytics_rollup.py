"""Analytics rollup pipeline tests (Doc 15 §6–§8, §21, §23) — Phase 8 A4/A5.

The properties under test are the ones the design leans on: a bucket is a pure function of its
sources, so re-running converges (§6.3); measures are additive, so a day equals the sum of its
hours (§6.2, §21.4); the trailing window absorbs late data (§8.2); and organizations never see each
other's numbers.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.analytics import (
    GRAIN_DAY,
    GRAIN_HOUR,
    KIND_MESSAGES,
    RUN_OK,
    AnalyticsContactRollup,
    AnalyticsMessageRollup,
    AnalyticsRollupRun,
    AnalyticsTaskRollup,
)
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import (
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    MSG_DELIVERED,
    MSG_FAILED,
    MSG_READ,
    Message,
)
from app.models.organization import Organization
from app.models.task import Task
from app.models.task_event import TASK_EVENT_COMPLETED, TASK_EVENT_CREATED, TaskEvent
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.services.analytics_rollup_service import (
    AnalyticsRollupService,
    floor_hour,
    hour_range,
    window_for,
)

#: A fixed "now" so every bucket assertion is deterministic.
NOW = datetime(2026, 7, 23, 14, 30, 0)
BUCKET = datetime(2026, 7, 23, 12, 0, 0)  # inside the trailing 6h window of NOW


# --- Seeding ------------------------------------------------------------------------------------
@pytest.fixture
async def org_fixture(db_session, organization):
    """One organization with a number, a contact and a conversation to hang messages off."""
    waba = WhatsAppBusinessAccount(
        organization_id=organization.id,
        waba_id="WABA-A",
        business_name="Vi",
        access_token_enc=b"cipher",
    )
    db_session.add(waba)
    await db_session.flush()
    number = PhoneNumber(
        organization_id=organization.id,
        waba_id=waba.id,
        phone_number_id="PN-A",
        display_number="+911111111111",
    )
    contact = Contact(
        organization_id=organization.id,
        wa_id="919990000001",
        phone_e164="+919990000001",
        full_name="Ramesh K.",
    )
    db_session.add_all([number, contact])
    await db_session.flush()
    conversation = Conversation(
        organization_id=organization.id,
        phone_number_id=number.id,
        contact_id=contact.id,
    )
    db_session.add(conversation)
    await db_session.commit()
    return {
        "organization_id": organization.id,
        "number_id": number.id,
        "contact_id": contact.id,
        "conversation_id": conversation.id,
    }


def _message(ctx: dict, *, created_at: datetime, status: str = MSG_DELIVERED,
             direction: str = DIRECTION_OUTBOUND, error_code: str | None = None,
             cost: float | None = None, sent_at: datetime | None = None,
             delivered_at: datetime | None = None) -> Message:
    return Message(
        organization_id=ctx["organization_id"],
        conversation_id=ctx["conversation_id"],
        phone_number_id=ctx["number_id"],
        contact_id=ctx["contact_id"],
        direction=direction,
        message_type="text",
        status=status,
        error_code=error_code,
        cost_amount=cost,
        sent_at=sent_at,
        delivered_at=delivered_at,
        created_at=created_at,
    )


async def _rollup(db_session, ctx: dict, *, start=None, end=None, kinds=None):
    service = AnalyticsRollupService(db_session)
    window_start, window_end = (start, end) if start else window_for(NOW, 6)
    return await service.rollup_organization(
        ctx["organization_id"], window_start, window_end, kinds
    )


async def _message_rows(db_session, organization_id: int, grain: str = GRAIN_HOUR):
    stmt = (
        select(AnalyticsMessageRollup)
        .where(
            AnalyticsMessageRollup.organization_id == organization_id,
            AnalyticsMessageRollup.grain == grain,
        )
        .order_by(AnalyticsMessageRollup.bucket_start, AnalyticsMessageRollup.direction)
    )
    return list((await db_session.scalars(stmt)).all())


# --- Bucket maths (Doc 15 §6.1, §8.1) -----------------------------------------------------------
def test_window_excludes_the_in_progress_hour():
    """A partial bucket stored as complete would read as a real dip in every chart."""
    start, end = window_for(NOW, 6)
    assert end == datetime(2026, 7, 23, 14, 0)  # 14:30 is still accumulating
    assert start == datetime(2026, 7, 23, 8, 0)
    assert len(hour_range(start, end)) == 6


def test_hour_range_is_half_open():
    buckets = hour_range(datetime(2026, 7, 23, 8, 0), datetime(2026, 7, 23, 11, 0))
    assert buckets == [
        datetime(2026, 7, 23, 8, 0),
        datetime(2026, 7, 23, 9, 0),
        datetime(2026, 7, 23, 10, 0),
    ]


def test_floor_hour_truncates():
    assert floor_hour(datetime(2026, 7, 23, 14, 59, 59, 999999)) == datetime(2026, 7, 23, 14, 0)


# --- Aggregation correctness (Doc 15 §9.1) ------------------------------------------------------
async def test_messages_rollup_counts_the_delivery_funnel(db_session, org_fixture):
    db_session.add_all([
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=1), status=MSG_READ),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=2), status=MSG_DELIVERED),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=3), status=MSG_FAILED,
                 error_code="131047"),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await _message_rows(db_session, org_fixture["organization_id"]))[0]
    assert row.accepted_count == 3
    assert row.sent_count == 2      # read + delivered reached the provider
    assert row.delivered_count == 2
    assert row.read_count == 1
    assert row.failed_count == 1


async def test_cost_is_summed_into_micros(db_session, org_fixture):
    db_session.add_all([
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=1), cost=0.0125),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=2), cost=0.0075),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await _message_rows(db_session, org_fixture["organization_id"]))[0]
    assert row.cost_micros == 20_000  # 0.02 of the org currency, exactly


async def test_delivery_latency_stores_components_not_an_average(db_session, org_fixture):
    """Doc 15 §6.2 — the sum and the count are stored; the mean is a read-time division."""
    db_session.add_all([
        _message(
            org_fixture, created_at=BUCKET + timedelta(minutes=1),
            sent_at=BUCKET + timedelta(minutes=1), delivered_at=BUCKET + timedelta(minutes=1, seconds=2),
        ),
        _message(
            org_fixture, created_at=BUCKET + timedelta(minutes=2),
            sent_at=BUCKET + timedelta(minutes=2), delivered_at=BUCKET + timedelta(minutes=2, seconds=4),
        ),
        # No delivery receipt yet — must not contribute to the denominator.
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=3),
                 sent_at=BUCKET + timedelta(minutes=3)),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await _message_rows(db_session, org_fixture["organization_id"]))[0]
    assert row.delivery_latency_ms_sum == 6000
    assert row.delivery_latency_count == 2  # the undelivered message is excluded


async def test_failures_group_by_error_code(db_session, org_fixture):
    from app.models.analytics import AnalyticsFailureRollup

    db_session.add_all([
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=1), status=MSG_FAILED,
                 error_code="131047"),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=2), status=MSG_FAILED,
                 error_code="131047"),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=3), status=MSG_FAILED,
                 error_code="470"),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    rows = (await db_session.scalars(
        select(AnalyticsFailureRollup).order_by(AnalyticsFailureRollup.error_code)
    )).all()
    assert {(r.error_code, r.failure_count) for r in rows} == {("131047", 2), ("470", 1)}


async def test_directions_are_separate_dimension_rows(db_session, org_fixture):
    db_session.add_all([
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=1),
                 direction=DIRECTION_OUTBOUND),
        _message(org_fixture, created_at=BUCKET + timedelta(minutes=2),
                 direction=DIRECTION_INBOUND),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    rows = await _message_rows(db_session, org_fixture["organization_id"])
    assert {r.direction for r in rows} == {DIRECTION_INBOUND, DIRECTION_OUTBOUND}
    assert all(r.accepted_count == 1 for r in rows)


# --- Idempotency & bucket replacement (Doc 15 §6.3) ---------------------------------------------
async def test_running_twice_is_identical(db_session, org_fixture):
    """The core guarantee: a re-run converges rather than double-counting."""
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=1)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)
    first = [(r.bucket_start, r.direction, r.accepted_count)
             for r in await _message_rows(db_session, org_fixture["organization_id"])]

    await _rollup(db_session, org_fixture)
    second = [(r.bucket_start, r.direction, r.accepted_count)
              for r in await _message_rows(db_session, org_fixture["organization_id"])]

    assert first == second
    assert len(second) == 1  # not duplicated


async def test_overlapping_runs_never_double_count(db_session, org_fixture):
    """Deterministic re-derivation is the concurrency strategy (Doc 15 §7) — no lock."""
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=1)))
    await db_session.commit()

    for _ in range(3):  # three overlapping passes over the same window
        await _rollup(db_session, org_fixture)

    rows = await _message_rows(db_session, org_fixture["organization_id"])
    assert len(rows) == 1
    assert rows[0].accepted_count == 1


async def test_bucket_replacement_removes_a_vanished_dimension(db_session, org_fixture):
    """Why the design rejects UPSERT: a stale dimension row must not survive (§6.3)."""
    message = _message(org_fixture, created_at=BUCKET + timedelta(minutes=1),
                       direction=DIRECTION_INBOUND)
    db_session.add(message)
    await db_session.commit()
    await _rollup(db_session, org_fixture)
    assert len(await _message_rows(db_session, org_fixture["organization_id"])) == 1

    # The source row is corrected — the inbound dimension no longer exists in this bucket.
    await db_session.delete(message)
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    assert await _message_rows(db_session, org_fixture["organization_id"]) == []


async def test_recomputation_reflects_corrected_source_data(db_session, org_fixture):
    message = _message(org_fixture, created_at=BUCKET + timedelta(minutes=1), status=MSG_DELIVERED)
    db_session.add(message)
    await db_session.commit()
    await _rollup(db_session, org_fixture)

    message.status = MSG_READ
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await _message_rows(db_session, org_fixture["organization_id"]))[0]
    assert row.read_count == 1


# --- Late data & the trailing window (Doc 15 §8.2) ----------------------------------------------
async def test_trailing_window_absorbs_late_arriving_data(db_session, org_fixture):
    """A receipt for a 12:59 send arriving at 13:05 lands in a bucket the next run recomputes."""
    await _rollup(db_session, org_fixture)  # window is empty at first
    assert await _message_rows(db_session, org_fixture["organization_id"]) == []

    # The row appears *after* the first run, backdated into an already-computed bucket.
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=59)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    rows = await _message_rows(db_session, org_fixture["organization_id"])
    assert len(rows) == 1 and rows[0].accepted_count == 1


async def test_data_outside_the_window_is_not_rolled_up(db_session, org_fixture):
    stale = datetime(2026, 7, 23, 2, 0)  # older than the 6h trailing window
    db_session.add(_message(org_fixture, created_at=stale + timedelta(minutes=5)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    assert await _message_rows(db_session, org_fixture["organization_id"]) == []


async def test_backfill_reaches_an_arbitrary_range(db_session, org_fixture):
    old_bucket = datetime(2026, 7, 20, 9, 0)
    db_session.add(_message(org_fixture, created_at=old_bucket + timedelta(minutes=5)))
    await db_session.commit()

    await AnalyticsRollupService(db_session).run_backfill(
        start=old_bucket,
        end=old_bucket + timedelta(hours=1),
        organization_id=org_fixture["organization_id"],
    )

    rows = await _message_rows(db_session, org_fixture["organization_id"])
    assert len(rows) == 1 and rows[0].bucket_start == old_bucket


# --- Watermarks (Doc 15 §9.7, §23) --------------------------------------------------------------
async def test_watermark_advances_to_the_last_closed_bucket(db_session, org_fixture):
    await _rollup(db_session, org_fixture)

    run = (await db_session.scalars(
        select(AnalyticsRollupRun).where(AnalyticsRollupRun.kind == KIND_MESSAGES)
    )).first()
    assert run is not None
    assert run.last_status == RUN_OK
    assert run.watermark_at == datetime(2026, 7, 23, 13, 0)  # last complete hour
    assert run.last_run_at is not None


async def test_watermark_never_moves_backwards(db_session, org_fixture):
    """A backfill of old data must not make the dashboard claim it is staler than it is."""
    await _rollup(db_session, org_fixture)
    ahead = (await db_session.scalars(
        select(AnalyticsRollupRun).where(AnalyticsRollupRun.kind == KIND_MESSAGES)
    )).first().watermark_at

    old = datetime(2026, 7, 20, 9, 0)
    await AnalyticsRollupService(db_session).run_backfill(
        start=old, end=old + timedelta(hours=1),
        organization_id=org_fixture["organization_id"],
    )

    run = (await db_session.scalars(
        select(AnalyticsRollupRun).where(AnalyticsRollupRun.kind == KIND_MESSAGES)
    )).first()
    await db_session.refresh(run)
    assert run.watermark_at == ahead


async def test_a_watermark_row_exists_per_kind(db_session, org_fixture):
    await _rollup(db_session, org_fixture)

    kinds = (await db_session.scalars(select(AnalyticsRollupRun.kind))).all()
    assert set(kinds) == {
        "messages", "failures", "campaigns", "conversations", "tasks", "contacts"
    }


async def test_selected_kinds_only_touch_their_own_watermarks(db_session, org_fixture):
    await _rollup(db_session, org_fixture, kinds=[KIND_MESSAGES])

    kinds = (await db_session.scalars(select(AnalyticsRollupRun.kind))).all()
    assert set(kinds) == {KIND_MESSAGES}


# --- Task metrics (Doc 15 §9.5, Doc 14 §12) -----------------------------------------------------
async def test_task_rollup_reads_the_immutable_history(db_session, org_fixture, make_user):
    agent = (await make_user(email="agent@vi.test", roles=("agent",))).user
    task = Task(
        organization_id=org_fixture["organization_id"],
        contact_id=org_fixture["contact_id"],
        assigned_agent_id=agent.id,
        title="Collect Aadhaar",
        task_type="collect_documents",
        status="completed",
        priority="high",
        due_at=BUCKET + timedelta(hours=2),
        completed_at=BUCKET + timedelta(minutes=30),
        created_at=BUCKET,
    )
    db_session.add(task)
    await db_session.flush()
    db_session.add_all([
        TaskEvent(organization_id=org_fixture["organization_id"], task_id=task.id,
                  event_type=TASK_EVENT_CREATED, created_at=BUCKET + timedelta(minutes=1)),
        TaskEvent(organization_id=org_fixture["organization_id"], task_id=task.id,
                  event_type=TASK_EVENT_COMPLETED, created_at=BUCKET + timedelta(minutes=30)),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await db_session.scalars(select(AnalyticsTaskRollup))).first()
    assert row is not None
    assert row.created_count == 1
    assert row.completed_count == 1
    assert row.completed_on_time_count == 1  # completed 90 min before due
    assert row.time_to_complete_count == 1
    assert row.time_to_complete_seconds_sum == 1800


async def test_late_completion_is_not_counted_on_time(db_session, org_fixture, make_user):
    agent = (await make_user(email="agent@vi.test", roles=("agent",))).user
    task = Task(
        organization_id=org_fixture["organization_id"],
        contact_id=org_fixture["contact_id"],
        assigned_agent_id=agent.id,
        title="Late",
        task_type="call",
        status="completed",
        priority="medium",
        due_at=BUCKET - timedelta(hours=1),          # was due before the bucket
        completed_at=BUCKET + timedelta(minutes=10),  # completed inside it
        created_at=BUCKET - timedelta(hours=2),
    )
    db_session.add(task)
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await db_session.scalars(select(AnalyticsTaskRollup))).first()
    assert row.completed_on_time_count == 0


# --- Customer metrics (Doc 15 §9.6) -------------------------------------------------------------
async def test_contact_rollup_counts_growth_and_activity(db_session, org_fixture):
    db_session.add(Contact(
        organization_id=org_fixture["organization_id"],
        wa_id="919990000002", phone_e164="+919990000002",
        created_at=BUCKET + timedelta(minutes=5),
    ))
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=6)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    row = (await db_session.scalars(select(AnalyticsContactRollup))).first()
    assert row is not None
    assert row.created_count == 1
    assert row.active_count == 1  # one distinct contact messaged this hour


async def test_an_empty_hour_writes_no_contact_row(db_session, org_fixture):
    """Densification is the read layer's job (Doc 15 §10) — the writer stores no zero rows."""
    await _rollup(db_session, org_fixture)
    assert (await db_session.scalars(select(AnalyticsContactRollup))).all() == []


# --- Daily consolidation (Doc 15 §21.4) ---------------------------------------------------------
async def test_a_day_is_the_sum_of_its_hours(db_session, org_fixture):
    """Additivity (§6.2) is what makes consolidation a pure re-sum, never a re-read of sources."""
    db_session.add_all([
        _message(org_fixture, created_at=datetime(2026, 7, 23, 9, 30)),
        _message(org_fixture, created_at=datetime(2026, 7, 23, 10, 30)),
        _message(org_fixture, created_at=datetime(2026, 7, 23, 11, 30)),
    ])
    await db_session.commit()

    service = AnalyticsRollupService(db_session)
    start, end = window_for(NOW, 6)
    await service.rollup_organization(org_fixture["organization_id"], start, end)
    await service.consolidate_days(org_fixture["organization_id"], start, end)

    hourly = await _message_rows(db_session, org_fixture["organization_id"], GRAIN_HOUR)
    daily = await _message_rows(db_session, org_fixture["organization_id"], GRAIN_DAY)
    assert len(hourly) == 3
    assert len(daily) == 1
    assert daily[0].accepted_count == sum(r.accepted_count for r in hourly)


async def test_consolidation_is_idempotent(db_session, org_fixture):
    db_session.add(_message(org_fixture, created_at=datetime(2026, 7, 23, 9, 30)))
    await db_session.commit()

    service = AnalyticsRollupService(db_session)
    start, end = window_for(NOW, 6)
    await service.rollup_organization(org_fixture["organization_id"], start, end)
    for _ in range(2):
        await service.consolidate_days(org_fixture["organization_id"], start, end)

    daily = await _message_rows(db_session, org_fixture["organization_id"], GRAIN_DAY)
    assert len(daily) == 1 and daily[0].accepted_count == 1


# --- Retention (Doc 15 §21.3) -------------------------------------------------------------------
async def test_prune_drops_only_rows_past_retention(db_session, org_fixture):
    service = AnalyticsRollupService(db_session)
    recent = floor_hour(NOW) - timedelta(days=1)
    ancient = floor_hour(NOW) - timedelta(days=120)
    db_session.add_all([
        AnalyticsMessageRollup(
            organization_id=org_fixture["organization_id"], grain=GRAIN_HOUR,
            bucket_start=recent, direction=DIRECTION_OUTBOUND, message_type="text",
            accepted_count=1,
        ),
        AnalyticsMessageRollup(
            organization_id=org_fixture["organization_id"], grain=GRAIN_HOUR,
            bucket_start=ancient, direction=DIRECTION_OUTBOUND, message_type="text",
            accepted_count=1,
        ),
    ])
    await db_session.commit()

    removed = await service.prune(now=NOW)

    remaining = await _message_rows(db_session, org_fixture["organization_id"])
    assert removed == 1
    assert [r.bucket_start for r in remaining] == [recent]


# --- Organization isolation ---------------------------------------------------------------------
async def test_organizations_never_see_each_other(db_session, org_fixture, session_factory):
    other = Organization(name="Other Co", slug="other-co")
    db_session.add(other)
    await db_session.flush()
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=1)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)
    await AnalyticsRollupService(db_session).rollup_organization(
        other.id, *window_for(NOW, 6)
    )

    mine = await _message_rows(db_session, org_fixture["organization_id"])
    theirs = await _message_rows(db_session, other.id)
    assert len(mine) == 1
    assert theirs == []


async def test_rollup_all_orgs_covers_every_organization(db_session, org_fixture):
    other = Organization(name="Other Co", slug="other-co")
    db_session.add(other)
    await db_session.commit()

    await AnalyticsRollupService(db_session).run_incremental(now=NOW)

    orgs = (await db_session.scalars(
        select(AnalyticsRollupRun.organization_id).distinct()
    )).all()
    assert set(orgs) == {org_fixture["organization_id"], other.id}


# --- Outcome reporting --------------------------------------------------------------------------
async def test_outcome_reports_what_the_run_did(db_session, org_fixture):
    db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=1)))
    await db_session.commit()

    outcome = await _rollup(db_session, org_fixture)

    assert outcome.organization_id == org_fixture["organization_id"]
    assert outcome.buckets == 6
    assert outcome.rows_written >= 1
    assert outcome.window_end == datetime(2026, 7, 23, 14, 0)


async def test_rows_are_scoped_to_their_bucket(db_session, org_fixture):
    db_session.add_all([
        _message(org_fixture, created_at=datetime(2026, 7, 23, 9, 30)),
        _message(org_fixture, created_at=datetime(2026, 7, 23, 12, 30)),
    ])
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    rows = await _message_rows(db_session, org_fixture["organization_id"])
    assert [r.bucket_start for r in rows] == [
        datetime(2026, 7, 23, 9, 0),
        datetime(2026, 7, 23, 12, 0),
    ]
    assert all(r.accepted_count == 1 for r in rows)


async def test_total_rows_equal_source_rows(db_session, org_fixture):
    """A sanity net: nothing is invented and nothing is lost across the window."""
    for minute in (5, 15, 25):
        db_session.add(_message(org_fixture, created_at=BUCKET + timedelta(minutes=minute)))
    await db_session.commit()

    await _rollup(db_session, org_fixture)

    total = await db_session.scalar(
        select(func.sum(AnalyticsMessageRollup.accepted_count)).where(
            AnalyticsMessageRollup.organization_id == org_fixture["organization_id"],
            AnalyticsMessageRollup.grain == GRAIN_HOUR,
        )
    )
    assert total == 3
