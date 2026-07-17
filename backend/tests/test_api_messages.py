"""Outbound send tests (Doc 04 §8/§18.2; FR-WA-10/12) — Module 4 outbound messaging.

No network and no broker: Meta is an ``httpx.MockTransport`` behind the adapter, the send task's
dispatch is captured, and the idempotency store is an in-memory stand-in.
"""

from __future__ import annotations

import uuid
from datetime import UTC

import httpx
import pytest

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.channels.errors import ChannelTransportError
from app.db.mixins import utcnow
from app.models.contact import OPT_IN_OPTED_OUT
from app.models.conversation import Conversation
from app.models.message import MSG_ACCEPTED, MSG_FAILED, MSG_SENT, Message
from app.services.message_service import MessageService
from app.services.send_service import SendService
from app.services.waba_service import WabaService
from app.services.webhook_service import WebhookService
from tests.test_api_conversations import SENDER, _rows
from tests.test_api_webhooks import _delivery, _events, _message, _post, _seed_number

PASSWORD = "Sup3r-Secret-Pass1"
SEND_URL = "/api/v1/messages/send"
WAMID_OUT = "wamid.OUTBOUND-1"


@pytest.fixture
def meta(monkeypatch) -> dict:
    """Bind every adapter the send path builds to a mock transport."""
    state: dict = {
        "handler": lambda request: httpx.Response(
            200,
            json={
                "messaging_product": "whatsapp",
                "contacts": [{"wa_id": SENDER}],
                "messages": [{"id": WAMID_OUT}],
            },
        ),
        "requests": [],
    }
    real = WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        def handler(request: httpx.Request) -> httpx.Response:
            state["requests"].append(request)
            return state["handler"](request)

        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter.client._owns_http = True
        return adapter

    monkeypatch.setattr(WabaService, "adapter_for", _adapter_for)
    return state


async def _headers(client, make_user, *, email: str = "owner@vi.co", **kw) -> dict[str, str]:
    await make_user(email=email, password=PASSWORD, **kw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _number_id(client, headers) -> str:
    numbers = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"]
    return numbers[0]["id"]


async def _open_window(client, session_factory, monkeypatch, make_user) -> None:
    """An inbound message from the customer — the only thing that opens the 24h window."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    just_now = _message() | {"timestamp": str(int(utcnow().replace(tzinfo=UTC).timestamp()))}
    await _post(client, _delivery(messages=[just_now]))
    routed: list[int] = []
    for row in await _events(session_factory):
        async with session_factory() as session:
            await WebhookService(session).process(row.id, dispatch_inbound=routed.append)
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])


def _body(number_id: str, **overrides) -> dict:
    payload = {
        "phone_number_id": number_id,
        "to": f"+{SENDER}",
        "type": "text",
        "text": {"body": "on it, thanks!"},
    }
    payload.update(overrides)
    return payload


def _key() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


# --- Accept (Doc 04 §18.2 — 202) ---------------------------------------------
async def test_send_accepts_and_queues_without_calling_meta(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    number_id = await _number_id(client, headers)

    resp = await client.post(SEND_URL, headers=headers | _key(), json=_body(number_id))
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == MSG_ACCEPTED
    # Only Meta issues a wamid, and it has not been asked yet.
    assert body["wamid"] is None and body["conversation_id"]
    assert body["queued_at"]

    # Nothing was sent on the request path.
    assert meta["requests"] == []
    outbound = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"]
    assert len(outbound) == 1 and outbound[0].status == MSG_ACCEPTED
    assert outbound[0].content_json == {"body": "on it, thanks!", "preview_url": False}
    assert sent == [outbound[0].id]


async def test_send_updates_the_thread_but_not_the_unread_count(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    (before,) = await _rows(session_factory, Conversation)

    await client.post(
        SEND_URL, headers=headers | _key(), json=_body(await _number_id(client, headers))
    )

    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.last_message_preview == "on it, thanks!"
    assert conversation.last_message_at > before.last_message_at
    # Unread counts what the customer said that nobody has read; our own reply is not that.
    assert conversation.unread_count == before.unread_count
    # The window belongs to the customer's last inbound, and we did not change it.
    assert conversation.last_inbound_at == before.last_inbound_at


async def test_send_is_audited(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    await client.post(
        SEND_URL, headers=headers | _key(), json=_body(await _number_id(client, headers))
    )

    entries = (await client.get("/api/v1/audit-logs?filter[action][eq]=message.sent", headers=headers))
    assert len(entries.json()["data"]) == 1


# --- 24-hour window (FR-WA-12; Doc 04 §18.2) ---------------------------------
async def test_free_form_outside_the_window_is_422(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """The default fixture message is a year old, so the thread's window is long closed."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[_message()]))
    routed: list[int] = []
    for row in await _events(session_factory):
        async with session_factory() as session:
            await WebhookService(session).process(row.id, dispatch_inbound=routed.append)
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    resp = await client.post(
        SEND_URL, headers=headers | _key(), json=_body(await _number_id(client, headers))
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "window_closed"
    # Nothing was accepted, queued, or written.
    assert sent == []
    assert [m for m in await _rows(session_factory, Message) if m.direction == "outbound"] == []


async def test_first_contact_has_no_window(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """A customer who has never messaged us cannot be sent free-form at all (FR-WA-12)."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_body(await _number_id(client, headers), to="+14155559999"),
    )
    assert resp.status_code == 422 and resp.json()["code"] == "window_closed"


async def test_opted_out_contact_is_refused(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    from app.models.contact import Contact

    async with session_factory() as session:
        (contact,) = list((await session.scalars(__import__("sqlalchemy").select(Contact))).all())
        contact.opt_in_status = OPT_IN_OPTED_OUT
        await session.commit()

    resp = await client.post(
        SEND_URL, headers=headers | _key(), json=_body(await _number_id(client, headers))
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "opt_out"
    assert sent == []


# --- Idempotency (Doc 04 §8) -------------------------------------------------
async def test_idempotency_key_is_required(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    resp = await client.post(SEND_URL, headers=headers, json=_body(await _number_id(client, headers)))
    assert resp.status_code == 422, resp.text
    assert resp.json()["errors"][0]["field"] == "Idempotency-Key"
    assert sent == []


async def test_retry_with_the_same_key_replays_instead_of_sending_twice(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """The client that times out has no way to know whether the message went out."""
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    number_id = await _number_id(client, headers)
    key = _key()

    first = await client.post(SEND_URL, headers=headers | key, json=_body(number_id))
    second = await client.post(SEND_URL, headers=headers | key, json=_body(number_id))

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    # One message, one queued task — the retry acted on neither.
    assert len([m for m in await _rows(session_factory, Message) if m.direction == "outbound"]) == 1
    assert len(sent) == 1


async def test_a_key_held_by_an_in_flight_request_is_409(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    key = _key()
    # Claimed, but no response recorded yet: the first attempt is still running.
    idem.store[f"idem:{key['Idempotency-Key']}"] = "__in_flight__"

    resp = await client.post(
        SEND_URL, headers=headers | key, json=_body(await _number_id(client, headers))
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "idempotency_in_flight"


async def test_a_rejected_send_releases_its_key(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """A 422 must not burn the key: nothing was sent, so the corrected retry may act."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    key = _key()

    rejected = await client.post(
        SEND_URL,
        headers=headers | key,
        json=_body(await _number_id(client, headers), to="+14155559999"),
    )
    assert rejected.status_code == 422
    assert idem.store == {}


async def test_send_fails_closed_without_an_idempotency_store(
    client, make_user, session_factory, monkeypatch, dispatched, sent, meta
) -> None:
    """A lost idempotency record costs a duplicate message to a real person."""
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    class _Down:
        async def set(self, *a, **k):
            raise ConnectionError("redis is down")

    import app.api.v1.endpoints.messages as endpoint

    monkeypatch.setattr(endpoint, "get_redis_client", lambda: _Down())
    resp = await client.post(
        SEND_URL, headers=headers | _key(), json=_body(await _number_id(client, headers))
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["code"] == "idempotency_unavailable"
    assert sent == []


# --- Deliver (Doc 06 §2.3 `sends.priority`) ----------------------------------
async def _accepted(client, make_user, session_factory, monkeypatch, **overrides) -> Message:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_body(await _number_id(client, headers), **overrides),
    )
    assert resp.status_code == 202, resp.text
    return [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]


async def test_deliver_sends_through_the_adapter_and_records_the_wamid(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    message = await _accepted(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        result = await SendService(session).deliver(message.id)
    assert result["status"] == "sent" and result["wamid"] == WAMID_OUT

    stored = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert stored.wamid == WAMID_OUT
    # The status stays `accepted`: only a webhook can say it was actually sent (Doc 06 §11).
    assert stored.status == MSG_ACCEPTED
    assert meta["requests"] and meta["requests"][0].url.path.endswith("/messages")


async def test_delivery_is_idempotent_on_the_wamid(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """At-least-once task delivery must not become at-least-once *sending* (Doc 06 §8)."""
    message = await _accepted(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        await SendService(session).deliver(message.id)
    calls = len(meta["requests"])

    async with session_factory() as session:
        again = await SendService(session).deliver(message.id)
    assert again["status"] == "already_sent"
    assert len(meta["requests"]) == calls


async def test_the_status_webhook_advances_a_sent_message(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """The full loop: accept → deliver → Meta's callback moves the ledger forward."""
    from tests.test_api_webhooks import _status

    message = await _accepted(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        await SendService(session).deliver(message.id)

    await _post(client, _delivery(statuses=[_status("sent", wamid=WAMID_OUT)]))
    for row in await _events(session_factory):
        if row.object_type == "statuses":
            async with session_factory() as session:
                await WebhookService(session).process(row.id, dispatch_inbound=lambda _: None)

    stored = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert stored.status == MSG_SENT and stored.sent_at is not None


async def test_terminal_send_failure_is_recorded_on_the_message(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """The ledger is where a failed send belongs — not a parked task nobody reads."""
    from app.channels.meta.errors import MetaApiError
    from app.models.message import MessageStatusHistory

    message = await _accepted(client, make_user, session_factory, monkeypatch)
    meta["handler"] = lambda request: httpx.Response(
        400, json={"error": {"message": "Recipient not a WhatsApp user", "code": 131026}}
    )

    async with session_factory() as session:
        with pytest.raises(MetaApiError) as raised:
            await SendService(session).deliver(message.id)
    async with session_factory() as session:
        await SendService(session).fail(
            message.id, error=str(raised.value), code=str(raised.value.code)
        )

    stored = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert stored.status == MSG_FAILED and stored.error_code == "131026"
    history = await _rows(session_factory, MessageStatusHistory)
    assert [h.status for h in history] == [MSG_FAILED]
    assert history[0].error_detail.startswith("Recipient not a WhatsApp user")


def test_a_terminal_meta_error_fails_the_message_rather_than_retrying(monkeypatch) -> None:
    """131026 (not a WhatsApp user) is terminal in Meta's error map — retrying is a certainty."""
    import app.channels.tasks as tasks
    from app.channels.meta.errors import MetaApiError

    failed: list[tuple[int, str | None]] = []

    async def _boom(message_pk: int):
        raise MetaApiError("Recipient not a WhatsApp user", code=131026)

    async def _fail(message_pk: int, error: str, code: str | None):
        failed.append((message_pk, code))
        return {"status": MSG_FAILED, "message_pk": message_pk}

    monkeypatch.setattr(tasks, "_deliver", _boom)
    monkeypatch.setattr(tasks, "_fail_send", _fail)

    assert tasks.send_message.run(9)["status"] == MSG_FAILED
    assert failed == [(9, "131026")]


def test_transient_send_failure_retries_rather_than_failing_the_message(monkeypatch) -> None:
    from celery.exceptions import Retry

    import app.channels.tasks as tasks

    async def _boom(message_pk: int):
        raise ChannelTransportError("Meta request timed out: /messages")

    async def _fail(message_pk: int, error: str, code: str | None):
        raise AssertionError("a transient failure must not mark the message failed")

    monkeypatch.setattr(tasks, "_deliver", _boom)
    monkeypatch.setattr(tasks, "_fail_send", _fail)
    with pytest.raises((Retry, ChannelTransportError)):
        tasks.send_message.run(3)


def test_send_task_is_bound_to_the_priority_lane() -> None:
    import app.channels.tasks as tasks

    assert tasks.send_message.queue_name == "sends.priority"


# --- Reads (Doc 04 §18.2) ----------------------------------------------------
async def test_get_message_and_status_history(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    message = await _accepted(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="reader@vi.co", roles=("agent",))

    fetched = await client.get(f"/api/v1/messages/{message.public_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["direction"] == "outbound"
    assert fetched.json()["status"] == MSG_ACCEPTED
    assert fetched.json()["content"]["body"] == "on it, thanks!"

    history = await client.get(
        f"/api/v1/messages/{message.public_id}/status-history", headers=headers
    )
    assert history.status_code == 200 and history.json()["data"] == []
    assert (
        await client.get(f"/api/v1/messages/{uuid.uuid4()}", headers=headers)
    ).status_code == 404


async def test_send_permission_is_enforced(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    owner = await _headers(client, make_user, email="owner2@vi.co", is_superuser=True)
    number_id = await _number_id(client, owner)

    viewer = await _headers(client, make_user, email="viewer@vi.co", roles=("viewer",))
    resp = await client.post(SEND_URL, headers=viewer | _key(), json=_body(number_id))
    assert resp.status_code == 403, resp.text
    assert (await client.post(SEND_URL, json=_body(number_id))).status_code == 401


# --- Request validation ------------------------------------------------------
async def test_payload_must_match_its_type(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    number_id = await _number_id(client, headers)

    mismatched = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json={"phone_number_id": number_id, "to": f"+{SENDER}", "type": "text",
              "media": {"kind": "image", "link": "https://x/y.jpg"}},
    )
    assert mismatched.status_code == 422

    both = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json={"phone_number_id": number_id, "to": f"+{SENDER}", "type": "media",
              "media": {"kind": "image", "link": "https://x/y.jpg", "media_id": "m-1"}},
    )
    assert both.status_code == 422


async def test_media_send_is_stored_and_dispatched_canonically(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    message = await _accepted(
        client, make_user, session_factory, monkeypatch,
        type="media", text=None,
        media={"kind": "image", "link": "https://cdn.vi/bill.jpg", "caption": "your bill"},
    )
    # Doc 03 §9.2's vocabulary is per-kind: an image is an `image`, not a `media`.
    assert message.message_type == "image"

    async with session_factory() as session:
        await SendService(session).deliver(message.id)

    import json as _json

    body = _json.loads(meta["requests"][0].content)
    assert body["type"] == "image"
    assert body["image"] == {"link": "https://cdn.vi/bill.jpg", "caption": "your bill"}


async def test_unknown_number_is_404(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    resp = await client.post(
        SEND_URL, headers=headers | _key(), json=_body(str(uuid.uuid4()))
    )
    assert resp.status_code == 404, resp.text
