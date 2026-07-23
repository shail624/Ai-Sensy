"""Export service (Doc 04 §14.1, Doc 06 §2.3 ``exports`` queue, FR-CON-15; Doc 15 §19).

**Entity dispatch.** One export system serves every exportable thing: contacts stream from the
operational table, analytics reports stream from the rollups. The ``exports`` row, the queue, the
repository, the format writers, the storage artifact and the signed-download flow are shared, so
adding an entity adds a row generator — never a second pipeline.

Mirrors the import split:

* :meth:`ExportService.start` — the request path. Validates the filter, records the ``exports``
  row + ``job_metadata``, and hands off to the **Queue Engine**. Always ``202`` — it never reads
  a contact.
* :meth:`ExportService.run` — the worker body. Resolves the filter through the **same compiler**
  the segments/search use (so an export returns exactly what its preview showed), then walks the
  result **in keyset batches**, handing each batch to a per-format writer rather than loading
  every contact — a 1M-row export never materialises 1M ORM objects. The artifact is written
  through the **Storage** abstraction and handed back as a signed, expiring URL.

CSV, Excel and JSON differ only in the writer (:mod:`app.crm.formats`); the audience, the columns
and the streaming loop are shared, so every format exports exactly the same rows (FR-CON-15).
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
from app.crm.formats import CONTENT_TYPES, EXPORT_FORMATS, export_writer
from app.crm.segment_compiler import AttributeSpec, compile_rules, validate_rule
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.job_records import (
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
    ExportJob,
)
from app.models.segment import MATCH_ALL, MATCH_TYPES
from app.models.user import User
from app.repositories.attribute import AttributeDefinitionRepository
from app.repositories.export_job import ExportRepository
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
REPORT_ENTITY_PREFIX = "report:"

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
}


def _parse_dt(value: Any) -> Any:
    """``filters_json`` round-trips through JSON, so datetimes come back as ISO strings."""
    from datetime import datetime as _dt

    return _dt.fromisoformat(value) if isinstance(value, str) else value


#: CSV, Excel and JSON (FR-CON-15) — matches ``exports.format``'s check constraint (Doc 03 §11.6).
SUPPORTED_FORMATS = EXPORT_FORMATS


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._exports = ExportRepository(session)
        self._evaluator = SegmentRepository(session)
        self._attributes = AttributeDefinitionRepository(session)
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
    ) -> ExportJob:
        """Record the export and enqueue it. Never reads contacts inline."""
        if file_format not in SUPPORTED_FORMATS:
            raise ValidationError(
                "Unsupported export format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(SUPPORTED_FORMATS)}",
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
            filters_json={"match_type": match_type, "rules": rules},
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
        if file_format not in SUPPORTED_FORMATS:
            raise ValidationError(
                "Unsupported export format.",
                errors=[
                    {
                        "field": "format",
                        "code": "unsupported",
                        "message": f"supported: {list(SUPPORTED_FORMATS)}",
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

    async def download_url(self, job: ExportJob) -> str | None:
        """Signed, expiring link to the artifact once ready (FR-MED-09 access rules)."""
        if not job.storage_key or job.status != STATUS_READY:
            return None
        if job.expires_at and job.expires_at <= utcnow():
            return None
        provider = get_provider(settings.storage_backend)
        return provider.signed_url(
            job.storage_key,
            media_id=f"export-{job.public_id}",
            expires_in=settings.storage_signed_url_ttl_seconds,
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
                writer = export_writer(job.format, ("period", *REPORT_METRICS[report]))
                written = await self._write_report(job, writer)
            else:
                writer = export_writer(job.format)
                written = await self._write_contacts(job, writer)

            key = f"org-{job.organization_id}/exports/{job.public_id}.{job.format}"
            await get_provider(settings.storage_backend).put(
                key, writer.finish(), content_type=CONTENT_TYPES[job.format]
            )
            job.storage_key = key
            job.row_count = written
            job.expires_at = utcnow() + timedelta(days=settings.storage_export_ttl_days)
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
        await self._session.commit()
        return job
