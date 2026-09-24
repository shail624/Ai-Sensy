"""Daily chat and agent activity for Manage → Analytics (UI-AIS-10).

Counted straight from the ledger rather than the analytics rollups, so the numbers are right the
moment a message lands:

* **User messages** — inbound messages from customers.
* **Business messages** — outbound messages sent by people or campaigns (and from the QR phone).
* **Chatbot messages** — outbound messages the platform sent on its own (automatic replies), which
  the send path audits with a system actor.
* **Closed** / **Intervened** — conversation status changes to ``resolved``, and agent
  interventions, from the audit trail.

Days are calendar days in the caller's timezone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM, AuditLog
from app.models.message import DIRECTION_INBOUND, DIRECTION_OUTBOUND, Message

MAX_DAYS = 31
_UTC = ZoneInfo("UTC")


@dataclass(slots=True)
class DayActivity:
    day: date
    user_messages: int = 0
    business_messages: int = 0
    chatbot_messages: int = 0
    closed: int = 0
    intervened: int = 0


class ChatActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def daily(self, *, organization_id: int, days: int, timezone: str) -> list[DayActivity]:
        if not 1 <= days <= MAX_DAYS:
            raise BadRequestError(f"days must be between 1 and {MAX_DAYS}.")
        try:
            zone = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise BadRequestError(f"Unknown timezone {timezone!r}.") from exc

        today = utcnow().replace(tzinfo=_UTC).astimezone(zone).date()
        first = today - timedelta(days=days - 1)
        start_utc = (
            datetime.combine(first, datetime.min.time(), tzinfo=zone)
            .astimezone(_UTC)
            .replace(tzinfo=None)
        )
        buckets = {
            first + timedelta(days=offset): DayActivity(first + timedelta(days=offset))
            for offset in range(days)
        }

        def bucket(moment: datetime) -> DayActivity | None:
            return buckets.get(moment.replace(tzinfo=_UTC).astimezone(zone).date())

        messages = await self._session.execute(
            select(Message.direction, Message.created_at).where(
                Message.organization_id == organization_id, Message.created_at >= start_utc
            )
        )
        for direction, created_at in messages:
            target = bucket(created_at)
            if target is None:
                continue
            if direction == DIRECTION_INBOUND:
                target.user_messages += 1
            elif direction == DIRECTION_OUTBOUND:
                target.business_messages += 1

        audits = await self._session.execute(
            select(
                AuditLog.action,
                AuditLog.actor_type,
                AuditLog.after_json,
                AuditLog.metadata_json,
                AuditLog.created_at,
            ).where(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at >= start_utc,
                AuditLog.action.in_(("message.sent", "conversation.status_changed")),
            )
        )
        for action, actor_type, after, metadata, created_at in audits:
            target = bucket(created_at)
            if target is None:
                continue
            if action == "message.sent":
                if actor_type == ACTOR_SYSTEM:
                    # Automatic replies were counted as business messages above; move them.
                    target.chatbot_messages += 1
                    target.business_messages = max(0, target.business_messages - 1)
                continue
            source = (metadata or {}).get("source")
            status = (after or {}).get("status")
            if source == "agent_intervention":
                target.intervened += 1
            elif status == "resolved":
                target.closed += 1
        return [buckets[key] for key in sorted(buckets)]
