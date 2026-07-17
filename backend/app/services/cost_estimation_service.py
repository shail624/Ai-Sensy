"""Campaign cost estimation (Doc 03 §8.5; Doc 04 §17) — FR-CAM-11.

Pre-send spend, from the rate card, by contact country × template category. Doc 04 §17 calls the
exact number the headline differentiator, and everything here serves that word:

* **It prices the materialized roster**, not a fresh audience query — the quote covers what would
  actually be sent (opt-outs are already gone from the roster, Doc 03 §8.3).
* **It never guesses.** A missing rate is a `422`, not a zero. The card ships empty (Doc 03 §8.5.1),
  so "no rate" is the *normal* first answer, and an estimate that quietly skipped India's 180k would
  understate the total while looking authoritative.
* **It never silently drops a recipient.** A contact with no country cannot be priced, so it is
  counted, reported and excluded — visibly (Doc 03 §8.5.4).
* **It rounds once.** Subtotals are exact; only the stored total is rounded (Doc 03 §8.5.3).

**Estimation only** (Doc 03 §8.5.5). This writes ``campaigns.estimated_cost`` and
``campaigns.cost_currency`` and nothing else: ``actual_cost`` must be the provider-authoritative
charge, and pricing it from our own card would produce a second estimate wearing the word "actual".
``pricing_model``, ``is_billable`` and ``messages.cost_*`` have no defined rules and stay untouched.

The three layers stay apart: **data** is operator-authored rows, **storage** is
:class:`~app.repositories.rate_card.RateCardRepository`, and the **engine** is this module — which
knows nothing about effective dating and holds no rate of its own.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import Campaign
from app.repositories.campaign import CampaignRecipientRepository, CampaignRepository
from app.repositories.rate_card import RateCardRepository
from app.repositories.template import TemplateRepository

logger = get_logger(__name__)

#: `campaigns.estimated_cost` is DECIMAL(14,4) — the single rounding boundary (Doc 03 §8.5.3).
TOTAL_QUANTUM = Decimal("0.0001")
#: What an unresolved recipient's `reason` says (Doc 04 §17).
UNRESOLVED_COUNTRY = "country_unknown"


class RateCardNotConfigured(ValidationError):
    """No rate in force for a pair the estimate needs (Doc 04 §17 → 422)."""

    code = "rate_card_not_configured"
    title = "Rate Card Not Configured"


class RateCardCurrencyConflict(ValidationError):
    """The card carries more than one currency at once (Doc 03 §8.5.3 → 422)."""

    code = "rate_card_currency_conflict"
    title = "Rate Card Currency Conflict"


@dataclass(slots=True)
class BreakdownRow:
    """One priced ``(country, category)`` group (Doc 04 §17)."""

    country: str
    category: str
    count: int
    unit: Decimal
    subtotal: Decimal


@dataclass(slots=True)
class Estimate:
    """What ``POST /campaigns/{uuid}/estimate-cost`` answers (FR-CAM-11).

    Invariant (Doc 04 §17): ``recipients == sum(r.count for r in breakdown) + unresolved_count``.
    """

    recipients: int
    breakdown: list[BreakdownRow]
    unresolved_count: int
    estimated_total: Decimal
    currency: str
    notes: list[str]


class CostEstimationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignRepository(session)
        self._recipients = CampaignRecipientRepository(session)
        self._templates = TemplateRepository(session)
        self._rates = RateCardRepository(session)

    async def estimate(
        self, *, organization_id: int, public_id: uuidlib.UUID, at: datetime | None = None
    ) -> Estimate:
        """Price the campaign's roster and cache the total on the campaign (FR-CAM-11).

        Rates resolve at **estimate time**: this is a point-in-time quote, not a promise about send
        time (Doc 03 §8.5.3). A card amended between quote and send changes the cost, and
        reconciling that is out of scope.
        """
        at = at or utcnow()
        campaign = await self._campaign(organization_id, public_id)
        category = await self._category(campaign)

        counts = await self._recipients.counts_by_country(campaign.id)
        unresolved = counts.pop(None, 0)
        recipients = sum(counts.values()) + unresolved

        currency = await self._currency(at)
        breakdown = await self._price(counts, category=category, at=at)

        # Exact all the way: `unit_price` is a 6-dp decimal and `count` an integer, so no subtotal
        # or partial sum ever needs rounding. Only the storage boundary does (Doc 03 §8.5.3).
        total = sum((row.subtotal for row in breakdown), Decimal(0))
        estimated_total = total.quantize(TOTAL_QUANTUM, rounding=ROUND_HALF_UP)

        await self._cache(campaign, estimated_total, currency)
        return Estimate(
            recipients=recipients,
            breakdown=breakdown,
            unresolved_count=unresolved,
            estimated_total=estimated_total,
            currency=currency,
            notes=self._notes(unresolved),
        )

    async def _currency(self, at: datetime) -> str:
        """The card's one currency, or a 422 (Doc 03 §8.5.3).

        Checked across the whole card rather than this estimate's slice, because the invariant is
        the card's. Resolved before pricing so an empty card fails on the honest reason — it is not
        configured — rather than on whichever pair happened to be looked up first.
        """
        currencies = await self._rates.currencies_in_force(at=at)
        if not currencies:
            raise RateCardNotConfigured(
                "No rate card is configured. An operator must publish rates before a campaign "
                "can be costed."
            )
        if len(currencies) > 1:
            raise RateCardCurrencyConflict(
                "The rate card carries multiple currencies at once "
                f"({', '.join(sorted(currencies))}); it must be authored in exactly one."
            )
        return currencies.pop()

    async def _price(
        self, counts: dict[str | None, int], *, category: str, at: datetime
    ) -> list[BreakdownRow]:
        """One priced row per country, or a 422 naming every pair the card cannot price."""
        countries = sorted(c for c in counts if c is not None)
        pairs = [(country, category) for country in countries]
        rates = await self._rates.resolve_many(pairs, at=at)

        missing = [f"{country}/{category}" for country in countries if (country, category) not in rates]
        if missing:
            # All of them, not the first: an operator fixing the card one 422 at a time would need
            # as many round trips as they have countries.
            raise RateCardNotConfigured(
                "No rate is configured for: " + ", ".join(missing) + "."
            )

        rows = []
        for country in countries:
            rate = rates[(country, category)]
            count = counts[country]
            rows.append(
                BreakdownRow(
                    country=country,
                    category=category,
                    count=count,
                    unit=rate.unit_price,
                    subtotal=rate.unit_price * count,
                )
            )
        return rows

    def _notes(self, unresolved: int) -> list[str]:
        """Advisory only — never a machine contract (Doc 04 §17).

        The machine-readable outcome is ``unresolved``; this is the sentence a human reads next to
        it, and it exists so an operator is told *why* the total covers fewer people than the roster.
        """
        if not unresolved:
            return []
        return [
            f"{unresolved} recipient{'s' if unresolved != 1 else ''} "
            "have no country and are excluded from the total."
        ]

    async def _cache(self, campaign: Campaign, total: Decimal, currency: str) -> None:
        """Persist the quote on the campaign (Doc 04 §17's side effect).

        A derived cache of the campaign's own data — so it deliberately does **not** bump
        ``row_version`` or ``updated_by``: an estimate is not an operator edit, and invalidating a
        client's optimistic lock because someone opened the cost step would be a bug.

        ``actual_cost`` is not touched here and must not be: it has to be the provider's billed
        amount, and this number is a quote (Doc 03 §8.5.5).
        """
        campaign.estimated_cost = total
        campaign.cost_currency = currency
        await self._campaigns.flush()
        await self._session.commit()

    async def _category(self, campaign: Campaign) -> str:
        """The campaign's billing category — its template's (Doc 03 §8.5.2).

        A campaign always sends a template, so the category is one of the three ``ck_tpl_category``
        allows; the ``service`` category the message ledger also permits is unreachable here.
        """
        template = await self._templates.get_by_id(campaign.template_id)
        if template is None:
            raise NotFoundError("The campaign's template no longer exists.")
        return template.category

    async def _campaign(self, organization_id: int, public_id: uuidlib.UUID) -> Campaign:
        campaign = await self._campaigns.get_active_by_uuid(organization_id, public_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign
