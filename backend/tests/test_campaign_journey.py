"""One realistic Vi reactivation campaign, end to end.

Every fix this session had its own test, and each one passed while the campaign as a whole was
still broken -- because nothing exercised the pieces *together*. A real reactivation offer is not
"a template with a button" or "a template with an image"; it is one message carrying an offer
picture, the customer's name, and a link only they can use. This drives exactly that, from the
template through the campaign to the reply that says it worked.

What it would have caught, had it existed this morning: the campaign silently dropping button
values (CAM-BTN-01), having nowhere to name an image (CAM-MEDIA-01), dispatching against a
template that had moved (CAM-DRIFT-01), and reporting zero replies forever (CAM-REPLY-01).
"""

from __future__ import annotations

import json

import httpx
from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.campaign import RECIPIENT_SENT, Campaign, CampaignRecipient
from app.models.template import MessageTemplate
from app.services.campaign_dispatch_service import CampaignDispatchService
from app.services.message_service import MessageService
from tests.test_api_campaigns import CAMPAIGNS_URL, _approved_template, _headers
from tests.test_api_conversations import SENDER, _deliver
from tests.test_api_webhooks import _delivery, _seed_number

PASSWORD = "Sup3r-Secret-Pass1"
PNG = b"\x89PNG\r\n\x1a\n" + b"d" * 64

#: The shape a Vi reactivation offer actually takes: a picture, a personal greeting, and a link
#: that is different for every customer.
OFFER_TEMPLATE = [
    {"type": "header", "format": "image"},
    {"type": "body", "text": "Hi {{1}}, your Vi number {{2}} has an offer waiting."},
    {"type": "footer", "text": "Reply STOP to opt out"},
    {
        "type": "buttons",
        "buttons": [
            {"type": "url", "text": "Recharge now", "url": "https://vi.co/pay/{{1}}"},
            {"type": "phone_number", "text": "Talk to us", "phone_number": "+911234567890"},
        ],
    },
]


async def test_the_whole_reactivation_journey(
    client, make_user, session_factory, monkeypatch, campaign_channel
) -> None:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template_id = await _approved_template(client, headers, session_factory, waba_id)
    async with session_factory() as session:
        (template,) = list((await session.scalars(select(MessageTemplate))).all())
        template.components_json = OFFER_TEMPLATE
        template.has_media_header = True
        await session.commit()
    number_id = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"][0]["id"]

    # --- The operator checks what a customer will receive, before committing to a send ----------
    preview = await client.get(
        f"/api/v1/templates/{template_id}/preview?body=Asha&body=99903293&button=TXN77",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    rendered = preview.json()
    assert rendered["body"] == "Hi Asha, your Vi number 99903293 has an offer waiting."
    assert rendered["buttons"][0]["target"] == "https://vi.co/pay/TXN77"
    assert rendered["expects"] == {"header": 0, "body": 2, "buttons": 1}

    # --- The offer image, and a customer to send it to -------------------------------------------
    uploaded = await client.post(
        "/api/v1/media/upload",
        headers=headers,
        files={"file": ("offer.png", PNG, "image/png")},
        data={"media_type": "image"},
    )
    assert uploaded.status_code == 201, uploaded.text
    contact = (
        await client.post(
            "/api/v1/contacts",
            headers=headers,
            json={"phone_e164": f"+{SENDER}", "full_name": "Asha Mehta"},
        )
    ).json()

    created = await client.post(
        CAMPAIGNS_URL,
        headers=headers,
        json={
            "name": "September winback",
            "phone_number_id": number_id,
            "template_id": template_id,
            "audience_type": "list",
            "audience_ref": {"contact_ids": [contact["id"]]},
            "variable_map": {
                "body": [
                    {"source": "field", "key": "full_name", "fallback": "there"},
                    {"source": "field", "key": "wa_id", "fallback": "your number"},
                ],
                "buttons": [{"source": "field", "key": "wa_id", "fallback": "0"}],
                "header_media": {"media_asset_id": uploaded.json()["id"]},
            },
        },
    )
    assert created.status_code == 201, created.text

    # --- Send it ---------------------------------------------------------------------------------
    def meta(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "MEDIA-OFFER"})
        return httpx.Response(200, json={"messages": [{"id": "wamid.JOURNEY"}]})

    campaign_channel["handler"] = meta
    assert (
        await client.post(f"{CAMPAIGNS_URL}/{created.json()['id']}/dispatch", headers=headers)
    ).status_code == 202

    async with session_factory() as session:
        campaign = (await session.scalars(select(Campaign))).one()
        plan = await CampaignDispatchService(session).plan(campaign.id)
    for batch_pk in plan["batches"]:
        async with session_factory() as session:
            fan = await CampaignDispatchService(session).fan_out(batch_pk)
        for recipient_pk in fan["recipients"]:
            async with session_factory() as session:
                await CampaignDispatchService(session).send_recipient(recipient_pk)

    async with session_factory() as session:
        recipient = (await session.scalars(select(CampaignRecipient))).one()
    assert recipient.status == RECIPIENT_SENT, recipient.error_detail

    # --- All three parts reached Meta in one message ----------------------------------------------
    (sent,) = [
        json.loads(request.content)
        for request in campaign_channel["requests"]
        if request.method == "POST" and not request.url.path.endswith("/media")
    ]
    parts = {component["type"]: component for component in sent["template"]["components"]}
    assert parts["header"]["parameters"][0]["type"] == "image"
    assert [p["text"] for p in parts["body"]["parameters"]] == ["Asha Mehta", SENDER]
    assert parts["button"]["sub_type"] == "url"
    assert parts["button"]["parameters"][0]["text"] == SENDER

    # --- The customer writes back, and the campaign says so ---------------------------------------
    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(
            messages=[
                {
                    "from": SENDER,
                    "id": "wamid.JOURNEY-REPLY",
                    "timestamp": "1752739200",
                    "type": "text",
                    "text": {"body": "yes please"},
                }
            ]
        ),
    )
    assert routed
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])

    body = (await client.get(f"{CAMPAIGNS_URL}/{created.json()['id']}", headers=headers)).json()
    assert body["replied_count"] == 1
