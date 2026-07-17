"""Campaign cost estimation tests (Doc 03 §8.5, Doc 04 §17; FR-CAM-11) — Phase 6 Step 5.

The card ships empty, so most tests seed rows directly. Money is asserted as `Decimal`, never
float — the whole point of the feature is exactness.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.mixins import utcnow
from app.models.campaign import Campaign
from app.models.rate_card import RateCard
from tests.test_api_campaigns import CAMPAIGNS_URL, _body, _headers


def _estimate_url(campaign_id: str) -> str:
    return f"{CAMPAIGNS_URL}/{campaign_id}/estimate-cost"


async def _rate(
    session_factory,
    *,
    country: str,
    category: str = "utility",
    price: str,
    currency: str = "USD",
    from_offset_days: int = -1,
    to_offset_days: int | None = None,
) -> None:
    """Author one rate row directly (the admin API is not built in Step 5, by design)."""
    async with session_factory() as session:
        session.add(
            RateCard(
                country_code=country,
                category=category,
                unit_price=Decimal(price),
                currency=currency,
                effective_from=utcnow() + timedelta(days=from_offset_days),
                effective_to=(
                    None if to_offset_days is None else utcnow() + timedelta(days=to_offset_days)
                ),
            )
        )
        await session.commit()


async def _campaign_with_countries(
    client, make_user, session_factory, monkeypatch, countries: list[str | None]
) -> tuple[dict, dict]:
    """A draft campaign whose N contacts carry the given country codes (None ⇒ unset)."""
    from tests.test_api_webhooks import _seed_number

    await _seed_number(client, make_user, session_factory, monkeypatch)
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    waba_id = (await client.get("/api/v1/waba", headers=headers)).json()["data"][0]["id"]
    from tests.test_api_campaigns import _approved_template

    template_id = await _approved_template(client, headers, session_factory, waba_id)
    number_id = (await client.get("/api/v1/phone-numbers", headers=headers)).json()["data"][0]["id"]

    contacts = []
    for i, country in enumerate(countries):
        body = {"phone_e164": f"+91999055{i:04d}", "full_name": f"C{i}"}
        if country is not None:
            body["country_code"] = country
        resp = await client.post("/api/v1/contacts", headers=headers, json=body)
        assert resp.status_code == 201, resp.text
        contacts.append(resp.json())

    created = (
        await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number_id, template_id, contacts))
    ).json()
    return headers, created


# --- Money & rounding (the headline number) ----------------------------------
@pytest.mark.anyio
async def test_estimate_sums_by_country(client, make_user, session_factory, monkeypatch) -> None:
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN", "IN", "US"]
    )
    await _rate(session_factory, country="IN", price="0.0094")
    await _rate(session_factory, country="US", price="0.025")

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recipients"] == 3
    assert body["unresolved"] == {"count": 0, "reason": "country_unknown"}
    rows = {r["country"]: r for r in body["breakdown"]}
    assert rows["IN"]["count"] == 2
    assert rows["IN"]["subtotal"] == "0.018800"  # 2 × 0.0094, exact
    assert rows["US"]["subtotal"] == "0.025000"
    # 0.0188 + 0.025 = 0.0438, rounded once to 4dp.
    assert body["estimated_total"] == "0.0438"
    assert body["currency"] == "USD"


@pytest.mark.anyio
async def test_total_rounds_half_up_once(client, make_user, session_factory, monkeypatch) -> None:
    """Round once at the boundary — not per row (Doc 03 §8.5.3)."""
    # 3 recipients × 0.00005 = 0.00015; ROUND_HALF_UP to 4dp = 0.0002. Rounding per row (each
    # 0.00005 → 0.0001, ×3 = 0.0003) would give a different, wrong answer.
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN", "IN", "IN"]
    )
    await _rate(session_factory, country="IN", price="0.00005")

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    body = resp.json()
    assert body["breakdown"][0]["subtotal"] == "0.000150"
    assert body["estimated_total"] == "0.0002"


@pytest.mark.anyio
async def test_estimate_persists_on_campaign(client, make_user, session_factory, monkeypatch) -> None:
    """The quote is cached on the campaign's own row (Doc 04 §17 side effect)."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )
    await _rate(session_factory, country="IN", price="1.5")

    before = await _one(session_factory, Campaign)
    resp = await client.post(_estimate_url(created["id"]), headers=headers)
    assert resp.status_code == 200
    after = await _one(session_factory, Campaign)

    assert after.estimated_cost == Decimal("1.5000")
    assert after.cost_currency == "USD"
    # actual_cost is untouched — it must be the provider's charge, not our quote (Doc 03 §8.5.5).
    assert after.actual_cost == Decimal("0")
    # A cache write is not an operator edit: no optimistic-lock churn.
    assert after.row_version == before.row_version


# --- Country resolution (Doc 03 §8.5.4) --------------------------------------
@pytest.mark.anyio
async def test_null_country_is_unresolved_not_dropped(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN", None, None]
    )
    await _rate(session_factory, country="IN", price="0.01")

    body = (await client.post(_estimate_url(created["id"]), headers=headers)).json()

    # The invariant: recipients == Σ breakdown.count + unresolved.count.
    assert body["recipients"] == 3
    assert sum(r["count"] for r in body["breakdown"]) == 1
    assert body["unresolved"] == {"count": 2, "reason": "country_unknown"}
    # Unresolved are excluded from the total, but the note tells the operator why.
    assert body["estimated_total"] == "0.0100"
    assert body["notes"] and "no country" in body["notes"][0]


# --- Empty / incomplete card (422) -------------------------------------------
@pytest.mark.anyio
async def test_empty_card_is_422(client, make_user, session_factory, monkeypatch) -> None:
    """The shipped state: no rates at all ⇒ rate_card_not_configured, never a zero total."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    assert resp.status_code == 422
    assert resp.json()["code"] == "rate_card_not_configured"


@pytest.mark.anyio
async def test_partial_card_is_422_naming_missing(
    client, make_user, session_factory, monkeypatch
) -> None:
    """A total that quietly skipped US would understate the headline number — so it refuses."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN", "US"]
    )
    await _rate(session_factory, country="IN", price="0.0094")  # US missing

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "rate_card_not_configured"
    assert "US/utility" in body["detail"]


@pytest.mark.anyio
async def test_conflicting_currencies_is_422(
    client, make_user, session_factory, monkeypatch
) -> None:
    """The single-currency invariant is the card's, checked across every row in force."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )
    await _rate(session_factory, country="IN", price="0.0094", currency="USD")
    await _rate(session_factory, country="GB", price="0.03", currency="EUR")

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    assert resp.status_code == 422
    assert resp.json()["code"] == "rate_card_currency_conflict"


# --- Effective dating (Doc 03 §8.5.3) ----------------------------------------
@pytest.mark.anyio
async def test_superseded_rate_is_ignored(client, make_user, session_factory, monkeypatch) -> None:
    """A closed row does not price a current estimate; the row in force does."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )
    # Old rate closed yesterday; new rate open since yesterday.
    await _rate(
        session_factory, country="IN", price="0.05", from_offset_days=-10, to_offset_days=-1
    )
    await _rate(session_factory, country="IN", price="0.0094", from_offset_days=-1)

    body = (await client.post(_estimate_url(created["id"]), headers=headers)).json()

    assert body["breakdown"][0]["unit"] == "0.009400"
    assert body["estimated_total"] == "0.0094"


@pytest.mark.anyio
async def test_future_rate_does_not_apply_yet(
    client, make_user, session_factory, monkeypatch
) -> None:
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )
    # Only a rate that starts tomorrow exists → nothing is in force now.
    await _rate(session_factory, country="IN", price="0.0094", from_offset_days=1)

    resp = await client.post(_estimate_url(created["id"]), headers=headers)

    assert resp.status_code == 422
    assert resp.json()["code"] == "rate_card_not_configured"


# --- Auth & not-found --------------------------------------------------------
@pytest.mark.anyio
async def test_estimate_unknown_campaign_is_404(client, make_user) -> None:
    headers = await _headers(client, make_user, email="mgr@vi.co", is_superuser=True)
    resp = await client.post(_estimate_url(str(uuid.uuid4())), headers=headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_estimate_requires_read_permission(
    client, make_user, session_factory, monkeypatch
) -> None:
    """estimate-cost is campaigns:read — an agent without it is forbidden."""
    headers, created = await _campaign_with_countries(
        client, make_user, session_factory, monkeypatch, ["IN"]
    )
    outsider = await _headers(client, make_user, email="nobody@vi.co", roles=())

    resp = await client.post(_estimate_url(created["id"]), headers=outsider)

    assert resp.status_code in (403, 404)


async def _one(session_factory, model):
    async with session_factory() as session:
        return (await session.scalars(select(model))).first()
