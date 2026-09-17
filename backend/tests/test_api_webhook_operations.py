"""Webhook operations reads (Doc 04 §23) — Webhooks: delivery/retry visibility.

The ingest path has always recorded every delivery and parked every unprocessable event in a
dead-letter queue. Nothing exposed either, so the parking was real but the human it was parked for
was never told. These tests are mostly about the two things that make such a view trustworthy:
that it shows a tenant *all* of their own traffic, and *none* of anybody else's.
"""

from __future__ import annotations

import pytest

from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.organization import Organization
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.models.webhook import WebhookDeadLetter, WebhookEvent

PASSWORD = "Sup3r-Secret-Pass1"
EVENTS_URL = "/api/v1/webhooks/events"
DLQ_URL = "/api/v1/webhooks/dead-letter"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _number(db_session, organization_id: int, suffix: str) -> PhoneNumber:
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
        display_number=f"+9111111111{suffix[:2]}",
    )
    db_session.add(number)
    await db_session.flush()
    return number


async def _endpoint(db_session, organization_id: int, suffix: str) -> ChannelEndpoint:
    """A WAHA route — the other way a delivery can belong to an organization (QR-08)."""
    connection = ChannelConnection(
        organization_id=organization_id,
        channel_family="whatsapp",
        connector_type="waha",
        display_name=f"connection-{suffix}",
    )
    db_session.add(connection)
    await db_session.flush()
    endpoint = ChannelEndpoint(
        organization_id=organization_id,
        connection_id=connection.id,
        endpoint_type="phone",
        normalized_address=f"+9122222222{suffix[:2]}",
        provider_endpoint_id=f"session-{suffix}",
    )
    db_session.add(endpoint)
    await db_session.flush()
    return endpoint


async def _event(db_session, **kwargs) -> WebhookEvent:
    row = WebhookEvent(payload_json={"redacted": True}, signature_ok=True, **kwargs)
    db_session.add(row)
    await db_session.flush()
    return row


async def test_a_delivery_is_reported_with_the_state_an_operator_needs(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    await _event(
        db_session,
        phone_number_id=number.id,
        event_id="wamid.ABC",
        object_type="message",
        status="processed",
        attempts=1,
    )
    await db_session.commit()

    body = (await client.get(EVENTS_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert [row["event_id"] for row in body["data"]] == ["wamid.ABC"]
    entry = body["data"][0]
    assert entry["status"] == "processed"
    assert entry["signature_ok"] is True
    assert entry["attempts"] == 1
    assert entry["object_type"] == "message"


async def test_the_raw_payload_is_never_returned(
    client, db_session, organization, make_user
) -> None:
    """Message content belongs to the Inbox, behind `inbox:read`.

    Returning the provider's body here would create a second copy of the conversation on a screen
    gated by a different permission — an operations view that quietly widens who can read
    customers' messages.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    row = WebhookEvent(
        phone_number_id=number.id,
        event_id="wamid.SECRET",
        object_type="message",
        status="received",
        signature_ok=True,
        payload_json={"messages": [{"text": {"body": "my medical report is ready"}}]},
    )
    db_session.add(row)
    await db_session.commit()

    response = await client.get(EVENTS_URL, headers=await _headers(client, "ops@vi.co"))

    assert "medical report" not in response.text
    assert "payload" not in response.text


async def test_both_routing_paths_are_reported(
    client, db_session, organization, make_user
) -> None:
    """A Meta delivery routes by phone number, a WAHA one by channel endpoint.

    Matching only one would show an operator half their traffic and let them read the missing half
    as silence — the exact wrong conclusion when diagnosing a stalled stream.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    endpoint = await _endpoint(db_session, organization.id, "A")
    await _event(db_session, phone_number_id=number.id, event_id="meta-1", status="processed")
    await _event(db_session, channel_endpoint_id=endpoint.id, event_id="waha-1", status="received")
    await db_session.commit()

    body = (await client.get(EVENTS_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert sorted(row["event_id"] for row in body["data"]) == ["meta-1", "waha-1"]


async def test_another_organizations_deliveries_are_not_visible(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    other = Organization(name="Other Telco", slug="other-telco")
    db_session.add(other)
    await db_session.flush()
    mine = await _number(db_session, organization.id, "A")
    theirs = await _number(db_session, other.id, "B")
    await _event(db_session, phone_number_id=mine.id, event_id="mine", status="processed")
    await _event(db_session, phone_number_id=theirs.id, event_id="theirs", status="processed")
    await db_session.commit()

    body = (await client.get(EVENTS_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert [row["event_id"] for row in body["data"]] == ["mine"]


async def test_deliveries_can_be_filtered_by_status(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    await _event(db_session, phone_number_id=number.id, event_id="ok", status="processed")
    await _event(db_session, phone_number_id=number.id, event_id="bad", status="failed")
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    failed = await client.get(EVENTS_URL, headers=headers, params={"status": "failed"})

    assert [row["event_id"] for row in failed.json()["data"]] == ["bad"]


async def test_delivery_pagination_is_declared_and_bounded(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    for index in range(3):
        await _event(db_session, phone_number_id=number.id, event_id=f"e{index}", status="received")
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    first = (await client.get(EVENTS_URL, headers=headers, params={"limit": 2})).json()

    assert len(first["data"]) == 2 and first["page"]["has_more"] is True
    assert first["page"]["total"] == 3
    following = await client.get(
        EVENTS_URL, headers=headers, params={"limit": 2, "cursor": first["page"]["next_cursor"]}
    )
    assert [row["event_id"] for row in following.json()["data"]] == ["e0"]
    assert (await client.get(EVENTS_URL, headers=headers, params={"limit": 0})).status_code == 422


async def test_a_dead_letter_reports_the_error_that_stopped_it(
    client, db_session, organization, make_user
) -> None:
    """Without the error an operator sees that something failed but not what to do about it."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    db_session.add(
        WebhookDeadLetter(
            source_event_id=source.id,
            payload_json={"redacted": True},
            error_detail="contact lookup timed out",
            attempts=5,
            status="pending",
        )
    )
    await db_session.commit()

    body = (await client.get(DLQ_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert len(body["data"]) == 1
    assert body["data"][0]["error_detail"] == "contact lookup timed out"
    assert body["data"][0]["attempts"] == 5
    assert body["data"][0]["status"] == "pending"


async def test_another_organizations_dead_letters_are_not_visible(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    other = Organization(name="Other Telco", slug="other-telco")
    db_session.add(other)
    await db_session.flush()
    mine = await _number(db_session, organization.id, "A")
    theirs = await _number(db_session, other.id, "B")
    my_event = await _event(db_session, phone_number_id=mine.id, event_id="m", status="failed")
    their_event = await _event(db_session, phone_number_id=theirs.id, event_id="t", status="failed")
    db_session.add_all(
        [
            WebhookDeadLetter(
                source_event_id=my_event.id, payload_json={}, error_detail="mine", status="pending"
            ),
            WebhookDeadLetter(
                source_event_id=their_event.id,
                payload_json={},
                error_detail="theirs",
                status="pending",
            ),
        ]
    )
    await db_session.commit()

    body = (await client.get(DLQ_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert [row["error_detail"] for row in body["data"]] == ["mine"]


async def test_an_unattributable_dead_letter_is_shown_to_nobody(
    client, db_session, organization, make_user
) -> None:
    """Its source event aged out, so there is no longer anything saying whose it was.

    `webhook_events` is kept 90 days and dead letters 180 (Doc 04 §23.1), so this is the normal
    end state of an old entry, not a corruption. Showing it to every organization because it can
    be attributed to none would be a tenant leak dressed as helpfulness.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    db_session.add(
        WebhookDeadLetter(
            source_event_id=None,
            payload_json={},
            error_detail="orphaned",
            status="pending",
        )
    )
    await db_session.commit()

    body = (await client.get(DLQ_URL, headers=await _headers(client, "ops@vi.co"))).json()

    assert body["data"] == []


@pytest.mark.parametrize("url", [EVENTS_URL, DLQ_URL])
async def test_reading_requires_the_webhooks_permission(client, make_user, url: str) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="nobody@vi.co", password=PASSWORD)

    denied = await client.get(url, headers=await _headers(client, "nobody@vi.co"))

    assert denied.status_code == 403


# --- Replay and discard (Doc 04 §23) ------------------------------------------------------------
async def _dead_letter(db_session, source_event_id: int | None, **kwargs) -> WebhookDeadLetter:
    entry = WebhookDeadLetter(
        source_event_id=source_event_id,
        payload_json={"redacted": True},
        error_detail="contact lookup timed out",
        attempts=5,
        status=kwargs.pop("status", "pending"),
        **kwargs,
    )
    db_session.add(entry)
    await db_session.flush()
    return entry


async def _replay(client, headers, entry_id: str):
    return await client.post(f"{DLQ_URL}/{entry_id}/replay", headers=headers)


async def _discard(client, headers, entry_id: str):
    return await client.post(f"{DLQ_URL}/{entry_id}/discard", headers=headers)


async def test_replaying_queues_the_original_event_again(
    client, db_session, organization, make_user, monkeypatch
) -> None:
    queued: list[int] = []
    from app.channels import tasks as channel_tasks

    monkeypatch.setattr(
        channel_tasks.process_webhook_event,
        "apply_async",
        lambda args=None, **kwargs: queued.append(args[0]),
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id)
    await db_session.commit()

    replayed = await _replay(client, await _headers(client, "ops@vi.co"), entry.public_id)

    assert replayed.status_code == 200
    assert replayed.json()["status"] == "replayed"
    assert replayed.json()["replayed_at"] is not None
    assert queued == [source.id]


async def test_replaying_twice_does_not_apply_the_event_twice(
    client, db_session, organization, make_user, monkeypatch
) -> None:
    """Idempotent per Doc 04 section 23.

    An operator who clicks twice, or a request the browser retried, must not double-apply an event
    whose entire purpose was to be applied once.
    """
    queued: list[int] = []
    from app.channels import tasks as channel_tasks

    monkeypatch.setattr(
        channel_tasks.process_webhook_event,
        "apply_async",
        lambda args=None, **kwargs: queued.append(args[0]),
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id)
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    first = await _replay(client, headers, entry.public_id)
    second = await _replay(client, headers, entry.public_id)

    assert first.status_code == second.status_code == 200
    assert second.json()["status"] == "replayed"
    assert queued == [source.id]  # queued once, not twice


async def test_an_event_past_its_retention_is_not_replayable_by_anyone(
    client, db_session, organization, make_user
) -> None:
    """`webhook_events` is kept 90 days, dead letters 180 (Doc 04 section 23.1).

    "Only events still within retention are replayable" needs no explicit check: ownership is read
    through the source event, so once it ages out the entry belongs to nobody — it leaves the
    listing and answers 404 here. A 409 saying "too old" would have to describe a row the operator
    was never shown.
    """
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id)
    await db_session.commit()
    await db_session.delete(source)  # the source aged out
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    assert (await _replay(client, headers, entry.public_id)).status_code == 404
    assert (await _discard(client, headers, entry.public_id)).status_code == 404
    # And it is gone from the listing too, so the two surfaces agree.
    assert (await client.get(DLQ_URL, headers=headers)).json()["data"] == []


async def test_discarding_closes_an_entry_without_processing_it(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id)
    await db_session.commit()

    discarded = await _discard(client, await _headers(client, "ops@vi.co"), entry.public_id)

    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"
    assert discarded.json()["replayed_at"] is None


async def test_a_replayed_entry_cannot_then_be_discarded(
    client, db_session, organization, make_user
) -> None:
    """The event was applied; recording it as discarded would leave the queue claiming otherwise."""
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id, status="replayed")
    await db_session.commit()

    refused = await _discard(client, await _headers(client, "ops@vi.co"), entry.public_id)

    assert refused.status_code == 409


async def test_a_discarded_entry_cannot_then_be_replayed(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id, status="discarded")
    await db_session.commit()

    refused = await _replay(client, await _headers(client, "ops@vi.co"), entry.public_id)

    assert refused.status_code == 409


async def test_another_organizations_entry_cannot_be_replayed_or_discarded(
    client, db_session, organization, make_user
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    other = Organization(name="Other Telco", slug="other-telco")
    db_session.add(other)
    await db_session.flush()
    theirs = await _number(db_session, other.id, "B")
    their_event = await _event(db_session, phone_number_id=theirs.id, event_id="t", status="failed")
    entry = await _dead_letter(db_session, their_event.id)
    await db_session.commit()
    headers = await _headers(client, "ops@vi.co")

    assert (await _replay(client, headers, entry.public_id)).status_code == 404
    assert (await _discard(client, headers, entry.public_id)).status_code == 404


@pytest.mark.parametrize("action", ["replay", "discard"])
async def test_acting_on_the_queue_requires_the_webhooks_permission(
    client, db_session, organization, make_user, action: str
) -> None:
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    await make_user(email="nobody@vi.co", password=PASSWORD)
    number = await _number(db_session, organization.id, "A")
    source = await _event(db_session, phone_number_id=number.id, event_id="e1", status="failed")
    entry = await _dead_letter(db_session, source.id)
    await db_session.commit()

    denied = await client.post(
        f"{DLQ_URL}/{entry.public_id}/{action}", headers=await _headers(client, "nobody@vi.co")
    )

    assert denied.status_code == 403
