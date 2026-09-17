"""A segment of what WhatsApp has said about the number (scope §13 "Create segment").

SCAN-01 made reachability visible; this makes it *actionable*. The distinction has a price: every
campaign send costs money, so a roster that keeps including numbers Meta has already refused pays
for the same refusal every month. Until now an operator could read that list and not exclude it.

The verdict here is compiled from the Scan screen's own predicate, deliberately. Written twice they
would drift, and that drift presents as a campaign quietly targeting a different population from
the one the operator read before building it.
"""

from __future__ import annotations

from app.db.mixins import utcnow
from app.models.campaign import Campaign, CampaignRecipient
from app.models.contact import Contact
from app.models.template import MessageTemplate
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount

PASSWORD = "Sup3r-Secret-Pass1"
NOT_A_WHATSAPP_USER = "131026"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _campaign(db_session, organization_id: int) -> Campaign:
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id, waba_id="WABA-S", business_name="Vi",
        access_token_enc=b"cipher",
    )
    db_session.add(waba)
    await db_session.flush()
    number = PhoneNumber(
        organization_id=organization_id, waba_id=waba.id,
        phone_number_id="PN-S", display_number="+918888800001",
    )
    template = MessageTemplate(
        organization_id=organization_id, waba_id=waba.id, name="winback",
        language="en", category="marketing", status="approved", components_json=[],
    )
    db_session.add_all([number, template])
    await db_session.flush()
    campaign = Campaign(
        organization_id=organization_id, name="Sept", phone_number_id=number.id,
        template_id=template.id, audience_type="list",
    )
    db_session.add(campaign)
    await db_session.flush()
    return campaign


async def _segment_names(client, headers, *, name: str, operator: str, value: object) -> set[str]:
    created = await client.post(
        "/api/v1/segments",
        headers=headers,
        json={
            "name": name,
            "rules": [
                {
                    "field_source": "scan",
                    "field_key": "reachability",
                    "operator": operator,
                    "value": value,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    preview = await client.get(
        f"/api/v1/segments/{created.json()['id']}/contacts", headers=headers
    )
    assert preview.status_code == 200, preview.text
    return {row["full_name"] for row in preview.json()["data"]}


async def _population(client, make_user, db_session, organization) -> dict[str, str]:
    """Three customers, one per verdict, with the evidence that produces it."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "ops@vi.co")
    campaign = await _campaign(db_session, organization.id)

    people = {}
    for suffix, name in (("01", "Reached Rita"), ("02", "Refused Raj"), ("03", "Untried Uma")):
        contact = Contact(
            organization_id=organization.id,
            wa_id=f"91999000{suffix}",
            phone_e164=f"+91999000{suffix}",
            full_name=name,
        )
        db_session.add(contact)
        await db_session.flush()
        people[name] = contact

    db_session.add(
        CampaignRecipient(
            campaign_id=campaign.id, contact_id=people["Reached Rita"].id,
            status="delivered", delivered_at=utcnow(),
        )
    )
    db_session.add(
        CampaignRecipient(
            campaign_id=campaign.id, contact_id=people["Refused Raj"].id,
            status="failed", error_code=NOT_A_WHATSAPP_USER, failed_at=utcnow(),
        )
    )
    # Untried Uma is in no campaign at all, which is the whole point of `unknown`.
    await db_session.commit()
    return headers


async def test_a_segment_can_exclude_numbers_whatsapp_has_refused(
    client, make_user, db_session, organization
) -> None:
    """The money case: stop paying to send to numbers Meta already said are not there."""
    headers = await _population(client, make_user, db_session, organization)

    assert await _segment_names(
        client, headers, name="Not on WhatsApp", operator="eq", value="unreachable"
    ) == {"Refused Raj"}

    assert await _segment_names(
        client, headers, name="Worth sending to", operator="ne", value="unreachable"
    ) == {"Reached Rita", "Untried Uma"}


async def test_never_messaged_is_its_own_verdict_not_a_soft_no(
    client, make_user, db_session, organization
) -> None:
    """`unknown` is the absence of evidence, so it is found by *not* matching rather than matching.

    It is also the segment worth having: a contact nobody has ever tried is a campaign waiting to
    happen, which is the opposite of what "not reachable" would call for.
    """
    headers = await _population(client, make_user, db_session, organization)

    assert await _segment_names(
        client, headers, name="Never tried", operator="eq", value="unknown"
    ) == {"Untried Uma"}

    assert await _segment_names(
        client, headers, name="Tried at least once", operator="ne", value="unknown"
    ) == {"Reached Rita", "Refused Raj"}


async def test_several_verdicts_at_once(client, make_user, db_session, organization) -> None:
    headers = await _population(client, make_user, db_session, organization)

    assert await _segment_names(
        client, headers, name="Any evidence", operator="in", value=["reachable", "unreachable"]
    ) == {"Reached Rita", "Refused Raj"}


async def test_a_nonsense_verdict_is_refused_rather_than_matching_nobody(
    client, make_user, db_session, organization
) -> None:
    """An empty segment reads as "nobody qualifies", which is a different claim from "typo"."""
    headers = await _population(client, make_user, db_session, organization)

    refused = await client.post(
        "/api/v1/segments",
        headers=headers,
        json={
            "name": "Typo",
            "rules": [
                {
                    "field_source": "scan",
                    "field_key": "reachability",
                    "operator": "eq",
                    "value": "reachible",
                }
            ],
        },
    )

    assert refused.status_code == 422
    assert "reachible" in refused.text


async def test_the_segment_and_the_scan_screen_describe_the_same_people(
    client, make_user, db_session, organization
) -> None:
    """One predicate, two screens. Written twice they would drift, and a campaign would then
    target a different population from the list the operator read before building it."""
    headers = await _population(client, make_user, db_session, organization)

    screen = await client.get(
        "/api/v1/scan/reachability", headers=headers, params={"verdict": "unreachable"}
    )
    assert screen.status_code == 200, screen.text
    from_screen = {row["full_name"] for row in screen.json()["data"]}

    from_segment = await _segment_names(
        client, headers, name="Same set", operator="eq", value="unreachable"
    )

    assert from_screen == from_segment == {"Refused Raj"}


async def test_the_unreachable_list_can_already_be_exported(
    client, make_user, db_session, organization
) -> None:
    """Scope §13's "Export", through the export path that already exists.

    The contacts export takes segment rules, and SCAN-02 made reachability one, so the list an
    operator wants to hand to somebody is already exportable without a second export pipeline --
    which is what this repository's export service says it exists to avoid.
    """
    headers = await _population(client, make_user, db_session, organization)

    import app.crm.tasks as tasks

    tasks.run_contact_export.apply_async = lambda args, task_id: None
    started = await client.post(
        "/api/v1/contacts/export",
        headers=headers,
        json={
            "format": "csv",
            "match_type": "all",
            "rules": [
                {
                    "field_source": "scan",
                    "field_key": "reachability",
                    "operator": "eq",
                    "value": "unreachable",
                }
            ],
        },
    )

    assert started.status_code == 202, started.text

    # 202 only proves the filter validated. What matters is which people come out of it.
    from app.services.export_service import ExportService
    from app.storage.base import get_provider

    job = await ExportService(db_session).run(started.json()["job"]["id"])

    assert job.row_count == 1
    body = (await get_provider("local").get(job.storage_key)).decode()
    assert "Refused Raj" in body
    assert "Reached Rita" not in body and "Untried Uma" not in body


async def test_a_scan_export_is_recognisable_in_the_download_center(
    client, make_user, db_session, organization
) -> None:
    """Every contacts export was called "Contacts export".

    So an operator who exported the reachability list and then the full roster saw two identical
    rows and had to open both to tell them apart. A scan export is a contacts export with a
    reachability rule, not a second kind of job, so the name is read back off that rule.
    """
    import app.crm.tasks as tasks

    tasks.run_contact_export.apply_async = lambda args, task_id: None
    headers = await _population(client, make_user, db_session, organization)

    await client.post(
        "/api/v1/contacts/export",
        headers=headers,
        json={
            "format": "csv",
            "match_type": "all",
            "rules": [
                {
                    "field_source": "scan",
                    "field_key": "reachability",
                    "operator": "eq",
                    "value": "unreachable",
                }
            ],
        },
    )
    await client.post(
        "/api/v1/contacts/export",
        headers=headers,
        json={"format": "csv", "match_type": "all", "rules": []},
    )

    listed = await client.get("/api/v1/downloads", headers=headers)
    assert listed.status_code == 200, listed.text
    names = [row["name"] for row in listed.json()["data"]]

    assert "Not on WhatsApp — contacts export" in names
    assert "Contacts export" in names


async def test_a_mixed_filter_keeps_the_plain_name(
    client, make_user, db_session, organization
) -> None:
    """A filter combining reachability with other conditions is not "the unreachable list".

    Naming it one would be a more confident claim than the filter supports, and worse than the
    generic title it replaces.
    """
    import app.crm.tasks as tasks

    tasks.run_contact_export.apply_async = lambda args, task_id: None
    headers = await _population(client, make_user, db_session, organization)

    await client.post(
        "/api/v1/contacts/export",
        headers=headers,
        json={
            "format": "csv",
            "match_type": "all",
            "rules": [
                {
                    "field_source": "scan",
                    "field_key": "reachability",
                    "operator": "eq",
                    "value": "unreachable",
                },
                {
                    "field_source": "contact",
                    "field_key": "opt_in_status",
                    "operator": "eq",
                    "value": "opted_in",
                },
            ],
        },
    )

    listed = await client.get("/api/v1/downloads", headers=headers)
    assert [row["name"] for row in listed.json()["data"]] == ["Contacts export"]
