"""Export service (Doc 04 §14.1, Doc 06 §2.3 ``exports`` queue, FR-CON-15; Doc 15 §19).

**Entity dispatch.** One export system serves every exportable thing: contacts stream from the
operational table, analytics reports stream from the rollups, and governed conversation transcripts
stream from the message ledger. The ``exports`` row, queue, format writers, storage artifact and
signed-download flow are shared, so adding an entity adds a row generator — never a second pipeline.

Mirrors the import split:

* :meth:`ExportService.start` — the request path. Validates the filter, records the ``exports``
  row + ``job_metadata``, and hands off to the **Queue Engine**. Always ``202`` — it never reads
  a contact.
* :meth:`ExportService.run` — the worker body. Resolves the filter through the **same compiler**
  the segments/search use (so an export returns exactly what its preview showed), then walks the
  result **in keyset batches**, handing each batch to a per-format writer rather than loading
  every contact — a 1M-row export never materialises 1M ORM objects. The artifact is written
  through the **Storage** abstraction and handed back as a signed, expiring URL.

CSV, Excel and JSON contact exports differ only in the writer (:mod:`app.crm.formats`). Analytics
reports additionally support PDF through that same writer boundary, queue, storage and signed-link
pipeline.
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.crm.csv_io import EXPORT_COLUMNS, neutralize_formula
from app.crm.formats import CONTENT_TYPES, EXPORT_FORMATS, export_writer
from app.crm.segment_compiler import AttributeSpec, compile_rules, validate_rule
from app.db.mixins import utcnow
from app.integrations.google_sheets import GoogleSheetsClient
from app.models.campaign import RECIPIENT_STATUSES, Campaign, CampaignRecipient
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.job_records import (
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
    ExportJob,
)
from app.models.message import Message
from app.models.segment import MATCH_ALL, MATCH_TYPES
from app.models.user import User
from app.repositories.attribute import AttributeDefinitionRepository
from app.repositories.campaign import CampaignRecipientRepository, CampaignRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.export_job import ExportRepository
from app.repositories.message import MessageRepository
from app.repositories.segment import SegmentRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.job_service import JobService
from app.storage.base import get_provider

logger = get_logger(__name__)

#: Rows pulled per keyset batch while streaming (bounded memory, Doc 06 §2.3 exports).
_BATCH = 500

# --- Entities (Doc 15 §19) -----------------------------------------------------------------------
#: ``exports.entity`` is a free VARCHAR, so analytics reports are new *values* in the existing
#: export system rather than a second one.
ENTITY_CONTACTS = "contacts"
ENTITY_CONVERSATION_TRANSCRIPT = "conversation_transcript"
ENTITY_CAMPAIGN_RESULTS = "campaign_results"
REPORT_ENTITY_PREFIX = "report:"

TRANSCRIPT_COLUMNS = (
    "timestamp_utc",
    "direction",
    "participant",
    "message_type",
    "content",
    "status",
    "message_id",
)

CAMPAIGN_RESULT_COLUMNS = (
    "campaign_id",
    "campaign_name",
    "contact_id",
    "contact_name_current",
    "phone_e164_current",
    "recipient_status",
    "error_code",
    "retry_count",
    "cost_amount",
    "cost_currency",
    "queued_at_utc",
    "sent_at_utc",
    "delivered_at_utc",
    "read_at_utc",
    "failed_at_utc",
)

#: Which metrics each report exports. Keys are ``AnalyticsQueryService.METRICS`` entries; the
#: query layer owns their definitions, so a report can never disagree with a dashboard.
REPORT_METRICS: dict[str, tuple[str, ...]] = {
    "messages": (
        "messages_accepted", "messages_sent", "messages_delivered",
        "messages_read", "messages_failed",
    ),
    "failures": ("failures",),
    "campaigns": (
        "campaign_targeted", "campaign_sent", "campaign_delivered",
        "campaign_read", "campaign_failed", "campaign_skipped",
    ),
    "conversations": (
        "conversations_opened", "conversations_resolved",
        "inbound_messages", "outbound_messages", "conversations_handled",
    ),
    "tasks": (
        "tasks_created", "tasks_completed", "tasks_completed_on_time",
        "tasks_skipped", "tasks_cancelled", "tasks_overdue_entered",
    ),
    "customers": (
        "contacts_created", "contacts_opted_in", "contacts_opted_out",
        "contacts_reactivated", "active_customer_hours",
    ),
    "costs": ("cost_micros", "campaign_cost_micros", "messages_delivered"),
    "reactivation": (
        "reactivation_cases_created",
        "reactivation_stage_transitions",
        "reactivation_completed",
        "reactivation_not_required",
        "eligibility_decisions",
        "eligibility_eligible",
        "eligibility_not_eligible",
        "eligibility_review_required",
        "reactivation_turnaround_seconds_sum",
        "reactivation_turnaround_count",
    ),
    "kyc": (
        "kyc_decisions",
        "kyc_approved",
        "kyc_rejected",
        "kyc_needs_information",
        "kyc_turnaround_seconds_sum",
        "kyc_turnaround_count",
    ),
    "service_levels": (
        "sla_started",
        "sla_breached",
        "sla_resolved",
        "sim_transitions",
        "sim_delivered",
        "sim_failed",
        "activation_transitions",
        "activations_completed",
        "activations_rejected",
    ),
    "team_productivity": (
        "conversations_opened",
        "conversations_resolved",
        "conversations_handled",
        "outbound_messages",
        "first_response_seconds_sum",
        "first_response_count",
        "resolution_seconds_sum",
        "resolution_count",
        "tasks_created",
        "tasks_completed",
        "tasks_completed_on_time",
        "tasks_overdue_entered",
        "time_to_complete_seconds_sum",
        "time_to_complete_count",
    ),
}


def _parse_dt(value: Any) -> Any:
    """``filters_json`` round-trips through JSON, so datetimes come back as ISO strings."""
    from datetime import datetime as _dt

    return _dt.fromisoformat(value) if isinstance(value, str) else value


#: Contacts preserve FR-CON-15's CSV/Excel/JSON contract. PDF is report-only because the built-in
#: report font and table layout are intentionally optimized for analytics labels and numeric facts.
SUPPORTED_FORMATS = tuple(value for value in EXPORT_FORMATS if value != "pdf")
REPORT_SUPPORTED_FORMATS = EXPORT_FORMATS
TRANSCRIPT_SUPPORTED_FORMATS = EXPORT_FORMATS
CAMPAIGN_RESULT_SUPPORTED_FORMATS = EXPORT_FORMATS


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._exports = ExportRepository(session)
        self._evaluator = SegmentRepository(session)
        self._attributes = AttributeDefinitionRepository(session)
        self._conversations = ConversationRepository(session)
        self._messages = MessageRepository(session)
        self._campaigns = CampaignRepository(session)
        self._campaign_recipients = CampaignRecipientRepository(session)
        self._audit = AuditService(session)

    async def _specs(self, organization_id: int) -> dict[str, AttributeSpec]:
        return {
            definition.key_name: AttributeSpec(
                attribute_id=definition.id,
                data_type=definition.data_type,
                enum_values=definition.enum_values_json,
            )
            for definition in await self._attributes.list_for_org(organization_id)
        }

    # --- Request path --------------------------------------------------------
    async def start(
        self,
        *,
        organization_id: int,
        actor: User,
        file_format: str,
        match_type: str,
        rules: list[dict[str, Any]],
        dispatch: Callable[[str, str], Any],
        spreadsheet_id: str | None = None,
    ) -> ExportJob:
        """Record the export and enqueue it. Never reads contacts inline."""
        supported = (*SUPPORTED_FORMATS, "google_sheet")
        if file_format not in supported:
            raise ValidationError(
                "Unsupported export format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(supported)}",
                    }
                ],
            )
        if match_type not in MATCH_TYPES:
            raise ValidationError(
                "Invalid filter.",
                errors=[
                    {"field": "match_type", "code": "invalid", "message": str(list(MATCH_TYPES))}
                ],
            )
        # Fail fast: a bad filter is rejected now, not discovered by a worker later.
        specs = await self._specs(organization_id)
        for rule in rules:
            validate_rule(
                rule["field_source"], rule["field_key"], rule["operator"], rule.get("value"), specs
            )

        return await self._enqueue(
            organization_id=organization_id,
            actor=actor,
            entity=ENTITY_CONTACTS,
            file_format=file_format,
            filters_json={
                "match_type": match_type,
                "rules": rules,
                **({"spreadsheet_id": spreadsheet_id} if spreadsheet_id else {}),
            },
            task_name="app.crm.tasks.run_contact_export",
            audit_after={"format": file_format, "rules": len(rules)},
            dispatch=dispatch,
        )

    async def start_report(
        self,
        *,
        organization_id: int,
        actor: User,
        report: str,
        file_format: str,
        filters: dict[str, Any],
        dispatch: Callable[[str, str], Any],
    ) -> ExportJob:
        """Start an analytics report export (Doc 15 §19).

        A report **is** an export: same ``exports`` row, same queue, same worker discipline, same
        signed-download flow. Only the ``entity`` and the row generator differ, so no second export
        pipeline exists. The resolved range travels in ``filters_json``, which makes the artifact
        reproducible and self-describing.
        """
        if file_format not in REPORT_SUPPORTED_FORMATS:
            raise ValidationError(
                "Unsupported export format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(REPORT_SUPPORTED_FORMATS)}",
                    }
                ],
            )
        if report not in REPORT_METRICS:
            raise ValidationError(
                "Unknown report.",
                errors=[
                    {"field": "report", "code": "invalid", "message": str(sorted(REPORT_METRICS))}
                ],
            )
        return await self._enqueue(
            organization_id=organization_id,
            actor=actor,
            entity=f"{REPORT_ENTITY_PREFIX}{report}",
            file_format=file_format,
            filters_json=filters,
            task_name="app.analytics.tasks.run_report_export",
            audit_after={"format": file_format, "report": report},
            dispatch=dispatch,
        )

    async def start_transcript(
        self,
        *,
        organization_id: int,
        actor: User,
        conversation_id: uuidlib.UUID,
        file_format: str,
        start: Any = None,
        end: Any = None,
        dispatch: Callable[[str, str], Any],
    ) -> ExportJob:
        """Queue one tenant-scoped conversation transcript without reading its ledger inline."""
        if file_format not in TRANSCRIPT_SUPPORTED_FORMATS:
            raise ValidationError(
                "Unsupported transcript format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(TRANSCRIPT_SUPPORTED_FORMATS)}",
                    }
                ],
            )
        conversation = await self._conversations.get_active_by_uuid(
            organization_id, conversation_id.bytes
        )
        if conversation is None:
            # Tenant misses deliberately collapse to 404 so a public UUID cannot be probed.
            raise NotFoundError("Conversation not found.")
        filters = {
            "conversation_id": conversation.public_id,
            "from": start.isoformat() if start is not None else None,
            "to": end.isoformat() if end is not None else None,
        }
        return await self._enqueue(
            organization_id=organization_id,
            actor=actor,
            entity=ENTITY_CONVERSATION_TRANSCRIPT,
            file_format=file_format,
            filters_json=filters,
            task_name="app.crm.tasks.run_conversation_transcript_export",
            audit_after={
                "format": file_format,
                "conversation_id": conversation.public_id,
                "from": filters["from"],
                "to": filters["to"],
            },
            dispatch=dispatch,
        )

    async def start_campaign_results(
        self,
        *,
        organization_id: int,
        actor: User,
        campaign_id: uuidlib.UUID,
        file_format: str,
        recipient_status: str | None,
        dispatch: Callable[[str, str], Any],
    ) -> ExportJob:
        """Queue one tenant-scoped campaign's authoritative recipient ledger."""
        if file_format not in CAMPAIGN_RESULT_SUPPORTED_FORMATS:
            raise ValidationError(
                "Unsupported campaign export format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(CAMPAIGN_RESULT_SUPPORTED_FORMATS)}",
                    }
                ],
            )
        if recipient_status is not None and recipient_status not in RECIPIENT_STATUSES:
            raise ValidationError(
                "Invalid recipient status.",
                errors=[
                    {
                        "field": "status",
                        "code": "invalid",
                        "message": f"supported: {list(RECIPIENT_STATUSES)}",
                    }
                ],
            )
        campaign = await self._campaigns.get_active_by_uuid(organization_id, campaign_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        filters = {
            "campaign_id": campaign.public_id,
            "campaign_name": campaign.name,
            "status": recipient_status,
        }
        return await self._enqueue(
            organization_id=organization_id,
            actor=actor,
            entity=ENTITY_CAMPAIGN_RESULTS,
            file_format=file_format,
            filters_json=filters,
            task_name="app.crm.tasks.run_campaign_results_export",
            audit_after={
                "format": file_format,
                "campaign_id": campaign.public_id,
                "status": recipient_status,
            },
            dispatch=dispatch,
        )

    async def _enqueue(
        self,
        *,
        organization_id: int,
        actor: User,
        entity: str,
        file_format: str,
        filters_json: dict[str, Any],
        task_name: str,
        audit_after: dict[str, Any],
        dispatch: Callable[[str, str], Any],
    ) -> ExportJob:
        """Record the job, register it with the Queue Engine, audit it, and hand it off.

        Shared by every entity — the request path never reads the data it is exporting.
        """
        job = ExportJob(
            organization_id=organization_id,
            requested_by=actor.id,
            entity=entity,
            format=file_format,
            filters_json=filters_json,
        )
        await self._exports.add(job)

        task_id = str(uuidlib.uuid4())
        await JobService(self._session).record_queued(
            task_id=task_id,
            task_name=task_name,
            queue="exports",
            args={"export_id": job.public_id},
            ref_type="export",
            ref_id=job.id,
        )
        await self._audit.record(
            AuditAction.EXPORT_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="export",
            entity_id=job.id,
            after=audit_after,
        )
        await self._session.commit()
        dispatch(job.public_id, task_id)
        return job

    async def get(self, organization_id: int, public_id: uuidlib.UUID) -> ExportJob:
        job = await self._exports.get_for_org(organization_id, public_id.bytes)
        if job is None:
            raise NotFoundError("Export not found.")
        return job

    async def get_owned(
        self,
        organization_id: int,
        requested_by: int,
        public_id: uuidlib.UUID,
        *,
        entity: str,
    ) -> ExportJob:
        """Resolve a personal artifact without disclosing another user's job identifier."""
        job = await self.get(organization_id, public_id)
        if job.requested_by != requested_by or job.entity != entity:
            raise NotFoundError("Export not found.")
        return job

    async def get_campaign_results_owned(
        self,
        organization_id: int,
        requested_by: int,
        campaign_id: uuidlib.UUID,
        export_id: uuidlib.UUID,
    ) -> ExportJob:
        """Resolve one personal campaign artifact without cross-campaign UUID substitution."""
        campaign = await self._campaigns.get_active_by_uuid(organization_id, campaign_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        job = await self.get_owned(
            organization_id,
            requested_by,
            export_id,
            entity=ENTITY_CAMPAIGN_RESULTS,
        )
        if str((job.filters_json or {}).get("campaign_id")) != campaign.public_id:
            raise NotFoundError("Export not found.")
        return job

    async def download_url(self, job: ExportJob) -> str | None:
        """Signed, expiring link to the artifact once ready (FR-MED-09 access rules)."""
        if not job.storage_key or job.status != STATUS_READY:
            return None
        now = utcnow()
        if job.expires_at and job.expires_at <= now:
            return None
        ttl = settings.storage_signed_url_ttl_seconds
        if job.expires_at is not None:
            ttl = min(ttl, max(0, int((job.expires_at - now).total_seconds())))
        provider = get_provider(settings.storage_backend)
        return provider.signed_url(
            job.storage_key,
            media_id=f"export-{job.public_id}",
            expires_in=ttl,
        )

    # --- Worker path ---------------------------------------------------------
    @staticmethod
    def _row(contact: Contact) -> dict[str, Any]:
        return {
            "phone_e164": contact.phone_e164,
            "wa_id": contact.wa_id,
            "full_name": contact.full_name,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "locale": contact.locale,
            "country_code": contact.country_code,
            "opt_in_status": contact.opt_in_status,
            "source": contact.source,
            "tags": "|".join(tag.name for tag in contact.tags),
            "created_at": contact.created_at.isoformat(),
        }

    async def _write_contacts(self, job: ExportJob, writer: Any) -> int:
        """Stream contacts in keyset batches — a 1M-row export never materialises 1M ORM objects.

        Unchanged from the original single-entity implementation; only its call site moved behind
        the entity dispatch.
        """
        filters = job.filters_json or {}
        condition = compile_rules(
            organization_id=job.organization_id,
            match_type=filters.get("match_type", MATCH_ALL),
            rules=filters.get("rules", []),
            attributes=await self._specs(job.organization_id),
        )
        cursor: tuple[Any, int] | None = None
        written = 0
        while True:
            batch, has_more = await self._evaluator.paginate_matching(
                job.organization_id, condition, limit=_BATCH, cursor=cursor
            )
            if not batch:
                break
            writer.add([self._row(c) for c in batch])
            written += len(batch)
            # Progress is visible while a long export runs.
            job.row_count = written
            await self._exports.flush()
            await self._session.commit()
            if not has_more:
                break
            cursor = (batch[-1].created_at, batch[-1].id)
        return written

    async def _write_report(self, job: ExportJob, writer: Any) -> int:
        """Stream an analytics report from the **rollup** tables (Doc 15 §19).

        One row per local period, one column per metric — the pivot of the series envelope, which
        is what a spreadsheet wants. Reading rollups rather than the ledger is what keeps a
        year-long report bounded work.
        """
        # Imported here: the analytics query layer depends on nothing in this module, and a
        # module-level import would make the contact export path pay for it.
        from app.services.analytics_query_service import (
            AnalyticsQueryService,
            resolve_range,
        )

        report = job.entity.removeprefix(REPORT_ENTITY_PREFIX)
        metrics = REPORT_METRICS[report]
        filters = job.filters_json or {}
        spec = resolve_range(
            start=_parse_dt(filters.get("from")),
            end=_parse_dt(filters.get("to")),
            preset=filters.get("preset"),
            granularity=filters.get("granularity", "day"),
            timezone=filters.get("timezone"),
        )
        result = await AnalyticsQueryService(self._session).series(
            organization_id=job.organization_id, spec=spec, metrics=metrics
        )

        # Pivot: series-per-metric → row-per-period.
        by_period: dict[str, dict[str, Any]] = {}
        for series in result.series:
            for point in series.points:
                by_period.setdefault(point.t, {"period": point.t})[series.key] = point.v

        rows = [by_period[key] for key in sorted(by_period)]
        if rows:
            writer.add(rows)
        job.row_count = len(rows)
        await self._exports.flush()
        await self._session.commit()
        return len(rows)

    @staticmethod
    def _transcript_content(message: Message) -> str:
        """Render canonical content while excluding provider/storage references from artifacts."""
        content = message.content_json or {}
        body = content.get("body")
        if isinstance(body, str):
            return body
        text = content.get("text")
        if isinstance(text, str):
            return text
        if isinstance(text, dict) and isinstance(text.get("body"), str):
            return str(text["body"])

        media = content.get("media")
        if isinstance(media, dict):
            kind = str(media.get("kind") or message.message_type).title()
            details = [
                str(value)
                for value in (media.get("filename"), media.get("caption"))
                if isinstance(value, str) and value
            ]
            return f"[{kind}]" + (f" {' — '.join(details)}" if details else "")

        template = content.get("template")
        if isinstance(template, dict):
            name = str(template.get("name") or "template")
            language = template.get("language")
            if isinstance(language, dict):
                language = language.get("code")
            suffix = f" ({language})" if isinstance(language, str) and language else ""
            values = template.get("body")
            rendered = " · ".join(str(value) for value in values) if isinstance(values, list) else ""
            return f"Template: {name}{suffix}" + (f" — {rendered}" if rendered else "")

        reaction = content.get("reaction")
        if isinstance(reaction, dict):
            return f"Reaction: {reaction.get('emoji') or 'removed'}"

        location = content.get("location")
        if isinstance(location, dict):
            label = str(location.get("name") or "Location")
            latitude, longitude = location.get("latitude"), location.get("longitude")
            coordinates = (
                f" ({latitude}, {longitude})"
                if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))
                else ""
            )
            return f"{label}{coordinates}"

        interactive = content.get("interactive")
        if isinstance(interactive, dict):
            reply = interactive.get("button_reply") or interactive.get("list_reply") or interactive
            if isinstance(reply, dict):
                value = reply.get("title") or reply.get("text") or interactive.get("type")
                if isinstance(value, str) and value:
                    return value
        return f"[{message.message_type.replace('_', ' ').title()} message]"

    @staticmethod
    def _transcript_row(message: Message, *, contact_label: str) -> dict[str, Any]:
        timestamp = message.created_at.isoformat(timespec="seconds")
        if message.created_at.tzinfo is None:
            timestamp += "Z"
        return {
            "timestamp_utc": timestamp,
            "direction": message.direction,
            "participant": contact_label if message.direction == "inbound" else "Business",
            "message_type": message.message_type,
            "content": ExportService._transcript_content(message),
            "status": message.status,
            "message_id": message.public_id,
        }

    async def _transcript_context(
        self, job: ExportJob
    ) -> tuple[Conversation, Contact | None, Any, Any]:
        filters = job.filters_json or {}
        try:
            conversation_id = uuidlib.UUID(str(filters["conversation_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("Transcript export has an invalid conversation filter.") from exc
        conversation = await self._conversations.get_active_by_uuid(
            job.organization_id, conversation_id.bytes
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        contact = await self._session.get(Contact, conversation.contact_id)
        return conversation, contact, _parse_dt(filters.get("from")), _parse_dt(filters.get("to"))

    async def _write_transcript(
        self,
        job: ExportJob,
        writer: Any,
        *,
        conversation: Conversation,
        contact: Contact | None,
        start: Any,
        end: Any,
    ) -> int:
        """Stream oldest-first ledger rows into the shared artifact writer."""
        contact_label = (
            (contact.full_name or contact.profile_name or contact.phone_e164)
            if contact is not None
            else "Customer"
        )
        cursor: tuple[Any, int] | None = None
        written = 0
        while True:
            batch, has_more = await self._messages.list_for_transcript(
                conversation.id,
                start=start,
                end=end,
                limit=_BATCH,
                cursor=cursor,
            )
            if not batch:
                break
            writer.add([self._transcript_row(row, contact_label=contact_label) for row in batch])
            written += len(batch)
            job.row_count = written
            await self._exports.flush()
            await self._session.commit()
            if not has_more:
                break
            cursor = (batch[-1].created_at, batch[-1].id)
        return written

    async def _write_contacts_to_google_sheet(self, job: ExportJob) -> int:
        """Stream contacts into a deterministic, retry-safe new tab in bounded batches."""
        filters = job.filters_json or {}
        spreadsheet_id = filters.get("spreadsheet_id")
        if not isinstance(spreadsheet_id, str):
            raise ValidationError("Google Sheets export has no spreadsheet destination.")

        tab = f"Contacts {job.created_at:%Y-%m-%d %H%M} {job.public_id}"
        client = GoogleSheetsClient()
        resume = filters.get("google_tab_created") is True
        await client.ensure_export_tab(spreadsheet_id, tab, resume=resume)
        if not resume:
            job.filters_json = {
                **filters,
                "google_tab_created": True,
                "google_tab_name": tab,
            }
            await self._exports.flush()
            await self._session.commit()
        await client.write_rows(spreadsheet_id, tab, 1, [list(EXPORT_COLUMNS)])

        condition = compile_rules(
            organization_id=job.organization_id,
            match_type=filters.get("match_type", MATCH_ALL),
            rules=filters.get("rules", []),
            attributes=await self._specs(job.organization_id),
        )
        cursor: tuple[Any, int] | None = None
        written = 0
        while True:
            batch, has_more = await self._evaluator.paginate_matching(
                job.organization_id, condition, limit=_BATCH, cursor=cursor
            )
            if not batch:
                break
            rows = [
                [neutralize_formula(self._row(contact)[column]) for column in EXPORT_COLUMNS]
                for contact in batch
            ]
            await client.write_rows(spreadsheet_id, tab, written + 2, rows)
            written += len(batch)
            job.row_count = written
            await self._exports.flush()
            await self._session.commit()
            if not has_more:
                break
            cursor = (batch[-1].created_at, batch[-1].id)
        return written

    @staticmethod
    def _utc_text(value: Any) -> str:
        if value is None:
            return ""
        rendered = value.isoformat(timespec="seconds")
        return rendered if value.tzinfo is not None else f"{rendered}Z"

    @staticmethod
    def _campaign_result_row(
        campaign: Campaign,
        recipient: CampaignRecipient,
        contact: Contact | None,
    ) -> dict[str, Any]:
        return {
            "campaign_id": campaign.public_id,
            "campaign_name": campaign.name,
            "contact_id": contact.public_id if contact is not None else "",
            "contact_name_current": (contact.full_name or contact.profile_name or "")
            if contact is not None
            else "",
            "phone_e164_current": contact.phone_e164 if contact is not None else "",
            "recipient_status": recipient.status,
            "error_code": recipient.error_code or "",
            "retry_count": recipient.retry_count,
            "cost_amount": str(recipient.cost_amount) if recipient.cost_amount is not None else "",
            "cost_currency": campaign.cost_currency or "",
            "queued_at_utc": ExportService._utc_text(recipient.queued_at),
            "sent_at_utc": ExportService._utc_text(recipient.sent_at),
            "delivered_at_utc": ExportService._utc_text(recipient.delivered_at),
            "read_at_utc": ExportService._utc_text(recipient.read_at),
            "failed_at_utc": ExportService._utc_text(recipient.failed_at),
        }

    async def _campaign_results_context(self, job: ExportJob) -> tuple[Campaign, str | None]:
        filters = job.filters_json or {}
        try:
            campaign_id = uuidlib.UUID(str(filters["campaign_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("Campaign export has an invalid campaign filter.") from exc
        campaign = await self._campaigns.get_active_by_uuid(
            job.organization_id, campaign_id.bytes
        )
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        recipient_status = filters.get("status")
        if recipient_status is not None and recipient_status not in RECIPIENT_STATUSES:
            raise ValidationError("Campaign export has an invalid recipient status.")
        return campaign, recipient_status

    async def _write_campaign_results(
        self,
        job: ExportJob,
        writer: Any,
        *,
        campaign: Campaign,
        recipient_status: str | None,
    ) -> int:
        """Stream the full roster oldest-first without materializing it in worker memory."""
        cursor: tuple[Any, int] | None = None
        written = 0
        while True:
            batch, has_more = await self._campaign_recipients.paginate_for_export(
                campaign.id,
                job.organization_id,
                status=recipient_status,
                limit=_BATCH,
                cursor=cursor,
            )
            if not batch:
                break
            writer.add(
                [
                    self._campaign_result_row(campaign, recipient, contact)
                    for recipient, contact in batch
                ]
            )
            written += len(batch)
            job.row_count = written
            await self._exports.flush()
            await self._session.commit()
            if not has_more:
                break
            last_recipient = batch[-1][0]
            cursor = (last_recipient.created_at, last_recipient.id)
        return written

    async def run(self, export_public_id: str) -> ExportJob:
        """Execute an export (task body). Re-running regenerates the artifact idempotently.

        Dispatches on ``entity``: contacts stream from the operational table, analytics reports
        stream from the rollups. Everything after the rows — artifact, storage, expiry, progress,
        audit — is shared.
        """
        job = await self._exports.get_by_uuid(uuidlib.UUID(export_public_id))
        if job is None:
            raise NotFoundError("Export not found.")
        actor = await UserRepository(self._session).get_by_id(job.requested_by or 0)
        if actor is None:
            raise NotFoundError("Export requester no longer exists.")

        job.status = STATUS_PROCESSING
        await self._exports.flush()
        await self._session.commit()

        try:
            # Entity dispatch: each entity supplies its columns and its rows; the artifact,
            # storage, expiry, progress and audit path below are shared by all of them.
            if job.entity.startswith(REPORT_ENTITY_PREFIX):
                report = job.entity.removeprefix(REPORT_ENTITY_PREFIX)
                writer = export_writer(
                    job.format,
                    ("period", *REPORT_METRICS[report]),
                    title=f"{report.replace('_', ' ').title()} report",
                )
                written = await self._write_report(job, writer)
            elif job.entity == ENTITY_CONVERSATION_TRANSCRIPT:
                conversation, contact, start, end = await self._transcript_context(job)
                contact_label = (
                    (contact.full_name or contact.profile_name or contact.phone_e164)
                    if contact is not None
                    else "Customer"
                )
                writer = export_writer(
                    job.format,
                    TRANSCRIPT_COLUMNS,
                    title=f"Chat transcript — {contact_label}",
                )
                written = await self._write_transcript(
                    job,
                    writer,
                    conversation=conversation,
                    contact=contact,
                    start=start,
                    end=end,
                )
            elif job.entity == ENTITY_CAMPAIGN_RESULTS:
                campaign, recipient_status = await self._campaign_results_context(job)
                writer = export_writer(
                    job.format,
                    CAMPAIGN_RESULT_COLUMNS,
                    title=f"Campaign results — {campaign.name}",
                )
                written = await self._write_campaign_results(
                    job,
                    writer,
                    campaign=campaign,
                    recipient_status=recipient_status,
                )
            elif job.entity == ENTITY_CONTACTS and job.format == "google_sheet":
                writer = None
                written = await self._write_contacts_to_google_sheet(job)
            elif job.entity == ENTITY_CONTACTS:
                writer = export_writer(job.format)
                written = await self._write_contacts(job, writer)
            else:
                raise ValidationError("Unknown export entity.")

            if writer is not None:
                key = f"org-{job.organization_id}/exports/{job.public_id}.{job.format}"
                await get_provider(settings.storage_backend).put(
                    key, writer.finish(), content_type=CONTENT_TYPES[job.format]
                )
                job.storage_key = key
            job.row_count = written
            job.expires_at = (
                None
                if job.format == "google_sheet"
                else utcnow() + timedelta(days=settings.storage_export_ttl_days)
            )
            job.status = STATUS_READY
        except Exception:
            job.status = STATUS_FAILED
            job.completed_at = utcnow()
            await self._exports.flush()
            await self._session.commit()
            # The task layer classifies and parks; this line is what makes a failed export
            # findable in the log by entity and job, not just as a generic task failure.
            logger.error(
                "export_failed",
                extra={
                    "export_id": job.public_id,
                    "entity": job.entity,
                    "format": job.format,
                    "organization_id": job.organization_id,
                },
            )
            raise

        job.completed_at = utcnow()
        await self._exports.flush()
        await self._audit.record(
            AuditAction.EXPORT_COMPLETED,
            actor_user_id=actor.id,
            organization_id=job.organization_id,
            entity_type="export",
            entity_id=job.id,
            after={"rows": job.row_count, "format": job.format},
        )
        schedule_id = (job.filters_json or {}).get("_report_schedule_id")
        if schedule_id:
            from app.services.notification_service import NotificationService

            report = job.entity.removeprefix(REPORT_ENTITY_PREFIX).replace("_", " ").title()
            await NotificationService(self._session).emit(
                organization_id=job.organization_id,
                recipient_user_id=actor.id,
                notification_type="report_ready",
                title=f"{report} report is ready",
                body=(
                    f"Your scheduled {job.format.upper()} report is available in Download Center."
                ),
                dedup_key=f"report-export-ready:{job.public_id}",
            )
        await self._session.commit()
        return job
