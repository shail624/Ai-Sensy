"""Template registry & template messaging tests (Doc 04 §15/§18.2; FR-TPL-01..04/08) — Module 5.

No network: Meta is an ``httpx.MockTransport`` behind the adapter.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.message import Message
from app.models.template import (
    TPL_APPROVED,
    TPL_DRAFT,
    TPL_PENDING,
    TPL_REJECTED,
    MessageTemplate,
    TemplateVersion,
)
from app.services.template_service import TemplateService
from app.services.template_validation import (
    TemplateInvalid,
    has_media_header,
    render,
    validate_definition,
    variable_count,
)
from app.services.waba_service import WabaService
from tests.test_api_conversations import SENDER, _rows
from tests.test_api_messages import SEND_URL, _headers, _key, _number_id, _open_window

PASSWORD = "Sup3r-Secret-Pass1"
TEMPLATES_URL = "/api/v1/templates"

BODY = {"type": "body", "text": "Hi {{1}}, your order {{2}} is {{3}}."}
HEADER = {"type": "header", "format": "text", "text": "Order {{1}}"}
BUTTONS = {"type": "buttons", "buttons": [{"type": "url", "text": "Track", "url": "https://vi.co/t"}]}
COMPONENTS = [HEADER, BODY, BUTTONS]


@pytest.fixture
def meta(monkeypatch) -> dict:
    """Bind every adapter to a transport that answers Meta's template endpoints."""
    state: dict = {"requests": [], "remote": [], "create": {"id": "tpl-1", "status": "PENDING"}}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        if request.method == "POST" and request.url.path.endswith("/message_templates"):
            return httpx.Response(200, json=state["create"])
        if request.method == "DELETE":
            return httpx.Response(200, json={"success": True})
        if request.url.path.endswith("/message_templates"):
            return httpx.Response(200, json={"data": state["remote"]})
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "wamid.TPL"}]})
        return httpx.Response(200, json={})

    real = WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter.client._owns_http = True
        return adapter

    monkeypatch.setattr(WabaService, "adapter_for", _adapter_for)
    return state


async def _owner(client, make_user) -> dict[str, str]:
    return await _headers(client, make_user, email="owner@vi.co", is_superuser=True)


async def _waba(client, headers) -> str:
    resp = await client.post(
        TEMPLATES_URL.replace("/templates", "/waba"),
        headers=headers,
        json={"waba_id": "waba-100", "business_name": "Vi", "access_token": "tok"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _payload(waba_id: str, **overrides) -> dict:
    payload = {
        "waba_id": waba_id,
        "name": "order_update",
        "language": "en_US",
        "category": "utility",
        "components": COMPONENTS,
    }
    payload.update(overrides)
    return payload


# --- Validation (Doc 04 §15; FR-TPL-02/04) -----------------------------------
def test_a_valid_definition_passes_and_derives_its_metadata() -> None:
    validate_definition(category="utility", components=COMPONENTS)
    # Header {{1}} + body {{1}}{{2}}{{3}} — variables are numbered per component, not globally.
    assert variable_count(COMPONENTS) == 4
    assert has_media_header(COMPONENTS) is False
    assert has_media_header([{"type": "header", "format": "image"}, BODY]) is True


def test_definitions_meta_would_reject_are_refused_first() -> None:
    """Every rule here saves a rejection round-trip (Doc 04 §15)."""
    with pytest.raises(TemplateInvalid, match="Category must be"):
        validate_definition(category="promotional", components=[BODY])
    with pytest.raises(TemplateInvalid, match="body"):
        validate_definition(category="utility", components=[HEADER])
    with pytest.raises(TemplateInvalid, match="no gaps"):
        validate_definition(
            category="utility", components=[{"type": "body", "text": "Hi {{1}} and {{3}}"}]
        )
    with pytest.raises(TemplateInvalid, match="at most 1 variable"):
        validate_definition(
            category="utility",
            components=[{"type": "header", "format": "text", "text": "{{1}} {{2}}"}, BODY],
        )
    with pytest.raises(TemplateInvalid, match="cannot also carry text"):
        validate_definition(
            category="utility",
            components=[{"type": "header", "format": "image", "text": "no"}, BODY],
        )
    with pytest.raises(TemplateInvalid, match="at most 10 buttons"):
        validate_definition(
            category="utility",
            components=[BODY, {"type": "buttons", "buttons": [
                {"type": "quick_reply", "text": f"b{i}"} for i in range(11)]}],
        )
    with pytest.raises(TemplateInvalid, match="footer cannot contain variables"):
        validate_definition(
            category="utility", components=[BODY, {"type": "footer", "text": "Ref {{1}}"}]
        )
    with pytest.raises(TemplateInvalid, match="only one body"):
        validate_definition(category="utility", components=[BODY, BODY])
    with pytest.raises(TemplateInvalid, match="URL button needs a url"):
        validate_definition(
            category="utility",
            components=[BODY, {"type": "buttons", "buttons": [{"type": "url", "text": "Go"}]}],
        )


def test_render_substitutes_and_never_invents_a_value() -> None:
    out = render(COMPONENTS, header=["#1234"], body=["Priya", "#1234", "shipped"])
    assert out["header"] == "Order #1234"
    assert out["body"] == "Hi Priya, your order #1234 is shipped."
    # Too few values leaves the placeholder visible rather than guessing.
    assert render(COMPONENTS, header=[], body=["Priya"])["body"].startswith("Hi Priya, your order {{2}}")


# --- Create & submit (FR-TPL-02/03) ------------------------------------------
async def test_create_submits_to_meta_and_takes_back_its_state(
    client, make_user, session_factory, meta
) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)

    resp = await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == TPL_PENDING and body["variable_count"] == 4
    assert body["has_media_header"] is False and body["is_sendable"] is False
    assert body["waba_id"] == waba_id

    (template,) = await _rows(session_factory, MessageTemplate)
    assert template.meta_template_id == "tpl-1" and template.last_synced_at is not None

    # The definition Meta received is Graph's dialect, built behind the seam.
    import json as _json

    submitted = _json.loads(
        [r for r in meta["requests"] if r.method == "POST"][0].content
    )
    assert submitted["category"] == "UTILITY"
    assert submitted["components"][0] == {"type": "HEADER", "format": "TEXT", "text": "Order {{1}}"}
    assert submitted["components"][2]["buttons"][0]["type"] == "URL"


async def test_a_draft_is_not_submitted(client, make_user, session_factory, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)

    resp = await client.post(
        TEMPLATES_URL, headers=headers, json=_payload(waba_id, submit=False)
    )
    assert resp.status_code == 201 and resp.json()["status"] == TPL_DRAFT
    assert [r for r in meta["requests"] if r.method == "POST"] == []


async def test_meta_may_recategorise_on_submission(client, make_user, session_factory, meta) -> None:
    """Meta's category review is Meta's; its answer wins over what we asked for."""
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    meta["create"] = {"id": "tpl-9", "status": "PENDING", "category": "MARKETING"}

    resp = await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))
    assert resp.json()["category"] == "marketing"


async def test_invalid_definition_never_reaches_meta(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)

    resp = await client.post(
        TEMPLATES_URL,
        headers=headers,
        json=_payload(waba_id, components=[{"type": "body", "text": "Hi {{2}}"}]),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "template_invalid"
    assert [r for r in meta["requests"] if r.method == "POST"] == []


async def test_duplicate_name_and_language_is_409(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))

    resp = await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))
    assert resp.status_code == 409, resp.text
    # Meta's own rule: one template per (WABA, name, language).
    other = await client.post(
        TEMPLATES_URL, headers=headers, json=_payload(waba_id, language="hi_IN")
    )
    assert other.status_code == 201


async def test_a_channel_failure_surfaces_as_502(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    meta["create"] = None

    def _boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "meta is down", "code": 2}})

    import app.services.waba_service as waba_service

    real = waba_service.WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(transport=httpx.MockTransport(_boom))
        adapter.client._owns_http = True
        return adapter

    waba_service.WabaService.adapter_for = _adapter_for
    try:
        resp = await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))
    finally:
        waba_service.WabaService.adapter_for = real
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "channel_error"


# --- Edit, versions & delete (Doc 04 §15) ------------------------------------
async def test_editing_a_draft_records_a_version(client, make_user, session_factory, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    created = (
        await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id, submit=False))
    ).json()

    resp = await client.patch(
        f"{TEMPLATES_URL}/{created['id']}",
        headers=headers,
        json={"components": [{"type": "body", "text": "Hi {{1}}, we shipped it."}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["variable_count"] == 1

    versions = (await client.get(f"{TEMPLATES_URL}/{created['id']}/versions", headers=headers))
    # Immutable history: what a message was sent against stays readable after the edit.
    assert [v["version_no"] for v in versions.json()["data"]] == [2, 1]
    assert versions.json()["data"][1]["components"][0]["type"] == "header"
    assert len(await _rows(session_factory, TemplateVersion)) == 2


async def test_an_approved_template_cannot_be_edited(
    client, make_user, session_factory, meta
) -> None:
    """Once Meta owns the state, an edit here would just be overwritten by the next sync."""
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()

    async with session_factory() as session:
        (template,) = list(
            (await session.scalars(__import__("sqlalchemy").select(MessageTemplate))).all()
        )
        template.status = TPL_APPROVED
        await session.commit()

    resp = await client.patch(
        f"{TEMPLATES_URL}/{created['id']}", headers=headers, json={"category": "marketing"}
    )
    assert resp.status_code == 409, resp.text


async def test_a_rejected_template_can_be_fixed_and_resubmitted(
    client, make_user, session_factory, meta
) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()

    async with session_factory() as session:
        (template,) = list(
            (await session.scalars(__import__("sqlalchemy").select(MessageTemplate))).all()
        )
        template.status = TPL_REJECTED
        template.rejection_reason = "Body text is promotional"
        await session.commit()

    resp = await client.patch(
        f"{TEMPLATES_URL}/{created['id']}",
        headers=headers,
        json={"category": "marketing", "submit": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == TPL_PENDING
    # The old reason must not linger on a template that has been resubmitted.
    assert resp.json()["rejection_reason"] is None


async def test_delete_withdraws_from_meta_then_removes_locally(
    client, make_user, session_factory, meta
) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()

    resp = await client.delete(f"{TEMPLATES_URL}/{created['id']}", headers=headers)
    assert resp.status_code == 204, resp.text
    assert [r for r in meta["requests"] if r.method == "DELETE"]
    assert (await client.get(f"{TEMPLATES_URL}/{created['id']}", headers=headers)).status_code == 404


# --- Sync (FR-TPL-01/03) -----------------------------------------------------
def _remote(name: str = "order_update", **overrides) -> dict:
    node = {
        "id": "tpl-remote-1",
        "name": name,
        "language": "en_US",
        "category": "UTILITY",
        "status": "APPROVED",
        "components": [
            {"type": "BODY", "text": "Hi {{1}}, your order is ready."},
            {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "Thanks"}]},
        ],
        "quality_score": {"score": "GREEN"},
    }
    node.update(overrides)
    return node


async def test_sync_returns_202_and_enqueues_without_calling_meta(
    client, make_user, meta
) -> None:
    headers = await _owner(client, make_user)
    await _waba(client, headers)

    dispatched: list = []
    import app.channels.tasks as tasks

    tasks.run_template_sync.apply_async = lambda args, task_id: dispatched.append((args, task_id))

    resp = await client.post(f"{TEMPLATES_URL}/sync", headers=headers)
    assert resp.status_code == 202, resp.text
    job = resp.json()["job"]
    assert job["type"] == "template_sync" and job["status"] == "queued"
    assert dispatched and len(dispatched[0][0][0]) == 1
    assert meta["requests"] == []


async def test_sync_creates_updates_and_removes(client, make_user, session_factory, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    meta["remote"] = [_remote(), _remote("welcome", id="tpl-remote-2", status="REJECTED",
                                        rejected_reason="Promotional content")]

    async with session_factory() as session:
        result = await TemplateService(session).run_sync([waba_id])
    assert result == {"created": 2, "updated": 0, "removed": 0}

    listing = (await client.get(TEMPLATES_URL, headers=headers)).json()["data"]
    order = next(t for t in listing if t["name"] == "order_update")
    assert order["status"] == TPL_APPROVED and order["quality_score"] == "GREEN"
    assert order["is_sendable"] is True and order["variable_count"] == 1
    # Graph's uppercase dialect never reaches the registry.
    assert order["components"][0] == {"type": "body", "text": "Hi {{1}}, your order is ready."}
    assert order["components"][1]["buttons"][0]["type"] == "quick_reply"

    welcome = next(t for t in listing if t["name"] == "welcome")
    assert welcome["status"] == TPL_REJECTED
    assert welcome["rejection_reason"] == "Promotional content"

    # Second sync: order_update is paused, welcome is gone.
    meta["remote"] = [_remote(status="PAUSED")]
    async with session_factory() as session:
        result = await TemplateService(session).run_sync([waba_id])
    assert result == {"created": 0, "updated": 1, "removed": 1}
    listing = (await client.get(TEMPLATES_URL, headers=headers)).json()["data"]
    assert [t["name"] for t in listing] == ["order_update"]
    assert listing[0]["status"] == "paused" and listing[0]["is_sendable"] is False


async def test_sync_is_idempotent(client, make_user, session_factory, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    meta["remote"] = [_remote()]

    async with session_factory() as session:
        assert (await TemplateService(session).run_sync([waba_id]))["created"] == 1
    async with session_factory() as session:
        assert (await TemplateService(session).run_sync([waba_id]))["updated"] == 1
    assert len(await _rows(session_factory, MessageTemplate)) == 1


async def test_sync_leaves_unsubmitted_drafts_alone(
    client, make_user, session_factory, meta
) -> None:
    """A draft Meta has never seen is ours; its absence from Meta proves nothing."""
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id, submit=False))
    meta["remote"] = []

    async with session_factory() as session:
        assert (await TemplateService(session).run_sync([waba_id]))["removed"] == 0
    assert len((await client.get(TEMPLATES_URL, headers=headers)).json()["data"]) == 1


# --- Listing, preview & permissions ------------------------------------------
async def test_list_filters(client, make_user, session_factory, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    meta["remote"] = [_remote(), _remote("promo", id="tpl-3", category="MARKETING")]
    async with session_factory() as session:
        await TemplateService(session).run_sync([waba_id])

    marketing = await client.get(f"{TEMPLATES_URL}?category=marketing", headers=headers)
    assert [t["name"] for t in marketing.json()["data"]] == ["promo"]
    approved = await client.get(f"{TEMPLATES_URL}?status=approved", headers=headers)
    assert len(approved.json()["data"]) == 2
    by_waba = await client.get(f"{TEMPLATES_URL}?waba={waba_id}", headers=headers)
    assert len(by_waba.json()["data"]) == 2
    searched = await client.get(f"{TEMPLATES_URL}?q=prom", headers=headers)
    assert [t["name"] for t in searched.json()["data"]] == ["promo"]


async def test_preview_renders_with_sample_values(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()

    resp = await client.get(
        f"{TEMPLATES_URL}/{created['id']}/preview?header=%231234&body=Priya&body=%231234&body=shipped",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "header": "Order #1234",
        "body": "Hi Priya, your order #1234 is shipped.",
        "footer": "",
    }


async def test_template_permissions(client, make_user, meta) -> None:
    owner = await _owner(client, make_user)
    waba_id = await _waba(client, owner)
    # An agent reads templates to reply with them, but may not author or sync them.
    agent = await _headers(client, make_user, email="agent2@vi.co", roles=("agent",))

    assert (await client.get(TEMPLATES_URL, headers=agent)).status_code == 200
    assert (
        await client.post(TEMPLATES_URL, headers=agent, json=_payload(waba_id))
    ).status_code == 403
    assert (await client.post(f"{TEMPLATES_URL}/sync", headers=agent)).status_code == 403

    viewer = await _headers(client, make_user, email="viewer@vi.co", roles=("viewer",))
    assert (await client.get(TEMPLATES_URL, headers=viewer)).status_code == 403
    assert (await client.get(TEMPLATES_URL)).status_code == 401


async def test_unknown_template_is_404(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    assert (await client.get(f"{TEMPLATES_URL}/{uuid.uuid4()}", headers=headers)).status_code == 404


async def test_template_actions_are_audited(client, make_user, meta) -> None:
    headers = await _owner(client, make_user)
    waba_id = await _waba(client, headers)
    await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))

    entries = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=template.created", headers=headers
    )
    assert len(entries.json()["data"]) == 1


# --- Template sending (Doc 04 §18.2; FR-TPL-03/04) ---------------------------
async def _approved_template(client, session_factory, headers, waba_id: str) -> dict:
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()
    async with session_factory() as session:
        (template,) = list(
            (await session.scalars(__import__("sqlalchemy").select(MessageTemplate))).all()
        )
        template.status = TPL_APPROVED
        await session.commit()
    return created


def _send_body(number_id: str, template_id: str, **overrides) -> dict:
    template = {
        "id": template_id,
        "header": ["#1234"],
        "body": ["Priya", "#1234", "shipped"],
        "buttons": [{"index": 0, "type": "url", "value": "1234"}],
    }
    template.update(overrides.pop("template", {}))
    return {
        "phone_number_id": number_id,
        "to": f"+{SENDER}",
        "type": "template",
        "template": template,
        **overrides,
    }


async def test_template_send_is_accepted_and_dispatched_as_values(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template = await _approved_template(client, session_factory, headers, waba_id)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_send_body(await _number_id(client, headers), template["id"]),
    )
    assert resp.status_code == 202, resp.text

    message = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert message.message_type == "template"
    # The ledger records what was sent and what it costs to send (Doc 03 §9.2).
    assert message.template_id is not None and message.category == "utility"
    assert message.content_json["template"]["name"] == "order_update"

    from app.services.send_service import SendService

    async with session_factory() as session:
        await SendService(session).deliver(message.id)

    import json as _json

    body = _json.loads([r for r in meta["requests"] if r.url.path.endswith("/messages")][0].content)
    assert body["template"]["name"] == "order_update"
    assert body["template"]["language"] == {"code": "en_US"}
    # Graph's parameter shape was built behind the seam, from the values we stored.
    assert body["template"]["components"] == [
        {"type": "header", "parameters": [{"type": "text", "text": "#1234"}]},
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": "Priya"},
                {"type": "text", "text": "#1234"},
                {"type": "text", "text": "shipped"},
            ],
        },
        {"type": "button", "sub_type": "url", "index": "0",
         "parameters": [{"type": "text", "text": "1234"}]},
    ]


async def test_a_template_crosses_a_closed_window(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """The whole point of a template: re-engaging a customer whose window has lapsed (FR-WA-12)."""
    from tests.test_api_webhooks import _seed_number

    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template = await _approved_template(client, session_factory, headers, waba_id)
    number_id = await _number_id(client, headers)

    # Free-form to a contact who never messaged us is refused …
    free_form = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json={"phone_number_id": number_id, "to": f"+{SENDER}", "type": "text",
              "text": {"body": "hello?"}},
    )
    assert free_form.status_code == 422 and free_form.json()["code"] == "window_closed"

    # … the template is not.
    resp = await client.post(
        SEND_URL, headers=headers | _key(), json=_send_body(number_id, template["id"])
    )
    assert resp.status_code == 202, resp.text


async def test_an_unapproved_template_cannot_be_sent(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    created = (await client.post(TEMPLATES_URL, headers=headers, json=_payload(waba_id))).json()

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_send_body(await _number_id(client, headers), created["id"]),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "template_not_sendable"
    assert sent == []


async def test_wrong_variable_counts_are_refused(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    """Checked here, where the caller can fix it — not an hour later from a failed delivery."""
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template = await _approved_template(client, session_factory, headers, waba_id)
    number_id = await _number_id(client, headers)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_send_body(number_id, template["id"], template={"body": ["Priya"]}),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "template_variables"
    assert "needs 3 body variable(s); 1 supplied" in resp.json()["detail"]
    assert sent == []


async def test_sending_an_unknown_template_is_404(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_send_body(await _number_id(client, headers), str(uuid.uuid4())),
    )
    assert resp.status_code == 404, resp.text


async def test_a_template_send_previews_as_the_customer_will_read_it(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, meta
) -> None:
    from app.models.conversation import Conversation

    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template = await _approved_template(client, session_factory, headers, waba_id)

    await client.post(
        SEND_URL,
        headers=headers | _key(),
        json=_send_body(await _number_id(client, headers), template["id"]),
    )
    (conversation,) = await _rows(session_factory, Conversation)
    assert conversation.last_message_preview == "Hi Priya, your order #1234 is shipped."


def test_template_sync_task_is_bound_to_the_sync_lane() -> None:
    import app.channels.tasks as tasks

    assert tasks.run_template_sync.queue_name == "templates.sync"
