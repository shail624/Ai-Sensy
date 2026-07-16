"""Bulk contact operations (Doc 04 §29/§30, Doc 06 §2.3 ``imports`` queue; FR-CON-06/07/08).

Completes the CRM's async surface alongside import/export, and follows the same split:

* ``start_*`` — the request path. Validates the action/payload and the filter, applies the §30
  ``expected_count`` guard, records the ``bulk_jobs`` row + ``job_metadata``, and hands off to the
  **Queue Engine**. Always ``202``: it never mutates a contact.
* ``run`` — the worker body. Resolves the audience through the **same compiler** segments, search
  and export use, walks it in **keyset batches**, and applies each item through the CRM's own
  services — so a bulk edit obeys exactly the same validation, timeline and audit rules as the
  single-contact endpoints, with no duplicated business logic.

Per Doc 04 §29 items commit **per item, not per request**: one bad contact is reported in
``errors[]`` and never rolls back the rest. Re-running a job converges rather than double-applying
— every action is idempotent (attaching a present tag, deleting a deleted contact and merging an
already-merged group are all no-ops), which is what makes the queue's at-least-once delivery safe
here (Doc 06 §8) without snapshotting a million-row selection.

**Queue placement:** bulk work runs on ``imports`` — Doc 06 §2.3 defines that queue as the
long-running CRM lane ("parse, validate, dedup, upsert", Jobs pool, 300s/600s, failure
destination ``job=failed`` + error report), and Doc 12 §56 gives M3 no other write queue.
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.crm.attribute_types import AttributeValueError, coerce_value
from app.crm.csv_io import (
    bulk_error_report_csv,
    dedup_report_header,
    dedup_report_rows,
)
from app.crm.segment_compiler import AttributeSpec, compile_rules, validate_rule
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_event import EVENT_CONTACT_MERGED
from app.models.job_records import (
    ACTION_ADD_TAGS,
    ACTION_REMOVE_TAGS,
    ERROR_CAP,
    MODE_MERGE,
    MODE_REPORT,
    OP_BULK_DELETE,
    OP_BULK_UPDATE,
    OP_DEDUPLICATE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    BulkJob,
)
from app.models.segment import MATCH_ALL
from app.models.user import User
from app.repositories.attribute import (
    AttributeDefinitionRepository,
    ContactAttributeValueRepository,
)
from app.repositories.bulk_job import BulkJobRepository
from app.repositories.contact import ContactRepository
from app.repositories.segment import SegmentRepository
from app.repositories.tag import ContactTagRepository, TagRepository
from app.repositories.user import UserRepository
from app.services.attribute_service import AttributeService
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService
from app.services.contact_service import ContactService
from app.services.job_service import JobService
from app.services.tag_service import TagService
from app.storage.base import get_provider

#: Contacts pulled per keyset batch (bounded memory, mirrors the export streamer).
_BATCH = 500
#: Duplicate groups scanned per page.
_GROUP_BATCH = 100

#: Fields a merge fills from a duplicate when the primary's is blank (FR-CON-06 "merge").
#: ``wa_id``/``phone_e164`` are excluded: they are the identity of the surviving contact.
_MERGE_FIELDS = (
    "full_name",
    "first_name",
    "last_name",
    "email",
    "locale",
    "country_code",
    "profile_name",
)

_TASK_BY_OPERATION = {
    OP_BULK_UPDATE: "app.crm.tasks.run_contact_bulk_update",
    OP_BULK_DELETE: "app.crm.tasks.run_contact_bulk_delete",
    OP_DEDUPLICATE: "app.crm.tasks.run_contact_deduplicate",
}


class BulkService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = BulkJobRepository(session)
        self._contacts = ContactRepository(session)
        self._evaluator = SegmentRepository(session)
        self._definitions = AttributeDefinitionRepository(session)
        self._values = ContactAttributeValueRepository(session)
        self._tags = TagRepository(session)
        self._links = ContactTagRepository(session)
        self._events = ContactEventService(session)
        self._audit = AuditService(session)

    async def _specs(self, organization_id: int) -> dict[str, AttributeSpec]:
        return {
            definition.key_name: AttributeSpec(
                attribute_id=definition.id,
                data_type=definition.data_type,
                enum_values=definition.enum_values_json,
            )
            for definition in await self._definitions.list_for_org(organization_id)
        }

    # --- Request-path validation ---------------------------------------------
    async def _validate_filter(self, organization_id: int, filters: dict[str, Any]) -> None:
        """Reject a bad filter now rather than letting a worker discover it later."""
        specs = await self._specs(organization_id)
        for rule in filters.get("rules", []):
            validate_rule(
                rule["field_source"], rule["field_key"], rule["operator"], rule.get("value"), specs
            )

    async def _validate_action(
        self, organization_id: int, action: str, payload: dict[str, Any]
    ) -> None:
        """Structural validation of the action payload (Doc 04 §30 — 422 up front)."""
        if action in (ACTION_ADD_TAGS, ACTION_REMOVE_TAGS):
            raw = payload.get("tags")
            if not isinstance(raw, list) or not raw:
                raise ValidationError(
                    "Invalid bulk payload.",
                    errors=[
                        {
                            "field": "payload.tags",
                            "code": "required",
                            "message": "expected a non-empty list of tag ids",
                        }
                    ],
                )
            try:
                wanted = [uuidlib.UUID(str(item)).bytes for item in raw]
            except ValueError as exc:
                raise ValidationError(
                    "Invalid bulk payload.",
                    errors=[
                        {"field": "payload.tags", "code": "invalid", "message": "not a valid id"}
                    ],
                ) from exc
            found = {tag.uuid for tag in await self._tags.get_by_uuids(organization_id, wanted)}
            missing = [uuidlib.UUID(bytes=item) for item in wanted if item not in found]
            if missing:
                raise ValidationError(
                    "One or more tags do not exist.",
                    errors=[
                        {"field": "payload.tags", "code": "unknown_tag", "message": str(item)}
                        for item in missing
                    ],
                )
            return

        # ACTION_SET_ATTRIBUTES — keys must exist and values must fit their declared type.
        attributes = payload.get("attributes")
        if not isinstance(attributes, dict) or not attributes:
            raise ValidationError(
                "Invalid bulk payload.",
                errors=[
                    {
                        "field": "payload.attributes",
                        "code": "required",
                        "message": "expected a non-empty attributes map",
                    }
                ],
            )
        errors: list[dict[str, str]] = []
        for key, value in attributes.items():
            definition = await self._definitions.get_by_key(organization_id, key)
            if definition is None:
                errors.append(
                    {"field": key, "code": "unknown_attribute", "message": "no such attribute"}
                )
                continue
            try:
                coerce_value(definition.data_type, value, definition.enum_values_json)
            except AttributeValueError as exc:
                errors.append({"field": key, "code": "invalid_value", "message": str(exc)})
        if errors:
            raise ValidationError("One or more attribute values are invalid.", errors=errors)

    async def _resolve_count(
        self, organization_id: int, request: dict[str, Any]
    ) -> int:
        """How many live contacts the request addresses (drives the §30 safety guard)."""
        ids = request.get("ids")
        if ids is not None:
            return len(ids)
        filters = request.get("filter") or {}
        condition = compile_rules(
            organization_id=organization_id,
            match_type=filters.get("match_type", MATCH_ALL),
            rules=filters.get("rules", []),
            attributes=await self._specs(organization_id),
        )
        return await self._evaluator.count_matching(organization_id, condition)

    async def _start(
        self,
        *,
        organization_id: int,
        actor: User,
        operation: str,
        action: str | None,
        request: dict[str, Any],
        expected_count: int | None,
        dispatch: Callable[[str, str], Any],
    ) -> BulkJob:
        """Record the job and enqueue it. Shared by all three bulk entry points."""
        total = await self._resolve_count(organization_id, request)
        if expected_count is not None and expected_count != total:
            # The data changed underneath the caller — act on nothing (Doc 04 §30).
            raise ConflictError(
                f"Expected {expected_count} contacts but the filter now matches {total}; "
                "reload and retry."
            )

        job = BulkJob(
            organization_id=organization_id,
            requested_by=actor.id,
            entity="contacts",
            operation=operation,
            action=action,
            request_json=request,
            total_items=total,
        )
        await self._jobs.add(job)

        task_name = _TASK_BY_OPERATION[operation]
        task_id = str(uuidlib.uuid4())
        await JobService(self._session).record_queued(
            task_id=task_id,
            task_name=task_name,
            queue="imports",
            args={"bulk_id": job.public_id},
            ref_type="bulk",
            ref_id=job.id,
        )
        await self._audit.record(
            AuditAction.BULK_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="bulk_job",
            entity_id=job.id,
            after={"operation": operation, "action": action, "total": total},
        )
        await self._session.commit()
        dispatch(job.public_id, task_id)
        return job

    async def start_bulk_update(
        self,
        *,
        organization_id: int,
        actor: User,
        action: str,
        payload: dict[str, Any],
        ids: list[uuidlib.UUID] | None,
        filters: dict[str, Any] | None,
        expected_count: int | None,
        dispatch: Callable[[str, str], Any],
    ) -> BulkJob:
        await self._validate_action(organization_id, action, payload)
        if filters is not None:
            await self._validate_filter(organization_id, filters)
        request: dict[str, Any] = {"payload": payload}
        if ids is not None:
            request["ids"] = [str(item) for item in ids]
        else:
            request["filter"] = filters
        return await self._start(
            organization_id=organization_id,
            actor=actor,
            operation=OP_BULK_UPDATE,
            action=action,
            request=request,
            expected_count=expected_count,
            dispatch=dispatch,
        )

    async def start_bulk_delete(
        self,
        *,
        organization_id: int,
        actor: User,
        ids: list[uuidlib.UUID] | None,
        filters: dict[str, Any] | None,
        expected_count: int | None,
        dispatch: Callable[[str, str], Any],
    ) -> BulkJob:
        if filters is not None:
            await self._validate_filter(organization_id, filters)
        request: dict[str, Any] = {}
        if ids is not None:
            request["ids"] = [str(item) for item in ids]
        else:
            request["filter"] = filters
        return await self._start(
            organization_id=organization_id,
            actor=actor,
            operation=OP_BULK_DELETE,
            action=None,
            request=request,
            expected_count=expected_count,
            dispatch=dispatch,
        )

    async def start_deduplicate(
        self,
        *,
        organization_id: int,
        actor: User,
        keys: list[str],
        mode: str,
        dispatch: Callable[[str, str], Any],
    ) -> BulkJob:
        for key in keys:
            # Raises 400 for a key outside the supported set.
            self._contacts.dedup_column(key)
        job = BulkJob(
            organization_id=organization_id,
            requested_by=actor.id,
            entity="contacts",
            operation=OP_DEDUPLICATE,
            action=mode,
            request_json={"keys": keys, "mode": mode},
        )
        await self._jobs.add(job)
        task_id = str(uuidlib.uuid4())
        await JobService(self._session).record_queued(
            task_id=task_id,
            task_name=_TASK_BY_OPERATION[OP_DEDUPLICATE],
            queue="imports",
            args={"bulk_id": job.public_id},
            ref_type="bulk",
            ref_id=job.id,
        )
        await self._audit.record(
            AuditAction.BULK_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="bulk_job",
            entity_id=job.id,
            after={"operation": OP_DEDUPLICATE, "mode": mode, "keys": keys},
        )
        await self._session.commit()
        dispatch(job.public_id, task_id)
        return job

    # --- Read surface ---------------------------------------------------------
    async def get(self, organization_id: int, public_id: uuidlib.UUID) -> BulkJob:
        job = await self._jobs.get_for_org(organization_id, public_id.bytes)
        if job is None:
            raise NotFoundError("Bulk job not found.")
        return job

    async def error_report_url(self, job: BulkJob) -> str | None:
        """Signed, expiring link to the full report when one exists (Doc 04 §29)."""
        if not job.error_report_key:
            return None
        return get_provider(settings.storage_backend).signed_url(
            job.error_report_key,
            media_id=f"bulk-{job.public_id}",
            expires_in=settings.storage_signed_url_ttl_seconds,
        )

    # --- Worker path ----------------------------------------------------------
    async def _audience(self, job: BulkJob):
        """Yield the addressed contacts in bounded batches (ids or resolved filter)."""
        request = job.request_json or {}
        ids = request.get("ids")
        if ids is not None:
            # Chunked so an explicit selection never becomes one unbounded IN clause.
            for start in range(0, len(ids), _BATCH):
                window = ids[start : start + _BATCH]
                raw = [uuidlib.UUID(item).bytes for item in window]
                found = await self._contacts.get_active_by_uuids(job.organization_id, raw)
                by_uuid = {contact.uuid: contact for contact in found}
                yield [(item, by_uuid.get(uuidlib.UUID(item).bytes)) for item in window]
            return

        filters = request.get("filter") or {}
        condition = compile_rules(
            organization_id=job.organization_id,
            match_type=filters.get("match_type", MATCH_ALL),
            rules=filters.get("rules", []),
            attributes=await self._specs(job.organization_id),
        )
        cursor: tuple[Any, int] | None = None
        while True:
            batch, has_more = await self._evaluator.paginate_matching(
                job.organization_id, condition, limit=_BATCH, cursor=cursor
            )
            if not batch:
                return
            yield [(contact.public_id, contact) for contact in batch]
            if not has_more:
                return
            cursor = (batch[-1].created_at, batch[-1].id)

    async def _apply_update(
        self,
        *,
        job: BulkJob,
        actor: User,
        contact: Contact,
        tag_service: TagService,
        attribute_service: AttributeService,
    ) -> bool:
        """Apply one bulk-update item. Returns True when it changed something."""
        payload = (job.request_json or {}).get("payload") or {}
        contact_uuid = uuidlib.UUID(contact.public_id)

        if job.action == ACTION_ADD_TAGS:
            before = await self._links.tag_ids_for_contact(contact.id)
            await tag_service.add_tags_to_contact(
                organization_id=job.organization_id,
                actor=actor,
                contact_uuid=contact_uuid,
                tag_uuids=[uuidlib.UUID(str(item)) for item in payload["tags"]],
            )
            after = await self._links.tag_ids_for_contact(contact.id)
            return after != before

        if job.action == ACTION_REMOVE_TAGS:
            changed = False
            for raw in payload["tags"]:
                try:
                    await tag_service.remove_tag_from_contact(
                        organization_id=job.organization_id,
                        actor=actor,
                        contact_uuid=contact_uuid,
                        tag_uuid=uuidlib.UUID(str(raw)),
                    )
                    changed = True
                except NotFoundError:
                    # The tag simply isn't on this contact — a no-op, not a failure.
                    continue
            return changed

        await attribute_service.set_contact_attributes(
            organization_id=job.organization_id,
            actor=actor,
            contact_uuid=contact_uuid,
            values=payload["attributes"],
        )
        return True

    async def _run_over_audience(self, job: BulkJob, actor: User) -> list[dict[str, Any]]:
        """Drive bulk-update / bulk-delete across the addressed set, per-item committed."""
        contacts = ContactService(self._session)
        tag_service = TagService(self._session)
        attribute_service = AttributeService(self._session)
        errors: list[dict[str, Any]] = []
        processed = succeeded = failed = skipped = 0

        async for batch in self._audience(job):
            for public_id, contact in batch:
                processed += 1
                if contact is None:
                    # Only reachable in ids mode: unknown or already-deleted contact.
                    failed += 1
                    errors.append(
                        {"id": public_id, "code": "not_found", "message": "Contact not found."}
                    )
                    continue
                try:
                    if job.operation == OP_BULK_DELETE:
                        await contacts.delete_contact(
                            organization_id=job.organization_id,
                            actor=actor,
                            public_id=uuidlib.UUID(contact.public_id),
                        )
                        succeeded += 1
                    elif await self._apply_update(
                        job=job,
                        actor=actor,
                        contact=contact,
                        tag_service=tag_service,
                        attribute_service=attribute_service,
                    ):
                        succeeded += 1
                    else:
                        skipped += 1
                except (ValidationError, ConflictError, NotFoundError) as exc:
                    # One bad item never rolls back the rest (Doc 04 §29).
                    failed += 1
                    errors.append(
                        {"id": public_id, "code": "rejected", "message": str(exc.detail)}
                    )
            job.processed_items, job.succeeded_items = processed, succeeded
            job.failed_items, job.skipped_items = failed, skipped
            job.errors_json = errors[:ERROR_CAP] or None
            await self._jobs.flush()
            await self._session.commit()
        return errors

    async def _merge_group(
        self, *, job: BulkJob, actor: User, primary: Contact, duplicates: list[Contact], key: str
    ) -> None:
        """Fold ``duplicates`` into ``primary``: fill blanks, move tags/attributes, soft-delete."""
        for duplicate in duplicates:
            for field in _MERGE_FIELDS:
                if getattr(primary, field, None) in (None, "") and getattr(
                    duplicate, field, None
                ) not in (None, ""):
                    setattr(primary, field, getattr(duplicate, field))

            primary_tags = await self._links.tag_ids_for_contact(primary.id)
            for tag_id in await self._links.tag_ids_for_contact(duplicate.id):
                await self._links.detach(duplicate.id, tag_id)
                tag = await self._tags.get_by_id(tag_id)
                if tag_id in primary_tags:
                    # Shared tag: the duplicate's link disappears with it.
                    if tag is not None:
                        tag.usage_count = max(0, tag.usage_count - 1)
                    continue
                # Moved tag: the link transfers, so the count is unchanged.
                await self._links.attach(primary.id, tag_id, tagged_by=actor.id)
                primary_tags.add(tag_id)

            for value in await self._values.list_for_contact(duplicate.id):
                if await self._values.get(primary.id, value.attribute_id) is None:
                    value.contact_id = primary.id  # the primary's own value always wins
            await self._values.flush()

            duplicate.deleted_at = utcnow()
            duplicate.updated_by = actor.id
            duplicate.row_version += 1
            await self._events.record(
                organization_id=job.organization_id,
                contact_id=primary.id,
                event_type=EVENT_CONTACT_MERGED,
                ref_type="contact",
                ref_id=duplicate.id,
                payload={"merged_from": duplicate.public_id, "key": key},
            )
            await self._audit.record(
                AuditAction.CONTACT_MERGED,
                actor_user_id=actor.id,
                organization_id=job.organization_id,
                entity_type="contact",
                entity_id=primary.id,
                before={"duplicate": duplicate.public_id},
                after={"primary": primary.public_id, "key": key},
            )

        await AttributeService(self._session).refresh_cache(primary)
        primary.updated_by = actor.id
        primary.row_version += 1
        await self._contacts.flush()

    async def _run_deduplicate(self, job: BulkJob, actor: User) -> list[bytes]:
        """Scan for duplicate groups; report them, or merge each into its oldest contact."""
        request = job.request_json or {}
        keys: list[str] = request.get("keys") or []
        mode: str = request.get("mode", MODE_REPORT)
        chunks: list[bytes] = [dedup_report_header()]
        groups = merged = 0
        # The scan discovers the total; a re-run that finds nothing must report zero rather
        # than leave the previous run's count standing.
        job.total_items = 0

        for key in keys:
            offset = 0
            while True:
                values = await self._contacts.duplicate_key_values(
                    job.organization_id, key, limit=_GROUP_BATCH, offset=offset
                )
                if not values:
                    break
                rendered: list[dict[str, Any]] = []
                for value in values:
                    members = await self._contacts.list_active_by_key(
                        job.organization_id, key, value
                    )
                    if len(members) < 2:
                        continue  # merged away by an earlier key in this same run
                    primary, duplicates = members[0], members[1:]
                    groups += 1
                    rendered.append(
                        {
                            "key": key,
                            "value": value,
                            "duplicate_count": len(duplicates),
                            "primary_id": primary.public_id,
                            "duplicate_ids": "|".join(c.public_id for c in duplicates),
                        }
                    )
                    if mode == MODE_MERGE:
                        await self._merge_group(
                            job=job,
                            actor=actor,
                            primary=primary,
                            duplicates=duplicates,
                            key=key,
                        )
                        merged += len(duplicates)
                chunks.append(dedup_report_rows(rendered))

                job.total_items = groups
                job.processed_items = groups
                job.succeeded_items = merged if mode == MODE_MERGE else groups
                await self._jobs.flush()
                await self._session.commit()
                # Merging removes rows from the duplicate set, so the next page starts where this
                # one did; a report leaves the set intact and must step past it. If a merge page
                # yielded nothing actionable, step past it too — never re-query the same page
                # without making progress.
                if mode != MODE_MERGE or not rendered:
                    offset += len(values)

        return chunks

    async def run(self, bulk_public_id: str) -> BulkJob:
        """Execute a bulk job (task body). Safe to retry: every action is idempotent."""
        job = await self._jobs.get_by_uuid(uuidlib.UUID(bulk_public_id))
        if job is None:
            raise NotFoundError("Bulk job not found.")
        actor = await UserRepository(self._session).get_by_id(job.requested_by or 0)
        if actor is None:
            raise NotFoundError("Bulk job requester no longer exists.")

        job.status = STATUS_PROCESSING
        # A retry recomputes from scratch, so the previous attempt's tallies must not survive
        # into this one (Doc 06 §8 — the task is re-run, not resumed mid-count).
        job.processed_items = job.succeeded_items = job.failed_items = job.skipped_items = 0
        job.errors_json = None
        job.error_report_key = None
        await self._jobs.flush()
        await self._session.commit()

        try:
            if job.operation == OP_DEDUPLICATE:
                chunks = await self._run_deduplicate(job, actor)
                key = f"org-{job.organization_id}/bulk/{job.public_id}-duplicates.csv"
                await get_provider(settings.storage_backend).put(
                    key, b"".join(chunks), content_type="text/csv"
                )
                job.error_report_key = key
            else:
                errors = await self._run_over_audience(job, actor)
                if errors:
                    key = f"org-{job.organization_id}/bulk/{job.public_id}-errors.csv"
                    await get_provider(settings.storage_backend).put(
                        key, bulk_error_report_csv(errors), content_type="text/csv"
                    )
                    job.error_report_key = key
            job.status = STATUS_COMPLETED
        except Exception:
            job.status = STATUS_FAILED
            job.completed_at = utcnow()
            await self._jobs.flush()
            await self._session.commit()
            raise

        job.completed_at = utcnow()
        await self._jobs.flush()
        await self._audit.record(
            AuditAction.BULK_COMPLETED,
            actor_user_id=actor.id,
            organization_id=job.organization_id,
            entity_type="bulk_job",
            entity_id=job.id,
            after={
                "operation": job.operation,
                "succeeded": job.succeeded_items,
                "failed": job.failed_items,
                "skipped": job.skipped_items,
            },
        )
        await self._session.commit()
        return job
