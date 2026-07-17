"""Rate card repository — pricing **storage** (Doc 03 §8.5).

Deliberately separate from the pricing **engine** (``CostEstimationService``) and from the pricing
**data** (operator-authored rows). The engine asks "what is the rate for this pair, at this instant"
and never learns how effective dating works; this module answers and never learns what a campaign is.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select

from app.models.rate_card import RateCard
from app.repositories.base import BaseRepository


class RateCardRepository(BaseRepository[RateCard]):
    model = RateCard

    async def resolve(self, country_code: str, category: str, *, at: datetime) -> RateCard | None:
        """The rate in force for one pair at one instant, or ``None`` (Doc 03 §8.5.3).

        ``effective_from <= at < effective_to`` (an open ``effective_to`` means "still in force").
        ``uq_ratecard_slot`` guarantees at most one row per pair per instant, so this is a lookup,
        not a search — but it orders by ``effective_from`` descending anyway, so a card corrupted by
        an out-of-band write resolves to the most recent applicable rate rather than an arbitrary one.
        """
        stmt = (
            select(RateCard)
            .where(
                RateCard.country_code == country_code,
                RateCard.category == category,
                RateCard.effective_from <= at,
                or_(RateCard.effective_to.is_(None), RateCard.effective_to > at),
            )
            .order_by(RateCard.effective_from.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def currencies_in_force(self, *, at: datetime) -> set[str]:
        """Every distinct currency the card carries at ``at`` (Doc 03 §8.5.3).

        The single-currency invariant is a property of the **whole card**, not of one estimate's
        slice, so it is checked here across every row in force. An empty set means the card is
        unpopulated — the platform's shipped state (Doc 03 §8.5.1).
        """
        stmt = (
            select(RateCard.currency)
            .where(
                RateCard.effective_from <= at,
                or_(RateCard.effective_to.is_(None), RateCard.effective_to > at),
            )
            .distinct()
        )
        return set((await self.session.scalars(stmt)).all())

    async def resolve_many(
        self, pairs: list[tuple[str, str]], *, at: datetime
    ) -> dict[tuple[str, str], RateCard]:
        """Resolve every ``(country, category)`` an estimate needs, in one round trip.

        An estimate touches one pair per country in its roster; asking per pair would be an N+1 on
        the request path. Rows are filtered to the pairs actually asked for, because the card is
        global and small but not necessarily *this* estimate's business.
        """
        if not pairs:
            return {}
        wanted = set(pairs)
        countries = {country for country, _ in pairs}
        categories = {category for _, category in pairs}
        stmt = (
            select(RateCard)
            .where(
                RateCard.country_code.in_(countries),
                RateCard.category.in_(categories),
                RateCard.effective_from <= at,
                or_(RateCard.effective_to.is_(None), RateCard.effective_to > at),
            )
            .order_by(RateCard.effective_from)
        )
        resolved: dict[tuple[str, str], RateCard] = {}
        for row in (await self.session.scalars(stmt)).all():
            key = (row.country_code, row.category)
            if key in wanted:
                # Ascending `effective_from`, so the last write wins: the newest applicable rate.
                resolved[key] = row
        return resolved
