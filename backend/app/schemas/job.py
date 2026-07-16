"""Job & queue schemas (Doc 04 §22)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.pagination import Page
from app.models.job import JobMetadata
from app.queue.health import QueueHealth
from app.queue.heartbeat import WorkerStatus


class JobResponse(BaseModel):
    id: str
    type: str = "job"
    task_name: str
    queue: str | None
    status: str
    ref_type: str | None
    ref_id: int | None
    attempts: int
    error_detail: str | None
    result: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    @classmethod
    def from_job(cls, job: JobMetadata) -> JobResponse:
        return cls(
            id=job.public_id,
            task_name=job.task_name,
            queue=job.queue,
            status=job.status,
            ref_type=job.ref_type,
            ref_id=job.ref_id,
            attempts=job.attempts,
            error_detail=job.error_detail,
            result=job.result_json,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
        )


class JobsPage(BaseModel):
    data: list[JobResponse]
    page: Page


class QueueHealthResponse(BaseModel):
    name: str
    purpose: str
    priority: int
    pool: str
    depth: int
    workers: int
    failure_destination: str

    @classmethod
    def from_health(cls, health: QueueHealth) -> QueueHealthResponse:
        return cls(
            name=health.name,
            purpose=health.purpose,
            priority=health.priority,
            pool=health.pool,
            depth=health.depth,
            workers=health.workers,
            failure_destination=health.failure_destination,
        )


class WorkerResponse(BaseModel):
    worker_id: str
    pool: str
    queues: list[str]
    active_tasks: int
    started_at: datetime | None
    last_seen_at: datetime | None

    @classmethod
    def from_worker(cls, worker: WorkerStatus) -> WorkerResponse:
        return cls(
            worker_id=worker.worker_id,
            pool=worker.pool,
            queues=worker.queues,
            active_tasks=worker.active_tasks,
            started_at=worker.started_at,
            last_seen_at=worker.last_seen_at,
        )


class QueuesResponse(BaseModel):
    """``GET /queues`` — depth/throughput per queue plus fleet health (Doc 06 §13.2)."""

    queues: list[QueueHealthResponse]
    workers: list[WorkerResponse]
    dead_letter_parked: int
