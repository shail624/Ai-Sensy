"""Worker framework — the base task every domain task inherits (Doc 06 §3.4).

Each task run is wrapped with: durable ``job_metadata`` state, structured logging, smart-retry
classification/backoff (§6), and a terminal **DLQ park** so nothing is ever silently lost (§7).

Domain modules declare tasks with :func:`register_task`, giving only their queue and business
logic; priority, timeouts, retry caps and failure destination come from the registry (§2.3).
"""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, Protocol, TypeVar, cast

if TYPE_CHECKING:

    class _TaskRequest(Protocol):
        retries: int

    class _CeleryTask:
        """Typed view of Celery's untyped ``Task`` base used by this module."""

        name: str
        request: _TaskRequest

        def retry(
            self,
            *,
            exc: BaseException,
            countdown: float,
            max_retries: int | None,
        ) -> BaseException: ...

else:
    from celery import Task as _CeleryTask

from app.core.logging import get_logger, request_id_ctx
from app.core.redis import close_redis
from app.db.session import dispose_engine, get_sessionmaker
from app.queue.celery_app import apply_queue_timeouts, celery_app
from app.queue.registry import DEFAULT, DEST_DLQ, DEST_RETRY, get_queue
from app.queue.retry import backoff_seconds, classify, should_retry
from app.services.job_service import DeadLetterService, JobService

logger = get_logger(__name__)

P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


class RegisteredTask(Protocol[P, R_co]):
    """The typed Celery surface domain modules use after task registration."""

    name: str
    queue_name: str

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...

    def run(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...

    def apply_async(
        self,
        args: Sequence[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        task_id: str | None = None,
        **options: Any,
    ) -> object: ...


def run_async[T](coro: Awaitable[T]) -> T:
    """Run an async unit of work from Celery's synchronous worker context.

    **Disposes the engine and Redis client before the loop closes.** Both are cached per running
    loop (``app.db.session``, ``app.core.redis``), because a worker gives every task its own
    ``asyncio.run(...)`` and a pool bound to a previous, closed loop is unusable. Rebuilding per
    loop fixes that, but merely *dropping* the old engine leaks its server-side connections: the
    sockets stay open until MySQL's ``wait_timeout`` reaps them, so a worker accumulates roughly
    one connection per task and exhausts ``max_connections`` — measured at 25 tasks → +26
    connections that never returned. Disposing inside the loop that owns them closes the sockets
    deterministically, trading one connect per task for a bounded pool.
    """

    async def _scoped() -> T:
        try:
            return await coro
        finally:
            await dispose_engine()
            await close_redis()

    return asyncio.run(_scoped())


#: Historical alias — the hooks below and the domain task modules both call through here.
_run = run_async


async def _record_started(task_id: str) -> None:
    async with get_sessionmaker()() as session:
        await JobService(session).mark_started(task_id)
        await session.commit()


async def _record_finished(task_id: str, *, status: str, error: str | None = None) -> None:
    async with get_sessionmaker()() as session:
        await JobService(session).mark_finished(task_id, status=status, error_detail=error)
        await session.commit()


async def _park(
    *,
    queue: str,
    task_name: str,
    task_id: str | None,
    payload: dict[str, Any] | None,
    error_class: str,
    error_detail: str,
    stack: str,
    attempts: int,
    request_id: str | None,
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


class TrackedTask(_CeleryTask):
    """Celery base task with job tracking, smart retry and DLQ parking (Doc 06 §3.4/§6/§7)."""

    #: Queue this task is bound to (drives timeouts/retry caps/failure destination).
    queue_name: str = DEFAULT

    def before_start(self, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:  # noqa: D102 - Celery hook
        _run(_record_started(task_id))

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:  # noqa: D102
        _run(_record_finished(task_id, status="success"))

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: object | None,
    ) -> None:  # noqa: D102
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

    def on_retry(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: object | None,
    ) -> None:  # noqa: D102
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


def register_task(
    *, queue: str, name: str | None = None, **options: Any
) -> Callable[
    [Callable[Concatenate[TrackedTask, P], R_co]],
    RegisteredTask[P, R_co],
]:
    """Declare a task on a registry queue; timeouts/retries come from its spec (Doc 06 §2.3)."""
    spec = get_queue(queue)
    if spec is None:
        raise ValueError(f"unknown queue {queue!r}; add it to the registry (Doc 06 §2.3)")

    def decorator(
        fn: Callable[Concatenate[TrackedTask, P], R_co],
    ) -> RegisteredTask[P, R_co]:
        task = cast(
            RegisteredTask[P, R_co],
            celery_app.task(
                base=TrackedTask,
                bind=True,
                name=name or f"{fn.__module__}.{fn.__qualname__}",
                queue=spec.name,
                max_retries=spec.max_attempts,
                **apply_queue_timeouts(name or fn.__name__, spec.name),
                **options,
            )(fn),
        )
        task.queue_name = spec.name
        return task

    return decorator
