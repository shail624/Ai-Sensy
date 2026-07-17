"""Campaign registry & audience tests (Doc 04 §17; FR-CAM-01/02) — Phase 6 Step 1.

No network: templates are approved directly in the database, and nothing here sends.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.campaign import (
    CAMPAIGN_DRAFT,
    CAMPAIGN_RUNNING,
    RECIPIENT_PENDING,
    Campaign,
    CampaignRecipient,
)
from app.models.contact import OPT_IN_OPTED_OUT, Contact
from app.models.template import TPL_APPROVED, MessageTemplate
from tests.test_api_conversations import _rows
from tests.test_api_messages import _headers
from tests.test_api_templates import _payload

CAMPAIGNS_URL = "/api/v1/campaigns"
PASSWORD = "Sup3r-Secret-Pass1"


async def _owner(client, make_user) -> dict[str, str]:
    return await _headers(client, make_user, email="owner@vi.co", is_superuser=True)


async def _number(client, headers, session_factory, monkeypatch) -> str:
    from tests.test_api_webhooks import _seed_number

    await _seed_number(client, make_user=None, session_factory=session_factory, monkeypatch=monkeypatch) \
        if False else None
    return ""


async def _approved_template(client, headers, session_factory, waba_id: str) -> str:
    created = (
        await client.post(
            "/api/v1/templates", headers=headers, json=_payload(waba_id, submit=False)
        )
    ).json()
    async with session_factory() as session:
        (template,) = list((await session.scalars(select(MessageTemplate))).all())
        template.status = TPL_APPROVED
        await session.commit()
    return created["id"]


async def _contacts(client, headers, count: int, **overrides) -> list[dict]:
    made = []
    for i in range(count):
        body = {"phone_e164": f"+9199903293{i:02d}", "full_name": f"Contact {i}"}
        body.update(overrides)
        resp = await client.post("/api/v1/contacts", headers=headers, json=body)
        assert resp.status_code == 201, resp.text
        made.append(resp.json())
    return made


async def _setup(client, make_user, session_factory, monkeypatch):
    """An owner, a synced number, an approved template and three contacts."""
    from tests.test_api_webhooks import _seed_number

    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template_id = await _approved_template(client, headers, session_factory, waba_id)
    number_id = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"][0]["id"]
    contacts = await _contacts(client, headers, 3)
    return headers, number_id, template_id, contacts


def _body(number_id: str, template_id: str, contacts: list[dict], **overrides) -> dict:
    payload = {
        "name": "Vi Reactivation",
        "phone_number_id": number_id,
        "template_id": template_id,
        "audience_type": "list",
        "audience_ref": {"contact_ids": [c["id"] for c in contacts]},
        # The fixture template declares header {{1}} and body {{1}}{{2}}{{3}}.
        "variable_map": {
            "header": [{"source": "literal", "value": "#1234"}],
            "body": [
                {"source": "field", "key": "full_name", "fallback": "there"},
                {"source": "literal", "value": "#1234"},
                {"source": "attribute", "key": "order_state", "fallback": "shipped"},
            ],
        },
    }
    payload.update(overrides)
    return payload


# --- Create & materialize (FR-CAM-01) ----------------------------------------
async def test_create_resolves_the_audience_into_a_roster(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    resp = await client.post(
        CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts)
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == CAMPAIGN_DRAFT and body["total_recipients"] == 3
    assert body["phone_number_id"] == number_id and body["template_id"] == template_id
    # Internal bookkeeping must not leak into the audience the caller specified.
    assert "_excluded_opted_out" not in (body["audience_ref"] or {})

    rows = await _rows(session_factory, CampaignRecipient)
    assert len(rows) == 3 and all(r.status == RECIPIENT_PENDING for r in rows)
    # Variables are resolved per contact at materialization, not at send.
    resolved = {r.variables_json["body"][0] for r in rows}
    assert resolved == {"Contact 0", "Contact 1", "Contact 2"}
    assert rows[0].variables_json["header"] == ["#1234"]
    # An attribute the contact lacks falls back rather than rendering a hole.
    assert rows[0].variables_json["body"][2] == "shipped"


async def test_a_field_mapping_falls_back_when_the_contact_lacks_it(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, _ = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    nameless = (
        await client.post("/api/v1/contacts", headers=headers, json={"phone_e164": "+919000000001"})
    ).json()

    await client.post(
        CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, [nameless])
    )
    (row,) = await _rows(session_factory, CampaignRecipient)
    # Meta rejects an empty parameter, so the fallback is what keeps the send valid.
    assert row.variables_json["body"][0] == "there"


# --- Opt-in validation (FR-CAM-02) -------------------------------------------
async def test_opted_out_contacts_are_excluded_from_the_roster(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The count an operator approves must be the count that gets messaged."""
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    async with session_factory() as session:
        rows = list((await session.scalars(select(Contact))).all())
        rows[0].opt_in_status = OPT_IN_OPTED_OUT
        await session.commit()

    resp = await client.post(
        CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts)
    )
    assert resp.json()["total_recipients"] == 2
    assert len(await _rows(session_factory, CampaignRecipient)) == 2

    preview = await client.post(
        f"{CAMPAIGNS_URL}/{resp.json()['id']}/preview", headers=headers
    )
    assert preview.json()["total"] == 2 and preview.json()["excluded_opted_out"] == 1


# --- Template eligibility (FR-CAM-02) ----------------------------------------
async def test_an_unapproved_template_cannot_be_broadcast(
    client, make_user, session_factory, monkeypatch
) -> None:
    from tests.test_api_webhooks import _seed_number

    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    # Created but left a draft — Meta has never approved it.
    template = (
        await client.post(
            "/api/v1/templates", headers=headers, json=_payload(waba_id, submit=False)
        )
    ).json()
    number_id = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"][0]["id"]
    contacts = await _contacts(client, headers, 1)

    resp = await client.post(
        CAMPAIGNS_URL, headers=headers, json=_body(number_id, template["id"], contacts)
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "template_not_eligible"
    assert await _rows(session_factory, Campaign) == []


# --- Variable mapping validation (FR-CAM-01) ---------------------------------
async def test_the_map_must_fill_exactly_the_templates_placeholders(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    resp = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(
            number_id, template_id, contacts,
            variable_map={"header": [{"source": "literal", "value": "x"}],
                          "body": [{"source": "field", "key": "full_name"}]},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "campaign_invalid"
    assert "needs 3 body variable mapping(s); 1 supplied" in resp.json()["detail"]


async def test_a_campaign_cannot_interpolate_a_field_that_is_not_a_whitelist(
    client, make_user, session_factory, monkeypatch
) -> None:
    """A campaign must not be able to put `password_hash` in a message to a customer."""
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    resp = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(
            number_id, template_id, contacts,
            variable_map={
                "header": [{"source": "literal", "value": "x"}],
                "body": [
                    {"source": "field", "key": "password_hash"},
                    {"source": "literal", "value": "a"},
                    {"source": "literal", "value": "b"},
                ],
            },
        ),
    )
    assert resp.status_code == 422 and resp.json()["code"] == "campaign_invalid"


# --- Audience sources --------------------------------------------------------
async def test_a_tag_audience_resolves_every_tagged_contact(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    tag = (await client.post("/api/v1/tags", headers=headers, json={"name": "lapsed"})).json()
    for contact in contacts[:2]:
        resp = await client.post(
            f"/api/v1/contacts/{contact['id']}/tags", headers=headers, json={"tags": [tag["id"]]}
        )
        assert resp.status_code in (200, 201, 204), resp.text

    resp = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, audience_type="tag",
                   audience_ref={"tag_ids": [tag["id"]]}),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_recipients"] == 2


async def test_a_segment_audience_uses_the_segments_own_rules(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The campaign asks the segment; it never reimplements the rules."""
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    segment = (
        await client.post(
            "/api/v1/segments",
            headers=headers,
            json={
                "name": "Named contacts",
                "match_type": "all",
                "rules": [
                    {"field_source": "contact", "field_key": "full_name",
                     "operator": "eq", "value": "Contact 1"}
                ],
            },
        )
    ).json()

    resp = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, audience_type="segment",
                   audience_ref={"segment_id": segment["id"]}),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_recipients"] == 1


async def test_an_upload_audience_is_refused_with_a_reason(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    resp = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, audience_type="upload", audience_ref={}),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "audience_invalid"


async def test_an_empty_or_unknown_audience_is_refused(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    empty = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, audience_type="tag", audience_ref={}),
    )
    assert empty.status_code == 422 and empty.json()["code"] == "audience_invalid"

    unknown = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json=_body(number_id, template_id, contacts, audience_type="segment",
                   audience_ref={"segment_id": str(uuid.uuid4())}),
    )
    assert unknown.status_code == 404


# --- Draft lifecycle (Doc 04 §17) --------------------------------------------
async def test_editing_a_draft_rebuilds_the_roster(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The roster is derived: a stale row would send the wrong message to a real person."""
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    assert created["total_recipients"] == 3

    resp = await client.patch(
        f"{CAMPAIGNS_URL}/{created['id']}",
        headers=headers,
        json={"audience_ref": {"contact_ids": [contacts[0]["id"]]}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_recipients"] == 1
    assert len(await _rows(session_factory, CampaignRecipient)) == 1


async def test_a_running_campaign_cannot_be_edited_or_deleted(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    async with session_factory() as session:
        (campaign,) = list((await session.scalars(select(Campaign))).all())
        campaign.status = CAMPAIGN_RUNNING
        await session.commit()

    edit = await client.patch(
        f"{CAMPAIGNS_URL}/{created['id']}", headers=headers, json={"name": "Renamed"}
    )
    assert edit.status_code == 409, edit.text
    remove = await client.delete(f"{CAMPAIGNS_URL}/{created['id']}", headers=headers)
    assert remove.status_code == 409


async def test_stale_version_is_rejected(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    resp = await client.patch(
        f"{CAMPAIGNS_URL}/{created['id']}", headers=headers, json={"name": "X", "row_version": 99}
    )
    assert resp.status_code == 409


async def test_delete_and_list_and_get(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()

    listing = (await client.get(CAMPAIGNS_URL, headers=headers)).json()["data"]
    assert [c["id"] for c in listing] == [created["id"]]
    assert (await client.get(f"{CAMPAIGNS_URL}?status=draft", headers=headers)).json()["data"]
    assert not (await client.get(f"{CAMPAIGNS_URL}?status=running", headers=headers)).json()["data"]
    assert (await client.get(f"{CAMPAIGNS_URL}?q=Reactiv", headers=headers)).json()["data"]

    assert (await client.delete(f"{CAMPAIGNS_URL}/{created['id']}", headers=headers)).status_code == 204
    assert (await client.get(f"{CAMPAIGNS_URL}/{created['id']}", headers=headers)).status_code == 404
    assert (await client.get(f"{CAMPAIGNS_URL}/{uuid.uuid4()}", headers=headers)).status_code == 404


# --- Preview & recipients (Doc 04 §17) ---------------------------------------
async def test_preview_renders_what_each_contact_will_read(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()

    resp = await client.post(f"{CAMPAIGNS_URL}/{created['id']}/preview", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3 and len(body["samples"]) == 3
    sample = body["samples"][0]
    assert sample["rendered"]["header"] == "Order #1234"
    assert sample["rendered"]["body"].startswith("Hi Contact")
    assert "your order #1234 is shipped." in sample["rendered"]["body"]
    assert sample["wa_id"] and sample["contact_id"]


async def test_recipients_are_paginated_with_their_contact(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()

    resp = await client.get(f"{CAMPAIGNS_URL}/{created['id']}/recipients", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["data"]) == 3 and body["has_more"] is False
    assert all(r["status"] == RECIPIENT_PENDING and r["wa_id"] for r in body["data"])

    filtered = await client.get(
        f"{CAMPAIGNS_URL}/{created['id']}/recipients?status=sent", headers=headers
    )
    assert filtered.json()["data"] == []


# --- Audit & permissions -----------------------------------------------------
async def test_campaign_actions_are_audited(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    entries = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=campaign.created", headers=headers
    )
    assert len(entries.json()["data"]) == 1


async def test_campaign_permissions(client, make_user, session_factory, monkeypatch) -> None:
    headers, number_id, template_id, contacts = await _setup(
        client, make_user, session_factory, monkeypatch
    )
    # An agent works the inbox; broadcasting is not theirs.
    agent = await _headers(client, make_user, email="agent@vi.co", roles=("agent",))
    assert (await client.get(CAMPAIGNS_URL, headers=agent)).status_code == 403
    assert (
        await client.post(CAMPAIGNS_URL, headers=agent, json=_body(number_id, template_id, contacts))
    ).status_code == 403

    analyst = await _headers(client, make_user, email="analyst@vi.co", roles=("analyst",))
    assert (await client.get(CAMPAIGNS_URL, headers=analyst)).status_code == 200
    assert (await client.get(CAMPAIGNS_URL)).status_code == 401


# --- Unbuilt surfaces are absent, not stubbed --------------------------------
def test_no_scheduling_surface_exists_yet() -> None:
    """A route that pretends to schedule would be worse than none — it implies it nearly works."""
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    for path in (
        "/api/v1/campaigns/{campaign_id}/schedule",
        "/api/v1/campaigns/{campaign_id}/estimate-cost",
    ):
        assert path not in paths
