"""Operational inbox policy backed by the organization settings authority (CORE-11A/11B).

The generic settings table remains the persistence mechanism, but this service gives the policy a
validated contract and real consumers: new-thread assignment, inbound consent recognition,
organization working hours, and guarded welcome/off-hours reply selection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM
from app.models.contact import OPT_IN_OPTED_IN, OPT_IN_OPTED_OUT, Contact
from app.models.contact_event import EVENT_OPTIN_CHANGED
from app.models.conversation import CONV_OPEN, CONV_PENDING, CONV_RESOLVED, Conversation
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.settings import SettingRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.settings import (
    InboxOperationsResponse,
    InboxOperationsSettings,
    WorkingDaySettings,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.business_event_service import BusinessEventService
from app.services.contact_event_service import ContactEventService

INBOX_OPERATIONS_KEY = "inbox.operations.v1"
AUTO_REPLY_MAX_AGE = timedelta(minutes=10)
AUTO_REPLY_FUTURE_TOLERANCE = timedelta(minutes=5)
AUTO_RESOLVE_SCAN_LIMIT = 100

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutomaticReplyDecision:
    kind: str
    body: str


class InboxOperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SettingRepository(session)
        self._users = UserRepository(session)
        self._conversations = ConversationRepository(session)
        self._tasks = TaskRepository(session)
        self._contacts = ContactRepository(session)
        self._organizations = OrganizationRepository(session)
        self._events = ContactEventService(session)
        self._business_events = BusinessEventService(session)
        self._audit = AuditService(session)

    async def get(self, organization_id: int) -> InboxOperationsResponse:
        row = await self._settings.get_org_setting(organization_id, INBOX_OPERATIONS_KEY)
        organization = await self._organizations.get_by_id(organization_id)
        policy = InboxOperationsSettings.model_validate(row.value_json if row is not None else {})
        return InboxOperationsResponse(
            **policy.model_dump(),
            configured=row is not None,
            updated_at=row.updated_at if row is not None else None,
            organization_timezone=organization.timezone if organization is not None else "UTC",
        )

    async def update(
        self, *, organization_id: int, actor: User, policy: InboxOperationsSettings
    ) -> InboxOperationsResponse:
        organization = await self._organizations.get_by_id(organization_id)
        timezone = organization.timezone if organization is not None else "UTC"
        if policy.working_hours.enabled:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValidationError(
                    "Working hours require a valid organization timezone.",
                    errors=[
                        {
                            "field": "working_hours",
                            "code": "invalid_organization_timezone",
                            "message": f"update the organization timezone before enabling hours ({timezone})",
                        }
                    ],
                ) from exc
        current = await self._settings.get_org_setting(organization_id, INBOX_OPERATIONS_KEY)
        before = current.value_json if current is not None else None
        value = policy.model_dump(mode="json")
        row = await self._settings.upsert_org(
            organization_id=organization_id,
            key=INBOX_OPERATIONS_KEY,
            value=value,
            value_type="json",
            updated_by=actor.id,
        )
        await self._audit.record(
            AuditAction.SETTING_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="setting",
            entity_id=row.id,
            before={"key": INBOX_OPERATIONS_KEY, "value": before},
            after={"key": INBOX_OPERATIONS_KEY, "value": value},
        )
        await self._session.commit()
        return InboxOperationsResponse(
            **policy.model_dump(),
            configured=True,
            updated_at=row.updated_at,
            organization_timezone=timezone,
        )

    async def assign_new_conversation(self, conversation: Conversation) -> None:
        """Apply the configured rule once, when a thread is first created.

        ``least_open`` selects an active same-organization user who can read the inbox, with Owner
        superusers participating through the normal bypass rule. Resolved threads do not count as
        active workload. Ties are stable by user id.
        """
        policy = await self.get(conversation.organization_id)
        if policy.assignment_mode != "least_open" or conversation.assigned_user_id is not None:
            return
        eligible = await self._users.list_active_with_permission(
            conversation.organization_id, "inbox:read"
        )
        if not eligible:
            return
        loads = await self._conversations.active_counts_by_assignee(
            conversation.organization_id, [user.id for user in eligible]
        )
        assignee = min(eligible, key=lambda user: (loads.get(user.id, 0), user.id))
        conversation.assigned_user_id = assignee.id
        await self._conversations.flush()
        await self._audit.record(
            AuditAction.CONVERSATION_ASSIGNED,
            actor_type=ACTOR_SYSTEM,
            organization_id=conversation.organization_id,
            entity_type="conversation",
            entity_id=conversation.id,
            before={"assigned_user_id": None},
            after={"assigned_user_id": assignee.id, "policy": "least_open"},
        )

    async def auto_resolve_inactive(
        self, *, now: datetime | None = None, limit_per_organization: int = AUTO_RESOLVE_SCAN_LIMIT
    ) -> dict[str, int]:
        """Resolve eligible inactive threads using the persisted organization policy.

        Candidate discovery is bounded per organization. Every row is then locked and rechecked,
        so overlapping scheduler ticks or a racing inbound/manual update converge safely.
        """
        evaluated_at = now or utcnow()
        result = {
            "organizations": 0,
            "candidates": 0,
            "resolved": 0,
            "skipped": 0,
            "invalid_policies": 0,
        }
        settings = await self._settings.list_org_settings_by_key(INBOX_OPERATIONS_KEY)
        for row in settings:
            try:
                policy = InboxOperationsSettings.model_validate(row.value_json or {})
            except ValueError:
                # A historic or out-of-band malformed JSON row must not stop every tenant's scan.
                result["invalid_policies"] += 1
                logger.warning(
                    "Skipping invalid inbox operations policy",
                    extra={"organization_id": row.organization_id, "setting_id": row.id},
                )
                continue
            if not policy.auto_resolve.enabled or row.organization_id is None:
                continue

            organization_id = int(row.organization_id)
            result["organizations"] += 1
            cutoff = evaluated_at - timedelta(hours=policy.auto_resolve.inactive_after_hours)
            candidates = await self._conversations.auto_resolve_candidates(
                organization_id=organization_id,
                cutoff=cutoff,
                limit=limit_per_organization,
            )
            result["candidates"] += len(candidates)
            for candidate in candidates:
                conversation = await self._conversations.lock_by_id(
                    organization_id, candidate.id
                )
                if not self._auto_resolve_eligible(conversation, cutoff=cutoff):
                    result["skipped"] += 1
                    await self._session.commit()
                    continue
                assert conversation is not None  # narrowed by the eligibility guard
                assert conversation.last_message_at is not None
                if await self._tasks.has_open_for_conversation(
                    organization_id=organization_id,
                    conversation_id=conversation.id,
                ):
                    result["skipped"] += 1
                    await self._session.commit()
                    continue

                previous_status = conversation.status
                activity_at = max(conversation.last_message_at, conversation.updated_at)
                conversation.status = CONV_RESOLVED
                conversation.row_version += 1
                await self._conversations.flush()
                await self._audit.record(
                    AuditAction.CONVERSATION_STATUS_CHANGED,
                    actor_type=ACTOR_SYSTEM,
                    organization_id=organization_id,
                    entity_type="conversation",
                    entity_id=conversation.id,
                    before={"status": previous_status},
                    after={"status": CONV_RESOLVED},
                    metadata={
                        "source": "inbox_operations",
                        "policy": "auto_resolve",
                        "inactive_after_hours": policy.auto_resolve.inactive_after_hours,
                        "activity_at": activity_at.isoformat(),
                    },
                )
                await self._business_events.record_conversation_auto_resolved(
                    organization_id=organization_id,
                    conversation_id=conversation.id,
                    contact_id=conversation.contact_id,
                    activity_at=activity_at,
                    resolved_at=evaluated_at,
                    previous_status=previous_status,
                    inactive_after_hours=policy.auto_resolve.inactive_after_hours,
                )
                await self._session.commit()
                result["resolved"] += 1
        return result

    @staticmethod
    def _auto_resolve_eligible(
        conversation: Conversation | None, *, cutoff: datetime
    ) -> bool:
        return bool(
            conversation is not None
            and conversation.deleted_at is None
            and conversation.status in {CONV_OPEN, CONV_PENDING}
            and conversation.unread_count == 0
            and conversation.last_message_at is not None
            and conversation.last_message_at <= cutoff
            and conversation.updated_at <= cutoff
        )

    async def apply_consent_keyword(
        self,
        *,
        contact: Contact,
        message_type: str,
        content: dict[str, Any],
        occurred_at: datetime,
        policy: InboxOperationsResponse | None = None,
    ) -> bool:
        """Apply an exact configured keyword to the contact, inside the inbound transaction."""
        if message_type != "text":
            return False
        policy = policy or await self.get(contact.organization_id)
        if not policy.consent.enabled:
            return False
        body = content.get("body")
        if not isinstance(body, str):
            return False
        keyword = " ".join(body.strip().upper().split())
        target: str | None = None
        if keyword in policy.consent.opt_in_keywords:
            target = OPT_IN_OPTED_IN
        elif keyword in policy.consent.opt_out_keywords:
            target = OPT_IN_OPTED_OUT
        if target is None or target == contact.opt_in_status:
            return False

        previous = contact.opt_in_status
        contact.opt_in_status = target
        if target == OPT_IN_OPTED_IN:
            contact.opt_in_at = occurred_at
        else:
            contact.opt_out_at = occurred_at
        contact.row_version += 1
        await self._contacts.flush()
        await self._events.record(
            organization_id=contact.organization_id,
            contact_id=contact.id,
            event_type=EVENT_OPTIN_CHANGED,
            payload={"from": previous, "to": target, "source": "inbound_keyword"},
        )
        await self._audit.record(
            AuditAction.CONTACT_UPDATED,
            actor_type=ACTOR_SYSTEM,
            organization_id=contact.organization_id,
            entity_type="contact",
            entity_id=contact.id,
            before={"opt_in_status": previous},
            after={"opt_in_status": target},
            metadata={"source": "inbound_keyword", "keyword": keyword},
        )
        return True

    @staticmethod
    def automatic_reply_decision(
        *,
        policy: InboxOperationsResponse,
        occurred_at: datetime,
        opened_new_window: bool,
        has_recent_off_hours_reply: bool,
        now: datetime | None = None,
    ) -> AutomaticReplyDecision | None:
        """Choose at most one safe reply for a freshly accepted inbound message.

        Historical replay must never contact a customer unexpectedly, so messages older than ten
        minutes (or implausibly far in the future) are ledger-only. When hours are enabled, an
        outside-hours reply takes precedence over a welcome reply. Welcome is limited to a newly
        opened 24-hour customer window; off-hours is limited by the caller to one per 24 hours.
        """
        evaluated_at = now or utcnow()
        age = evaluated_at - occurred_at
        if age > AUTO_REPLY_MAX_AGE or age < -AUTO_REPLY_FUTURE_TOLERANCE:
            return None

        replies = policy.automatic_replies
        if policy.working_hours.enabled:
            zone = InboxOperationsService._safe_zone(policy.organization_timezone)
            if zone is None:
                return None
            if not InboxOperationsService._is_within_working_hours(
                occurred_at, zone, policy.working_hours.days
            ):
                if replies.off_hours_enabled and not has_recent_off_hours_reply:
                    return AutomaticReplyDecision(kind="off_hours", body=replies.off_hours_body)
                return None

        if opened_new_window and replies.welcome_enabled:
            return AutomaticReplyDecision(kind="welcome", body=replies.welcome_body)
        return None

    @staticmethod
    def _safe_zone(name: str) -> ZoneInfo | None:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            return None

    @staticmethod
    def _is_within_working_hours(
        occurred_at: datetime, zone: ZoneInfo, days: list[WorkingDaySettings]
    ) -> bool:
        local = occurred_at.replace(tzinfo=UTC).astimezone(zone)
        by_day: dict[str, WorkingDaySettings] = {day.day: day for day in days}
        # Include yesterday so a Monday 22:00–Tuesday 06:00 interval is open at Tuesday 01:00.
        for date_offset in (0, -1):
            anchor = local.date() + timedelta(days=date_offset)
            schedule = by_day[anchor.strftime("%A").lower()]
            if not schedule.enabled:
                continue
            start_value = time.fromisoformat(schedule.start)
            end_value = time.fromisoformat(schedule.end)
            start = datetime.combine(anchor, start_value, tzinfo=zone)
            end_date = anchor + timedelta(days=1) if end_value <= start_value else anchor
            end = datetime.combine(end_date, end_value, tzinfo=zone)
            if start <= local < end:
                return True
        return False
