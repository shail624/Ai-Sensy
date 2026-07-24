"""Job status tracking & dead-letter services (Doc 03 §11.7, Doc 06 §7, Doc 04 §22).

``JobService`` owns the durable job lifecycle (queued → started → success/failure/retry/revoked)
that the ``/jobs`` surface reads. ``DeadLetterService`` parks exhausted/poison work and supports
inspect / replay / discard — replay routes the original payload back through the **same
idempotent processor**, so replaying already-applied work is a safe no-op (Doc 06 §7.4/§8).
"""

from __future__ import annotations

import hashlib
import uuid as uuidlib
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.mixins import utcnow
from app.models.job import (
    DL_DISCARDED,
    DL_PARKED,
    DL_REPLAYED,
    JOB_QUEUED,
    JOB_REVOKED,
    JOB_STARTED,
    DeadLetter,
    JobMetadata,
)
from app.models.user import User
from app.repositories.job import DeadLetterRepository, JobRepository
from app.services.audit_service import AuditAction, AuditService


def fingerprint(task_name: str, error_class: str | None, error_detail: str | None) -> str:
    """Group identical root causes so a spike shows one cause, not thousands (Doc 06 §7.4)."""
    shape = f"{task_name}|{error_class or ''}|{(error_detail or '')[:120]}"
    return hashlib.sha1(shape.encode("utf-8")).hexdigest()  # noqa: S324 - grouping key, not security


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = JobRepository(session)
        self._audit = AuditService(session)

    # --- Lifecycle (called by the worker framework) --------------------------
    async def record_queued(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None,
        args: dict[str, Any] | None = None,
        ref_type: str | None = None,
        ref_id: int | None = None,
    ) -> JobMetadata:
        existing = await self._jobs.get_by_task_id(task_id)
        if existing is not None:
            return existing
        job = JobMetadata(
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            status=JOB_QUEUED,
            args_json=args,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        return await self._jobs.add(job)

    async def mark_started(self, task_id: str) -> JobMetadata | None:
        job = await self._jobs.get_by_task_id(task_id)
        if job is None:
            return None
        job.status = JOB_STARTED
        job.started_at = utcnow()
        job.attempts += 1
        await self._jobs.flush()
        return job

    async def mark_finished(
        self,
        task_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error_detail: str | None = None,
    ) -> JobMetadata | None:
        job = await self._jobs.get_by_task_id(task_id)
        if job is None:
            return None
        job.status = status
        job.result_json = result
        job.error_detail = (error_detail or None) and error_detail[:1024]
        job.finished_at = utcnow()
        await self._jobs.flush()
        return job

    # --- Read surface (Doc 04 §22) -------------------------------------------
    async def list_jobs(
        self,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None,
        task_name: str | None,
        queue: str | None,
    ) -> tuple[list[JobMetadata], bool, int]:
        jobs, has_more = await self._jobs.paginate(
            limit=limit, cursor=cursor, status=status, task_name=task_name, queue=queue
        )
        total = await self._jobs.count(status=status, task_name=task_name, queue=queue)
        return jobs, has_more, total

    async def get_job(self, public_id: uuidlib.UUID) -> JobMetadata:
        job = await self._jobs.get_by_uuid(public_id)
        if job is None:
            raise NotFoundError("Job not found.")
        return job

    async def cancel_job(
        self,
        *,
        actor: User,
        public_id: uuidlib.UUID,
        revoke: Callable[[str], Any],
    ) -> JobMetadata:
        """Revoke a cancellable job (Doc 04 §22). Terminal jobs cannot be cancelled."""
        job = await self.get_job(public_id)
        if job.is_terminal:
            raise ConflictError(f"Job is already {job.status} and cannot be cancelled.")
        revoke(job.task_id)
        job.status = JOB_REVOKED
        job.finished_at = utcnow()
        await self._jobs.flush()
        await self._audit.record(
            AuditAction.JOB_CANCELLED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="job",
            entity_id=job.id,
            after={"task_name": job.task_name, "task_id": job.task_id},
        )
        await self._session.commit()
        return job


class DeadLetterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._dlq = DeadLetterRepository(session)
        self._audit = AuditService(session)

    async def park(
        self,
        *,
        source_queue: str,
        task_name: str,
        task_id: str | None,
        payload: dict[str, Any] | None,
        error_class: str | None,
        error_detail: str | None,
        stack_trace: str | None = None,
        attempts: int = 0,
        request_id: str | None = None,
    ) -> DeadLetter:
        """Durably park unprocessable work — the last safety net (Doc 06 §7.2/§7.6)."""
        entry = DeadLetter(
            source_queue=source_queue,
            task_name=task_name,
            task_id=task_id,
            payload_json=payload,
            error_class=error_class,
            error_detail=(error_detail or None) and error_detail[:1024],
            stack_trace=(stack_trace or None) and stack_trace[:4096],
            attempts=attempts,
            fingerprint=fingerprint(task_name, error_class, error_detail),
            request_id=request_id,
        )
        return await self._dlq.add(entry)

    async def get(self, public_id: uuidlib.UUID) -> DeadLetter:
        entry = await self._dlq.get_by_uuid(public_id)
        if entry is None:
            raise NotFoundError("Dead-letter entry not found.")
        return entry

    async def replay(
        self,
        *,
        actor: User,
        public_id: uuidlib.UUID,
        send: Callable[[str, dict[str, Any], str], Any],
    ) -> DeadLetter:
        """Re-dispatch the original payload through the same processor (Doc 06 §7.4)."""
        entry = await self.get(public_id)
        if entry.status != DL_PARKED:
            raise ConflictError(f"Entry is already {entry.status}.")
        send(entry.task_name, entry.payload_json or {}, entry.source_queue)
        entry.status = DL_REPLAYED
        entry.resolved_by = actor.id
        entry.resolved_at = utcnow()
        await self._dlq.flush()
        await self._audit.record(
            AuditAction.DEAD_LETTER_REPLAYED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="dead_letter",
            entity_id=entry.id,
            after={"task_name": entry.task_name, "queue": entry.source_queue},
        )
        await self._session.commit()
        return entry

    async def discard(self, *, actor: User, public_id: uuidlib.UUID) -> DeadLetter:
        """Explicitly drop a known-bad entry (audited, Doc 06 §7.4)."""
        entry = await self.get(public_id)
        if entry.status != DL_PARKED:
            raise ConflictError(f"Entry is already {entry.status}.")
        entry.status = DL_DISCARDED
        entry.resolved_by = actor.id
        entry.resolved_at = utcnow()
        await self._dlq.flush()
        await self._audit.record(
            AuditAction.DEAD_LETTER_DISCARDED,
            actor_user_id=actor.id,
            organization_id=actor.organization_id,
            entity_type="dead_letter",
            entity_id=entry.id,
            before={"task_name": entry.task_name},
        )
        await self._session.commit()
        return entry
