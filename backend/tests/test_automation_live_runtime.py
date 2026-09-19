"""Automatic inbound governed live-action runtime contract."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.automation import tasks as automation_tasks
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM, AuditLog
from app.models.automation import (
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SKIPPED,
    AUTOMATION_RUN_FAILED,
    AUTOMATION_RUN_RETRYING,
    AUTOMATION_RUN_SUCCEEDED,
    AUTOMATION_TRIGGER_RECEIPT_FAILED,
    AUTOMATION_TRIGGER_RECEIPT_PROCESSED,
    AUTOMATION_TRIGGER_RECEIPT_PROCESSING,
    AUTOMATION_WAIT_MATCHED,
    AUTOMATION_WAIT_TIMED_OUT,
    AUTOMATION_WAIT_WAITING,
    AutomationFlowVersion,
    AutomationRun,
    AutomationStepAttempt,
    AutomationTriggerReceipt,
    AutomationWaitSubscription,
)
from app.models.business_event import (
    BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED,
    BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED,
    BUSINESS_EVENT_LEAD_STAGE_CHANGED,
    BUSINESS_EVENT_MESSAGE_RECEIVED,
    BUSINESS_EVENT_REACTIVATION_TRANSITIONED,
    BUSINESS_EVENT_TASK_COMPLETED,
    BusinessEvent,
)
from app.models.contact import Contact
from app.models.contact_event import (
    EVENT_TAG_ADDED,
    EVENT_TAG_REMOVED,
    EVENT_TASK_CREATED,
    ContactEvent,
)
from app.models.conversation import CONV_OPEN, CONV_PENDING, CONV_RESOLVED, Conversation
from app.models.notification import NOTIFICATION_AUTOMATION_ATTENTION, Notification
from app.models.tag import Tag, contact_tags
from app.models.task import TASK_PRIORITY_HIGH, TASK_STATUS_OPEN, TASK_TYPE_CALL, Task
from app.models.task_event import TASK_EVENT_CREATED, TaskEvent
from app.models.user import User
from app.services.automation_live_runtime_service import AutomationLiveRuntimeService
from app.services.business_event_service import (
    AutomationReceiptDispatch,
    BusinessEventService,
)
from app.services.message_service import MessageService
from app.services.tag_service import TagService
from tests.test_api_conversations import _deliver, _fresh_message, _inbound
from tests.test_api_webhooks import _delivery

PASSWORD = "Sup3r-Secret-Pass1"
AUTOMATIONS = "/api/v1/automations"


def _graph(
    *,
    effect: str | None = "handoff",
    condition: bool = False,
    condition_field: str = "payload.message_type",
    condition_operator: str = "eq",
    condition_value: str = "text",
    tag_id: str | None = None,
    assignment_user_id: str | None = None,
) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "message.received"},
        }
    ]
    edges: list[dict[str, str]] = []
    previous = "trigger-1"
    if condition:
        nodes.append(
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {
                    "field": condition_field,
                    "operator": condition_operator,
                    "value": condition_value,
                },
            }
        )
        edges.append({"id": "edge-1", "source": "trigger-1", "target": "condition-1"})
        previous = "condition-1"
    if effect == "handoff":
        nodes.append(
            {
                "id": "handoff-1",
                "kind": "handoff",
                "config": {"reason": "Route inbound customer to support"},
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "handoff-1"})
    elif effect == "task":
        nodes.append(
            {
                "id": "task-1",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "Call inbound customer",
                    "task_type": "call",
                    "priority": "high",
                    "due_in_minutes": 90,
                },
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "task-1"})
    elif effect == "tag":
        assert tag_id is not None
        nodes.append(
            {
                "id": "tag-1",
                "kind": "tag",
                "config": {"tag_id": tag_id},
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "tag-1"})
    elif effect == "remove_tag":
        assert tag_id is not None
        nodes.append(
            {
                "id": "remove-tag-1",
                "kind": "remove_tag",
                "config": {"tag_id": tag_id},
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "remove-tag-1"})
    elif effect == "assignment":
        nodes.append(
            {
                "id": "assignment-1",
                "kind": "assignment",
                "config": (
                    {"mode": "user", "user_id": assignment_user_id}
                    if assignment_user_id is not None
                    else {"mode": "round_robin", "user_id": None}
                ),
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "assignment-1"})
    elif effect == "notification":
        nodes.append(
            {
                "id": "notification-1",
                "kind": "notification",
                "config": {"message": "An inbound customer needs operator attention"},
            }
        )
        edges.append({"id": "edge-2", "source": previous, "target": "notification-1"})
    return {"nodes": nodes, "edges": edges}


def _branch_graph(*, condition_value: str) -> dict:
    return {
        "nodes": [
            {
                "id": "trigger-1",
                "kind": "trigger",
                "config": {"event": "message.received"},
            },
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {
                    "field": "payload.message_type",
                    "operator": "eq",
                    "value": condition_value,
                },
            },
            {
                "id": "notification-yes",
                "kind": "notification",
                "config": {"message": "Yes branch selected"},
            },
            {
                "id": "notification-no",
                "kind": "notification",
                "config": {"message": "No branch selected"},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "condition-1"},
            {
                "id": "edge-yes",
                "source": "condition-1",
                "target": "notification-yes",
                "label": "yes",
            },
            {
                "id": "edge-no",
                "source": "condition-1",
                "target": "notification-no",
                "label": "no",
            },
        ],
    }


def _multi_step_branch_graph(*, condition_value: str) -> dict:
    graph = _branch_graph(condition_value=condition_value)
    graph["nodes"].extend(
        [
            {
                "id": "task-yes",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "Yes branch follow-up",
                    "task_type": "call",
                    "priority": "high",
                    "due_in_minutes": 90,
                },
            },
            {
                "id": "task-no",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "No branch follow-up",
                    "task_type": "call",
                    "priority": "high",
                    "due_in_minutes": 90,
                },
            },
        ]
    )
    graph["edges"].extend(
        [
            {
                "id": "edge-yes-task",
                "source": "notification-yes",
                "target": "task-yes",
            },
            {
                "id": "edge-no-task",
                "source": "notification-no",
                "target": "task-no",
            },
        ]
    )
    return graph


def _merged_branch_graph(*, condition_value: str) -> dict:
    graph = _branch_graph(condition_value=condition_value)
    graph["nodes"].append(
        {
            "id": "task-shared",
            "kind": "action",
            "config": {
                "action": "create_task",
                "title": "Shared branch follow-up",
                "task_type": "call",
                "priority": "high",
                "due_in_minutes": 90,
            },
        }
    )
    graph["edges"].extend(
        [
            {
                "id": "edge-yes-shared",
                "source": "notification-yes",
                "target": "task-shared",
            },
            {
                "id": "edge-no-shared",
                "source": "notification-no",
                "target": "task-shared",
            },
        ]
    )
    return graph


def _delayed_merged_branch_graph(*, condition_value: str) -> dict:
    graph = _merged_branch_graph(condition_value=condition_value)
    graph["nodes"].insert(
        -1,
        {
            "id": "delay-shared",
            "kind": "delay",
            "config": {"seconds": 60},
        },
    )
    graph["edges"] = [
        edge
        for edge in graph["edges"]
        if edge["target"] != "task-shared"
    ]
    graph["edges"].extend(
        [
            {
                "id": "edge-yes-delay",
                "source": "notification-yes",
                "target": "delay-shared",
            },
            {
                "id": "edge-no-delay",
                "source": "notification-no",
                "target": "delay-shared",
            },
            {
                "id": "edge-delay-shared",
                "source": "delay-shared",
                "target": "task-shared",
            },
        ]
    )
    return graph


def _sequential_graph(*, tag_id: str, condition_value: str | None = None) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "message.received"},
        }
    ]
    if condition_value is not None:
        nodes.append(
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {
                    "field": "payload.message_type",
                    "operator": "eq",
                    "value": condition_value,
                },
            }
        )
    nodes.extend(
        [
            {
                "id": "tag-1",
                "kind": "tag",
                "config": {"tag_id": tag_id},
            },
            {
                "id": "task-1",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "Call sequential inbound customer",
                    "task_type": "call",
                    "priority": "high",
                    "due_in_minutes": 90,
                },
            },
            {
                "id": "notification-1",
                "kind": "notification",
                "config": {"message": "Sequential inbound work is ready"},
            },
        ]
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


def _delayed_graph(*, tag_id: str, condition_value: str | None = None) -> dict:
    graph = _sequential_graph(tag_id=tag_id, condition_value=condition_value)
    nodes = graph["nodes"]
    task_index = next(index for index, node in enumerate(nodes) if node["kind"] == "action")
    nodes[task_index] = {
        "id": "delay-1",
        "kind": "delay",
        "config": {"seconds": 60},
    }
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


def _contact_created_graph(
    *,
    tag_id: str,
    condition_value: str | None = None,
    include_task: bool = False,
) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "contact.created"},
        }
    ]
    if condition_value is not None:
        nodes.append(
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {
                    "field": "payload.opt_in_status",
                    "operator": "eq",
                    "value": condition_value,
                },
            }
        )
    nodes.append(
        {
            "id": "tag-1",
            "kind": "tag",
            "config": {"tag_id": tag_id},
        }
    )
    if include_task:
        nodes.append(
            {
                "id": "task-1",
                "kind": "action",
                "config": {
                    "action": "create_task",
                    "title": "Unsupported contact task",
                    "task_type": "custom",
                    "priority": "medium",
                    "due_in_minutes": 60,
                },
            }
        )
    else:
        nodes.append(
            {
                "id": "notification-1",
                "kind": "notification",
                "config": {"message": "A new contact entered the workspace"},
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


def _wait_graph(
    *,
    event: str = "message.received",
    timeout_seconds: int | None = 300,
    wait_last: bool = False,
) -> dict:
    wait_config: dict[str, object] = {"event": event}
    if timeout_seconds is not None:
        wait_config["timeout_seconds"] = timeout_seconds
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "contact.created"},
        },
        {
            "id": "wait-1",
            "kind": "wait",
            "config": wait_config,
        },
        {
            "id": "notification-1",
            "kind": "notification",
            "config": {"message": "The new contact replied"},
        },
    ]
    if wait_last:
        nodes[1], nodes[2] = nodes[2], nodes[1]
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


def _conversation_auto_resolved_graph(
    *,
    tag_id: str,
    condition_value: str | None = None,
    include_handoff: bool = False,
) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "conversation.auto_resolved"},
        }
    ]
    if condition_value is not None:
        nodes.append(
            {
                "id": "condition-1",
                "kind": "condition",
                "config": {
                    "field": "payload.previous_status",
                    "operator": "eq",
                    "value": condition_value,
                },
            }
        )
    nodes.append(
        {
            "id": "tag-1",
            "kind": "tag",
            "config": {"tag_id": tag_id},
        }
    )
    if include_handoff:
        nodes.append(
            {
                "id": "handoff-1",
                "kind": "handoff",
                "config": {"reason": "Unsupported resolved conversation handoff"},
            }
        )
    else:
        nodes.extend(
            [
                {
                    "id": "task-1",
                    "kind": "action",
                    "config": {
                        "action": "create_task",
                        "title": "Follow up after auto-resolution",
                        "task_type": "call",
                        "priority": "high",
                        "due_in_minutes": 120,
                    },
                },
                {
                    "id": "notification-1",
                    "kind": "notification",
                    "config": {"message": "An inactive conversation was auto-resolved"},
                },
            ]
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


def _lead_stage_changed_graph(*, tag_id: str) -> dict:
    nodes = [
        {
            "id": "trigger-1",
            "kind": "trigger",
            "config": {"event": "lead.stage_changed"},
        },
        {
            "id": "condition-1",
            "kind": "condition",
            "config": {
                "field": "payload.to_stage",
                "operator": "eq",
                "value": "lead_confirmed",
            },
        },
        {
            "id": "tag-1",
            "kind": "tag",
            "config": {"tag_id": tag_id},
        },
        {
            "id": "task-1",
            "kind": "action",
            "config": {
                "action": "create_task",
                "title": "Follow up confirmed lead",
                "task_type": "call",
                "priority": "high",
                "due_in_minutes": 120,
            },
        },
        {
            "id": "notification-1",
            "kind": "notification",
            "config": {"message": "A lead moved to confirmed"},
        },
    ]
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


async def _owner(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@vi.co", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _publish(
    client,
    owner: dict[str, str],
    *,
    effect: str | None = "handoff",
    condition: bool = False,
    condition_field: str = "payload.message_type",
    condition_operator: str = "eq",
    condition_value: str = "text",
    tag_id: str | None = None,
    assignment_user_id: str | None = None,
    graph: dict | None = None,
) -> dict:
    created = await client.post(
        AUTOMATIONS,
        headers=owner,
        json={
            "name": "Live inbound handoff",
            "graph": graph
            or _graph(
                effect=effect,
                condition=condition,
                condition_field=condition_field,
                condition_operator=condition_operator,
                condition_value=condition_value,
                tag_id=tag_id,
                assignment_user_id=assignment_user_id,
            ),
        },
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"{AUTOMATIONS}/{created.json()['id']}/publish",
        headers=owner,
        json={"expected_row_version": created.json()["row_version"]},
    )
    assert published.status_code == 200, published.text
    return published.json()


async def _receive_after_publish(
    client,
    make_user,
    session_factory,
    monkeypatch,
    *,
    effect: str | None = "handoff",
    condition: bool = False,
    condition_field: str = "payload.message_type",
    condition_operator: str = "eq",
    condition_value: str = "text",
    assignment_user_id: str | None = None,
) -> tuple[dict[str, str], dict, dict]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    owner = await _owner(client)
    tag_id = None
    if effect in {"tag", "remove_tag"}:
        async with session_factory() as session:
            publisher = (
                await session.scalars(select(User).where(User.email == "owner@vi.co"))
            ).one()
            tag = Tag(
                organization_id=publisher.organization_id,
                name="Automation VIP",
                color="#0f766e",
                created_by=publisher.id,
            )
            session.add(tag)
            await session.commit()
            tag_id = tag.public_id
    flow = await _publish(
        client,
        owner,
        effect=effect,
        condition=condition,
        condition_field=condition_field,
        condition_operator=condition_operator,
        condition_value=condition_value,
        tag_id=tag_id,
        assignment_user_id=assignment_user_id,
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[_fresh_message(wamid="wamid.live-automation-2", body="private live body")]
        ),
    )
    async with session_factory() as session:
        result = await MessageService(session).apply_inbound(routed[-1])
    if effect == "remove_tag":
        assert tag_id is not None
        async with session_factory() as session:
            publisher = (
                await session.scalars(select(User).where(User.email == "owner@vi.co"))
            ).one()
            await TagService(session).apply_tag_to_contact(
                organization_id=publisher.organization_id,
                actor=publisher,
                contact_uuid=uuid.UUID(result["contact_id"]),
                tag_uuid=uuid.UUID(tag_id),
            )
    return owner, flow, result


async def _receive_branch_after_publish(
    client,
    make_user,
    session_factory,
    monkeypatch,
    *,
    condition_value: str,
    multi_step: bool = False,
    shared_follow_up: bool = False,
    shared_delay: bool = False,
) -> tuple[dict[str, str], dict, dict]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    owner = await _owner(client)
    if shared_delay:
        branch_graph = _delayed_merged_branch_graph(condition_value=condition_value)
    elif shared_follow_up:
        branch_graph = _merged_branch_graph(condition_value=condition_value)
    elif multi_step:
        branch_graph = _multi_step_branch_graph(condition_value=condition_value)
    else:
        branch_graph = _branch_graph(condition_value=condition_value)
    flow = await _publish(
        client,
        owner,
        graph=branch_graph,
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[
                _fresh_message(
                    wamid=f"wamid.live-automation-branch-{condition_value}",
                    body="private branch body",
                )
            ]
        ),
    )
    async with session_factory() as session:
        result = await MessageService(session).apply_inbound(routed[-1])
    return owner, flow, result


async def _receive_sequential_after_publish(
    client,
    make_user,
    session_factory,
    monkeypatch,
    *,
    condition_value: str | None = None,
    delay: bool = False,
) -> tuple[dict[str, str], dict, dict, str]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    owner = await _owner(client)
    async with session_factory() as session:
        publisher = (
            await session.scalars(select(User).where(User.email == "owner@vi.co"))
        ).one()
        tag = Tag(
            organization_id=publisher.organization_id,
            name="Sequential Automation",
            color="#0f766e",
            created_by=publisher.id,
        )
        session.add(tag)
        await session.commit()
        tag_id = tag.public_id
    flow = await _publish(
        client,
        owner,
        graph=(
            _delayed_graph(tag_id=tag_id, condition_value=condition_value)
            if delay
            else _sequential_graph(tag_id=tag_id, condition_value=condition_value)
        ),
    )
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[
                _fresh_message(
                    wamid="wamid.live-automation-sequence",
                    body="private sequential body",
                )
            ]
        ),
    )
    async with session_factory() as session:
        result = await MessageService(session).apply_inbound(routed[-1])
    return owner, flow, result, tag_id


async def _create_contact_after_publish(
    client,
    make_user,
    session_factory,
    *,
    condition_value: str | None = None,
    include_task: bool = False,
    graph: dict | None = None,
) -> tuple[dict[str, str], dict, dict, str, int]:
    await make_user(
        email="owner@vi.co",
        password=PASSWORD,
        full_name="Automation Owner",
        is_superuser=True,
    )
    owner = await _owner(client)
    async with session_factory() as session:
        publisher = (
            await session.scalars(select(User).where(User.email == "owner@vi.co"))
        ).one()
        tag = Tag(
            organization_id=publisher.organization_id,
            name="New Contact Automation",
            color="#0f766e",
            created_by=publisher.id,
        )
        session.add(tag)
        await session.commit()
        tag_id = tag.public_id
    flow = await _publish(
        client,
        owner,
        graph=(
            graph
            or _contact_created_graph(
                tag_id=tag_id,
                condition_value=condition_value,
                include_task=include_task,
            )
        ),
    )
    created = await client.post(
        "/api/v1/contacts",
        headers=owner,
        json={
            "phone_e164": "+14155550991",
            "full_name": "New Automation Contact",
            "opt_in_status": "opted_in",
            "source": "manual",
        },
    )
    assert created.status_code == 201, created.text
    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
    return owner, flow, created.json(), tag_id, receipt.id


async def _auto_resolve_after_publish(
    client,
    make_user,
    session_factory,
    monkeypatch,
    *,
    condition_value: str | None = None,
    include_handoff: bool = False,
) -> tuple[dict[str, str], dict, str, str, str, int]:
    await _inbound(client, make_user, session_factory, monkeypatch)
    owner = await _owner(client)
    async with session_factory() as session:
        publisher = (
            await session.scalars(select(User).where(User.email == "owner@vi.co"))
        ).one()
        tag = Tag(
            organization_id=publisher.organization_id,
            name="Auto-resolved Follow-up",
            color="#0f766e",
            created_by=publisher.id,
        )
        session.add(tag)
        await session.commit()
        tag_id = tag.public_id
    flow = await _publish(
        client,
        owner,
        graph=_conversation_auto_resolved_graph(
            tag_id=tag_id,
            condition_value=condition_value,
            include_handoff=include_handoff,
        ),
    )
    async with session_factory() as session:
        publisher = (
            await session.scalars(select(User).where(User.email == "owner@vi.co"))
        ).one()
        conversation = (
            await session.scalars(
                select(Conversation)
                .where(Conversation.organization_id == publisher.organization_id)
                .order_by(Conversation.id.desc())
            )
        ).first()
        assert conversation is not None
        contact = await session.get(Contact, conversation.contact_id)
        assert contact is not None
        activity_at = conversation.last_message_at or conversation.created_at
        conversation.status = CONV_RESOLVED
        event = await BusinessEventService(session).record_conversation_auto_resolved(
            organization_id=publisher.organization_id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            activity_at=activity_at,
            resolved_at=utcnow(),
            previous_status=CONV_OPEN,
            inactive_after_hours=72,
        )
        await session.commit()
        receipt = (
            await session.scalars(
                select(AutomationTriggerReceipt).where(
                    AutomationTriggerReceipt.event_uuid == event.uuid
                )
            )
        ).one()
        return owner, flow, conversation.public_id, contact.public_id, tag_id, receipt.id


async def test_inbound_receipt_executes_one_pinned_live_handoff(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, flow, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch
    )
    assert len(inbound["automation_receipts"]) == 1
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
    async with session_factory() as session:
        duplicate = await MessageService(session).apply_inbound(inbound["event_pk"])
    assert duplicate["automation_receipts"] == []

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
        message_event = (
            await session.scalars(
                select(BusinessEvent)
                .where(BusinessEvent.event_type == BUSINESS_EVENT_MESSAGE_RECEIVED)
                .order_by(BusinessEvent.id.desc())
            )
        ).first()
        handoff_count = await session.scalar(
            select(func.count())
            .select_from(BusinessEvent)
            .where(BusinessEvent.event_type == BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED)
        )

    assert receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
    assert receipt.run_id == run.id and receipt.processed_at is not None
    assert run.mode == "live" and run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 2
    assert [attempt.node_kind for attempt in attempts] == ["trigger", "handoff"]
    assert all(attempt.status == "succeeded" for attempt in attempts)
    assert conversation.status == CONV_PENDING and conversation.assigned_user_id is None
    assert handoff_count == 1
    assert message_event is not None
    serialized = str(message_event.payload_json)
    assert "private live body" not in serialized
    assert "wamid.live-automation-2" not in serialized

    receipts = await client.get(f"{AUTOMATIONS}/{flow['id']}/trigger-receipts", headers=owner)
    runs = await client.get(f"{AUTOMATIONS}/{flow['id']}/runs", headers=owner)
    assert receipts.status_code == runs.status_code == 200
    assert receipts.json()["data"][0]["status"] == "processed"
    assert runs.json()["data"][0]["mode"] == "live"


async def test_matching_privacy_safe_condition_executes_live_handoff(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition=True,
        condition_value="text",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 3
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "handoff",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        "succeeded",
    ]
    assert attempts[1].input_json == {
        "field": "payload.message_type",
        "present": True,
    }
    assert attempts[1].output_json == {
        "field": "payload.message_type",
        "operator": "eq",
        "matched": True,
    }
    assert conversation.status == CONV_PENDING


async def test_unmatched_condition_records_skipped_handoff_without_live_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    owner, flow, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition=True,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
        handoff_count = await session.scalar(
            select(func.count())
            .select_from(BusinessEvent)
            .where(BusinessEvent.event_type == BUSINESS_EVENT_CONVERSATION_HANDOFF_REQUESTED)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 3
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert attempts[1].output_json is not None
    assert attempts[1].output_json["matched"] is False
    assert attempts[2].output_json == {
        "reason": "condition_not_matched",
        "condition_node_id": "condition-1",
    }
    assert conversation.status == CONV_OPEN
    assert handoff_count == 0

    run_response = await client.get(f"/api/v1/automation-runs/{run.public_id}", headers=owner)
    assert run_response.status_code == 200
    assert run_response.json()["attempts"][2]["status"] == "skipped"
    assert flow["id"] == run_response.json()["automation_id"]


@pytest.mark.parametrize(
    ("condition_value", "expected_body", "selected_branch", "selected_node", "skipped_node"),
    [
        ("text", "Yes branch selected", "yes", "notification-yes", "notification-no"),
        ("image", "No branch selected", "no", "notification-no", "notification-yes"),
    ],
)
async def test_bounded_yes_no_branch_executes_only_selected_effect_once(
    client,
    make_user,
    session_factory,
    monkeypatch,
    dispatched,
    condition_value,
    expected_body,
    selected_branch,
    selected_node,
    skipped_node,
) -> None:
    _, _, inbound = await _receive_branch_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=condition_value,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        notifications = list((await session.scalars(select(Notification))).all())

    attempts_by_node = {attempt.node_id: attempt for attempt in attempts}
    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 4
    assert len(notifications) == 1
    assert notifications[0].body == expected_body
    assert attempts_by_node[selected_node].status == "succeeded"
    assert attempts_by_node[skipped_node].status == AUTOMATION_ATTEMPT_SKIPPED
    assert attempts_by_node[skipped_node].output_json == {
        "reason": "branch_not_selected",
        "condition_node_id": "condition-1",
        "selected_branch": selected_branch,
    }


@pytest.mark.parametrize(
    (
        "condition_value",
        "selected_branch",
        "expected_body",
        "expected_title",
        "selected_nodes",
        "skipped_nodes",
    ),
    [
        (
            "text",
            "yes",
            "Yes branch selected",
            "Yes branch follow-up",
            {"notification-yes", "task-yes"},
            {"notification-no", "task-no"},
        ),
        (
            "image",
            "no",
            "No branch selected",
            "No branch follow-up",
            {"notification-no", "task-no"},
            {"notification-yes", "task-yes"},
        ),
    ],
)
async def test_bounded_yes_no_branch_executes_two_ordered_effects_per_selected_side(
    client,
    make_user,
    session_factory,
    monkeypatch,
    dispatched,
    condition_value,
    selected_branch,
    expected_body,
    expected_title,
    selected_nodes,
    skipped_nodes,
) -> None:
    _, _, inbound = await _receive_branch_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=condition_value,
        multi_step=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list((await session.scalars(select(AutomationStepAttempt))).all())
        notifications = list((await session.scalars(select(Notification))).all())
        tasks = list((await session.scalars(select(Task))).all())

    attempts_by_node = {attempt.node_id: attempt for attempt in attempts}
    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 6
    assert [notification.body for notification in notifications] == [expected_body]
    assert [task.title for task in tasks] == [expected_title]
    assert all(attempts_by_node[node_id].status == "succeeded" for node_id in selected_nodes)
    for node_id in skipped_nodes:
        assert attempts_by_node[node_id].status == AUTOMATION_ATTEMPT_SKIPPED
        assert attempts_by_node[node_id].output_json == {
            "reason": "branch_not_selected",
            "condition_node_id": "condition-1",
            "selected_branch": selected_branch,
        }


@pytest.mark.parametrize(
    ("condition_value", "selected_branch", "expected_body", "selected_node", "skipped_node"),
    [
        ("text", "yes", "Yes branch selected", "notification-yes", "notification-no"),
        ("image", "no", "No branch selected", "notification-no", "notification-yes"),
    ],
)
async def test_bounded_branch_executes_one_shared_follow_up_after_either_outcome(
    client,
    make_user,
    session_factory,
    monkeypatch,
    dispatched,
    condition_value,
    selected_branch,
    expected_body,
    selected_node,
    skipped_node,
) -> None:
    _, _, inbound = await _receive_branch_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=condition_value,
        shared_follow_up=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list((await session.scalars(select(AutomationStepAttempt))).all())
        notifications = list((await session.scalars(select(Notification))).all())
        tasks = list((await session.scalars(select(Task))).all())

    attempts_by_node = {attempt.node_id: attempt for attempt in attempts}
    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 5
    assert [notification.body for notification in notifications] == [expected_body]
    assert [task.title for task in tasks] == ["Shared branch follow-up"]
    assert attempts_by_node[selected_node].status == "succeeded"
    assert attempts_by_node["task-shared"].status == "succeeded"
    assert attempts_by_node[skipped_node].status == AUTOMATION_ATTEMPT_SKIPPED
    assert attempts_by_node[skipped_node].output_json == {
        "reason": "branch_not_selected",
        "condition_node_id": "condition-1",
        "selected_branch": selected_branch,
    }


@pytest.mark.parametrize(
    ("condition_value", "selected_branch", "expected_body", "selected_node", "skipped_node"),
    [
        ("text", "yes", "Yes branch selected", "notification-yes", "notification-no"),
        ("image", "no", "No branch selected", "notification-no", "notification-yes"),
    ],
)
async def test_bounded_branch_shared_delay_resumes_once_before_follow_up(
    client,
    make_user,
    session_factory,
    monkeypatch,
    dispatched,
    condition_value,
    selected_branch,
    expected_body,
    selected_node,
    skipped_node,
) -> None:
    _, _, inbound = await _receive_branch_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=condition_value,
        shared_delay=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        assert service.resume_in_seconds is not None
        assert 1 <= service.resume_in_seconds <= 60

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        delay_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_id == "delay-shared"
                )
            )
        ).one()
        notification_count = await session.scalar(
            select(func.count()).select_from(Notification)
        )
        task_count = await session.scalar(select(func.count()).select_from(Task))
        assert notification_count == 1
        assert task_count == 0
        delay_attempt.started_at -= timedelta(seconds=61)
        await session.commit()

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list((await session.scalars(select(AutomationStepAttempt))).all())
        notifications = list((await session.scalars(select(Notification))).all())
        tasks = list((await session.scalars(select(Task))).all())

    attempts_by_node = {attempt.node_id: attempt for attempt in attempts}
    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 6
    assert [notification.body for notification in notifications] == [expected_body]
    assert [task.title for task in tasks] == ["Shared branch follow-up"]
    assert attempts_by_node[selected_node].status == "succeeded"
    assert attempts_by_node["delay-shared"].status == "succeeded"
    assert attempts_by_node["task-shared"].status == "succeeded"
    assert attempts_by_node[skipped_node].status == AUTOMATION_ATTEMPT_SKIPPED
    assert attempts_by_node[skipped_node].output_json == {
        "reason": "branch_not_selected",
        "condition_node_id": "condition-1",
        "selected_branch": selected_branch,
    }


async def test_private_identifier_condition_fails_closed_without_live_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition=True,
        condition_field="payload.contact_id",
        condition_value="never-evaluated",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_FAILED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
    assert run.error_code == "unsupported_live_graph"
    assert conversation.status == CONV_OPEN


async def test_create_task_action_is_durable_and_replay_safe(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch, effect="task"
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        version = (await session.scalars(select(AutomationFlowVersion))).one()
        task = (await session.scalars(select(Task))).one()
        action_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "action")
            )
        ).one()
        task_events = list((await session.scalars(select(TaskEvent))).all())
        timeline_events = list(
            (
                await session.scalars(
                    select(ContactEvent).where(ContactEvent.event_type == EVENT_TASK_CREATED)
                )
            ).all()
        )
        task_audit = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "task.created",
                    AuditLog.entity_id == task.id,
                )
            )
        ).one()

        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 2
        assert task.status == TASK_STATUS_OPEN
        assert task.title == "Call inbound customer"
        assert task.task_type == TASK_TYPE_CALL
        assert task.priority == TASK_PRIORITY_HIGH
        assert task.contact_id is not None and task.conversation_id is not None
        assert task.created_by is None and task.assigned_agent_id == version.published_by
        assert task.idempotency_key == receipt.uuid and task.request_hash is not None
        assert task.due_at == receipt.event_occurred_at + timedelta(minutes=90)
        assert [event.event_type for event in task_events] == [TASK_EVENT_CREATED]
        assert task_events[0].actor_user_id is None
        assert len(timeline_events) == 1
        assert task_audit.actor_type == ACTOR_SYSTEM and task_audit.actor_user_id is None
        assert action_attempt.output_json is not None
        assert action_attempt.output_json["task_id"] == task.public_id
        assert action_attempt.output_json["replayed"] is False

        await session.delete(action_attempt)
        run.status = "running"
        run.completed_steps = 1
        run.finished_at = None
        receipt.status = "processing"
        receipt.processing_started_at = receipt.received_at - timedelta(minutes=6)
        receipt.processed_at = None
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Task)) == 1
        assert await session.scalar(select(func.count()).select_from(TaskEvent)) == 1
        replayed_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "action")
            )
        ).one()
        assert replayed_attempt.output_json is not None
        assert replayed_attempt.output_json["replayed"] is True


async def test_unmatched_condition_skips_create_task_without_task_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="task",
        condition=True,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        task_count = await session.scalar(select(func.count()).select_from(Task))
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "action",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert task_count == 0


async def test_apply_tag_action_is_durable_and_replay_safe(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch, effect="tag"
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        tag = (await session.scalars(select(Tag))).one()
        link = (await session.execute(select(contact_tags))).mappings().one()
        tag_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "tag")
            )
        ).one()
        tag_events = list(
            (
                await session.scalars(
                    select(ContactEvent).where(ContactEvent.event_type == EVENT_TAG_ADDED)
                )
            ).all()
        )
        tag_audits = list(
            (
                await session.scalars(select(AuditLog).where(AuditLog.action == "contact.tagged"))
            ).all()
        )

        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 2
        assert tag.usage_count == 1
        assert link["tag_id"] == tag.id and link["tagged_by"] is None
        assert len(tag_events) == 1 and tag_events[0].ref_id == tag.id
        assert len(tag_audits) == 1
        assert tag_audits[0].actor_type == ACTOR_SYSTEM
        assert tag_audits[0].actor_user_id is None
        assert tag_attempt.output_json == {
            "contact_id": inbound["contact_id"],
            "tag_id": tag.public_id,
            "tag_name": "Automation VIP",
            "outcome": "applied",
            "applied": True,
        }

        await session.delete(tag_attempt)
        run.status = "running"
        run.completed_steps = 1
        run.finished_at = None
        receipt.status = "processing"
        receipt.processing_started_at = receipt.received_at - timedelta(minutes=6)
        receipt.processed_at = None
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        tag = (await session.scalars(select(Tag))).one()
        assert tag.usage_count == 1
        assert len((await session.execute(select(contact_tags))).all()) == 1
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ContactEvent)
                .where(ContactEvent.event_type == EVENT_TAG_ADDED)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "contact.tagged")
            )
            == 1
        )
        replayed_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "tag")
            )
        ).one()
        assert replayed_attempt.output_json is not None
        assert replayed_attempt.output_json["outcome"] == "already_present"
        assert replayed_attempt.output_json["applied"] is False


async def test_unmatched_condition_skips_apply_tag_without_crm_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="tag",
        condition=True,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (await session.scalars(select(Tag))).one()
        tag_event_count = await session.scalar(
            select(func.count())
            .select_from(ContactEvent)
            .where(ContactEvent.event_type == EVENT_TAG_ADDED)
        )
        tag_audit_count = await session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "contact.tagged")
        )
        link_count = len((await session.execute(select(contact_tags))).all())

    assert [attempt.node_kind for attempt in attempts] == ["trigger", "condition", "tag"]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert tag.usage_count == 0
    assert link_count == tag_event_count == tag_audit_count == 0


async def test_remove_tag_action_is_durable_and_replay_safe(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch, effect="remove_tag"
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        tag = (await session.scalars(select(Tag))).one()
        remove_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "remove_tag"
                )
            )
        ).one()
        removed_events = list(
            (
                await session.scalars(
                    select(ContactEvent).where(ContactEvent.event_type == EVENT_TAG_REMOVED)
                )
            ).all()
        )
        removed_audits = list(
            (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "contact.untagged")
                )
            ).all()
        )

        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 2
        assert tag.usage_count == 0
        assert len((await session.execute(select(contact_tags))).all()) == 0
        assert len(removed_events) == 1 and removed_events[0].ref_id == tag.id
        assert len(removed_audits) == 1
        assert removed_audits[0].actor_type == ACTOR_SYSTEM
        assert removed_audits[0].actor_user_id is None
        assert remove_attempt.output_json == {
            "contact_id": inbound["contact_id"],
            "tag_id": tag.public_id,
            "tag_name": "Automation VIP",
            "outcome": "removed",
            "removed": True,
        }

        await session.delete(remove_attempt)
        run.status = "running"
        run.completed_steps = 1
        run.finished_at = None
        receipt.status = "processing"
        receipt.processing_started_at = receipt.received_at - timedelta(minutes=6)
        receipt.processed_at = None
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        assert len((await session.execute(select(contact_tags))).all()) == 0
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ContactEvent)
                .where(ContactEvent.event_type == EVENT_TAG_REMOVED)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "contact.untagged")
            )
            == 1
        )
        replayed_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "remove_tag"
                )
            )
        ).one()
        assert replayed_attempt.output_json is not None
        assert replayed_attempt.output_json["outcome"] == "already_absent"
        assert replayed_attempt.output_json["removed"] is False


async def test_unmatched_condition_skips_remove_tag_without_crm_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="remove_tag",
        condition=True,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (await session.scalars(select(Tag))).one()
        removed_event_count = await session.scalar(
            select(func.count())
            .select_from(ContactEvent)
            .where(ContactEvent.event_type == EVENT_TAG_REMOVED)
        )
        removed_audit_count = await session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "contact.untagged")
        )
        link_count = len((await session.execute(select(contact_tags))).all())

    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "remove_tag",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert tag.usage_count == 1
    assert link_count == 1
    assert removed_event_count == removed_audit_count == 0


async def test_notification_action_is_durable_and_replay_safe(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch, effect="notification"
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        owner = (await session.scalars(select(User).where(User.email == "owner@vi.co"))).one()
        notification = (await session.scalars(select(Notification))).one()
        notification_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "notification"
                )
            )
        ).one()

        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 2
        assert notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION
        assert notification.recipient_user_id == owner.id
        assert notification.actor_user_id is None
        assert notification.contact_id is not None
        assert notification.title == "Automation needs attention"
        assert notification.body == "An inbound customer needs operator attention"
        assert notification.dedup_key == f"automation:{receipt.public_id}:notification-1"
        assert notification_attempt.output_json == {
            "notification_id": notification.public_id,
            "recipient_id": owner.public_id,
            "contact_id": inbound["contact_id"],
            "outcome": "delivered",
            "delivered": True,
        }

        await session.delete(notification_attempt)
        run.status = "running"
        run.completed_steps = 1
        run.finished_at = None
        receipt.status = "processing"
        receipt.processing_started_at = receipt.received_at - timedelta(minutes=6)
        receipt.processed_at = None
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Notification)) == 1
        replayed_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "notification"
                )
            )
        ).one()
        assert replayed_attempt.output_json is not None
        assert replayed_attempt.output_json["outcome"] == "already_delivered"
        assert replayed_attempt.output_json["delivered"] is False


async def test_unmatched_condition_skips_notification_without_delivery(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="notification",
        condition=True,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        notification_count = await session.scalar(select(func.count()).select_from(Notification))

    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "notification",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert notification_count == 0


async def test_specific_user_assignment_is_durable_and_replay_safe(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    agent = await make_user(
        email="assignment-agent@vi.co",
        password=PASSWORD,
        full_name="Assignment Agent",
        roles=("agent",),
    )
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="assignment",
        assignment_user_id=agent.user.public_id,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
        assignment_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "assignment")
            )
        ).one()
        assignment_audit = (
            await session.scalars(
                select(AuditLog).where(AuditLog.action == "conversation.assigned")
            )
        ).one()
        assigned_row_version = conversation.row_version

        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 2
        assert conversation.assigned_user_id == agent.user.id
        assert assignment_audit.actor_type == ACTOR_SYSTEM
        assert assignment_audit.actor_user_id is None
        assert assignment_audit.after_json == {
            "assigned_user_id": agent.user.id,
            "policy": "automation_user",
        }
        assert assignment_audit.metadata_json is not None
        assert assignment_audit.metadata_json["source"] == "automation"
        assert assignment_attempt.output_json == {
            "conversation_id": inbound["conversation_id"],
            "assignee_id": agent.user.public_id,
            "mode": "user",
            "outcome": "assigned",
            "applied": True,
        }

        await session.delete(assignment_attempt)
        run.status = "running"
        run.completed_steps = 1
        run.finished_at = None
        receipt.status = "processing"
        receipt.processing_started_at = receipt.received_at - timedelta(minutes=6)
        receipt.processed_at = None
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
        replayed_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(AutomationStepAttempt.node_kind == "assignment")
            )
        ).one()
        assignment_audit_count = await session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "conversation.assigned")
        )
        assert conversation.row_version == assigned_row_version
        assert assignment_audit_count == 1
        assert replayed_attempt.output_json is not None
        assert replayed_attempt.output_json["outcome"] == "already_assigned"
        assert replayed_attempt.output_json["applied"] is False


async def test_round_robin_assignment_uses_durable_flow_rotation(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    # The agent is created before the Owner account, so the first durable flow receipt selects it.
    agent = await make_user(
        email="round-robin-agent@vi.co",
        password=PASSWORD,
        full_name="Round Robin Agent",
        roles=("agent",),
    )
    _, _, inbound = await _receive_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        effect="assignment",
        condition=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    second_message = _fresh_message(wamid="wamid.live-assignment-2")
    second_message["from"] = "919990329330"
    second_delivery = _delivery(messages=[second_message])
    second_delivery["entry"][0]["changes"][0]["value"]["contacts"] = [
        {"profile": {"name": "Round Robin Customer"}, "wa_id": "919990329330"}
    ]
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        second_delivery,
    )
    async with session_factory() as session:
        second_inbound = await MessageService(session).apply_inbound(routed[-1])
    second_receipt_pk = second_inbound["automation_receipts"][0]["receipt_pk"]
    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(second_receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        conversations = list(
            (await session.scalars(select(Conversation).order_by(Conversation.id))).all()
        )
        owner = (await session.scalars(select(User).where(User.email == "owner@vi.co"))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        assignment_audits = list(
            (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "conversation.assigned")
                )
            ).all()
        )

    assert [conversation.assigned_user_id for conversation in conversations] == [
        agent.user.id,
        owner.id,
    ]
    assert [attempt.node_kind for attempt in attempts[:3]] == [
        "trigger",
        "condition",
        "assignment",
    ]
    assert [attempt.node_kind for attempt in attempts[3:]] == [
        "trigger",
        "condition",
        "assignment",
    ]
    assert all(attempt.status == "succeeded" for attempt in attempts)
    assert attempts[2].output_json is not None
    assert attempts[2].output_json["mode"] == "round_robin"
    assert attempts[2].output_json["assignee_id"] == agent.user.public_id
    assert attempts[5].output_json is not None
    assert attempts[5].output_json["assignee_id"] == owner.public_id
    assert [audit.after_json["policy"] for audit in assignment_audits] == [
        "automation_round_robin",
        "automation_round_robin",
    ]


async def test_distinct_internal_effects_execute_in_published_sequence(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound, tag_id = await _receive_sequential_after_publish(
        client, make_user, session_factory, monkeypatch
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (
            await session.scalars(
                select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes)
            )
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        task_count = await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.title == "Call sequential inbound customer")
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 4
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "tag",
        "action",
        "notification",
    ]
    assert all(attempt.status == "succeeded" for attempt in attempts)
    assert association_count == task_count == notification_count == 1


async def test_unmatched_condition_skips_every_sequential_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound, tag_id = await _receive_sequential_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value="image",
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (
            await session.scalars(
                select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes)
            )
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        task_count = await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.title == "Call sequential inbound customer")
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 5
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert association_count == task_count == notification_count == 0


async def test_sequential_retry_resumes_after_completed_effects_without_duplicates(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound, _ = await _receive_sequential_after_publish(
        client, make_user, session_factory, monkeypatch
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)

        async def interrupt_notification(**_: object) -> dict[str, object]:
            raise RuntimeError("simulated worker interruption")

        monkeypatch.setattr(service, "_notification_effect", interrupt_notification)
        try:
            await service.consume_receipt(receipt_pk)
        except RuntimeError as exc:
            await service.mark_task_failure(receipt_pk, retrying=True, error=exc)
        else:
            raise AssertionError("the simulated interruption did not occur")

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        task_count = await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.title == "Call sequential inbound customer")
        )
        tag_event_count = await session.scalar(
            select(func.count())
            .select_from(ContactEvent)
            .where(ContactEvent.event_type == EVENT_TAG_ADDED)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )
        tag_attempt_count = await session.scalar(
            select(func.count())
            .select_from(AutomationStepAttempt)
            .where(AutomationStepAttempt.node_kind == "tag")
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 4
    assert task_count == tag_event_count == notification_count == tag_attempt_count == 1


async def test_contact_created_receipt_is_claimed_and_executes_event_safe_effects(
    client, make_user, session_factory, monkeypatch
) -> None:
    _, _, _, tag_id, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
    )

    async with session_factory() as session:
        dispatches = await BusinessEventService(
            session
        ).claim_automation_receipt_dispatches(limit=50)
        assert dispatches == [
            AutomationReceiptDispatch(receipt_pk=receipt_pk, task_id=dispatches[0].task_id)
        ]
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        assert receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        assert receipt.processing_started_at is not None
        assert (
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
            == []
        )
        receipt.processing_started_at -= timedelta(minutes=6)
        stale_started_at = receipt.processing_started_at
        await session.commit()
        recovered = await BusinessEventService(
            session
        ).claim_automation_receipt_dispatches(limit=50)
        assert len(recovered) == 1
        await session.refresh(receipt)
        assert receipt.processing_started_at == stale_started_at

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 3
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "tag",
        "notification",
    ]
    assert association_count == notification_count == 1


async def test_contact_created_false_condition_skips_every_effect(
    client, make_user, session_factory, monkeypatch
) -> None:
    _, _, _, tag_id, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        condition_value="opted_out",
    )
    async with session_factory() as session:
        dispatches = await BusinessEventService(
            session
        ).claim_automation_receipt_dispatches(limit=50)
        assert len(dispatches) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert association_count == notification_count == 0


async def test_contact_created_rejects_conversation_effect_before_tagging(
    client, make_user, session_factory, monkeypatch
) -> None:
    _, _, _, tag_id, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        include_task=True,
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_FAILED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        attempt_count = await session.scalar(
            select(func.count()).select_from(AutomationStepAttempt)
        )

    assert run.error_code == "unsupported_live_graph"
    assert association_count == attempt_count == 0


async def test_auto_resolved_receipt_executes_followup_task_tag_and_notification(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, conversation_id, contact_id, tag_id, receipt_pk = await _auto_resolve_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=CONV_OPEN,
    )
    async with session_factory() as session:
        dispatches = await BusinessEventService(
            session
        ).claim_automation_receipt_dispatches(limit=50)
        assert len(dispatches) == 1
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        event = (
            await session.scalars(
                select(BusinessEvent).where(
                    BusinessEvent.event_type == BUSINESS_EVENT_CONVERSATION_AUTO_RESOLVED
                )
            )
        ).one()
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        task = (
            await session.scalars(
                select(Task).where(Task.title == "Follow up after auto-resolution")
            )
        ).one()
        conversation = (
            await session.scalars(
                select(Conversation).where(Conversation.uuid == uuid.UUID(conversation_id).bytes)
            )
        ).one()
        contact = await session.get(Contact, conversation.contact_id)
        assert contact is not None
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.contact_id == contact.id, contact_tags.c.tag_id == tag.id)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert receipt.status == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
    assert event.payload_json["inactive_after_hours"] == 72
    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 5
    assert run.trigger_input_json["payload"]["conversation_id"] == conversation_id
    assert run.trigger_input_json["payload"]["contact_id"] == contact_id
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "tag",
        "action",
        "notification",
    ]
    assert conversation.status == CONV_RESOLVED
    assert task.conversation_id == conversation.id and task.contact_id == contact.id
    assert association_count == notification_count == 1


async def test_auto_resolved_false_condition_skips_followup_effects(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, _, _, tag_id, receipt_pk = await _auto_resolve_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value=CONV_PENDING,
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        task_count = await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.title == "Follow up after auto-resolution")
        )
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert task_count == association_count == notification_count == 0


async def test_auto_resolved_rejects_handoff_before_tagging(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, _, _, tag_id, receipt_pk = await _auto_resolve_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        include_handoff=True,
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_FAILED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        tag = (
            await session.scalars(select(Tag).where(Tag.uuid == uuid.UUID(tag_id).bytes))
        ).one()
        association_count = await session.scalar(
            select(func.count())
            .select_from(contact_tags)
            .where(contact_tags.c.tag_id == tag.id)
        )
        attempt_count = await session.scalar(
            select(func.count()).select_from(AutomationStepAttempt)
        )

    assert run.error_code == "unsupported_live_graph"
    assert association_count == attempt_count == 0


async def test_bounded_delay_pauses_and_resumes_without_duplicate_effects(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound, _ = await _receive_sequential_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        delay=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        first = await service.consume_receipt(receipt_pk)
        assert first == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        assert service.resume_in_seconds is not None
        assert 1 <= service.resume_in_seconds <= 60
        assert (
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
            == []
        )

    async with session_factory() as session:
        # An early duplicate delivery converges on the same running delay checkpoint.
        service = AutomationLiveRuntimeService(session)
        assert (
            await service.consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        )
        run = (await session.scalars(select(AutomationRun))).one()
        delay_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "delay"
                )
            )
        ).one()
        assert run.status == AUTOMATION_RUN_RETRYING
        assert delay_attempt.status == AUTOMATION_ATTEMPT_RUNNING
        assert delay_attempt.output_json is not None
        assert delay_attempt.output_json["seconds"] == 60
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
            )
            == 0
        )
        delay_attempt.started_at -= timedelta(seconds=61)
        await session.commit()

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag_event_count = await session.scalar(
            select(func.count())
            .select_from(ContactEvent)
            .where(ContactEvent.event_type == EVENT_TAG_ADDED)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )
        delay_attempt_count = await session.scalar(
            select(func.count())
            .select_from(AutomationStepAttempt)
            .where(AutomationStepAttempt.node_kind == "delay")
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 4
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "tag",
        "delay",
        "notification",
    ]
    assert all(attempt.status == "succeeded" for attempt in attempts)
    assert tag_event_count == notification_count == delay_attempt_count == 1


async def test_unmatched_condition_skips_delay_and_every_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound, _ = await _receive_sequential_after_publish(
        client,
        make_user,
        session_factory,
        monkeypatch,
        condition_value="image",
        delay=True,
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        assert service.resume_in_seconds is None

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        attempts = list(
            (
                await session.scalars(
                    select(AutomationStepAttempt).order_by(AutomationStepAttempt.id)
                )
            ).all()
        )
        tag_event_count = await session.scalar(
            select(func.count())
            .select_from(ContactEvent)
            .where(ContactEvent.event_type == EVENT_TAG_ADDED)
        )
        notification_count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == NOTIFICATION_AUTOMATION_ATTENTION)
        )

    assert run.status == AUTOMATION_RUN_SUCCEEDED
    assert run.completed_steps == run.total_steps == 5
    assert [attempt.node_kind for attempt in attempts] == [
        "trigger",
        "condition",
        "tag",
        "delay",
        "notification",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
        AUTOMATION_ATTEMPT_SKIPPED,
    ]
    assert tag_event_count == notification_count == 0


async def test_contact_wait_resumes_on_future_message_without_duplicate_notification(
    client, make_user, session_factory
) -> None:
    _, _, contact_json, _, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        graph=_wait_graph(),
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        service = AutomationLiveRuntimeService(session)
        assert await service.consume_receipt(receipt_pk) == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        assert service.resume_in_seconds is None
        run = (await session.scalars(select(AutomationRun))).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        receipt = await session.get(AutomationTriggerReceipt, receipt_pk)
        assert run.status == AUTOMATION_RUN_RETRYING
        assert wait.status == AUTOMATION_WAIT_WAITING
        assert wait.event_type == BUSINESS_EVENT_MESSAGE_RECEIVED
        assert receipt is not None and receipt.processing_started_at is None
        assert await session.scalar(select(func.count()).select_from(Notification)) == 0

    reply_event_id = uuid.uuid4()
    async with session_factory() as session:
        contact = (
            await session.scalars(
                select(Contact).where(
                    Contact.uuid == uuid.UUID(contact_json["id"]).bytes
                )
            )
        ).one()
        event = await BusinessEventService(session).record_domain_event(
            organization_id=contact.organization_id,
            event_id=reply_event_id,
            event_type=BUSINESS_EVENT_MESSAGE_RECEIVED,
            actor_id=None,
            actor_type="connector",
            subject_type="message",
            subject_id=900001,
            contact_id=contact.id,
            occurred_at=utcnow(),
            source="test_connector",
            payload={"direction": "inbound", "message_type": "text"},
        )
        dispatches = await BusinessEventService(session).receipt_dispatches_for_event(
            contact.organization_id, uuid.UUID(bytes=event.uuid)
        )
        projected_wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert projected_wait.status == AUTOMATION_WAIT_MATCHED
        await session.commit()
        assert [item.receipt_pk for item in dispatches] == [receipt_pk]

    async with session_factory() as session:
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )
        # A redelivery after the completed checkpoint cannot repeat the internal delivery.
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        wait_attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "wait"
                )
            )
        ).one()
        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 3
        assert wait.status == AUTOMATION_WAIT_MATCHED
        assert wait.matched_event_uuid == reply_event_id.bytes
        assert wait_attempt.output_json is not None
        assert wait_attempt.output_json["outcome"] == "matched"
        assert wait_attempt.output_json["matched_event_id"] == str(reply_event_id)
        assert await session.scalar(select(func.count()).select_from(Notification)) == 1


async def test_contact_wait_resumes_on_same_contact_task_completion(
    client, make_user, session_factory
) -> None:
    owner, _, contact_json, _, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        graph=_wait_graph(event="task.completed"),
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        )
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert wait.status == AUTOMATION_WAIT_WAITING
        assert wait.event_type == BUSINESS_EVENT_TASK_COMPLETED

    async with session_factory() as session:
        original_contact = (
            await session.scalars(
                select(Contact).where(
                    Contact.uuid == uuid.UUID(contact_json["id"]).bytes
                )
            )
        ).one()
        unrelated = Contact(
            organization_id=original_contact.organization_id,
            wa_id="14155550993",
            phone_e164="+14155550993",
            full_name="Unrelated Task Contact",
            opt_in_status="opted_in",
            source="test",
        )
        session.add(unrelated)
        await session.commit()
        unrelated_contact_id = unrelated.public_id

    async def complete_for(contact_id: str, title: str) -> str:
        created = await client.post(
            "/api/v1/tasks",
            headers=owner,
            json={
                "contact_id": contact_id,
                "title": title,
                "task_type": "call",
                "priority": "high",
                "due_at": (utcnow() + timedelta(days=1)).isoformat() + "Z",
                "has_time": True,
            },
        )
        assert created.status_code == 201, created.text
        task_id = created.json()["id"]
        completed = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=owner,
            json={"completion_notes": "Not exposed to Automation"},
        )
        assert completed.status_code == 200, completed.text
        return task_id

    await complete_for(unrelated_contact_id, "Wrong customer task")
    async with session_factory() as session:
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert wait.status == AUTOMATION_WAIT_WAITING
        assert (
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
            == []
        )

    completed_task_id = await complete_for(contact_json["id"], "Matching customer task")
    async with session_factory() as session:
        task_event = (
            await session.scalars(
                select(BusinessEvent)
                .where(
                    BusinessEvent.event_type == BUSINESS_EVENT_TASK_COMPLETED,
                    BusinessEvent.contact_id
                    == select(Contact.id)
                    .where(Contact.uuid == uuid.UUID(contact_json["id"]).bytes)
                    .scalar_subquery(),
                )
                .order_by(BusinessEvent.id.desc())
            )
        ).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert wait.status == AUTOMATION_WAIT_MATCHED
        assert wait.matched_event_uuid == task_event.uuid
        assert task_event.payload_json["task_id"] == completed_task_id
        assert "title" not in task_event.payload_json
        assert "completion_notes" not in task_event.payload_json
        dispatches = await BusinessEventService(session).claim_automation_receipt_dispatches(
            limit=50
        )
        assert [item.receipt_pk for item in dispatches] == [receipt_pk]
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert wait.status == AUTOMATION_WAIT_MATCHED
        assert await session.scalar(select(func.count()).select_from(Notification)) == 1


async def test_lead_stage_change_runs_contact_follow_up_without_private_reason(
    client, make_user, session_factory
) -> None:
    await make_user(
        email="owner@vi.co",
        password=PASSWORD,
        full_name="Automation Owner",
        is_superuser=True,
    )
    owner = await _owner(client)
    async with session_factory() as session:
        publisher = (
            await session.scalars(select(User).where(User.email == "owner@vi.co"))
        ).one()
        tag = Tag(
            organization_id=publisher.organization_id,
            name="Confirmed Lead",
            color="#0f766e",
            created_by=publisher.id,
        )
        session.add(tag)
        await session.commit()
        tag_id = tag.public_id

    await _publish(client, owner, graph=_lead_stage_changed_graph(tag_id=tag_id))
    created = await client.post(
        "/api/v1/contacts",
        headers=owner,
        json={
            "phone_e164": "+14155550994",
            "full_name": "Lead Stage Automation Contact",
            "opt_in_status": "opted_in",
            "source": "manual",
        },
    )
    assert created.status_code == 201, created.text
    contact_id = created.json()["id"]
    case = await client.post(
        f"/api/v1/contacts/{contact_id}/reactivation-cases",
        headers=owner,
        json={"idempotency_key": str(uuid.uuid4()), "source": "manual"},
    )
    assert case.status_code == 201, case.text
    transitioned = await client.post(
        f"/api/v1/reactivation-cases/{case.json()['id']}/transition",
        headers=owner,
        json={
            "idempotency_key": str(uuid.uuid4()),
            "expected_row_version": 0,
            "to_stage": "lead_confirmed",
            "reason": "Private operator rationale must not enter Automation",
        },
    )
    assert transitioned.status_code == 200, transitioned.text

    async with session_factory() as session:
        receipt = (
            await session.scalars(
                select(AutomationTriggerReceipt).where(
                    AutomationTriggerReceipt.event_type == BUSINESS_EVENT_LEAD_STAGE_CHANGED
                )
            )
        ).one()
        domain_event = (
            await session.scalars(
                select(BusinessEvent).where(BusinessEvent.uuid == receipt.event_uuid)
            )
        ).one()
        assert domain_event.event_type == BUSINESS_EVENT_REACTIVATION_TRANSITIONED
        assert domain_event.payload_json is not None
        assert domain_event.payload_json["reason"] == (
            "Private operator rationale must not enter Automation"
        )
        receipt_pk = receipt.id
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        task = (await session.scalars(select(Task))).one()
        notification = (await session.scalars(select(Notification))).one()
        trigger_input = run.trigger_input_json
        assert trigger_input is not None
        assert trigger_input["event_type"] == BUSINESS_EVENT_LEAD_STAGE_CHANGED
        assert trigger_input["payload"] == {
            "from_stage": "new_lead",
            "to_stage": "lead_confirmed",
            "contact_id": contact_id,
        }
        assert "Private operator rationale" not in str(trigger_input)
        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert run.completed_steps == run.total_steps == 5
        assert task.contact_id == notification.contact_id
        assert task.conversation_id is None
        assert task.title == "Follow up confirmed lead"
        assert notification.body == "A lead moved to confirmed"
        assert len((await session.execute(select(contact_tags))).all()) == 1
        assert await session.scalar(select(func.count()).select_from(Task)) == 1
        assert await session.scalar(select(func.count()).select_from(Notification)) == 1


async def test_contact_wait_resumes_on_future_lead_stage_change(
    client, make_user, session_factory
) -> None:
    owner, _, contact_json, _, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        graph=_wait_graph(event="lead.stage_changed"),
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        )
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert wait.status == AUTOMATION_WAIT_WAITING
        assert wait.event_type == BUSINESS_EVENT_LEAD_STAGE_CHANGED

    case = await client.post(
        f"/api/v1/contacts/{contact_json['id']}/reactivation-cases",
        headers=owner,
        json={"idempotency_key": str(uuid.uuid4()), "source": "manual"},
    )
    assert case.status_code == 201, case.text
    transitioned = await client.post(
        f"/api/v1/reactivation-cases/{case.json()['id']}/transition",
        headers=owner,
        json={
            "idempotency_key": str(uuid.uuid4()),
            "expected_row_version": 0,
            "to_stage": "lead_confirmed",
        },
    )
    assert transitioned.status_code == 200, transitioned.text

    async with session_factory() as session:
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        matched = (
            await session.scalars(
                select(BusinessEvent).where(BusinessEvent.uuid == wait.matched_event_uuid)
            )
        ).one()
        assert wait.status == AUTOMATION_WAIT_MATCHED
        assert matched.event_type == BUSINESS_EVENT_REACTIVATION_TRANSITIONED
        dispatches = await BusinessEventService(session).claim_automation_receipt_dispatches(
            limit=50
        )
        assert [item.receipt_pk for item in dispatches] == [receipt_pk]
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        assert run.status == AUTOMATION_RUN_SUCCEEDED
        assert wait.status == AUTOMATION_WAIT_MATCHED
        assert await session.scalar(select(func.count()).select_from(Notification)) == 1


async def test_wait_ignores_another_contact_and_timeout_scanner_resumes_once(
    client, make_user, session_factory
) -> None:
    _, _, contact_json, _, receipt_pk = await _create_contact_after_publish(
        client,
        make_user,
        session_factory,
        graph=_wait_graph(timeout_seconds=300),
    )
    async with session_factory() as session:
        assert len(
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
        ) == 1
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
        )

    async with session_factory() as session:
        original_contact = (
            await session.scalars(
                select(Contact).where(
                    Contact.uuid == uuid.UUID(contact_json["id"]).bytes
                )
            )
        ).one()
        other_contact = Contact(
            organization_id=original_contact.organization_id,
            wa_id="14155550992",
            phone_e164="+14155550992",
            full_name="Unrelated Automation Contact",
            opt_in_status="opted_in",
            source="test",
        )
        session.add(other_contact)
        await session.flush()
        await BusinessEventService(session).record_domain_event(
            organization_id=other_contact.organization_id,
            event_id=uuid.uuid4(),
            event_type=BUSINESS_EVENT_MESSAGE_RECEIVED,
            actor_id=None,
            actor_type="connector",
            subject_type="message",
            subject_id=900002,
            contact_id=other_contact.id,
            occurred_at=utcnow(),
            source="test_connector",
            payload={"direction": "inbound", "message_type": "text"},
        )
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        await BusinessEventService(session).record_domain_event(
            organization_id=original_contact.organization_id,
            event_id=uuid.uuid4(),
            event_type=BUSINESS_EVENT_MESSAGE_RECEIVED,
            actor_id=None,
            actor_type="connector",
            subject_type="message",
            subject_id=900003,
            contact_id=original_contact.id,
            occurred_at=wait.started_at - timedelta(seconds=1),
            source="delayed_test_connector",
            payload={"direction": "inbound", "message_type": "text"},
        )
        await session.commit()
        waits = list((await session.scalars(select(AutomationWaitSubscription))).all())
        assert len(waits) == 1
        assert waits[0].status == AUTOMATION_WAIT_WAITING
        assert (
            await BusinessEventService(session).claim_automation_receipt_dispatches(limit=50)
            == []
        )
        waits[0].timeout_at = utcnow() - timedelta(seconds=1)
        await session.commit()

    async with session_factory() as session:
        dispatches = await BusinessEventService(session).claim_automation_receipt_dispatches(
            limit=50
        )
        assert [item.receipt_pk for item in dispatches] == [receipt_pk]
        assert (
            await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
            == AUTOMATION_TRIGGER_RECEIPT_PROCESSED
        )

    async with session_factory() as session:
        original_contact = (
            await session.scalars(
                select(Contact).where(
                    Contact.uuid == uuid.UUID(contact_json["id"]).bytes
                )
            )
        ).one()
        wait = (await session.scalars(select(AutomationWaitSubscription))).one()
        attempt = (
            await session.scalars(
                select(AutomationStepAttempt).where(
                    AutomationStepAttempt.node_kind == "wait"
                )
            )
        ).one()
        notification = (await session.scalars(select(Notification))).one()
        assert wait.contact_id == original_contact.id
        assert wait.status == AUTOMATION_WAIT_TIMED_OUT
        assert wait.matched_event_uuid is None
        assert attempt.output_json is not None
        assert attempt.output_json["outcome"] == "timed_out"
        assert notification.contact_id == original_contact.id


def test_live_wait_contract_rejects_unbounded_unavailable_and_terminal_waits() -> None:
    assert (
        AutomationLiveRuntimeService._supported_path(
            _wait_graph(timeout_seconds=None), "contact.created"
        )
        is None
    )
    task_wait = AutomationLiveRuntimeService._supported_path(
        _wait_graph(event="task.completed"), "contact.created"
    )
    assert task_wait is not None
    assert [step["kind"] for step in task_wait[2]] == ["wait", "notification"]
    assert (
        AutomationLiveRuntimeService._supported_path(
            _wait_graph(wait_last=True), "contact.created"
        )
        is None
    )
    supported = AutomationLiveRuntimeService._supported_path(
        _wait_graph(), "contact.created"
    )
    assert supported is not None
    assert [step["kind"] for step in supported[2]] == ["wait", "notification"]


def test_live_sequence_accepts_bounded_branches_shared_follow_up_and_delay() -> None:
    bounded = AutomationLiveRuntimeService._supported_path(
        _branch_graph(condition_value="text"), "message.received"
    )
    assert bounded is not None
    assert [step["id"] for step in bounded[2]] == ["notification-yes"]
    assert [step["id"] for step in bounded[3]] == ["notification-no"]

    two_step = AutomationLiveRuntimeService._supported_path(
        _multi_step_branch_graph(condition_value="text"), "message.received"
    )
    assert two_step is not None
    assert [step["id"] for step in two_step[2]] == ["notification-yes", "task-yes"]
    assert [step["id"] for step in two_step[3]] == ["notification-no", "task-no"]

    merged = AutomationLiveRuntimeService._supported_path(
        _merged_branch_graph(condition_value="text"), "message.received"
    )
    assert merged is not None
    assert [step["id"] for step in merged[2]] == ["notification-yes", "task-shared"]
    assert [step["id"] for step in merged[3]] == ["notification-no", "task-shared"]

    delayed_merged = AutomationLiveRuntimeService._supported_path(
        _delayed_merged_branch_graph(condition_value="text"), "message.received"
    )
    assert delayed_merged is not None
    assert [step["id"] for step in delayed_merged[2]] == [
        "notification-yes",
        "delay-shared",
        "task-shared",
    ]
    assert [step["id"] for step in delayed_merged[3]] == [
        "notification-no",
        "delay-shared",
        "task-shared",
    ]

    branch_specific_delay = _delayed_merged_branch_graph(condition_value="text")
    next(
        edge for edge in branch_specific_delay["edges"] if edge["id"] == "edge-no-delay"
    )["target"] = "task-shared"
    assert AutomationLiveRuntimeService._supported_path(
        branch_specific_delay, "message.received"
    ) is None

    repeated_shared_effect = _merged_branch_graph(condition_value="text")
    repeated_shared_effect["nodes"][-1] = {
        "id": "task-shared",
        "kind": "notification",
        "config": {"message": "Invalid repeated shared notification"},
    }
    assert (
        AutomationLiveRuntimeService._supported_path(
            repeated_shared_effect, "message.received"
        )
        is None
    )

    repeated_branch_effect = _multi_step_branch_graph(condition_value="text")
    repeated_branch_effect["nodes"][4] = {
        "id": "task-yes",
        "kind": "notification",
        "config": {"message": "Repeated notification"},
    }
    assert (
        AutomationLiveRuntimeService._supported_path(
            repeated_branch_effect, "message.received"
        )
        is None
    )

    oversized_branch = _multi_step_branch_graph(condition_value="text")
    oversized_branch["nodes"].append(
        {
            "id": "tag-yes",
            "kind": "tag",
            "config": {"tag_id": str(uuid.uuid4())},
        }
    )
    oversized_branch["edges"].append(
        {
            "id": "edge-yes-tag",
            "source": "task-yes",
            "target": "tag-yes",
        }
    )
    assert (
        AutomationLiveRuntimeService._supported_path(oversized_branch, "message.received")
        is None
    )

    repeated = _sequential_graph(tag_id=str(uuid.uuid4()))
    repeated["nodes"][2] = {
        "id": "tag-2",
        "kind": "tag",
        "config": {"tag_id": str(uuid.uuid4())},
    }
    repeated["edges"][1]["target"] = "tag-2"
    repeated["edges"][2]["source"] = "tag-2"
    assert AutomationLiveRuntimeService._supported_path(repeated, "message.received") is None

    branched = _sequential_graph(tag_id=str(uuid.uuid4()))
    branched["edges"][1]["source"] = "trigger-1"
    assert AutomationLiveRuntimeService._supported_path(branched, "message.received") is None

    repeated_delay = _delayed_graph(tag_id=str(uuid.uuid4()))
    repeated_delay["nodes"].insert(
        -1,
        {"id": "delay-2", "kind": "delay", "config": {"seconds": 60}},
    )
    repeated_delay["edges"] = [
        {
            "id": f"edge-{index}",
            "source": repeated_delay["nodes"][index - 1]["id"],
            "target": node["id"],
        }
        for index, node in enumerate(repeated_delay["nodes"][1:], start=1)
    ]
    assert AutomationLiveRuntimeService._supported_path(
        repeated_delay, "message.received"
    ) is None

    invalid_delay = _delayed_graph(tag_id=str(uuid.uuid4()))
    next(node for node in invalid_delay["nodes"] if node["kind"] == "delay")["config"][
        "seconds"
    ] = 59
    assert AutomationLiveRuntimeService._supported_path(
        invalid_delay, "message.received"
    ) is None


def test_live_task_schedules_the_durable_delay_resume(monkeypatch) -> None:
    queued: list[dict[str, object]] = []

    def run_without_database(coroutine) -> tuple[str, int]:
        coroutine.close()
        return AUTOMATION_TRIGGER_RECEIPT_PROCESSING, 47

    monkeypatch.setattr(automation_tasks, "run_async", run_without_database)
    monkeypatch.setattr(
        automation_tasks.consume_automation_trigger_receipt,
        "apply_async",
        lambda **options: queued.append(options),
    )

    assert (
        automation_tasks.consume_automation_trigger_receipt.run(17)
        == AUTOMATION_TRIGGER_RECEIPT_PROCESSING
    )
    assert len(queued) == 1
    assert queued[0]["args"] == [17]
    assert queued[0]["countdown"] == 47


def test_receipt_dispatcher_hands_claimed_rows_to_live_worker(monkeypatch) -> None:
    queued: list[dict[str, object]] = []
    dispatches = [
        AutomationReceiptDispatch(receipt_pk=17, task_id=str(uuid.uuid4())),
        AutomationReceiptDispatch(receipt_pk=23, task_id=str(uuid.uuid4())),
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

    assert automation_tasks.dispatch_automation_trigger_receipts.run() == {"claimed": 2}
    assert queued == [
        {"args": [17], "task_id": dispatches[0].task_id},
        {"args": [23], "task_id": dispatches[1].task_id},
    ]


async def test_unsupported_live_graph_fails_closed_without_conversation_effect(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    _, _, inbound = await _receive_after_publish(
        client, make_user, session_factory, monkeypatch, effect=None
    )
    receipt_pk = inbound["automation_receipts"][0]["receipt_pk"]

    async with session_factory() as session:
        outcome = await AutomationLiveRuntimeService(session).consume_receipt(receipt_pk)
    assert outcome == AUTOMATION_TRIGGER_RECEIPT_FAILED

    async with session_factory() as session:
        receipt = (await session.scalars(select(AutomationTriggerReceipt))).one()
        run = (await session.scalars(select(AutomationRun))).one()
        conversation = (
            await session.scalars(
                select(Conversation).where(
                    Conversation.uuid == uuid.UUID(inbound["conversation_id"]).bytes
                )
            )
        ).one()
    assert receipt.status == AUTOMATION_TRIGGER_RECEIPT_FAILED
    assert run.status == AUTOMATION_RUN_FAILED
    assert run.error_code == "unsupported_live_graph"
    assert conversation.status == CONV_OPEN
