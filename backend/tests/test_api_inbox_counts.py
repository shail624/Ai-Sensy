"""Inbox category counts (CORE-11).

The chips overlap by construction, so these are three independent totals and never a breakdown
to sum. The property that matters is predictiveness: a badge must equal the number of rows the
operator gets when they click it. Activating a category replaces status, assignee and tag and
carries only the search across, so the count is scoped by ``q`` alone — and these tests pin that,
because a count that silently honoured the current filters would label the chip with a list the
click never produces.
"""

from __future__ import annotations

import pytest

from tests.test_api_inbox import CONVERSATIONS_URL, _seeded, _user_id

COUNTS_URL = f"{CONVERSATIONS_URL}/counts"


async def _counts(client, headers, **params) -> dict:
    resp = await client.get(COUNTS_URL, headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_unassigned_open_thread_counts_active_and_requesting(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, _ = await _seeded(client, make_user, session_factory, monkeypatch)

    body = await _counts(client, agent)

    # Requesting is a subset of active, not a disjoint bucket: the one thread is in both.
    assert body == {"active": 1, "requesting": 1, "intervened": 0}


@pytest.mark.anyio
async def test_assignment_moves_the_thread_from_requesting_to_intervened(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    assignee_id = await _user_id(session_factory, "agent@vi.co")

    assign = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": assignee_id}
    )
    assert assign.status_code == 200, assign.text

    body = await _counts(client, agent)

    # Still open, so still active; no longer unassigned, so no longer requesting.
    assert body == {"active": 1, "requesting": 0, "intervened": 1}


@pytest.mark.anyio
async def test_counts_predict_what_activating_the_category_returns(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, _ = await _seeded(client, make_user, session_factory, monkeypatch)

    counts = await _counts(client, agent)
    listed = await client.get(CONVERSATIONS_URL, headers=agent, params={"status": "open"})

    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]) == counts["active"]


@pytest.mark.anyio
async def test_search_narrows_every_category(
    client, make_user, session_factory, monkeypatch, dispatched
):
    agent, _ = await _seeded(client, make_user, session_factory, monkeypatch)

    assert await _counts(client, agent, q="zzz-no-such-customer") == {
        "active": 0,
        "requesting": 0,
        "intervened": 0,
    }


@pytest.mark.anyio
async def test_status_and_assignee_filters_are_not_honoured(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """The rule this endpoint exists to hold.

    Clicking a chip replaces status and assignee, so counting with the *current* ones applied
    would advertise a result the click never produces — and a contradictory filter such as
    ``status=closed`` would drive active and requesting to a permanent zero.
    """
    agent, _ = await _seeded(client, make_user, session_factory, monkeypatch)
    unfiltered = await _counts(client, agent)

    contradictory = await _counts(client, agent, status="closed", assignee="unassigned")

    assert contradictory == unfiltered


@pytest.mark.anyio
async def test_intervened_spans_statuses_while_active_does_not(
    client, make_user, session_factory, monkeypatch, dispatched
):
    """Intervened is ownership, not openness.

    Resolving an assigned thread takes it out of active but leaves it intervened, because the
    category means "assigned to me" across statuses. If this ever regresses to an open-only
    predicate, an agent loses sight of their own resolved work.
    """
    agent, conv_id = await _seeded(client, make_user, session_factory, monkeypatch)
    assignee_id = await _user_id(session_factory, "agent@vi.co")
    assign = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/assign", headers=agent, json={"assignee_id": assignee_id}
    )
    assert assign.status_code == 200, assign.text

    resolved = await client.post(
        f"{CONVERSATIONS_URL}/{conv_id}/status", headers=agent, json={"status": "resolved"}
    )
    assert resolved.status_code == 200, resolved.text

    assert await _counts(client, agent) == {"active": 0, "requesting": 0, "intervened": 1}
