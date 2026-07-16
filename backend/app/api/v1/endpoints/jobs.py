"""Background job & queue monitoring endpoints (Doc 04 §22).

Reads require ``system:read``; cancelling requires ``system:manage`` (Owner superuser bypasses).
Job state is read from the durable ``job_metadata`` mirror; queue depth and worker liveness are
read live from the broker/heartbeat registry (Doc 06 §13.2).
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.core.redis import get_redis_client
from app.models.user import User
from app.queue.celery_app import celery_app
from app.queue.health import collect
from app.queue.heartbeat import live_workers
from app.repositories.job import DeadLetterRepository
from app.schemas.job import (
    JobResponse,
    JobsPage,
    QueueHealthResponse,
    QueuesResponse,
    WorkerResponse,
)
from app.services.job_service import JobService

router = APIRouter()

SystemReadActor = Annotated[User, Depends(require_permissions("system:read"))]
SystemManageActor = Annotated[User, Depends(require_permissions("system:manage"))]


@router.get("/jobs", response_model=JobsPage, summary="List background jobs")
async def list_jobs(request: Request, session: SessionDep, actor: SystemReadActor) -> JobsPage:
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    jobs, has_more, total = await JobService(session).list_jobs(
        limit=limit,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
        status=params.get("filter[status][eq]"),
        task_name=params.get("filter[task_name][eq]"),
        queue=params.get("filter[queue][eq]"),
    )
    next_cursor = (
        encode_cursor(jobs[-1].created_at, jobs[-1].id) if has_more and jobs else None
    )
    return JobsPage(
        data=[JobResponse.from_job(job) for job in jobs],
        page=Page(limit=limit, has_more=has_more, next_cursor=next_cursor, total=total),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, summary="Job detail / progress")
async def get_job(
    job_id: uuidlib.UUID, session: SessionDep, actor: SystemReadActor
) -> JobResponse:
    return JobResponse.from_job(await JobService(session).get_job(job_id))


@router.post(
    "/jobs/{job_id}/cancel", response_model=JobResponse, summary="Cancel a cancellable job"
)
async def cancel_job(
    job_id: uuidlib.UUID, session: SessionDep, actor: SystemManageActor
) -> JobResponse:
    job = await JobService(session).cancel_job(
        actor=actor,
        public_id=job_id,
        revoke=lambda task_id: celery_app.control.revoke(task_id, terminate=False),
    )
    return JobResponse.from_job(job)


@router.get("/queues", response_model=QueuesResponse, summary="Queue depth & fleet health")
async def get_queues(session: SessionDep, actor: SystemReadActor) -> QueuesResponse:
    redis = get_redis_client()
    return QueuesResponse(
        queues=[QueueHealthResponse.from_health(h) for h in await collect(redis)],
        workers=[WorkerResponse.from_worker(w) for w in await live_workers(redis)],
        dead_letter_parked=await DeadLetterRepository(session).count_parked(),
    )
