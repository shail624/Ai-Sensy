"""Campaign dispatch tests (Doc 04 §17, Doc 06 §2.3; FR-CAM-05/09/10) — Phase 6 Step 2.

No network and no broker: Meta is an ``httpx.MockTransport`` behind the adapter, and the control
lane's fan-out is driven directly.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.campaign import (
    BATCH_DONE,
    BATCH_PENDING,
    CAMPAIGN_COMPLETED,
    CAMPAIGN_QUEUED,
    CAMPAIGN_RUNNING,
    RECIPIENT_FAILED,
    RECIPIENT_SENT,
    Campaign,
    CampaignBatch,
    CampaignRecipient,
)
from app.models.contact import OPT_IN_OPTED_OUT, Contact
from app.models.message import Message
from app.models.template import TPL_PAUSED, MessageTemplate
from app.services.campaign_dispatch_service import CampaignDispatchService
from tests.test_api_campaigns import CAMPAIGNS_URL, _body, _setup
from tests.test_api_conversations import _rows


@pytest.fixture
def dispatched_tasks(monkeypatch) -> dict[str, list]:
    """Capture what each lane hands to the broker."""
    import app.crm.campaign_tasks as tasks

    calls: dict[str, list] = {"campaign": [], "batch": [], "recipient": []}
    monkeypatch.setattr(
        tasks.dispatch_campaign, "apply_async", lambda args: calls["campaign"].append(args[0])
    )
    monkeypatch.setattr(
        tasks.dispatch_campaign_batch, "apply_async", lambda args: calls["batch"].append(args[0])
    )
    monkeypatch.setattr(
        tasks.send_campaign_recipient, "apply_async", lambda args: calls["recipient"].append(args[0])
    )
    return calls


async def _approved_campaign(client, make_user, session_factory, monkeypatch) -> tuple[dict, dict]:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    return headers, created


async def _run(session_factory, campaign_pk: int) -> None:
    """Drive the control lane by hand: plan → fan out → send each recipient."""
    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign_pk)
    for batch_pk in plan["batches"]:
        async with session_factory() as session:
            fan = await CampaignDispatchService(session).fan_out(batch_pk)
        for recipient_pk in fan["recipients"]:
            async with session_factory() as session:
                await CampaignDispatchService(session).send_recipient(recipient_pk)


# --- Accept (Doc 04 §17 — 202) -----------------------------------------------
async def test_dispatch_accepts_and_queues_without_sending(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == CAMPAIGN_QUEUED and body["total_recipients"] == 3
    assert body["progress_url"].endswith(f"/campaigns/{created['id']}/progress")

    # Nothing reached Meta on the request path, and the control lane has the work.
    assert campaign_channel["requests"] == []
    assert len(dispatched_tasks["campaign"]) == 1
    assert await _rows(session_factory, Message) == []


async def test_dispatch_is_audited_once_not_per_message(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    """A campaign is one operator decision; its messages are data, not decisions."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
    await _run(session_factory, campaign.id)

    dispatch = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=campaign.dispatched", headers=headers
    )
    assert len(dispatch.json()["data"]) == 1
    # Three messages went out; the audit trail is not three rows longer for it.
    per_message = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=message.sent", headers=headers
    )
    assert per_message.json()["data"] == []


# --- Validation before dispatch (FR-CAM-02/05) -------------------------------
async def test_a_paused_template_stops_the_dispatch(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    """Re-checked here, not just at create: Meta may have paused it since the draft was written."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (template,) = list((await session.scalars(select(MessageTemplate))).all())
        template.status = TPL_PAUSED
        await session.commit()

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "campaign_not_dispatchable"
    assert dispatched_tasks["campaign"] == []


async def test_an_empty_campaign_cannot_be_dispatched(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    async with session_factory() as session:
        rows = list((await session.scalars(select(Contact))).all())
        for row in rows:
            row.opt_in_status = OPT_IN_OPTED_OUT
        await session.commit()
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    assert created["total_recipients"] == 0

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    assert resp.status_code == 409 and "no recipients" in resp.json()["detail"]


async def test_a_running_campaign_cannot_be_dispatched_again(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        campaign.status = CAMPAIGN_RUNNING
        await session.commit()

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
    assert resp.status_code == 409, resp.text


# --- Batching & checkpoints (FR-CAM-09) --------------------------------------
async def test_planning_batches_the_roster_and_marks_it_running(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        result = await CampaignDispatchService(session).plan(campaign.id)

    assert result["status"] == CAMPAIGN_RUNNING
    (batch,) = await _rows(session_factory, CampaignBatch)
    assert batch.batch_index == 0 and batch.size == 3 and batch.status == BATCH_PENDING
    # Every recipient carries its checkpoint, which is what makes a resume able to skip.
    assert all(r.batch_id == batch.id for r in await _rows(session_factory, CampaignRecipient))


async def test_planning_twice_reuses_the_existing_checkpoints(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    """A redelivered control task is a resume, not a restart: renumbering would lose the place."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        first = await CampaignDispatchService(session).plan(campaign.id)
    async with session_factory() as session:
        second = await CampaignDispatchService(session).plan(campaign.id)

    assert first["batches"] == second["batches"]
    assert len(await _rows(session_factory, CampaignBatch)) == 1


async def test_batches_close_only_when_their_work_is_done(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        plan = await CampaignDispatchService(session).plan(campaign.id)
    batch_pk = plan["batches"][0]

    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(batch_pk)
    # Fan-out is not completion: the batch is in progress, not done.
    assert (await _rows(session_factory, CampaignBatch))[0].status == "in_progress"

    for recipient_pk in fan["recipients"][:-1]:
        async with session_factory() as session:
            await CampaignDispatchService(session).send_recipient(recipient_pk)
    assert (await _rows(session_factory, CampaignBatch))[0].status == "in_progress"

    async with session_factory() as session:
        await CampaignDispatchService(session).send_recipient(fan["recipients"][-1])
    assert (await _rows(session_factory, CampaignBatch))[0].status == BATCH_DONE


# --- Sending (FR-CAM-05/10) --------------------------------------------------
async def test_dispatch_sends_every_recipient_through_the_ledger(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
    await _run(session_factory, campaign.id)

    recipients = await _rows(session_factory, CampaignRecipient)
    assert all(r.status == RECIPIENT_SENT and r.wamid and r.message_id for r in recipients)

    # A campaign message is an ordinary ledger message that happens to be one of many.
    messages = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"]
    assert len(messages) == 3
    assert all(m.campaign_id == campaign.id for m in messages)
    assert all(m.message_type == "template" and m.category == "utility" for m in messages)
    # Rendered per recipient from the variables materialized at create time.
    bodies = {m.content_json["template"]["body"][0] for m in messages}
    assert bodies == {"Contact 0", "Contact 1", "Contact 2"}


async def test_progress_is_derived_from_the_roster(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())

    before = (await client.get(f"{CAMPAIGNS_URL}/{created['id']}/progress", headers=headers)).json()
    assert before["total"] == 3 and before["pending"] == 3 and before["sent"] == 0

    await _run(session_factory, campaign.id)
    after = (await client.get(f"{CAMPAIGNS_URL}/{created['id']}/progress", headers=headers)).json()
    assert after["sent"] == 3 and after["pending"] == 0 and after["failed"] == 0
    assert after["batches_total"] == 1 and after["batches_done"] == 1
    # Nothing is outstanding, so the campaign closed itself.
    assert after["status"] == CAMPAIGN_COMPLETED

    # The denormalized counters mirror the roster they were computed from (Doc 03 §8.1).
    listing = (await client.get(f"{CAMPAIGNS_URL}/{created['id']}", headers=headers)).json()
    assert listing["sent_count"] == 3 and listing["status"] == CAMPAIGN_COMPLETED


# --- Idempotency & resume (FR-CAM-09) ----------------------------------------
async def test_a_redelivered_send_does_not_message_anyone_twice(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
    await _run(session_factory, campaign.id)
    sends = len([r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")])

    # At-least-once delivery: the whole campaign's tasks arrive again.
    await _run(session_factory, campaign.id)
    assert len([r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")]) == sends
    assert len([m for m in await _rows(session_factory, Message) if m.direction == "outbound"]) == 3


async def test_a_resumed_campaign_only_sends_what_it_still_owes(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    """The crash case: half the roster went out, the worker died, the task comes back."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        plan = await CampaignDispatchService(session).plan(campaign.id)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])

    async with session_factory() as session:
        await CampaignDispatchService(session).send_recipient(fan["recipients"][0])
    sends_before = len([r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")])
    assert sends_before == 1

    # … and now the restart re-derives what is owed from the database.
    await _run(session_factory, campaign.id)
    sends_after = len([r for r in campaign_channel["requests"] if r.url.path.endswith("/messages")])
    assert sends_after == 3  # the two that were owed, and not the one already sent
    assert len([m for m in await _rows(session_factory, Message) if m.direction == "outbound"]) == 3


async def test_a_settled_recipient_is_left_alone(session_factory, campaign_channel) -> None:
    async with session_factory() as session:
        assert (await CampaignDispatchService(session).send_recipient(9999))["status"] == "missing"


# --- Failure accounting ------------------------------------------------------
async def test_a_rejected_recipient_fails_alone_and_the_batch_carries_on(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    """One opted-out contact must not stop the other two from being messaged."""
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        # Opted out *after* the roster was built — the send path is the last line of defence.
        contact = (await session.scalars(select(Contact))).first()
        contact.opt_in_status = OPT_IN_OPTED_OUT
        await session.commit()

    await _run(session_factory, campaign.id)

    recipients = await _rows(session_factory, CampaignRecipient)
    failed = [r for r in recipients if r.status == RECIPIENT_FAILED]
    assert len(failed) == 1 and failed[0].error_code == "rejected"
    assert "OptedOutError" in failed[0].error_detail
    assert len([r for r in recipients if r.status == RECIPIENT_SENT]) == 2

    progress = (await client.get(f"{CAMPAIGNS_URL}/{created['id']}/progress", headers=headers)).json()
    assert progress["failed"] == 1 and progress["sent"] == 2
    assert progress["status"] == CAMPAIGN_COMPLETED


async def test_a_channel_failure_marks_the_recipient_not_the_campaign(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
    # 131026 is terminal in Meta's own error map: not a WhatsApp user.
    campaign_channel["handler"] = lambda request: (
        httpx.Response(400, json={"error": {"message": "not a WhatsApp user", "code": 131026}})
        if request.url.path.endswith("/messages")
        else httpx.Response(200, json={})
    )

    async with session_factory() as session:
        plan = await CampaignDispatchService(session).plan(campaign.id)
    async with session_factory() as session:
        fan = await CampaignDispatchService(session).fan_out(plan["batches"][0])
    async with session_factory() as session:
        result = await CampaignDispatchService(session).send_recipient(fan["recipients"][0])

    # The failure lands on the recipient, and the retry engine's verdict decides what follows:
    # 131026 is terminal in Meta's error map, so there is nothing to wait for (FR-CAM-08).
    assert result["status"] == RECIPIENT_FAILED
    rows = await _rows(session_factory, CampaignRecipient)
    failed = [r for r in rows if r.id == fan["recipients"][0]][0]
    assert failed.status == RECIPIENT_FAILED and failed.error_code == "131026"
    # The campaign itself is untouched by one bad number.
    async with session_factory() as session:
        (stored,) = list((await session.scalars(select(Campaign))).all())
    assert stored.status == CAMPAIGN_RUNNING


# --- Queue wiring (Doc 06 §2.3) ----------------------------------------------
def test_tasks_are_bound_to_their_documented_lanes() -> None:
    import app.crm.campaign_tasks as tasks

    assert tasks.dispatch_campaign.queue_name == "campaigns.control"
    assert tasks.dispatch_campaign_batch.queue_name == "campaigns.control"
    # Bulk carries the millions and must not starve the priority lane.
    assert tasks.send_campaign_recipient.queue_name == "sends.bulk"


def test_the_control_task_fans_out_one_task_per_batch(monkeypatch) -> None:
    import app.crm.campaign_tasks as tasks

    queued: list[list[int]] = []
    monkeypatch.setattr(tasks.dispatch_campaign_batch, "apply_async", lambda args: queued.append(args))

    async def _planned(campaign_pk: int):
        return {"status": "running", "campaign": campaign_pk, "batches": [7, 8]}

    monkeypatch.setattr(tasks, "_plan", _planned)
    tasks.dispatch_campaign.run(1)
    assert queued == [[7], [8]]


def test_the_batch_task_fans_out_one_send_per_recipient(monkeypatch) -> None:
    import app.crm.campaign_tasks as tasks

    queued: list[list[int]] = []
    monkeypatch.setattr(
        tasks.send_campaign_recipient, "apply_async", lambda args: queued.append(args)
    )

    async def _fanned(batch_pk: int):
        return {"status": "dispatched", "batch": batch_pk, "recipients": [11, 12, 13]}

    monkeypatch.setattr(tasks, "_fan_out", _fanned)
    assert tasks.dispatch_campaign_batch.run(5)["dispatched"] == 3
    assert queued == [[11], [12], [13]]


# --- Permissions -------------------------------------------------------------
async def test_dispatch_requires_the_send_permission(
    client, make_user, session_factory, monkeypatch, dispatched_tasks, campaign_channel
) -> None:
    headers, created = await _approved_campaign(client, make_user, session_factory, monkeypatch)
    from tests.test_api_messages import _headers

    # An analyst reads campaigns; broadcasting to real customers is not theirs.
    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    assert (
        await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=analyst)
    ).status_code == 403
    assert (await client.get(f"{CAMPAIGNS_URL}/{created['id']}/progress", headers=analyst)).status_code == 200
    assert (await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch")).status_code == 401


async def test_unknown_campaign_is_404(
    client, make_user, session_factory, monkeypatch, campaign_channel
) -> None:
    headers, _, _, _ = await _setup(client, make_user, session_factory, monkeypatch)
    assert (
        await client.post(f"{CAMPAIGNS_URL}/{uuid.uuid4()}/dispatch", headers=headers)
    ).status_code == 404
    assert (
        await client.get(f"{CAMPAIGNS_URL}/{uuid.uuid4()}/progress", headers=headers)
    ).status_code == 404
