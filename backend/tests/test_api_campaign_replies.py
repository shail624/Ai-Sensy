"""Campaign reply attribution — `campaigns.replied_count` (Doc 03 §8.1).

The counter has been on the model, in the API response and printed on the campaign screen as
"Replies: N (X% of delivered)" since the schema was written, and nothing ever wrote it. Every
campaign reported zero replies for its whole life, on the one number a *reactivation* campaign
exists to produce.

These tests are about the attribution rule as much as the counter: which campaign a reply belongs
to, and how many times one customer can count.
"""

from __future__ import annotations

from sqlalchemy import select

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.models.campaign import Campaign, CampaignRecipient
from app.services.campaign_dispatch_service import CampaignDispatchService
from tests.test_api_campaigns import CAMPAIGNS_URL, _approved_template, _headers
from tests.test_api_conversations import SENDER, _deliver
from tests.test_api_webhooks import _delivery, _seed_number

PASSWORD = "Sup3r-Secret-Pass1"


def _from(sender: str, wamid: str, body: str = "yes please") -> dict:
    return {
        "from": sender,
        "id": wamid,
        "timestamp": "1752739200",
        "type": "text",
        "text": {"body": body},
    }


async def _reply(client, session_factory, monkeypatch, make_user, *, sender, wamid) -> None:
    """One inbound message from `sender`, applied end-to-end."""
    from app.services.message_service import MessageService

    routed = await _deliver(
        client,
        session_factory,
        monkeypatch,
        make_user,
        _delivery(messages=[_from(sender, wamid)]),
    )
    assert routed, "the webhook processor must route an inbound message"
    async with session_factory() as session:
        await MessageService(session).apply_inbound(routed[0])


async def _sent_campaign(client, make_user, session_factory, monkeypatch) -> tuple[dict, dict]:
    """A dispatched campaign whose single recipient is the number the tests reply from."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    template_id = await _approved_template(client, headers, session_factory, waba_id)
    number_id = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"][0]["id"]
    contact = (
        await client.post(
            "/api/v1/contacts",
            headers=headers,
            json={"phone_e164": f"+{SENDER}", "full_name": "Asha"},
        )
    ).json()

    created = (
        await client.post(
            CAMPAIGNS_URL,
            headers=headers,
            json={
                "name": "Vi Reactivation",
                "phone_number_id": number_id,
                "template_id": template_id,
                "audience_type": "list",
                "audience_ref": {"contact_ids": [contact["id"]]},
                "variable_map": {
                    "header": [{"source": "literal", "value": "#1234"}],
                    "body": [
                        {"source": "field", "key": "full_name", "fallback": "there"},
                        {"source": "literal", "value": "#1234"},
                        {"source": "literal", "value": "ready"},
                    ],
                },
            },
        )
    ).json()
    assert (
        await client.post(f"{CAMPAIGNS_URL}/{created['id']}/dispatch", headers=headers)
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
    return headers, created


async def test_a_reply_is_counted_against_the_campaign_that_reached_them(
    client, make_user, session_factory, monkeypatch, campaign_channel
) -> None:
    """The number the campaign screen has always printed, now measured.

    Attribution is the campaign whose message the contact most recently *received* — the send
    already stamped `sent_at` on that row, so nothing is invented to decide it.
    """
    headers, created = await _sent_campaign(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        before = (await session.scalars(select(CampaignRecipient))).one()
    assert before.replied_at is None

    await _reply(
        client, session_factory, monkeypatch, make_user, sender=SENDER, wamid="wamid.REPLY-1"
    )

    async with session_factory() as session:
        after = (await session.scalars(select(CampaignRecipient))).one()
        campaign = (await session.scalars(select(Campaign))).one()
    assert after.replied_at is not None
    assert campaign.replied_count == 1

    # And the API says so, which is where the operator reads it.
    body = (await client.get(f"{CAMPAIGNS_URL}/{created['id']}", headers=headers)).json()
    assert body["replied_count"] == 1


async def test_a_customer_who_sends_five_messages_is_one_reply(
    client, make_user, session_factory, monkeypatch, campaign_channel
) -> None:
    """The counter measures whether the campaign reached somebody, not how much they typed."""
    await _sent_campaign(client, make_user, session_factory, monkeypatch)

    for index in range(3):
        await _reply(
            client,
            session_factory,
            monkeypatch,
            make_user,
            sender=SENDER,
            wamid=f"wamid.REPLY-{index}",
        )

    async with session_factory() as session:
        campaign = (await session.scalars(select(Campaign))).one()
    assert campaign.replied_count == 1


async def test_an_inbound_message_from_nobody_in_a_campaign_counts_nothing(
    client, make_user, session_factory, monkeypatch, campaign_channel
) -> None:
    """The ordinary case for an inbound message, and it must not fail or attribute itself."""
    await _sent_campaign(client, make_user, session_factory, monkeypatch)

    await _reply(
        client,
        session_factory,
        monkeypatch,
        make_user,
        sender="919000000123",
        wamid="wamid.STRANGER",
    )

    async with session_factory() as session:
        campaign = (await session.scalars(select(Campaign))).one()
        replied = list(
            (
                await session.scalars(
                    select(CampaignRecipient).where(CampaignRecipient.replied_at.is_not(None))
                )
            ).all()
        )
    assert campaign.replied_count == 0
    assert replied == []
