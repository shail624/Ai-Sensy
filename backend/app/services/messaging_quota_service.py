"""Per-number messaging quota for the Campaigns header (UI-AIS-17).

Meta limits how many *unique customers* a number may start conversations with in a rolling 24
hours (its messaging tier). Meta does not report how much of that is left, so the platform counts
it from its own ledger: distinct customers sent a template (business-initiated) message from the
number in the last 24 hours. It is an estimate — sends made outside this platform are invisible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.message import DIRECTION_OUTBOUND, Message
from app.models.waba import PhoneNumber
from app.services.rate_gate import TIER_CAPS, TIER_WINDOW_SECONDS


@dataclass(slots=True)
class NumberQuota:
    phone_number_id: str
    display_number: str
    quality_rating: str | None
    messaging_tier: str | None
    #: Unique customers per 24h; ``None`` for an unlimited or not-yet-reported tier.
    daily_limit: int | None
    used_last_24h: int
    remaining: int | None


class MessagingQuotaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_organization(self, organization_id: int) -> list[NumberQuota]:
        numbers = (
            await self._session.scalars(
                select(PhoneNumber)
                .where(
                    PhoneNumber.organization_id == organization_id,
                    PhoneNumber.deleted_at.is_(None),
                )
                .order_by(PhoneNumber.is_default.desc(), PhoneNumber.id)
            )
        ).all()
        since = utcnow() - timedelta(seconds=TIER_WINDOW_SECONDS)
        quotas: list[NumberQuota] = []
        for number in numbers:
            used = int(
                await self._session.scalar(
                    select(func.count(func.distinct(Message.contact_id))).where(
                        Message.organization_id == organization_id,
                        Message.phone_number_id == number.id,
                        Message.direction == DIRECTION_OUTBOUND,
                        Message.template_id.is_not(None),
                        Message.created_at >= since,
                    )
                )
                or 0
            )
            tier = (number.messaging_tier or "").upper() or None
            limit = TIER_CAPS.get(tier) if tier else None
            quotas.append(
                NumberQuota(
                    phone_number_id=number.public_id,
                    display_number=number.display_number,
                    quality_rating=number.quality_rating,
                    messaging_tier=number.messaging_tier,
                    daily_limit=limit,
                    used_last_24h=used,
                    remaining=max(0, limit - used) if limit is not None else None,
                )
            )
        return quotas
