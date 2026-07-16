"""Contact export service (Doc 04 §14.1, Doc 06 §2.3 ``exports`` queue, FR-CON-15).

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

#: Rows pulled per keyset batch while streaming (bounded memory, Doc 06 §2.3 exports).
_BATCH = 500
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

        job = ExportJob(
            organization_id=organization_id,
            requested_by=actor.id,
            entity="contacts",
            format=file_format,
            filters_json={"match_type": match_type, "rules": rules},
        )
        await self._exports.add(job)

        task_id = str(uuidlib.uuid4())
        await JobService(self._session).record_queued(
            task_id=task_id,
            task_name="app.crm.tasks.run_contact_export",
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
            after={"format": file_format, "rules": len(rules)},
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

    async def run(self, export_public_id: str) -> ExportJob:
        """Execute an export (task body). Re-running regenerates the artifact idempotently."""
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
            filters = job.filters_json or {}
            condition = compile_rules(
                organization_id=job.organization_id,
                match_type=filters.get("match_type", MATCH_ALL),
                rules=filters.get("rules", []),
                attributes=await self._specs(job.organization_id),
            )
            writer = export_writer(job.format)
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
