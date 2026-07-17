"""Campaign smart retry (Doc 03 §8.4; Doc 06 §6) — FR-CAM-08.

**The retry engine decides; this records.** Which failures are worth another attempt, how many, and
how long to wait are :mod:`app.queue.retry`'s answers — the same ones the webhook, send and media
lanes use, including Meta's own error map. Nothing about backoff or classification is restated
here; that would let a campaign drift from the platform's definition of "retryable".

What this adds is **durability** (Doc 03 §8.4, NFR-DR-06). A Celery retry lives in Redis, and a
campaign paused on Meta's rate limit at 3am must still finish after a flush. So every pending
re-attempt is a row: ``next_attempt_at`` carries the engine's backoff, ``attempt`` carries its cap,
and a scanner picks up whatever is due.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    RECIPIENT_FAILED,
    RETRY_EXHAUSTED,
    RETRY_PENDING,
    RETRY_RETRYING,
    RETRY_SUCCEEDED,
    CampaignRecipient,
    CampaignRetry,
)
from app.queue.retry import backoff_seconds, classify, should_retry
from app.repositories.campaign import CampaignRecipientRepository, CampaignRetryRepository

logger = get_logger(__name__)

#: Doc 06 §2.3's delayed re-attempt lane.
RETRY_QUEUE = "sends.retry"
RETRY_TASK = "app.crm.campaign_tasks.retry_campaign_recipient"


class CampaignRetryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._retries = CampaignRetryRepository(session)
        self._recipients = CampaignRecipientRepository(session)

    async def record(self, recipient: CampaignRecipient, exc: BaseException) -> str:
        """Schedule another attempt, or fail the recipient for good (FR-CAM-08).

        Returns the outcome: ``pending`` (queued to retry) or ``failed`` (terminal or exhausted).
        """
        failure = classify(exc)
        attempt = recipient.retry_count + 1
        detail = f"{type(exc).__name__}: {exc}"
        code = getattr(exc, "code", None)

        if not should_retry(failure, attempt):
            # Terminal by class, or out of attempts — either way, asking again cannot help.
            await self._exhaust(recipient, code=code, detail=detail)
            return RECIPIENT_FAILED

        recipient.retry_count = attempt
        recipient.error_code = str(code)[:24] if code else str(failure)[:24]
        recipient.error_detail = detail[:512]
        await self._recipients.flush()
        await self._retries.add(
            CampaignRetry(
                campaign_id=recipient.campaign_id,
                recipient_id=recipient.id,
                attempt=attempt,
                error_code=str(code)[:24] if code else str(failure)[:24],
                # The engine's curve, not ours: exponential with full jitter (Doc 06 §6.3).
                next_attempt_at=utcnow() + timedelta(seconds=backoff_seconds(failure, attempt)),
                status=RETRY_PENDING,
            )
        )
        await self._session.commit()
        logger.info(
            "campaign_retry_scheduled",
            extra={"recipient": recipient.id, "attempt": attempt, "class": str(failure)},
        )
        return RETRY_PENDING

    async def _exhaust(self, recipient: CampaignRecipient, *, code, detail: str) -> None:
        recipient.status = RECIPIENT_FAILED
        recipient.error_code = str(code)[:24] if code else None
        recipient.error_detail = detail[:512]
        recipient.failed_at = utcnow()
        for row in await self._retries.for_recipient(recipient.id):
            if row.status in (RETRY_PENDING, RETRY_RETRYING):
                row.status = RETRY_EXHAUSTED
        await self._recipients.flush()
        await self._session.commit()
        logger.warning(
            "campaign_retry_exhausted",
            extra={"recipient": recipient.id, "attempts": recipient.retry_count},
        )

    async def due(self, *, limit: int) -> list[CampaignRetry]:
        """Rows whose backoff has expired — what the scanner hands back to the send lane."""
        return await self._retries.due(utcnow(), limit=limit)

    async def claim(self, retry: CampaignRetry) -> None:
        retry.status = RETRY_RETRYING
        await self._retries.flush()
        await self._session.commit()

    async def settle(self, recipient_pk: int, *, succeeded: bool) -> None:
        """Close out a recipient's retry rows once the re-attempt resolved."""
        for row in await self._retries.for_recipient(recipient_pk):
            if row.status in (RETRY_PENDING, RETRY_RETRYING):
                row.status = RETRY_SUCCEEDED if succeeded else RETRY_EXHAUSTED
        await self._retries.flush()
        await self._session.commit()

    async def cancel_for_campaign(self, campaign_pk: int) -> int:
        """Drop a cancelled campaign's pending re-attempts (FR-CAM-07)."""
        rows = [
            r
            for r in await self._retries.for_campaign(campaign_pk)
            if r.status in (RETRY_PENDING, RETRY_RETRYING)
        ]
        for row in rows:
            row.status = RETRY_EXHAUSTED
        await self._retries.flush()
        return len(rows)
