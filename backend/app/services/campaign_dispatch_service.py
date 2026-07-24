"""Campaign dispatch (Doc 04 §17; Doc 06 §2.3) — FR-CAM-05/09/10.

The engine that turns a materialized roster into messages. It orchestrates; it does not send:
every message goes through :class:`~app.services.send_service.SendService`, which is what puts each
one through the rate gate, the ledger, the conversation engine and the retry engine exactly as an
agent's send would. A campaign is a lot of ordinary sends, not a special kind of send.

**Resume is the design, not a feature** (FR-CAM-09). Nothing here trusts the queue: batches and
recipient status are durable, so a restarted worker re-derives what is owed from the database.
Re-dispatching a campaign is safe — planned batches are reused, and a recipient that already has a
message is skipped rather than sent to a real person twice.

**Progress is derived, then denormalized** (FR-CAM-10). The counters on `campaigns` are a mirror of
`campaign_recipients`, recomputed from the roster rather than incremented in flight, because an
increment that races or replays leaves a number nobody can explain.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.models import MessageType
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    CAMPAIGN_COMPLETED,
    CAMPAIGN_DISPATCHABLE,
    CAMPAIGN_QUEUED,
    CAMPAIGN_RUNNING,
    CAMPAIGN_SENDING,
    RECIPIENT_DELIVERED,
    RECIPIENT_FAILED,
    RECIPIENT_PENDING,
    RECIPIENT_QUEUED,
    RECIPIENT_READ,
    RECIPIENT_SENT,
    Campaign,
    CampaignRecipient,
)
from app.models.message import Message
from app.models.user import User
from app.repositories.campaign import (
    CampaignBatchRepository,
    CampaignRecipientRepository,
    CampaignRepository,
)
from app.repositories.contact import ContactRepository
from app.repositories.template import TemplateRepository
from app.repositories.user import UserRepository
from app.repositories.waba import PhoneNumberRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.campaign_batch_service import CampaignBatchService
from app.services.campaign_retry_service import CampaignRetryService
from app.services.send_service import SendService

logger = get_logger(__name__)

#: Doc 06 §2.3 lanes: control orchestrates, bulk sends.
CONTROL_QUEUE = "campaigns.control"
BULK_QUEUE = "sends.bulk"
DISPATCH_TASK = "app.crm.campaign_tasks.dispatch_campaign"
BATCH_TASK = "app.crm.campaign_tasks.dispatch_campaign_batch"
RECIPIENT_TASK = "app.crm.campaign_tasks.send_campaign_recipient"

#: Recipient states that mean the send happened; a dispatch never revisits them (FR-CAM-09).
RECIPIENT_SETTLED = (
    RECIPIENT_SENT,
    RECIPIENT_DELIVERED,
    RECIPIENT_READ,
    RECIPIENT_FAILED,
)


@dataclass(slots=True)
class Progress:
    """What ``GET /campaigns/{uuid}/progress`` answers (FR-CAM-10)."""

    status: str
    total: int
    pending: int
    queued: int
    sent: int
    delivered: int
    read: int
    failed: int
    batches_total: int
    batches_done: int


class CampaignNotDispatchable(ConflictError):
    """The campaign is not in a state where handing it to the send fabric makes sense."""

    code = "campaign_not_dispatchable"
    title = "Campaign Not Dispatchable"


class CampaignDispatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignRepository(session)
        self._recipients = CampaignRecipientRepository(session)
        self._batches = CampaignBatchRepository(session)
        self._contacts = ContactRepository(session)
        self._templates = TemplateRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._users = UserRepository(session)
        self._batch_service = CampaignBatchService(session)
        self._retry_service = CampaignRetryService(session)
        self._audit = AuditService(session)

    # --- Accept (request path) ----------------------------------------------
    async def start(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> Campaign:
        """Validate and hand the campaign to the control lane. No sending on this path."""
        campaign = await self._campaign(organization_id, public_id)
        if campaign.status not in CAMPAIGN_DISPATCHABLE:
            raise CampaignNotDispatchable(
                f"A {campaign.status} campaign cannot be dispatched."
            )
        await self._validate(campaign)

        campaign.status = CAMPAIGN_QUEUED
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._campaigns.flush()
        # One audit row for the act an operator took. The messages it produces are data, not
        # decisions — auditing each of a hundred thousand would bury the trail it belongs in.
        await self._audit.record(
            AuditAction.CAMPAIGN_DISPATCHED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            after={"total_recipients": campaign.total_recipients, "name": campaign.name},
        )
        await self._session.commit()
        return campaign

    async def _validate(self, campaign: Campaign) -> None:
        """Everything that must be true before a single message is queued (FR-CAM-02/05)."""
        if not campaign.total_recipients:
            raise CampaignNotDispatchable(
                "This campaign has no recipients; resolve its audience first."
            )
        template = await self._templates.get_by_id(campaign.template_id)
        if template is None or not template.is_sendable:
            # Re-checked at dispatch, not just at create: Meta may have paused the template since.
            raise CampaignNotDispatchable(
                f"Template is {template.status if template else 'missing'} and cannot be sent."
            )
        number = await self._numbers.get_by_id(campaign.phone_number_id)
        if number is None or number.deleted_at is not None:
            raise CampaignNotDispatchable("The sending number is no longer connected.")

    # --- Orchestration (campaigns.control) ----------------------------------
    async def plan(self, campaign_pk: int) -> dict[str, Any]:
        """Batch the roster and report what to fan out (FR-CAM-05/09).

        Idempotent by re-derivation (Doc 06 §2.3 "control tasks are idempotent"): a redelivered
        task finds the batches it already made and returns the ones still owed.
        """
        campaign = await self._campaigns.get_by_id(campaign_pk)
        if campaign is None:
            return {"status": "missing", "campaign": campaign_pk}

        batches = await self._batch_service.plan(campaign)
        if campaign.status != CAMPAIGN_RUNNING:
            campaign.status = CAMPAIGN_RUNNING
            campaign.started_at = campaign.started_at or utcnow()
        await self._campaigns.flush()
        await self._session.commit()
        return {
            "status": CAMPAIGN_RUNNING,
            "campaign": campaign_pk,
            "batches": [b.id for b in batches],
        }

    async def fan_out(self, batch_pk: int) -> dict[str, Any]:
        """The recipients a batch still owes (FR-CAM-05)."""
        batch = await self._batches.get_by_id(batch_pk)
        if batch is None:
            return {"status": "missing", "batch": batch_pk}
        recipients = await self._recipients.list_for_batch(batch_pk)
        await self._batch_service.mark_dispatched(batch)
        await self._session.commit()
        return {
            "status": "dispatched",
            "batch": batch_pk,
            "recipients": [r.id for r in recipients],
        }

    # --- Per-recipient send (sends.bulk) ------------------------------------
    async def send_recipient(self, recipient_pk: int) -> dict[str, Any]:
        """Send one campaign message, through SendService (FR-CAM-05/10).

        Idempotent on the recipient row (Doc 06 §2.3 keys on ``campaign_recipient_id``): a settled
        recipient is left alone, and one that already produced a message is delivered rather than
        re-accepted, so a redelivered task cannot double-send.
        """
        recipient = await self._recipients.get_by_id(recipient_pk)
        if recipient is None:
            return {"status": "missing", "recipient": recipient_pk}
        if recipient.status in RECIPIENT_SETTLED:
            return {"status": recipient.status, "recipient": recipient_pk, "skipped": True}

        campaign = await self._campaigns.get_by_id(recipient.campaign_id)
        if campaign is None:
            return {"status": "missing", "recipient": recipient_pk}
        if campaign.status not in CAMPAIGN_SENDING:
            # The switch pause and cancel throw (FR-CAM-06/07). Tasks already fanned out keep
            # arriving and keep declining, which is why pausing is not a race against the queue.
            return {"status": "halted", "recipient": recipient_pk, "campaign": campaign.status}

        sender = SendService(self._session)
        if recipient.message_id is None:
            message = await self._accept(sender, campaign, recipient)
            if message is None:
                return {"status": recipient.status, "recipient": recipient_pk}
            recipient.message_id = message.id
            recipient.status = RECIPIENT_QUEUED
            recipient.queued_at = utcnow()
            await self._recipients.flush()
            await self._session.commit()

        # Throttling and channel failures are classified by the retry engine and recorded
        # durably (FR-CAM-08): Celery's own retry lives in Redis, and a campaign held at Meta's
        # rate limit must survive a flush (Doc 03 §8.4).
        try:
            result = await sender.deliver(recipient.message_id)
        except Exception as exc:  # noqa: BLE001 - the engine decides retry vs terminal
            outcome = await self._retry_service.record(recipient, exc)
            await self.refresh_progress(recipient.campaign_id)
            return {"status": outcome, "recipient": recipient_pk}
        recipient.wamid = result.get("wamid")
        recipient.status = RECIPIENT_SENT if result.get("wamid") else recipient.status
        if result.get("status") == "failed":
            recipient.status = RECIPIENT_FAILED
            recipient.failed_at = utcnow()
        elif recipient.status == RECIPIENT_SENT:
            recipient.sent_at = utcnow()
        await self._recipients.flush()
        await self._session.commit()

        await self._retry_service.settle(
            recipient_pk, succeeded=recipient.status == RECIPIENT_SENT
        )
        if recipient.batch_id:
            await self._batch_service.settle(recipient.batch_id)
        await self.refresh_progress(recipient.campaign_id)
        return {"status": recipient.status, "recipient": recipient_pk, "wamid": recipient.wamid}

    async def _accept(
        self, sender: SendService, campaign: Campaign, recipient: CampaignRecipient
    ) -> Message | None:
        """Hand one recipient's message to SendService, or record why it cannot be sent."""
        contact = await self._contacts.get_by_id(recipient.contact_id)
        template = await self._templates.get_by_id(campaign.template_id)
        number = await self._numbers.get_by_id(campaign.phone_number_id)
        if contact is None or template is None or number is None:
            await self._skip(
                recipient,
                code="missing_ref",
                detail="contact, template, or sending number is gone",
            )
            return None

        variables = recipient.variables_json or {}
        try:
            return await sender.accept(
                organization_id=campaign.organization_id,
                actor=await self._creator(campaign),
                number=number,
                to=contact.phone_e164,
                message_type=MessageType.TEMPLATE,
                content={
                    "template": {
                        "id": template.public_id,
                        "header": list(variables.get("header") or []),
                        "body": list(variables.get("body") or []),
                        "buttons": [],
                    }
                },
                campaign_id=campaign.id,
                audit=False,
            )
        except Exception as exc:  # noqa: BLE001 - a rejected recipient must not stop the batch
            # Opt-out, an unapproved template, a bad variable count: all of them are this
            # recipient's problem, and the rest of the campaign carries on (Doc 07 §17.4's
            # isolation principle applied to a roster).
            await self._skip(recipient, code="rejected", detail=f"{type(exc).__name__}: {exc}")
            return None

    async def _skip(self, recipient: CampaignRecipient, *, code: str, detail: str) -> None:
        recipient.status = RECIPIENT_FAILED
        recipient.error_code = code[:24]
        recipient.error_detail = detail[:512]
        recipient.failed_at = utcnow()
        await self._recipients.flush()
        await self._session.commit()
        logger.warning(
            "campaign_recipient_rejected",
            extra={"recipient": recipient.id, "code": code, "detail": detail[:256]},
        )

    async def _creator(self, campaign: Campaign) -> User:
        """The operator the campaign's messages are attributed to."""
        user = await self._users.get_by_id(campaign.created_by) if campaign.created_by else None
        if user is None:
            raise NotFoundError("The campaign's creator no longer exists.")
        return user

    # --- Progress (FR-CAM-10) -----------------------------------------------
    async def refresh_progress(self, campaign_pk: int) -> Campaign | None:
        """Recompute the denormalized counters from the roster (Doc 03 §8.1).

        Derived rather than incremented: an increment that replays or races produces a counter
        nobody can reconcile, and the roster is the authority anyway.
        """
        campaign = await self._campaigns.get_by_id(campaign_pk)
        if campaign is None:
            return None
        counts = await self._recipients.counts_by_status(campaign_pk)
        campaign.queued_count = counts.get(RECIPIENT_QUEUED, 0)
        campaign.sent_count = counts.get(RECIPIENT_SENT, 0)
        campaign.delivered_count = counts.get(RECIPIENT_DELIVERED, 0)
        campaign.read_count = counts.get(RECIPIENT_READ, 0)
        campaign.failed_count = counts.get(RECIPIENT_FAILED, 0)

        outstanding = counts.get(RECIPIENT_PENDING, 0) + counts.get(RECIPIENT_QUEUED, 0)
        if not outstanding and campaign.status == CAMPAIGN_RUNNING:
            campaign.status = CAMPAIGN_COMPLETED
            campaign.completed_at = utcnow()
        await self._campaigns.flush()
        await self._session.commit()
        return campaign

    async def progress(self, organization_id: int, public_id: uuidlib.UUID) -> Progress:
        campaign = await self._campaign(organization_id, public_id)
        counts = await self._recipients.counts_by_status(campaign.id)
        batches = await self._batches.list_for_campaign(campaign.id)
        return Progress(
            status=campaign.status,
            total=campaign.total_recipients,
            pending=counts.get(RECIPIENT_PENDING, 0),
            queued=counts.get(RECIPIENT_QUEUED, 0),
            sent=counts.get(RECIPIENT_SENT, 0),
            delivered=counts.get(RECIPIENT_DELIVERED, 0),
            read=counts.get(RECIPIENT_READ, 0),
            failed=counts.get(RECIPIENT_FAILED, 0),
            batches_total=len(batches),
            batches_done=len([b for b in batches if b.status == "done"]),
        )

    async def _campaign(self, organization_id: int, public_id: uuidlib.UUID) -> Campaign:
        campaign = await self._campaigns.get_active_by_uuid(organization_id, public_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign
