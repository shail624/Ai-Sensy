"""Celery entrypoint for deterministic automation test runs (Design Book 23)."""

from __future__ import annotations

from app.db.session import get_sessionmaker
from app.queue.base_task import TrackedTask, register_task, run_async
from app.queue.registry import AUTOMATION_RUN
from app.queue.retry import classify, should_retry
from app.services.automation_runtime_service import AutomationRuntimeService


async def _execute(run_id: int) -> str:
    async with get_sessionmaker()() as session:
        return await AutomationRuntimeService(session).execute_test_run(run_id)


async def _mark_failure(run_id: int, *, retrying: bool, error: BaseException) -> None:
    async with get_sessionmaker()() as session:
        await AutomationRuntimeService(session).mark_task_failure(
            run_id, retrying=retrying, error=error
        )


@register_task(
    queue=AUTOMATION_RUN,
    name="app.automation.tasks.execute_automation_test_run",
)
def execute_automation_test_run(self: TrackedTask, run_id: int) -> str:
    """Execute or resume one side-effect-free test run from durable checkpoints."""

    try:
        return run_async(_execute(run_id))
    except BaseException as exc:
        failure_class = classify(exc)
        retrying = should_retry(failure_class, self.request.retries + 1)
        run_async(_mark_failure(run_id, retrying=retrying, error=exc))
        self.smart_retry(exc)
        raise AssertionError("smart_retry must raise") from exc  # pragma: no cover
