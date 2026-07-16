"""Contact import service (Doc 04 §14.1, Doc 06 §2.3 ``imports`` queue, FR-CON-03/05/06).

Two halves:

* :meth:`ImportService.start` — the request path. Validates the mapping, resolves the uploaded
  source through the **Storage** abstraction, creates the ``imports`` record + a ``job_metadata``
  row, and hands the work to the **Queue Engine**. It never parses a byte: the response is always
  ``202`` with a job id and poll URL (Doc 04 §3).
* :meth:`ImportService.run` — the task body executed by a worker. Streams rows through the CRM's
  own :class:`ContactService`, so import creates contacts by exactly the same rules (validation,
  dedup, timeline events, audit) as the API — no duplicated business logic.

Resumability: progress is committed to ``imports`` as it goes and already-imported rows are
no-ops under ``skip``/``merge``, so a retried task converges rather than duplicating (Doc 06 §8).
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.crm.csv_io import (
    ATTR_PREFIX,
    CONTACT_FIELDS,
    RowError,
    error_report_csv,
    map_and_validate,
    read_csv,
)
from app.db.mixins import utcnow
from app.models.job_records import (
    DEDUP_OVERWRITE,
    DEDUP_SKIP,
    DEDUP_STRATEGIES,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    ImportJob,
)
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.import_job import ImportRepository
from app.repositories.media import MediaRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_service import ContactService, wa_id_from_e164
from app.services.job_service import JobService
from app.storage.base import get_provider

#: How often progress is flushed while streaming rows.
_PROGRESS_EVERY = 25


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._imports = ImportRepository(session)
        self._media = MediaRepository(session)
        self._contacts = ContactRepository(session)
        self._audit = AuditService(session)

    # --- Request path --------------------------------------------------------
    @staticmethod
    def _validate_mapping(mapping: dict[str, str], dedup_strategy: str) -> None:
        errors: list[dict[str, str]] = []
        if dedup_strategy not in DEDUP_STRATEGIES:
            errors.append(
                {
                    "field": "dedup_strategy",
                    "code": "invalid",
                    "message": f"must be one of {list(DEDUP_STRATEGIES)}",
                }
            )
        targets = set(mapping.values())
        for target in sorted(targets):
            if not target.startswith(ATTR_PREFIX) and target not in CONTACT_FIELDS:
                errors.append(
                    {"field": "mapping", "code": "unknown_target", "message": target}
                )
        if "phone_e164" not in targets:
            errors.append(
                {
                    "field": "mapping",
                    "code": "required",
                    "message": "mapping must include a phone_e164 target",
                }
            )
        if errors:
            raise ValidationError("The import mapping is invalid.", errors=errors)

    async def start(
        self,
        *,
        organization_id: int,
        actor: User,
        upload_id: uuidlib.UUID,
        file_format: str,
        mapping: dict[str, str],
        dedup_strategy: str,
        dispatch: Callable[[str, str], Any],
    ) -> ImportJob:
        """Create the import record and enqueue it. Never processes inline."""
        self._validate_mapping(mapping, dedup_strategy)
        if file_format != "csv":
            raise ValidationError(
                "Unsupported import format.",
                errors=[
                    {"field": "format", "code": "unsupported", "message": "only 'csv' is supported"}
                ],
            )
        asset = await self._media.get_active_by_uuid(organization_id, upload_id.bytes)
        if asset is None:
            raise NotFoundError("Uploaded file not found.")

        job = ImportJob(
            organization_id=organization_id,
            requested_by=actor.id,
            entity="contacts",
            format=file_format,
            source_key=asset.storage_key,
            mapping_json=mapping,
            dedup_strategy=dedup_strategy,
        )
        await self._imports.add(job)

        task_id = str(uuidlib.uuid4())
        await JobService(self._session).record_queued(
            task_id=task_id,
            task_name="app.crm.tasks.run_contact_import",
            queue="imports",
            args={"import_id": job.public_id},
            ref_type="import",
            ref_id=job.id,
        )
        await self._audit.record(
            AuditAction.IMPORT_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="import",
            entity_id=job.id,
            after={"format": file_format, "dedup_strategy": dedup_strategy},
        )
        await self._session.commit()
        dispatch(job.public_id, task_id)
        return job

    async def get(self, organization_id: int, public_id: uuidlib.UUID) -> ImportJob:
        job = await self._imports.get_for_org(organization_id, public_id.bytes)
        if job is None:
            raise NotFoundError("Import not found.")
        return job

    async def error_report_url(self, job: ImportJob) -> str | None:
        """A signed, expiring link to the error report, when one exists (FR-CON-05/09)."""
        if not job.error_report_key:
            return None
        provider = get_provider(settings.storage_backend)
        return provider.signed_url(
            job.error_report_key,
            media_id=f"import-{job.public_id}",
            expires_in=settings.storage_signed_url_ttl_seconds,
        )

    # --- Worker path ---------------------------------------------------------
    async def _apply_row(
        self,
        *,
        contacts: ContactService,
        organization_id: int,
        actor: User,
        fields: dict[str, Any],
        strategy: str,
    ) -> bool:
        """Create/merge one contact; returns True when a row was applied."""
        phone = fields.pop("phone_e164")
        opt_in = fields.pop("opt_in_status", "unknown")
        existing = await self._contacts.get_active_by_wa_id(
            organization_id, wa_id_from_e164(phone)
        )

        if existing is None:
            await contacts.create_contact(
                organization_id=organization_id,
                actor=actor,
                phone_e164=phone,
                opt_in_status=opt_in,
                source="import",
                fields={key: fields.get(key) for key in CONTACT_FIELDS if key in fields},
            )
            return True

        if strategy == DEDUP_SKIP:
            return False
        # merge → only fill blanks; overwrite → replace supplied fields (FR-CON-06)
        updates = {
            key: value
            for key, value in fields.items()
            if strategy == DEDUP_OVERWRITE or getattr(existing, key, None) in (None, "")
        }
        await contacts.update_contact(
            organization_id=organization_id,
            actor=actor,
            public_id=uuidlib.UUID(existing.public_id),
            opt_in_status=opt_in if strategy == DEDUP_OVERWRITE else None,
            fields=updates,
            expected_version=None,
        )
        return True

    async def run(self, import_public_id: str) -> ImportJob:
        """Execute an import (task body). Idempotent enough to be retried safely."""
        job = (
            await self._imports.get_by_uuid(uuidlib.UUID(import_public_id))
        )
        if job is None:
            raise NotFoundError("Import not found.")
        actor = await UserRepository(self._session).get_by_id(job.requested_by or 0)
        if actor is None:
            raise NotFoundError("Import requester no longer exists.")

        job.status = STATUS_PROCESSING
        await self._imports.flush()
        await self._session.commit()

        try:
            provider = get_provider(settings.storage_backend)
            data = await provider.get(job.source_key or "")
            parsed = map_and_validate(read_csv(data), job.mapping_json or {})
            job.total_rows = parsed.total
            job.error_rows = len(parsed.errors)
            await self._imports.flush()
            await self._session.commit()

            contacts = ContactService(self._session)
            strategy = job.dedup_strategy or DEDUP_SKIP
            processed = len(parsed.errors)
            success = 0
            for row in parsed.rows:
                try:
                    if await self._apply_row(
                        contacts=contacts,
                        organization_id=job.organization_id,
                        actor=actor,
                        fields=dict(row.fields),
                        strategy=strategy,
                    ):
                        success += 1
                except (ValidationError, ConflictError) as exc:
                    # A rejected row is reported, never fatal to the import (FR-CON-05).
                    parsed.errors.append(RowError(row.row_number, str(exc.detail), row.fields))
                    job.error_rows += 1
                processed += 1
                if processed % _PROGRESS_EVERY == 0:
                    job.processed_rows, job.success_rows = processed, success
                    await self._imports.flush()
                    await self._session.commit()

            job.processed_rows, job.success_rows = processed, success
            if parsed.errors:
                key = f"org-{job.organization_id}/imports/{job.public_id}-errors.csv"
                await provider.put(key, error_report_csv(parsed.errors), content_type="text/csv")
                job.error_report_key = key
            job.status = STATUS_COMPLETED
        except Exception:
            job.status = STATUS_FAILED
            job.completed_at = utcnow()
            await self._imports.flush()
            await self._session.commit()
            raise

        job.completed_at = utcnow()
        await self._imports.flush()
        await self._audit.record(
            AuditAction.IMPORT_COMPLETED,
            actor_user_id=actor.id,
            organization_id=job.organization_id,
            entity_type="import",
            entity_id=job.id,
            after={
                "total": job.total_rows,
                "success": job.success_rows,
                "errors": job.error_rows,
            },
        )
        await self._session.commit()
        return job
