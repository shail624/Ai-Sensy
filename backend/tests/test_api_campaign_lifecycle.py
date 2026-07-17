"""Campaign lifecycle tests (Doc 04 §17, Doc 03 §8.4; FR-CAM-06/07/08) — Phase 6 Step 3.

No network and no broker: Meta is an ``httpx.MockTransport``, and the lanes are driven directly.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.db.mixins import utcnow
from app.models.campaign import (
    CAMPAIGN_CANCELLED,
    CAMPAIGN_PAUSED,
    CAMPAIGN_RUNNING,
    RECIPIENT_CANCELLED,
    RECIPIENT_FAILED,
    RECIPIENT_PENDING,
    RECIPIENT_SENT,
    RETRY_EXHAUSTED,
    RETRY_PENDING,
    RETRY_SUCCEEDED,
    Campaign,
    CampaignRecipient,
    CampaignRetry,
)
from app.models.message import Message
from app.services.campaign_dispatch_service import CampaignDispatchService
from tests.test_api_campaign_dispatch import _approved_campaign, _run
from tests.test_api_campaigns import CAMPAIGNS_URL
from tests.test_api_conversations import _rows


@pytest.fixture
def tasks(monkeypatch) -> dict[str, list]:
    """Capture the broker hand-offs the lifecycle triggers."""
    import app.crm.campaign_tasks as campaign_tasks

    calls: dict[str, list] = {"dispatch": [], "retry": []}
    monkeypatch.setattr(
        campaign_tasks.dispatch_campaign, "apply_async", lambda args: calls["dispatch"].append(args[0])
    )
    monkeypatch.setattr(
        campaign_tasks.retry_campaign_recipient,
        "apply_async",
        lambda args: calls["retry"].append(args[0]),
    )
    return calls


async def _started(client, make_user, session_factory, monkeypatch) -> tuple[dict, dict, int]:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        await CampaignDispatchService(session).plan(campaign.id)
    return headers, created, campaign.id


# --- Pause & resume (FR-CAM-06) ----------------------------------------------
async def test_pause_stops_sends_that_were_already_fanned_out(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    """Pausing is not a race against the queue: the tasks arrive and decline."""
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == CAMPAIGN_PAUSED

    # The tasks were already out; every one of them declines to send.
    for recipient_pk in fan["recipients"]:
        async with session_factory() as session:
            result = await CampaignDispatchService(session).send_recipient(recipient_pk)
        assert result["status"] == "halted"
    assert [r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")] == []
    assert all(r.status == RECIPIENT_PENDING for r in await _rows(session_factory, CampaignRecipient))


async def test_resume_sends_only_what_is_still_owed(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    """Half went out, then a pause; resuming must not message anyone a second time."""
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        await CampaignDispatchService(session).send_recipient(fan["recipients"][0])

    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause", headers=headers)
    resume = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/resume", headers=headers)
    assert resume.status_code == 200 and resume.json()["status"] == CAMPAIGN_RUNNING
    # Resume re-dispatches rather than re-sending.
    assert tasks["dispatch"][-1] == campaign_pk

    await _run(session_factory, campaign_pk)
    sends = [r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")]
    assert len(sends) == 3
    assert len([m for m in await _rows(session_factory, Message) if m.direction == "outbound"]) == 3


async def test_pause_and_resume_reject_the_wrong_state(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)

    # Running: cannot resume.
    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/resume", headers=headers)
    assert resp.status_code == 409 and resp.json()["code"] == "campaign_state"

    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause", headers=headers)
    # Paused: cannot pause again.
    assert (
        await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause", headers=headers)
    ).status_code == 409


# --- Cancel (FR-CAM-07) ------------------------------------------------------
async def test_cancel_stops_pending_sends_and_drops_retries(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == CAMPAIGN_CANCELLED

    # Cancelled, not failed: nothing went wrong with them — they are what the operator stopped.
    recipients = await _rows(session_factory, CampaignRecipient)
    assert all(r.status == RECIPIENT_CANCELLED for r in recipients)

    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    for batch_pk in plan["batches"]:
        async with session_factory() as session:
            fan = await CampaignDispatchService(session).fan_out(batch_pk)
        assert fan["recipients"] == []
    assert [r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")] == []


async def test_cancel_leaves_what_already_went_out_alone(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    """A message handed to Meta cannot be unsent, and the ledger must not pretend otherwise."""
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        await CampaignDispatchService(session).send_recipient(fan["recipients"][0])

    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)
    recipients = await _rows(session_factory, CampaignRecipient)
    assert len([r for r in recipients if r.status == RECIPIENT_SENT]) == 1
    assert len([r for r in recipients if r.status == RECIPIENT_CANCELLED]) == 2


async def test_a_completed_campaign_cannot_be_cancelled(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    await _run(session_factory, campaign_pk)
    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)
    assert resp.status_code == 409, resp.text


# --- Smart retry (FR-CAM-08) -------------------------------------------------
async def test_a_retryable_failure_is_scheduled_with_the_engines_backoff(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    """The retry engine classifies and times it; this only records what it decided."""
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    # 131048 is a Meta throttle code in the platform's own error map.
    campaign_channel["handler"] = lambda request: (
        httpx.Response(400, json={"error": {"message": "spam rate limit", "code": 131048}})
        if request.url.path.endswith("/messages")
        else httpx.Response(200, json={})
    )

    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        result = await CampaignDispatchService(session).send_recipient(fan["recipients"][0])

    assert result["status"] == RETRY_PENDING
    (retry,) = await _rows(session_factory, CampaignRetry)
    assert retry.status == RETRY_PENDING and retry.attempt == 1
    assert retry.error_code == "131048"
    # Scheduled forward, by the engine's curve rather than a number invented here.
    assert retry.next_attempt_at > utcnow()
    # The recipient still owes a send; it is not failed.
    (recipient,) = [r for r in await _rows(session_factory, CampaignRecipient) if r.id == fan["recipients"][0]]
    assert recipient.status != RECIPIENT_FAILED and recipient.retry_count == 1


async def test_a_terminal_failure_never_enters_the_retry_queue(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    """131026 is "not a WhatsApp user": asking again cannot change the answer."""
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    campaign_channel["handler"] = lambda request: (
        httpx.Response(400, json={"error": {"message": "not a WhatsApp user", "code": 131026}})
        if request.url.path.endswith("/messages")
        else httpx.Response(200, json={})
    )

    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        result = await CampaignDispatchService(session).send_recipient(fan["recipients"][0])

    assert result["status"] == RECIPIENT_FAILED
    assert await _rows(session_factory, CampaignRetry) == []
    (recipient,) = [r for r in await _rows(session_factory, CampaignRecipient) if r.id == fan["recipients"][0]]
    assert recipient.status == RECIPIENT_FAILED and recipient.error_code == "131026"


async def test_the_scanner_only_claims_what_is_due(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    from app.services.campaign_retry_service import CampaignRetryService

    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        session.add_all(
            [
                CampaignRetry(
                    campaign_id=campaign_pk,
                    recipient_id=1,
                    attempt=1,
                    next_attempt_at=utcnow() - timedelta(seconds=1),
                ),
                CampaignRetry(
                    campaign_id=campaign_pk,
                    recipient_id=2,
                    attempt=1,
                    next_attempt_at=utcnow() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        due = await CampaignRetryService(session).due(limit=10)
    # The one still inside its backoff is left alone.
    assert [r.recipient_id for r in due] == [1]


async def test_a_successful_retry_closes_its_row(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    campaign_channel["handler"] = lambda request: (
        httpx.Response(400, json={"error": {"message": "spam rate limit", "code": 131048}})
        if request.url.path.endswith("/messages")
        else httpx.Response(200, json={})
    )
    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        await CampaignDispatchService(session).send_recipient(fan["recipients"][0])
    assert (await _rows(session_factory, CampaignRetry))[0].status == RETRY_PENDING

    # Meta recovers; the re-attempt goes through the same send path.
    campaign_channel["handler"] = None
    async with session_factory() as session:
        result = await CampaignDispatchService(session).send_recipient(fan["recipients"][0])
    assert result["status"] == RECIPIENT_SENT
    assert (await _rows(session_factory, CampaignRetry))[0].status == RETRY_SUCCEEDED


async def test_cancelling_drops_pending_retries(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        session.add(
            CampaignRetry(
                campaign_id=campaign_pk,
                recipient_id=1,
                attempt=1,
                next_attempt_at=utcnow() - timedelta(seconds=1),
            )
        )
        await session.commit()

    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)
    assert (await _rows(session_factory, CampaignRetry))[0].status == RETRY_EXHAUSTED


# --- Manual retry (Doc 04 §17) -----------------------------------------------
async def test_manual_retry_resets_failed_recipients_and_redispatches(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    campaign_channel["handler"] = lambda request: (
        httpx.Response(400, json={"error": {"message": "not a WhatsApp user", "code": 131026}})
        if request.url.path.endswith("/messages")
        else httpx.Response(200, json={})
    )
    await _run(session_factory, campaign_pk)
    assert all(r.status == RECIPIENT_FAILED for r in await _rows(session_factory, CampaignRecipient))

    campaign_channel["handler"] = None
    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/retry", headers=headers)
    assert resp.status_code == 202, resp.text
    assert resp.json()["retried"] == 3 and resp.json()["status"] == CAMPAIGN_RUNNING

    rows = await _rows(session_factory, CampaignRecipient)
    # Reset to owing a send, with the failure cleared and the old message abandoned.
    assert all(r.status == RECIPIENT_PENDING and r.error_code is None for r in rows)
    assert all(r.message_id is None and r.batch_id is None for r in rows)

    await _run(session_factory, campaign_pk)
    assert all(r.status == RECIPIENT_SENT for r in await _rows(session_factory, CampaignRecipient))


async def test_retry_with_nothing_failed_is_a_conflict(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    await _run(session_factory, campaign_pk)
    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/retry", headers=headers)
    assert resp.status_code == 409 and "no failed recipients" in resp.json()["detail"]


async def test_a_cancelled_campaign_cannot_be_retried(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)
    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/retry", headers=headers)
    assert resp.status_code == 409, resp.text


# --- Audit, queue wiring & permissions ---------------------------------------
async def test_every_transition_is_audited(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause", headers=headers)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/resume", headers=headers)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/cancel", headers=headers)

    for action in ("campaign.paused", "campaign.resumed", "campaign.cancelled"):
        entries = await client.get(f"/api/v1/audit-logs?filter[action][eq]={action}", headers=headers)
        assert len(entries.json()["data"]) == 1, action


def test_retry_tasks_are_bound_to_the_retry_lane() -> None:
    import app.crm.campaign_tasks as campaign_tasks

    assert campaign_tasks.scan_campaign_retries.queue_name == "sends.retry"
    assert campaign_tasks.retry_campaign_recipient.queue_name == "sends.retry"


def test_the_scanner_hands_due_retries_to_the_send_lane(monkeypatch) -> None:
    import app.crm.campaign_tasks as campaign_tasks

    queued: list[list[int]] = []
    monkeypatch.setattr(
        campaign_tasks.retry_campaign_recipient, "apply_async", lambda args: queued.append(args)
    )

    async def _due(limit: int):
        return [4, 5]

    monkeypatch.setattr(campaign_tasks, "_due_retries", _due)
    assert campaign_tasks.scan_campaign_retries.run()["claimed"] == 2
    assert queued == [[4], [5]]


async def test_lifecycle_permissions(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    from tests.test_api_messages import _headers

    headers, created, campaign_pk = await _started(client, make_user, session_factory, monkeypatch)
    # A manager runs campaigns; an analyst reads them.
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    for action in ("pause", "resume", "cancel", "retry"):
        resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/{action}", headers=analyst)
        assert resp.status_code == 403, action
    assert (await client.post(f"{CAMPAIGNS_URL}/{created['id']}/pause")).status_code == 401


async def test_unknown_campaign_is_404(
    client, make_user, session_factory, monkeypatch, campaign_channel, tasks
) -> None:
    headers, _, _ = await _started(client, make_user, session_factory, monkeypatch)
    for action in ("pause", "resume", "cancel", "retry"):
        resp = await client.post(f"{CAMPAIGNS_URL}/{uuid.uuid4()}/{action}", headers=headers)
        assert resp.status_code == 404, action


def test_lifecycle_never_restates_the_retry_engines_judgement() -> None:
    """The classification and the curve must come from one place (Doc 06 §6)."""
    import inspect

    from app.services import campaign_retry_service

    source = inspect.getsource(campaign_retry_service)
    assert "from app.queue.retry import backoff_seconds, classify, should_retry" in source
    # No local backoff maths, no local retryable/terminal table.
    assert "2 **" not in source and "FailureClass." not in source
