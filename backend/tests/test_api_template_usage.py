"""Template usage analytics (Templates: usage analytics).

Templates are picked by name, which means they are picked by memory. Every number here was already
in `campaigns` and `campaign_recipients`; nothing read them per template. These tests are mostly
about the two places the obvious implementation gets it wrong: dropping templates nobody has sent,
and reporting a delivery rate of zero for them.
"""

from __future__ import annotations

from datetime import timedelta

from app.db.mixins import utcnow
from app.models.campaign import Campaign, CampaignRecipient
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.template import MessageTemplate
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount

PASSWORD = "Sup3r-Secret-Pass1"
URL = "/api/v1/templates/usage"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _waba_and_number(db_session, organization_id: int, suffix: str):
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id,
        waba_id=f"WABA-{suffix}",
        business_name="Vi",
        access_token_enc=b"cipher",
    )
    db_session.add(waba)
    await db_session.flush()
    number = PhoneNumber(
        organization_id=organization_id,
        waba_id=waba.id,
        phone_number_id=f"PN-{suffix}",
        display_number=f"+9188888{waba.id:05d}",
    )
    db_session.add(number)
    await db_session.flush()
    return waba, number


async def _template(db_session, organization_id: int, waba_id: int, name: str) -> MessageTemplate:
    template = MessageTemplate(
        organization_id=organization_id,
        waba_id=waba_id,
        name=name,
        language="en",
        category="marketing",
        status="approved",
        components_json=[],
    )
    db_session.add(template)
    await db_session.flush()
    return template


async def _campaign(
    db_session, organization_id, number_id, template_id, name, created_at=None, *, sent=True
):
    """A dispatched campaign by default; pass ``sent=False`` for one still sitting as a draft.

    The default is the dispatched one because that is what every test here means by "a campaign
    that used this template". A draft materialises an identical roster, so a fixture that left
    ``started_at`` unset was quietly describing an impossible campaign -- one never dispatched,
    whose recipients had nonetheless been delivered.
    """
    campaign = Campaign(
        organization_id=organization_id,
        name=name,
        phone_number_id=number_id,
        template_id=template_id,
        audience_type="list",
    )
    if created_at is not None:
        campaign.created_at = created_at
    if sent:
        campaign.status = "completed"
        campaign.started_at = created_at if created_at is not None else utcnow()
    db_session.add(campaign)
    await db_session.flush()
    return campaign


async def _contact(db_session, organization_id: int, suffix: str) -> Contact:
    contact = Contact(
        organization_id=organization_id,
        wa_id=f"9199000{suffix}",
        phone_e164=f"+9199000{suffix}",
        full_name=f"Customer {suffix}",
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


async def _rows(client, headers) -> list[dict]:
    response = await client.get(URL, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_a_sent_template_reports_what_it_achieved(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    template = await _template(db_session, organization.id, waba.id, "reactivation_offer")
    campaign = await _campaign(db_session, organization.id, number.id, template.id, "Sept batch")
    for index in range(3):
        contact = await _contact(db_session, organization.id, f"00{index}1")
        db_session.add(
            CampaignRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="delivered" if index < 2 else "failed",
                delivered_at=utcnow() if index < 2 else None,
                failed_at=None if index < 2 else utcnow(),
            )
        )
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["name"] == "reactivation_offer"
    assert row["campaigns"] == 1
    assert row["recipients"] == 3
    assert row["delivered"] == 2
    assert row["failed"] == 1
    assert row["delivery_rate"] == 0.6667
    assert row["last_used_at"] is not None


async def test_a_template_nobody_has_sent_is_listed_with_no_rate_rather_than_zero(
    client, db_session, organization, make_user
) -> None:
    """Zero reads as "everything failed"; nothing was tried.

    The two call for opposite actions -- fix it, or try it -- and an unused template is exactly the
    one an operator needs to notice, so it is listed rather than dropped.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, _number = await _waba_and_number(db_session, organization.id, "A")
    await _template(db_session, organization.id, waba.id, "never_sent")
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["name"] == "never_sent"
    assert row["campaigns"] == 0 and row["recipients"] == 0
    assert row["delivery_rate"] is None
    assert row["last_used_at"] is None


async def test_a_read_message_counts_as_delivered(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    template = await _template(db_session, organization.id, waba.id, "read_only")
    campaign = await _campaign(db_session, organization.id, number.id, template.id, "Read batch")
    contact = await _contact(db_session, organization.id, "0021")
    db_session.add(
        CampaignRecipient(
            campaign_id=campaign.id, contact_id=contact.id, status="read", read_at=utcnow()
        )
    )
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["delivered"] == 1 and row["delivery_rate"] == 1.0


async def test_usage_is_summed_across_every_campaign_that_used_the_template(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    template = await _template(db_session, organization.id, waba.id, "repeated")
    for batch in range(2):
        campaign = await _campaign(
            db_session, organization.id, number.id, template.id, f"Batch {batch}"
        )
        contact = await _contact(db_session, organization.id, f"003{batch}")
        db_session.add(
            CampaignRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="delivered",
                delivered_at=utcnow(),
            )
        )
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["campaigns"] == 2 and row["recipients"] == 2


async def test_the_most_recently_used_template_comes_first_and_unused_ones_come_last(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    old = await _template(db_session, organization.id, waba.id, "older")
    recent = await _template(db_session, organization.id, waba.id, "recent")
    await _template(db_session, organization.id, waba.id, "unused")
    await _campaign(
        db_session, organization.id, number.id, old.id, "Old", utcnow() - timedelta(days=30)
    )
    await _campaign(db_session, organization.id, number.id, recent.id, "New", utcnow())
    await db_session.commit()

    names = [row["name"] for row in await _rows(client, await _headers(client, "ops@vi.co"))]

    assert names == ["recent", "older", "unused"]


async def test_another_organizations_sends_are_not_counted(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    other = Organization(name="Other Telco", slug="other-telco")
    db_session.add(other)
    await db_session.flush()
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    await _template(db_session, organization.id, waba.id, "mine")
    their_waba, their_number = await _waba_and_number(db_session, other.id, "B")
    theirs = await _template(db_session, other.id, their_waba.id, "theirs")
    await _campaign(db_session, other.id, their_number.id, theirs.id, "Theirs")
    await db_session.commit()

    rows = await _rows(client, await _headers(client, "ops@vi.co"))

    assert [row["name"] for row in rows] == ["mine"]
    assert rows[0]["campaigns"] == 0


async def test_usage_is_not_read_as_a_template_identifier(
    client, db_session, organization, make_user
) -> None:
    """`/templates/usage` must be declared before `/templates/{template_id}`.

    Declared the other way round, "usage" is parsed as an id and the screen 404s.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    await db_session.commit()

    assert (await client.get(URL, headers=await _headers(client, "ops@vi.co"))).status_code == 200


async def test_reading_usage_requires_template_read_permission(client, make_user) -> None:
    await make_user(email="nobody@vi.co", password=PASSWORD)

    denied = await client.get(URL, headers=await _headers(client, "nobody@vi.co"))

    assert denied.status_code == 403


# --- Regressions found by reading the shipped diff back ------------------------------------------
async def test_an_unsent_draft_does_not_dilute_a_working_template(
    client, db_session, organization, make_user
) -> None:
    """A campaign materialises its whole roster the moment it is created, while still a draft.

    So a 5,000-person draft that has never been sent puts 5,000 `pending` rows in the ledger under
    this template, and counting them as recipients divides the delivery rate by the size of
    somebody's unfinished work. The screen exists to answer "which template works"; a template
    delivering 100% would read here as 29% because a colleague is mid-draft, and the obvious
    response to that number is to retire a template that is working.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    template = await _template(db_session, organization.id, waba.id, "reactivation_offer")

    sent = await _campaign(db_session, organization.id, number.id, template.id, "Sent batch")
    for index in range(2):
        contact = await _contact(db_session, organization.id, f"01{index}1")
        db_session.add(
            CampaignRecipient(
                campaign_id=sent.id,
                contact_id=contact.id,
                status="delivered",
                delivered_at=utcnow(),
            )
        )

    draft = await _campaign(
        db_session, organization.id, number.id, template.id, "Not sent yet", sent=False
    )
    for index in range(5):
        contact = await _contact(db_session, organization.id, f"02{index}1")
        db_session.add(
            CampaignRecipient(campaign_id=draft.id, contact_id=contact.id, status="pending")
        )
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["recipients"] == 2, "a pending row was never attempted"
    assert row["delivered"] == 2
    assert row["delivery_rate"] == 1.0
    assert row["campaigns"] == 1, "a draft is not a use of the template"


async def test_drafting_a_campaign_does_not_make_a_template_look_recently_used(
    client, db_session, organization, make_user
) -> None:
    """`last_used_at` answers "when did we last send this", not "when did somebody open it"."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    waba, number = await _waba_and_number(db_session, organization.id, "A")
    template = await _template(db_session, organization.id, waba.id, "dormant_winback")
    await _campaign(
        db_session, organization.id, number.id, template.id, "Drafted today", sent=False
    )
    await db_session.commit()

    row = (await _rows(client, await _headers(client, "ops@vi.co")))[0]

    assert row["last_used_at"] is None
    assert row["campaigns"] == 0
    assert row["recipients"] == 0
    assert row["delivery_rate"] is None
