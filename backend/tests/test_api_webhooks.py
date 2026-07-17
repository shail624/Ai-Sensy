"""Inbound webhook tests (Doc 04 §23, Doc 06 §11; FR-WA-05/06/07/08) — M4 Step 3.

No network and no broker: the endpoint's dispatch is captured, and the tasks are driven directly.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.channels.models import InboundEventType
from app.core.config import settings
from app.models.webhook import (
    WH_DUPLICATE,
    WH_FAILED,
    WH_PROCESSED,
    WH_RECEIVED,
    WHDL_PENDING,
    WebhookDeadLetter,
    WebhookEvent,
)
from app.services.waba_service import WabaService
from app.services.webhook_service import WebhookService
from tests.conftest import META_APP_SECRET as APP_SECRET
from tests.conftest import META_WEBHOOK_VERIFY_TOKEN as VERIFY_TOKEN

PASSWORD = "Sup3r-Secret-Pass1"
WEBHOOK_URL = "/api/v1/webhooks/whatsapp"
NUMBER_ID = "pn-1"

WAMID = "wamid.HBgLMTQxNTU1NTAwMDE="

#: A sink for the ids `process()` routes onto `inbound.process`, for the tests that only care that
#: the event settled. Tests that assert on routing itself pass their own list.
_routed: list[int] = []


def _sign(body: bytes, *, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _delivery(*, messages: list | None = None, statuses: list | None = None, field: str = "messages",
              number_id: str = NUMBER_ID) -> dict:
    value: dict = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "+14155550001", "phone_number_id": number_id},
    }
    if messages is not None:
        value["contacts"] = [{"profile": {"name": "Priya"}, "wa_id": "919990329329"}]
        value["messages"] = messages
    if statuses is not None:
        value["statuses"] = statuses
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba-100", "changes": [{"field": field, "value": value}]}],
    }


def _message(wamid: str = WAMID, body: str = "hello") -> dict:
    return {
        "from": "919990329329",
        "id": wamid,
        "timestamp": "1752739200",
        "type": "text",
        "text": {"body": body},
    }


def _status(state: str = "delivered", wamid: str = WAMID) -> dict:
    return {
        "id": wamid,
        "status": state,
        "timestamp": "1752739260",
        "recipient_id": "919990329329",
    }


async def _post(client, payload: dict, *, secret: str = APP_SECRET, signature: str | None = None):
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature if signature is not None else _sign(body, secret=secret),
    }
    return await client.post(WEBHOOK_URL, content=body, headers=headers)


async def _seed_number(client, make_user, session_factory, monkeypatch) -> None:
    """A synced phone number, so an inbound event has somewhere to route (Doc 03 §5.2)."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@vi.co", "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/v1/waba",
        headers=headers,
        json={"waba_id": "waba-100", "business_name": "Vi", "access_token": "tok"},
    )
    waba_id = created.json()["id"]

    real = WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "data": [
                            {"id": NUMBER_ID, "display_phone_number": "+14155550001",
                             "quality_rating": "GREEN", "status": "connected"}
                        ]
                    },
                )
            )
        )
        adapter.client._owns_http = True
        return adapter

    monkeypatch.setattr(WabaService, "adapter_for", _adapter_for)
    async with session_factory() as session:
        await WabaService(session).run_sync(waba_id)
    monkeypatch.setattr(WabaService, "adapter_for", real)


async def _events(session_factory) -> list[WebhookEvent]:
    async with session_factory() as session:
        stmt = select(WebhookEvent).order_by(WebhookEvent.id)
        return list((await session.scalars(stmt)).all())


# --- Verification handshake (Doc 04 §23) -------------------------------------
async def test_handshake_echoes_challenge_on_matching_token(client) -> None:
    resp = await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "1158201444"},
    )
    assert resp.status_code == 200, resp.text
    # Meta requires the bare challenge as the body, not JSON.
    assert resp.text == "1158201444"
    assert resp.headers["content-type"].startswith("text/plain")


async def test_handshake_rejects_wrong_token_and_wrong_mode(client) -> None:
    wrong = await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": "guessed", "hub.challenge": "x"},
    )
    assert wrong.status_code == 403, wrong.text
    assert "x" not in wrong.text

    mode = await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "unsubscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "x"},
    )
    assert mode.status_code == 403


async def test_only_a_successful_handshake_is_audited(client, session_factory) -> None:
    """Config-time and security-relevant, but only writable by a caller holding the token —
    auditing rejections on a public endpoint would let anyone write the audit trail."""
    from app.models.audit import ACTOR_SYSTEM, AuditLog

    await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": "guessed", "hub.challenge": "42"},
    )
    await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "42"},
    )

    async with session_factory() as session:
        rows = list(
            (
                await session.scalars(select(AuditLog).where(AuditLog.action == "webhook.verified"))
            ).all()
        )
    assert len(rows) == 1 and rows[0].actor_type == ACTOR_SYSTEM


async def test_handshake_is_public(client) -> None:
    """No Authorization header anywhere — Meta cannot hold a JWT."""
    resp = await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "9"},
    )
    assert resp.status_code == 200


# --- Signature verification (FR-WA-05) ---------------------------------------
async def test_unsigned_and_badly_signed_deliveries_are_rejected_without_storing(
    client, session_factory, dispatched
) -> None:
    payload = _delivery(messages=[_message()])
    body = json.dumps(payload).encode()

    missing = await client.post(WEBHOOK_URL, content=body)
    assert missing.status_code == 403, missing.text

    forged = await _post(client, payload, secret="not-the-app-secret")
    assert forged.status_code == 403

    malformed = await _post(client, payload, signature="garbage")
    assert malformed.status_code == 403

    # An unverified body is never trusted, so it is never persisted or queued (Doc 06 §11.2).
    assert await _events(session_factory) == []
    assert dispatched == []


async def test_signature_is_computed_over_the_raw_body(client, session_factory, dispatched) -> None:
    """Re-serialized JSON has a different HMAC; the endpoint must hash exactly what arrived."""
    body = b'{"object":"whatsapp_business_account","entry":[{"id":"waba-100","changes":[{"field":"messages","value":{"metadata":{"phone_number_id":"pn-1"},"messages":[{"id":"wamid.RAW","timestamp":"1752739200","type":"text","text":{"body":"hi"}}]}}]}]}'
    resp = await client.post(
        WEBHOOK_URL,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )
    assert resp.status_code == 200, resp.text
    assert [e.event_id for e in await _events(session_factory)] == ["wamid.RAW"]


async def test_missing_app_secret_is_a_configuration_error_not_a_rejection(
    client, monkeypatch, session_factory
) -> None:
    """Answering 403 while misconfigured would look like an attack and silently drop real events.

    A 503 is honest and recoverable: Meta redelivers non-200 for up to seven days.
    """
    monkeypatch.setattr(settings, "meta_app_secret", "")
    resp = await _post(client, _delivery(messages=[_message()]))
    assert resp.status_code == 503, resp.text
    assert resp.json()["code"] == "webhook_not_configured"
    assert await _events(session_factory) == []


async def test_missing_verify_token_is_a_configuration_error(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "meta_webhook_verify_token", "")
    resp = await client.get(
        WEBHOOK_URL,
        params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"},
    )
    assert resp.status_code == 503, resp.text


# --- Durable-first ingest + fast ack (FR-WA-05) ------------------------------
async def test_delivery_is_persisted_then_acked_and_enqueued(
    client, session_factory, dispatched
) -> None:
    resp = await _post(client, _delivery(messages=[_message()], statuses=[_status()]))
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "received", "events": 2}

    rows = await _events(session_factory)
    assert [r.status for r in rows] == [WH_RECEIVED, WH_RECEIVED]
    assert all(r.signature_ok is True for r in rows)
    # One event per message/status, each independently replayable (Doc 06 §11.6).
    assert [r.object_type for r in rows] == [
        InboundEventType.MESSAGES.value,
        InboundEventType.STATUSES.value,
    ]
    assert rows[0].payload_json["message"]["text"]["body"] == "hello"
    assert rows[0].payload_json["contacts"][0]["wa_id"] == "919990329329"
    assert rows[1].payload_json["status"]["status"] == "delivered"
    # Nothing is processed on the request path.
    assert all(r.processed_at is None and r.attempts == 0 for r in rows)

    # Exactly one broker message for the delivery, carrying both persisted rows.
    assert dispatched == [[rows[0].id, rows[1].id]]


async def test_status_dedup_key_is_message_id_plus_state(client, session_factory, dispatched) -> None:
    """sent → delivered → read are three distinct events for one message (Doc 06 §11.4)."""
    await _post(
        client,
        _delivery(statuses=[_status("sent"), _status("delivered"), _status("read")]),
    )
    assert [r.event_id for r in await _events(session_factory)] == [
        f"{WAMID}:sent",
        f"{WAMID}:delivered",
        f"{WAMID}:read",
    ]


async def test_inbound_routing_resolves_the_phone_number(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))

    rows = await _events(session_factory)
    assert rows[0].phone_number_id is not None


async def test_unreadable_signed_body_is_stored_not_dropped(
    client, session_factory, dispatched
) -> None:
    """A signed body is authentic; failing the request would only make Meta redeliver it."""
    body = b"this is not json"
    resp = await client.post(
        WEBHOOK_URL, content=body, headers={"X-Hub-Signature-256": _sign(body)}
    )
    assert resp.status_code == 200, resp.text

    rows = await _events(session_factory)
    assert len(rows) == 1
    assert rows[0].object_type == InboundEventType.UNKNOWN.value
    assert rows[0].payload_json["_unreadable"] == "this is not json"


async def test_unknown_change_type_is_surfaced_as_an_unknown_event(
    client, session_factory, dispatched
) -> None:
    """A template-status update is valid, signed, and not ours to apply yet (Doc 06 §11.6)."""
    await _post(client, _delivery(field="message_template_status_update"))
    rows = await _events(session_factory)
    assert [r.object_type for r in rows] == [InboundEventType.UNKNOWN.value]
    assert rows[0].event_id is None


# --- Processing & idempotency (FR-WA-07) -------------------------------------
async def test_process_routes_and_settles_an_event(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))
    (row,) = await _events(session_factory)

    async with session_factory() as session:
        result = await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)
    assert result["status"] == WH_PROCESSED

    (after,) = await _events(session_factory)
    assert after.status == WH_PROCESSED and after.processed_at is not None
    assert after.attempts == 1


async def test_redelivered_event_is_marked_duplicate_and_not_reapplied(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """Meta retries for up to 7 days; the second copy must never be applied twice."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))
    await _post(client, _delivery(messages=[_message()]))  # Meta redelivers the same message id

    first, second = await _events(session_factory)
    assert first.event_id == second.event_id == WAMID

    async with session_factory() as session:
        service = WebhookService(session)
        assert (await service.process(first.id, dispatch_inbound=_routed.append))["status"] == WH_PROCESSED
        assert (await service.process(second.id, dispatch_inbound=_routed.append))["status"] == WH_DUPLICATE

    stored = await _events(session_factory)
    assert [r.status for r in stored] == [WH_PROCESSED, WH_DUPLICATE]


async def test_processing_the_same_row_twice_is_a_no_op(
    client, make_user, session_factory, monkeypatch, dispatched
) -> None:
    """At-least-once delivery means the task itself can arrive twice (Doc 06 §8)."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))
    (row,) = await _events(session_factory)

    async with session_factory() as session:
        await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)
    async with session_factory() as session:
        again = await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)

    assert again["skipped"] is True and again["status"] == WH_PROCESSED
    # The attempt counter proves the body did not run a second time.
    assert (await _events(session_factory))[0].attempts == 1


async def test_a_missing_row_is_not_an_error(session_factory) -> None:
    async with session_factory() as session:
        assert (await WebhookService(session).process(9999, dispatch_inbound=_routed.append))["status"] == "missing"


# --- Dead letter (FR-WA-08; Doc 06 §11.6) ------------------------------------
async def test_event_for_an_unowned_number_is_unprocessable(
    client, session_factory, dispatched
) -> None:
    from app.services.webhook_service import WebhookUnprocessable

    await _post(client, _delivery(messages=[_message()], number_id="pn-not-ours"))
    (row,) = await _events(session_factory)
    assert row.phone_number_id is None

    async with session_factory() as session:
        with pytest.raises(WebhookUnprocessable, match="does not own"):
            await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)


async def test_unknown_event_type_is_unprocessable(client, session_factory, dispatched) -> None:
    from app.services.webhook_service import WebhookUnprocessable

    await _post(client, _delivery(field="account_update"))
    (row,) = await _events(session_factory)
    async with session_factory() as session:
        with pytest.raises(WebhookUnprocessable, match="unknown event type"):
            await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)


async def test_dead_letter_isolates_the_event_and_audits_it(
    client, session_factory, dispatched
) -> None:
    from app.services.webhook_service import WebhookUnprocessable

    await _post(client, _delivery(field="account_update"))
    (row,) = await _events(session_factory)

    # Drive the real failure path, so the attempt is counted the way a worker would count it.
    async with session_factory() as session:
        with pytest.raises(WebhookUnprocessable):
            await WebhookService(session).process(row.id, dispatch_inbound=_routed.append)
    async with session_factory() as session:
        entry = await WebhookService(session).dead_letter(row.id, error="unknown event type")

    assert entry.status == WHDL_PENDING and entry.source_event_id == row.id
    # The payload is copied, not referenced: a dead letter outlives its source row (Doc 04 §23.1).
    assert entry.payload_json["field"] == "account_update"
    # The attempt survived the rolled-back transaction that raised.
    assert entry.attempts == 1

    async with session_factory() as session:
        parked = list((await session.scalars(select(WebhookDeadLetter))).all())
        assert len(parked) == 1
        (event,) = list((await session.scalars(select(WebhookEvent))).all())
        assert event.status == WH_FAILED

        from app.models.audit import ACTOR_SYSTEM, AuditLog

        audit = list(
            (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "webhook.dead_lettered")
                )
            ).all()
        )
        assert len(audit) == 1
        assert audit[0].actor_type == ACTOR_SYSTEM and audit[0].entity_id == row.id


def test_poison_event_parks_once_and_the_task_succeeds(monkeypatch) -> None:
    """A poison event is isolated, not retried — and the task *succeeds* at isolating it.

    Synchronous on purpose: the task body calls ``asyncio.run``, which cannot nest inside
    pytest-asyncio's loop (the same reason the migration tests are sync).
    """
    import app.channels.tasks as tasks
    from app.services.webhook_service import WebhookUnprocessable

    parked: list[tuple[int, str]] = []

    async def _boom(event_pk: int):
        raise WebhookUnprocessable("unknown event type 'account_update'")

    async def _park(event_pk: int, error: str):
        parked.append((event_pk, error))
        return {"status": "dead_lettered", "event_pk": event_pk}

    monkeypatch.setattr(tasks, "_process", _boom)
    monkeypatch.setattr(tasks, "_dead_letter", _park)

    result = tasks.process_webhook_event.run(11)

    # Returning (not raising) is what keeps `TrackedTask.on_failure` from parking the same
    # problem a second time in the generic `dead_letter` store (Doc 06 §7 vs Doc 03 §9.4).
    assert result == {"status": "dead_lettered", "event_pk": 11}
    assert len(parked) == 1 and parked[0][0] == 11
    assert "WebhookUnprocessable" in parked[0][1]


def test_transient_failure_retries_rather_than_parking(monkeypatch) -> None:
    """Only poison goes to the DLQ; a retryable failure must go back to the queue (Doc 06 §6)."""
    from celery.exceptions import Retry

    import app.channels.tasks as tasks

    async def _boom(event_pk: int):
        raise ConnectionError("mysql went away")

    async def _park(event_pk: int, error: str):
        raise AssertionError("a transient failure must not be dead-lettered")

    monkeypatch.setattr(tasks, "_process", _boom)
    monkeypatch.setattr(tasks, "_dead_letter", _park)

    # A worker raises `Retry`; a direct call re-raises the original instead (Celery's
    # `called_directly`). Either way the assertion that matters is that `_park` never ran.
    with pytest.raises((Retry, ConnectionError)):
        tasks.process_webhook_event.run(12)


# --- Fan-out (Doc 06 §2.3 webhooks.ingest → webhooks.process) ----------------
async def test_ingest_task_fans_out_one_task_per_event(monkeypatch) -> None:
    import app.channels.tasks as tasks

    calls: list[list[int]] = []
    monkeypatch.setattr(tasks.process_webhook_event, "apply_async", lambda args: calls.append(args))
    assert tasks.ingest_webhook_events.run([7, 8, 9]) == {"dispatched": 3}
    assert calls == [[7], [8], [9]]


# --- The seam (Doc 07 §5.3) --------------------------------------------------
def test_the_adapter_declares_official_webhooks_and_is_resolved_from_the_registry() -> None:
    from app.channels.base import get_adapter
    from app.channels.capabilities import CONNECTOR_META_CLOUD, Capability

    adapter = get_adapter(CONNECTOR_META_CLOUD)
    assert adapter.supports(Capability.OFFICIAL_WEBHOOKS)


def test_a_channel_without_the_capability_refuses_rather_than_guessing() -> None:
    from app.channels.base import ChannelAdapter
    from app.channels.capabilities import ChannelType
    from app.channels.errors import ChannelNotSupported
    from app.channels.models import ChannelStatus

    class Silent(ChannelAdapter):
        channel_type = ChannelType.WHATSAPP
        connector_type = "silent"

        async def authenticate(self) -> ChannelStatus:
            return ChannelStatus(connected=True)

        async def status(self) -> ChannelStatus:
            return ChannelStatus(connected=True)

        async def _dispatch(self, message):
            raise NotImplementedError

    with pytest.raises(ChannelNotSupported):
        Silent().parse_webhook({})
    with pytest.raises(ChannelNotSupported):
        Silent().verify_webhook_signature(b"", None)
