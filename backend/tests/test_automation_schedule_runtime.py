"""Durable, timezone-aware live Automation schedule contract."""

from __future__ import annotations

import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.automation import tasks as automation_tasks
from app.db.mixins import utcnow
from app.models.automation import (
    AUTOMATION_TRIGGER_RECEIPT_PROCESSED,
    AutomationFlow,
    AutomationRun,
    AutomationTriggerReceipt,
)
from app.models.business_event import BUSINESS_EVENT_AUTOMATION_SCHEDULED, BusinessEvent
from app.models.notification import Notification
from app.models.organization import Organization
from app.services.automation_live_runtime_service import AutomationLiveRuntimeService
from app.services.business_event_service import AutomationReceiptDispatch, BusinessEventService
from tests.test_automation_live_runtime import AUTOMATIONS, _inbound, _owner, _publish


def _schedule_graph(*, effect: str = "notification", delay: bool = False) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "schedule", "schedule_cron": "0 9 * * 1-5"},
        }
    ]
    if delay:
        nodes.append({"id": "delay-1", "kind": "delay", "config": {"seconds": 60}})
    if effect == "notification":
        nodes.append(
            {
                "id": "notification-1",
                "kind": "notification",
                "config": {"message": "Review today's scheduled workspace follow-ups"},
            }
        )
    else:
        nodes.append(
            {
                "id": "task-1",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "Unsupported scheduled task",
                    "task_type": "custom",
                    "priority": "medium",
                    "due_in_minutes": 60,
                },
            }
        )
    return {
        "nodes": nodes,
        "edges": [
            {
                "id": f"edge-{index}",
                "source": nodes[index - 1]["id"],
                "target": node["id"],
            }
            for index, node in enumerate(nodes[1:], start=1)
        ],
    }


async def _published_schedule(client, make_user, session_factory, monkeypatch) -> tuple[dict, dict]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        organization = (await session.scalars(select(Organization))).one()
        organization.timezone = "Asia/Kolkata"
        await session.commit()
    owner = await _owner(client)
    flow = await _publish(client, owner, graph=_schedule_graph())
    return owner, flow


async def test_schedule_slot_projects_once_advances_and_notifies_without_contact(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, published = await _published_schedule(
        client, make_user, session_factory, monkeypatch
    )
    assert published["next_run_at"] is not None

    now = utcnow().replace(second=30, microsecond=0)
    due_at = now - timedelta(minutes=1)
    async with session_factory() as session:
        flow = (
            await session.scalars(
                select(AutomationFlow).where(
                    AutomationFlow.uuid == uuid.UUID(published["id"]).bytes
                )
            )
        ).one()
        flow.next_run_at = due_at
        await session.commit()

    async with session_factory() as session:
        first = await BusinessEventService(session).claim_due_automation_schedules(
            now=now, limit=10
        )
    assert len(first) == 1

    async with session_factory() as session:
        second = await BusinessEventService(session).claim_due_automation_schedules(
            now=now, limit=10
        )
        flow = (
            await session.scalars(
                select(AutomationFlow).where(
                    AutomationFlow.uuid == uuid.UUID(published["id"]).bytes
                )
            )
        ).one()
        events = list(
            (
                await session.scalars(
                    select(BusinessEvent).where(
                        BusinessEvent.event_type == BUSINESS_EVENT_AUTOMATION_SCHEDULED
                    )
                )
            ).all()
        )
        receipts = list((await session.scalars(select(AutomationTriggerReceipt))).all())
    assert second == []
    assert flow.next_run_at is not None and flow.next_run_at > now
    local_next_run = flow.next_run_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(
        ZoneInfo("Asia/Kolkata")
    )
    assert (local_next_run.hour, local_next_run.minute) == (9, 0)
    assert local_next_run.weekday() < 5
    assert len(events) == 1
    assert events[0].contact_id is None
    assert events[0].occurred_at == due_at
    assert events[0].payload_json == {
        "automation_id": published["id"],
        "version_no": 1,
        "scheduled_for": due_at.isoformat(),
        "timezone": "Asia/Kolkata",
    }
    assert len(receipts) == 1
    assert receipts[0].event_uuid == events[0].uuid

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(first[0].receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )
    async with session_factory() as session:
        # Redelivery converges on the same run and workspace-only notification.
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(first[0].receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )
        notification = (await session.scalars(select(Notification))).one()
        run_count = int((await session.scalar(select(func.count()).select_from(AutomationRun))) or 0)
    assert notification.contact_id is None
    assert notification.body == "Review today's scheduled workspace follow-ups"
    assert run_count == 1


async def test_schedule_disable_clears_due_time_and_enable_recomputes_it(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, published = await _published_schedule(
        client, make_user, session_factory, monkeypatch
    )
    disabled = await client.post(
        f"{AUTOMATIONS}/{published['id']}/disable",
        headers=owner,
        json={"expected_row_version": published["row_version"]},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["next_run_at"] is None

    enabled = await client.post(
        f"{AUTOMATIONS}/{published['id']}/enable",
        headers=owner,
        json={"expected_row_version": disabled.json()["row_version"]},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["next_run_at"] is not None

    edited_graph = _schedule_graph()
    edited_graph["nodes"][0]["config"]["schedule_cron"] = "15 10 * * 1-5"
    edited = await client.patch(
        f"{AUTOMATIONS}/{published['id']}",
        headers=owner,
        json={
            "graph": edited_graph,
            "expected_row_version": enabled.json()["row_version"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["has_unpublished_changes"] is True

    now = utcnow()
    async with session_factory() as session:
        flow = (
            await session.scalars(
                select(AutomationFlow).where(
                    AutomationFlow.uuid == uuid.UUID(published["id"]).bytes
                )
            )
        ).one()
        flow.next_run_at = now - timedelta(minutes=1)
        await session.commit()
    async with session_factory() as session:
        assert (
            await BusinessEventService(session).claim_due_automation_schedules(
                now=now, limit=10
            )
            == []
        )

    restored = await client.post(
        f"{AUTOMATIONS}/{published['id']}/versions/1/restore",
        headers=owner,
        json={"expected_row_version": edited.json()["row_version"]},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["has_unpublished_changes"] is False
    assert restored.json()["next_run_at"] is not None


async def test_invalid_cron_is_rejected_and_unsupported_schedule_effect_fails_closed(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _inbound(client, make_user, session_factory, monkeypatch)
    owner = await _owner(client)
    invalid = _schedule_graph()
    invalid["nodes"][0]["config"]["schedule_cron"] = "0 9 *"
    response = await client.post(
        AUTOMATIONS,
        headers=owner,
        json={"name": "Invalid schedule", "graph": invalid},
    )
    assert response.status_code == 422

    assert (
        AutomationLiveRuntimeService._supported_path(
            _schedule_graph(effect="task"), BUSINESS_EVENT_AUTOMATION_SCHEDULED
        )
        is None
    )
    supported = AutomationLiveRuntimeService._supported_path(
        _schedule_graph(delay=True), BUSINESS_EVENT_AUTOMATION_SCHEDULED
    )
    assert supported is not None
    assert [node["kind"] for node in supported[2]] == ["delay", "notification"]


def test_schedule_dispatcher_hands_claimed_slots_to_live_worker(monkeypatch) -> None:
    queued: list[dict[str, object]] = []
    dispatches = [
        AutomationReceiptDispatch(receipt_pk=31, task_id=str(uuid.uuid4())),
        AutomationReceiptDispatch(receipt_pk=47, task_id=str(uuid.uuid4())),
    ]

    def run_without_database(coroutine) -> list[AutomationReceiptDispatch]:
        coroutine.close()
        return dispatches

    monkeypatch.setattr(automation_tasks, "run_async", run_without_database)
    monkeypatch.setattr(
        automation_tasks.consume_automation_trigger_receipt,
        "apply_async",
        lambda **options: queued.append(options),
    )

    assert automation_tasks.dispatch_scheduled_automations.run() == {"claimed": 2}
    assert queued == [
        {"args": [31], "task_id": dispatches[0].task_id},
        {"args": [47], "task_id": dispatches[1].task_id},
    ]
