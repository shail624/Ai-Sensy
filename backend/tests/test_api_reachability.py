"""WhatsApp reachability derived from delivery evidence (scope §13 — Scan).

Section 13 excludes unofficial WhatsApp Web enumeration and Meta's Cloud API offers no lookup, so
the verdict is read from what Meta already said about messages that were actually sent. These tests
are mostly about restraint: which failures count as evidence about a *number*, and which are facts
about our own configuration that must not be allowed to condemn a reachable customer.
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
URL = "/api/v1/scan/reachability"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


async def _campaign(db_session, organization_id: int, name: str = "Reactivation") -> Campaign:
    """A campaign only needs to exist and belong to an organization for these tests.

    The verdict is read from its recipients, never from the campaign itself, so the WABA, number
    and template are scaffolding for the non-null columns rather than part of what is under test.
    """
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id,
        waba_id=f"WABA-{organization_id}-{name}",
        business_name="Vi",
        access_token_enc=b"cipher",
    )
    db_session.add(waba)
    await db_session.flush()
    number = PhoneNumber(
        organization_id=organization_id,
        waba_id=waba.id,
        phone_number_id=f"PN-{waba.id}",
        display_number=f"+9188888{waba.id:05d}",
    )
    template = MessageTemplate(
        organization_id=organization_id,
        waba_id=waba.id,
        name=f"template_{waba.id}",
        language="en",
        category="marketing",
        status="approved",
        components_json=[],
    )
    db_session.add_all([number, template])
    await db_session.flush()
    campaign = Campaign(
        organization_id=organization_id,
        name=name,
        phone_number_id=number.id,
        template_id=template.id,
        audience_type="list",
    )
    db_session.add(campaign)
    await db_session.flush()
    return campaign


async def _recipient(db_session, campaign: Campaign, contact: Contact, **kwargs) -> None:
    db_session.add(
        CampaignRecipient(campaign_id=campaign.id, contact_id=contact.id, **kwargs)
    )
    await db_session.flush()


async def _rows(client, headers, **params) -> list[dict]:
    response = await client.get(URL, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _verdict_of(client, headers, contact: Contact) -> str:
    rows = await _rows(client, headers)
    match = [row for row in rows if row["contact_id"] == contact.public_id]
    assert len(match) == 1
    return match[0]["verdict"]


async def test_a_delivered_message_proves_the_number_is_reachable(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    contact = await _contact(db_session, organization.id, "0001")
    campaign = await _campaign(db_session, organization.id)
    await _recipient(
        db_session, campaign, contact, status="delivered", delivered_at=utcnow()
    )
    await db_session.commit()

    assert await _verdict_of(client, await _headers(client, "ops@vi.co"), contact) == "reachable"


async def test_metas_not_a_whatsapp_user_is_the_one_failure_that_counts(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    contact = await _contact(db_session, organization.id, "0002")
    campaign = await _campaign(db_session, organization.id)
    await _recipient(
        db_session,
        campaign,
        contact,
        status="failed",
        error_code="131026",
        failed_at=utcnow(),
    )
    await db_session.commit()

    assert await _verdict_of(client, await _headers(client, "ops@vi.co"), contact) == "unreachable"


async def test_our_own_configuration_failures_do_not_condemn_a_customer(
    client, db_session, organization, make_user
) -> None:
    """The restraint this whole feature turns on.

    A paused template (132015), a closed 24-hour window (131047) and a throttle (131048) are facts
    about us, not about the customer's number. Counting them as "not on WhatsApp" would mark
    reachable people unreachable on the strength of our own mistakes — and they would then be
    excluded from the very campaigns meant to win them back.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    campaign = await _campaign(db_session, organization.id)
    headers = await _headers(client, "ops@vi.co")
    for index, code in enumerate(("132015", "131047", "131048", "131000")):
        contact = await _contact(db_session, organization.id, f"01{index:02d}")
        await _recipient(
            db_session, campaign, contact, status="failed", error_code=code, failed_at=utcnow()
        )
    await db_session.commit()

    assert {row["verdict"] for row in await _rows(client, headers)} == {"unknown"}


async def test_a_contact_no_campaign_ever_touched_is_untested_not_unreachable(
    client, db_session, organization, make_user
) -> None:
    """"We have never asked" and "we know they are not there" call for opposite next actions."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    contact = await _contact(db_session, organization.id, "0003")
    await db_session.commit()

    assert await _verdict_of(client, await _headers(client, "ops@vi.co"), contact) == "unknown"


async def test_the_more_recent_fact_wins(
    client, db_session, organization, make_user
) -> None:
    """A number can be deactivated after having been reachable, and the other way round.

    "Ever delivered" would call a disconnected number reachable forever; "ever refused" would
    condemn one that has since come back.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    campaign = await _campaign(db_session, organization.id)
    headers = await _headers(client, "ops@vi.co")
    old = utcnow() - timedelta(days=180)
    recent = utcnow()

    gone = await _contact(db_session, organization.id, "0004")
    await _recipient(db_session, campaign, gone, status="delivered", delivered_at=old)
    await _recipient(
        db_session,
        await _campaign(db_session, organization.id, "Later"),
        gone,
        status="failed",
        error_code="131026",
        failed_at=recent,
    )

    back = await _contact(db_session, organization.id, "0005")
    await _recipient(
        db_session, campaign, back, status="failed", error_code="131026", failed_at=old
    )
    await _recipient(
        db_session,
        await _campaign(db_session, organization.id, "Later again"),
        back,
        status="delivered",
        delivered_at=recent,
    )
    await db_session.commit()

    assert await _verdict_of(client, headers, gone) == "unreachable"
    assert await _verdict_of(client, headers, back) == "reachable"


async def test_a_read_receipt_counts_as_reached(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    contact = await _contact(db_session, organization.id, "0006")
    campaign = await _campaign(db_session, organization.id)
    await _recipient(db_session, campaign, contact, status="read", read_at=utcnow())
    await db_session.commit()

    assert await _verdict_of(client, await _headers(client, "ops@vi.co"), contact) == "reachable"


async def test_the_evidence_behind_a_verdict_is_returned_with_it(
    client, db_session, organization, make_user
) -> None:
    """A bare label would have to be taken on trust; the dates let an operator disagree."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    contact = await _contact(db_session, organization.id, "0007")
    campaign = await _campaign(db_session, organization.id)
    await _recipient(db_session, campaign, contact, status="delivered", delivered_at=utcnow())
    await db_session.commit()

    rows = await _rows(client, await _headers(client, "ops@vi.co"))

    assert rows[0]["last_delivered_at"] is not None
    assert rows[0]["last_undeliverable_at"] is None


async def test_the_counts_describe_the_same_set_as_the_rows(
    client, db_session, organization, make_user
) -> None:
    """Split onto their own endpoint because they cost differently, not because they differ.

    The tallies read every recipient row to decide one contact's verdict; the page reads fifty
    contacts. Measured at 200,000 recipients that is 425ms against 9ms, so returning them together
    made the fast answer wait for the slow one. They still use the same predicates, which is what
    this asserts.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    campaign = await _campaign(db_session, organization.id)
    reached = await _contact(db_session, organization.id, "0008")
    refused = await _contact(db_session, organization.id, "0009")
    await _contact(db_session, organization.id, "0010")  # never messaged
    await _recipient(db_session, campaign, reached, status="delivered", delivered_at=utcnow())
    await _recipient(
        db_session, campaign, refused, status="failed", error_code="131026", failed_at=utcnow()
    )
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    counts = (await client.get(f"{URL}/counts", headers=headers)).json()

    assert counts == {"reachable": 1, "unreachable": 1, "unknown": 1}
    for verdict, expected in (("reachable", 1), ("unreachable", 1), ("unknown", 1)):
        assert len(await _rows(client, headers, verdict=verdict)) == expected


async def test_the_counts_honour_the_same_search_as_the_list(
    client, db_session, organization, make_user
) -> None:
    """Two endpoints, one population: a tally that ignored the search would contradict the rows."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    campaign = await _campaign(db_session, organization.id)
    reached = await _contact(db_session, organization.id, "0013")
    await _contact(db_session, organization.id, "9998")
    await _recipient(db_session, campaign, reached, status="delivered", delivered_at=utcnow())
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    counts = (await client.get(f"{URL}/counts", headers=headers, params={"q": "0013"})).json()

    assert counts == {"reachable": 1, "unreachable": 0, "unknown": 0}
    assert len(await _rows(client, headers, q="0013")) == 1


async def test_counts_is_not_read_as_a_verdict_or_an_identifier(
    client, make_user
) -> None:
    """`/scan/reachability/counts` sits under the list path and must not be parsed as one of it."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)

    response = await client.get(f"{URL}/counts", headers=await _headers(client, "ops@vi.co"))

    assert response.status_code == 200
    assert set(response.json()) == {"reachable", "unreachable", "unknown"}


async def test_another_organizations_delivery_evidence_is_not_borrowed(
    client, db_session, organization, make_user
) -> None:
    """`campaign_recipients` has no organization_id, so ownership is read through the campaign.

    Getting this wrong would let one tenant's send decide another tenant's verdict.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    other = Organization(name="Other Telco", slug="other-telco")
    db_session.add(other)
    await db_session.flush()
    mine = await _contact(db_session, organization.id, "0011")
    their_campaign = await _campaign(db_session, other.id, "Theirs")
    # The same contact row, reached by somebody else's campaign: not our evidence.
    await _recipient(db_session, their_campaign, mine, status="delivered", delivered_at=utcnow())
    await db_session.commit()

    assert await _verdict_of(client, await _headers(client, "ops@vi.co"), mine) == "unknown"


async def test_contacts_can_be_searched_by_number(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    await _contact(db_session, organization.id, "0012")
    await _contact(db_session, organization.id, "9999")
    await db_session.commit()

    rows = await _rows(client, await _headers(client, "ops@vi.co"), q="9999")

    assert [row["phone_e164"] for row in rows] == ["+91990009999"]


async def test_pagination_is_declared_and_bounded(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    for index in range(3):
        await _contact(db_session, organization.id, f"02{index:02d}")
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    first = (await client.get(URL, headers=headers, params={"limit": 2})).json()

    assert len(first["data"]) == 2 and first["page"]["has_more"] is True
    following = await client.get(
        URL, headers=headers, params={"limit": 2, "cursor": first["page"]["next_cursor"]}
    )
    assert following.status_code == 200
    assert (await client.get(URL, headers=headers, params={"limit": 0})).status_code == 422


async def test_reading_requires_both_contact_and_campaign_permission(
    client, db_session, organization, make_user
) -> None:
    """The rows are contacts but the verdicts are campaign outcomes, a contact at a time."""
    await make_user(email="nobody@vi.co", password=PASSWORD)

    denied = await client.get(URL, headers=await _headers(client, "nobody@vi.co"))

    assert denied.status_code == 403
