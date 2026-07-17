"""Campaign batching & checkpoints (Doc 03 §8.4; FR-CAM-09).

Batches are how a campaign survives a crash. Splitting the roster into fixed slices and recording
each slice's state means a restarted worker asks the database "what still owes work?" instead of
guessing — and the recipients inside a slice carry its ``batch_id``, so an already-sent row is
skipped rather than sent to a real person twice.

The live queue is Celery/Redis; this is the **durable** checkpoint beside it, so a Redis flush
costs throughput rather than state (Doc 03 §8.4; NFR-DR-06).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    BATCH_DONE,
    BATCH_IN_PROGRESS,
    BATCH_PENDING,
    Campaign,
    CampaignBatch,
)
from app.repositories.campaign import (
    CampaignBatchRepository,
    CampaignRecipientRepository,
)

logger = get_logger(__name__)

#: Recipients per checkpoint. Small enough that a crash re-does little, large enough that the
#: control lane is not fanning out one task per message.
BATCH_SIZE = 500


class CampaignBatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._batches = CampaignBatchRepository(session)
        self._recipients = CampaignRecipientRepository(session)

    async def plan(self, campaign: Campaign) -> list[CampaignBatch]:
        """Slice whatever still owes a send into checkpoints, and report what is unfinished.

        Additive rather than idempotent-by-short-circuit, because "what is owed" changes for three
        different reasons and all three land here: a first dispatch (the whole roster is
        unbatched), a resume (nothing is unbatched — the existing checkpoints still hold the
        pending rows), and a manual retry (only the reset rows are unbatched). Existing batches are
        never renumbered; a worker may be part-way through one.
        """
        existing = await self._batches.list_for_campaign(campaign.id)
        unbatched = await self._recipients.list_unbatched(campaign.id)
        next_index = max((b.batch_index for b in existing), default=-1) + 1

        created: list[CampaignBatch] = []
        for index in range(0, len(unbatched), BATCH_SIZE):
            slice_ = unbatched[index : index + BATCH_SIZE]
            batch = CampaignBatch(
                campaign_id=campaign.id,
                batch_index=next_index + (index // BATCH_SIZE),
                size=len(slice_),
                status=BATCH_PENDING,
            )
            await self._batches.add(batch)
            for recipient in slice_:
                recipient.batch_id = batch.id
            created.append(batch)
        await self._batches.flush()

        outstanding = [b for b in existing if b.status != BATCH_DONE] + created
        logger.info(
            "campaign_batches_planned",
            extra={
                "campaign": campaign.id,
                "created": len(created),
                "outstanding": len(outstanding),
            },
        )
        return outstanding

    async def mark_dispatched(self, batch: CampaignBatch) -> None:
        batch.status = BATCH_IN_PROGRESS
        batch.dispatched_at = utcnow()
        await self._batches.flush()

    async def settle(self, batch_pk: int) -> bool:
        """Close a batch once nothing in it is still owed. Returns whether it closed.

        Checked after each recipient settles rather than assumed at fan-out: a batch is done when
        its work is done, not when its tasks were enqueued.
        """
        batch = await self._batches.get_by_id(batch_pk)
        if batch is None or batch.status == BATCH_DONE:
            return False
        outstanding = await self._recipients.count_unsettled(batch.campaign_id, batch_pk)
        if outstanding:
            return False
        batch.status = BATCH_DONE
        batch.completed_at = utcnow()
        await self._batches.flush()
        return True

    async def pending_for(self, campaign: Campaign) -> list[CampaignBatch]:
        return [
            b
            for b in await self._batches.list_for_campaign(campaign.id)
            if b.status in (BATCH_PENDING, BATCH_IN_PROGRESS)
        ]

