"""Per-user notification categories (Notifications: notification settings).

Muting is a *display* choice. The notification is still recorded, a supervisor's team view still
shows it, and unmuting brings it back unread. These tests are mostly about that distinction,
because the tempting implementation -- drop it at emit -- quietly destroys work evidence and
blinds oversight, and no test of the happy path would notice.
"""

from __future__ import annotations

import pytest

from app.services.notification_service import NotificationService

PASSWORD = "Sup3r-Secret-Pass!"
URL = "/api/v1/notifications"
SETTINGS_URL = f"{URL}/settings"


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _emit(db_session, organization, recipient, notification_type: str, key: str) -> None:
    await NotificationService(db_session).emit(
        organization_id=organization.id,
        recipient_user_id=recipient.id,
        notification_type=notification_type,
        title=f"{notification_type} title",
        body=f"{notification_type} body",
        dedup_key=key,
    )
    await db_session.commit()


async def _types(client, headers, **params) -> list[str]:
    response = await client.get(URL, headers=headers, params=params)
    assert response.status_code == 200
    return [item["type"] for item in response.json()["data"]]


async def _unread(client, headers) -> int:
    response = await client.get(f"{URL}/unread-count", headers=headers)
    assert response.status_code == 200
    return int(response.json()["unread"])


async def test_nothing_is_muted_until_the_user_says_so(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")

    body = (await client.get(SETTINGS_URL, headers=headers)).json()

    assert body["muted_types"] == []


async def test_muting_hides_the_category_from_the_list(
    client, db_session, organization, make_user
) -> None:
    created = await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")
    await _emit(db_session, organization, created.user, "case_assigned", "k-assigned")
    await _emit(db_session, organization, created.user, "report_ready", "k-report")
    assert sorted(await _types(client, headers)) == ["case_assigned", "report_ready"]

    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": ["report_ready"]})

    assert await _types(client, headers) == ["case_assigned"]


async def test_the_unread_badge_agrees_with_the_list(
    client, db_session, organization, make_user
) -> None:
    """A badge counting what the list refuses to show is worse than no setting at all.

    The operator taps a "2" and finds one row, so they stop believing the badge — and then stop
    noticing the one that mattered.
    """
    created = await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")
    await _emit(db_session, organization, created.user, "case_assigned", "k-assigned")
    await _emit(db_session, organization, created.user, "report_ready", "k-report")

    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": ["report_ready"]})

    assert await _unread(client, headers) == len(await _types(client, headers)) == 1


async def test_mark_all_read_leaves_muted_notifications_unread(
    client, db_session, organization, make_user
) -> None:
    """Mark-all-read clears what the operator was shown, not what was hidden from them.

    Otherwise unmuting a category later returns a list of things already marked read that the
    operator never actually saw — the setting would have silently consumed the evidence.
    """
    created = await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")
    await _emit(db_session, organization, created.user, "case_assigned", "k-assigned")
    await _emit(db_session, organization, created.user, "report_ready", "k-report")
    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": ["report_ready"]})

    cleared = await client.post(f"{URL}/read-all", headers=headers)

    assert cleared.json()["updated"] == 1  # the visible one only
    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": []})
    assert await _unread(client, headers) == 1  # the muted one is back, still unread


async def test_unmuting_restores_what_was_hidden(
    client, db_session, organization, make_user
) -> None:
    """Nothing was destroyed: the row was always there, only this user's view of it changed."""
    created = await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")
    await _emit(db_session, organization, created.user, "report_ready", "k-report")
    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": ["report_ready"]})
    assert await _types(client, headers) == []

    await client.put(SETTINGS_URL, headers=headers, json={"muted_types": []})

    assert await _types(client, headers) == ["report_ready"]


async def test_a_supervisors_team_view_is_not_filtered_by_the_agents_mute(
    client, db_session, organization, make_user
) -> None:
    """The reason muting is applied at read and scoped to the owner's own view.

    A lead reviewing an agent's queue is accountable for the work in it. If the agent's personal
    tidying removed rows from that review, the setting would be a way to hide from supervision.
    """
    await make_user(email="lead@vi.co", password=PASSWORD, is_superuser=True)
    agent = await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    agent_headers = await _headers(client, "agent@vi.co")
    lead_headers = await _headers(client, "lead@vi.co")
    await _emit(db_session, organization, agent.user, "case_assigned", "k-assigned")
    await client.put(SETTINGS_URL, headers=agent_headers, json={"muted_types": ["case_assigned"]})
    assert await _types(client, agent_headers) == []

    seen = await _types(client, lead_headers, assignee_id=agent.user.public_id)

    assert seen == ["case_assigned"]


async def test_one_users_setting_does_not_reach_another(
    client, db_session, organization, make_user
) -> None:
    first = await make_user(email="first@vi.co", password=PASSWORD, is_superuser=True)
    second = await make_user(email="second@vi.co", password=PASSWORD, is_superuser=True)
    first_headers = await _headers(client, "first@vi.co")
    second_headers = await _headers(client, "second@vi.co")
    await _emit(db_session, organization, first.user, "report_ready", "k-first")
    await _emit(db_session, organization, second.user, "report_ready", "k-second")

    await client.put(SETTINGS_URL, headers=first_headers, json={"muted_types": ["report_ready"]})

    assert await _types(client, first_headers) == []
    assert await _types(client, second_headers) == ["report_ready"]


@pytest.mark.parametrize("body", [{"muted_types": ["phase_of_moon"]}, {"muted_types": "all"}])
async def test_an_unknown_category_is_refused(client, make_user, body: dict) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")

    assert (await client.put(SETTINGS_URL, headers=headers, json=body)).status_code == 422


async def test_repeated_categories_come_back_as_a_stable_set(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")

    saved = await client.put(
        SETTINGS_URL,
        headers=headers,
        json={"muted_types": ["report_ready", "case_assigned", "report_ready"]},
    )

    assert saved.json()["muted_types"] == ["case_assigned", "report_ready"]


async def test_the_generic_preferences_endpoint_will_not_write_this_key(client, make_user) -> None:
    """The typed endpoint owns the key, as the inbox operations policy owns its own.

    `/users/me/preferences` takes a free-form dict, so allowing the key here would let a client
    store a shape the typed endpoint would never accept — and the notification list would then be
    filtered by something no validator ever saw.
    """
    await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")

    refused = await client.put(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"preferences": {"notification_settings": "whatever-i-like"}},
    )

    assert refused.status_code == 422
    assert "notifications/settings" in refused.text


async def test_a_corrupt_stored_value_does_not_break_the_list(
    client, db_session, organization, make_user
) -> None:
    """A user setting outlives the code that wrote it, so the read defends itself.

    Anything that is not a list of known categories mutes nothing, which fails towards showing the
    operator too much rather than too little.
    """
    created = await make_user(email="agent@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "agent@vi.co")
    await _emit(db_session, organization, created.user, "report_ready", "k-report")
    from app.repositories.settings import SettingRepository
    from app.services.notification_service import NOTIFICATION_SETTINGS_KEY

    await SettingRepository(db_session).upsert_user(
        user_id=created.user.id,
        organization_id=organization.id,
        key=NOTIFICATION_SETTINGS_KEY,
        value={"muted_types": ["report_ready", "a_category_that_no_longer_exists"]},
        value_type="json",
    )
    await db_session.commit()

    assert await _types(client, headers) == []  # the known name still mutes
    assert (await client.get(SETTINGS_URL, headers=headers)).json()["muted_types"] == [
        "report_ready"
    ]  # the unknown one is dropped rather than echoed back
