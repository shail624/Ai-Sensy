"""Worker framework — the base task every domain task inherits (Doc 06 §3.4).

Each task run is wrapped with: durable ``job_metadata`` state, structured logging, smart-retry
classification/backoff (§6), and a terminal **DLQ park** so nothing is ever silently lost (§7).

Domain modules declare tasks with :func:`register_task`, giving only their queue and business
logic; priority, timeouts, retry caps and failure destination come from the registry (§2.3).
"""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import Callable
from typing import Any

from celery import Task

from app.core.logging import get_logger, request_id_ctx
from app.db.session import get_sessionmaker
from app.queue.celery_app import apply_queue_timeouts, celery_app
from app.queue.registry import DEFAULT, DEST_DLQ, DEST_RETRY, get_queue
from app.queue.retry import backoff_seconds, classify, should_retry
from app.services.job_service import DeadLetterService, JobService

logger = get_logger(__name__)


def _run(coro):
    """Run an async unit of work from Celery's synchronous worker context."""
    return asyncio.run(coro)


async def _record_started(task_id: str) -> None:
    async with get_sessionmaker()() as session:
        await JobService(session).mark_started(task_id)
        await session.commit()


async def _record_finished(task_id: str, *, status: str, error: str | None = None) -> None:
    async with get_sessionmaker()() as session:
        await JobService(session).mark_finished(task_id, status=status, error_detail=error)
        await session.commit()


async def _park(
    *, queue: str, task_name: str, task_id: str | None, payload: dict[str, Any] | None,
    error_class: str, error_detail: str, stack: str, attempts: int, request_id: str | None,
) -> None:
    async with get_sessionmaker()() as session:
        await DeadLetterService(session).park(
            source_queue=queue,
            task_name=task_name,
            task_id=task_id,
            payload=payload,
            error_class=error_class,
            error_detail=error_detail,
            stack_trace=stack,
            attempts=attempts,
            request_id=request_id,
        )
        await session.commit()


class TrackedTask(Task):
    """Celery base task with job tracking, smart retry and DLQ parking (Doc 06 §3.4/§6/§7)."""

    #: Queue this task is bound to (drives timeouts/retry caps/failure destination).
    queue_name: str = DEFAULT

    def before_start(self, task_id: str, args, kwargs) -> None:  # noqa: D102 - Celery hook
        _run(_record_started(task_id))

    def on_success(self, retval, task_id: str, args, kwargs) -> None:  # noqa: D102
        _run(_record_finished(task_id, status="success"))

    def on_failure(self, exc, task_id: str, args, kwargs, einfo) -> None:  # noqa: D102
        """Terminal failure: record it and park the work if the queue's dest is the DLQ."""
        spec = get_queue(self.queue_name)
        failure_class = classify(exc)
        detail = f"{type(exc).__name__}: {exc}"
        _run(_record_finished(task_id, status="failure", error=detail))
        destination = spec.failure_destination if spec else DEST_DLQ
        if destination in (DEST_DLQ, DEST_RETRY):
            _run(
                _park(
                    queue=self.queue_name,
                    task_name=self.name,
                    task_id=task_id,
                    payload={"args": list(args), "kwargs": dict(kwargs)},
                    error_class=str(failure_class),
                    error_detail=detail,
                    stack=str(einfo)[:4096] if einfo else traceback.format_exc()[:4096],
                    attempts=self.request.retries + 1,
                    request_id=request_id_ctx.get(),
                )
            )
        else:
            # park+alert / job=failed destinations are owned by the domain module; never
            # silently dropped — the failure is recorded on job_metadata above.
            logger.error(
                "task_failed_no_dlq",
                extra={"task": self.name, "queue": self.queue_name, "dest": destination},
            )

    def on_retry(self, exc, task_id: str, args, kwargs, einfo) -> None:  # noqa: D102
        _run(_record_finished(task_id, status="retry", error=f"{type(exc).__name__}: {exc}"))

    def smart_retry(self, exc: BaseException) -> None:
        """Classify ``exc`` and either retry with backoff or let it fail terminally (§6)."""
        failure_class = classify(exc)
        attempt = self.request.retries + 1
        if not should_retry(failure_class, attempt):
            raise exc
        countdown = backoff_seconds(failure_class, attempt)
        logger.warning(
            "task_retry_scheduled",
            extra={
                "task": self.name,
                "queue": self.queue_name,
                "class": str(failure_class),
                "attempt": attempt,
                "countdown": round(countdown, 3),
            },
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=None)


def register_task(*, queue: str, name: str | None = None, **options) -> Callable:
    """Declare a task on a registry queue; timeouts/retries come from its spec (Doc 06 §2.3)."""
    spec = get_queue(queue)
    if spec is None:
        raise ValueError(f"unknown queue {queue!r}; add it to the registry (Doc 06 §2.3)")

    def decorator(fn: Callable) -> Any:
        task = celery_app.task(
            base=TrackedTask,
            bind=True,
            name=name or f"{fn.__module__}.{fn.__qualname__}",
            queue=spec.name,
            max_retries=spec.max_attempts,
            **apply_queue_timeouts(name or fn.__name__, spec.name),
            **options,
        )(fn)
        task.queue_name = spec.name
        return task

    return decorator
