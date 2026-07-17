"""Campaign lifecycle (Doc 04 §17) — FR-CAM-06/07/08.

Pause, resume, cancel, retry. Four transitions, one mechanism: **the campaign's status is the
switch**. Every send checks it before calling Meta, so pausing is not a race against a queue that
has already fanned out — the tasks keep arriving and keep declining to send.

That is also why pause and resume cannot duplicate (FR-CAM-06). Resume does not re-send anything:
it re-plans, and planning only ever picks up recipients that still owe a send. A recipient that
went out before the pause is settled, and settled rows are never revisited.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    CAMPAIGN_CANCELLED,
    CAMPAIGN_PAUSED,
    CAMPAIGN_QUEUED,
    CAMPAIGN_RUNNING,
    CAMPAIGN_TERMINAL,
    RECIPIENT_FAILED,
    RECIPIENT_PENDING,
    Campaign,
)
from app.models.user import User
from app.repositories.campaign import CampaignRecipientRepository, CampaignRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.campaign_retry_service import CampaignRetryService

logger = get_logger(__name__)


class CampaignStateError(ConflictError):
    """The transition does not apply from the campaign's current state (Doc 04 §17 → 409)."""

    code = "campaign_state"
    title = "Campaign State Conflict"


class CampaignLifecycleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignRepository(session)
        self._recipients = CampaignRecipientRepository(session)
        self._retries = CampaignRetryService(session)
        self._audit = AuditService(session)

    # --- Transitions ---------------------------------------------------------
    async def pause(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> Campaign:
        """Stop sending without losing the place (FR-CAM-06).

        In-flight tasks are not chased: they will read the paused status and decline. Nothing is
        rolled back, because a message already handed to Meta cannot be unsent.
        """
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status not in (CAMPAIGN_RUNNING, CAMPAIGN_QUEUED):
            raise CampaignStateError(f"A {campaign.status} campaign cannot be paused.")
        return await self._transition(
            campaign, CAMPAIGN_PAUSED, actor, AuditAction.CAMPAIGN_PAUSED
        )

    async def resume(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> Campaign:
        """Pick the campaign back up (FR-CAM-06).

        Sets it running; the caller re-dispatches, and planning is what makes that safe — it reuses
        the existing batches and only ever collects recipients that still owe a send.
        """
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status != CAMPAIGN_PAUSED:
            raise CampaignStateError(f"A {campaign.status} campaign cannot be resumed.")
        return await self._transition(
            campaign, CAMPAIGN_RUNNING, actor, AuditAction.CAMPAIGN_RESUMED
        )

    async def cancel(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> Campaign:
        """Stop the campaign for good and drop what it still owes (FR-CAM-07)."""
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status in CAMPAIGN_TERMINAL:
            raise CampaignStateError(f"A {campaign.status} campaign cannot be cancelled.")

        # Pending recipients are dropped, not failed: nothing went wrong with them, and they are
        # what the operator chose to stop (Doc 03 §8.3 `cancelled`).
        stopped = await self._recipients.cancel_pending(campaign.id)
        dropped = await self._retries.cancel_for_campaign(campaign.id)
        campaign.completed_at = utcnow()
        result = await self._transition(
            campaign,
            CAMPAIGN_CANCELLED,
            actor,
            AuditAction.CAMPAIGN_CANCELLED,
            extra={"recipients_cancelled": stopped, "retries_dropped": dropped},
        )
        logger.info(
            "campaign_cancelled",
            extra={"campaign": campaign.id, "cancelled": stopped, "retries": dropped},
        )
        return result

    async def retry_failed(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> tuple[Campaign, list[int]]:
        """Put failed recipients back in the queue (FR-CAM-08, Doc 04 §17).

        Deliberately manual and deliberately unfiltered by error class: automatic retry already
        happened and gave up. This is an operator saying "try again anyway" — usually after fixing
        the template or the number — so the answer is to reset and let the engine judge afresh.
        """
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status in (CAMPAIGN_CANCELLED,):
            raise CampaignStateError("A cancelled campaign cannot be retried.")

        failed = await self._recipients.list_by_status(campaign.id, RECIPIENT_FAILED)
        if not failed:
            raise CampaignStateError("This campaign has no failed recipients to retry.")

        for recipient in failed:
            recipient.status = RECIPIENT_PENDING
            recipient.error_code = None
            recipient.error_detail = None
            recipient.failed_at = None
            # The message it produced (if any) is abandoned: a fresh attempt gets a fresh ledger
            # row, so the failed one stays readable as what actually happened.
            recipient.message_id = None
            recipient.retry_count = 0
            recipient.batch_id = None
        campaign.status = CAMPAIGN_RUNNING
        campaign.completed_at = None
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._recipients.flush()
        await self._audit.record(
            AuditAction.CAMPAIGN_RETRIED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            after={"recipients": len(failed)},
        )
        await self._session.commit()
        return campaign, [r.id for r in failed]

    async def _transition(
        self,
        campaign: Campaign,
        status: str,
        actor: User,
        action: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> Campaign:
        before = campaign.status
        campaign.status = status
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._campaigns.flush()
        await self._audit.record(
            action,
            actor_user_id=actor.id,
            organization_id=campaign.organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            before={"status": before},
            after={"status": status, **(extra or {})},
        )
        await self._session.commit()
        return campaign

    async def _campaign(self, organization_id: int, public_id: uuidlib.UUID) -> Campaign:
        campaign = await self._campaigns.get_active_by_uuid(organization_id, public_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign
