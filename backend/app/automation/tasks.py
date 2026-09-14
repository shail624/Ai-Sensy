"""Celery entrypoints for deterministic test runs and bounded live consumption."""

from __future__ import annotations

from app.core.config import settings
from app.db.session import get_sessionmaker
from app.queue.base_task import TrackedTask, register_task, run_async
from app.queue.registry import AUTOMATION_RUN, SCHEDULER_TICK
from app.queue.retry import classify, should_retry
from app.services.automation_live_runtime_service import AutomationLiveRuntimeService
from app.services.automation_runtime_service import AutomationRuntimeService
from app.services.business_event_service import AutomationReceiptDispatch, BusinessEventService


async def _execute(run_id: int) -> str:
    async with get_sessionmaker()() as session:
        return await AutomationRuntimeService(session).execute_test_run(run_id)


async def _mark_failure(run_id: int, *, retrying: bool, error: BaseException) -> None:
    async with get_sessionmaker()() as session:
        await AutomationRuntimeService(session).mark_task_failure(
            run_id, retrying=retrying, error=error
        )


async def _consume_live(receipt_id: int) -> tuple[str, int | None]:
    async with get_sessionmaker()() as session:
        service = AutomationLiveRuntimeService(session)
        status = await service.consume_receipt(receipt_id)
        return status, service.resume_in_seconds


async def _mark_live_failure(
    receipt_id: int, *, retrying: bool, error: BaseException
) -> None:
    async with get_sessionmaker()() as session:
        await AutomationLiveRuntimeService(session).mark_task_failure(
            receipt_id, retrying=retrying, error=error
        )


async def _claim_live_receipts() -> list[AutomationReceiptDispatch]:
    async with get_sessionmaker()() as session:
        return await BusinessEventService(session).claim_automation_receipt_dispatches(
            limit=settings.scheduler_tick_scan_limit
        )


async def _claim_scheduled_automations() -> list[AutomationReceiptDispatch]:
    async with get_sessionmaker()() as session:
        return await BusinessEventService(session).claim_due_automation_schedules(
            limit=settings.scheduler_tick_scan_limit
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


@register_task(
    queue=AUTOMATION_RUN,
    name="app.automation.tasks.consume_automation_trigger_receipt",
)
def consume_automation_trigger_receipt(self: TrackedTask, receipt_id: int) -> str:
    """Consume one durable receipt; duplicate dispatches converge on one live run."""

    try:
        status, resume_in_seconds = run_async(_consume_live(receipt_id))
        if resume_in_seconds is not None:
            consume_automation_trigger_receipt.apply_async(
                args=[receipt_id],
                countdown=resume_in_seconds,
                task_id=getattr(self.request, "id", None),
            )
        return status
    except BaseException as exc:
        failure_class = classify(exc)
        retrying = should_retry(failure_class, self.request.retries + 1)
        run_async(_mark_live_failure(receipt_id, retrying=retrying, error=exc))
        self.smart_retry(exc)
        raise AssertionError("smart_retry must raise") from exc  # pragma: no cover


@register_task(
    queue=SCHEDULER_TICK,
    name="app.automation.tasks.dispatch_automation_trigger_receipts",
)
def dispatch_automation_trigger_receipts(self: TrackedTask) -> dict[str, int]:
    """Recover durable new/stale receipts and hand them to the idempotent live consumer."""

    try:
        dispatches = run_async(_claim_live_receipts())
        for dispatch in dispatches:
            consume_automation_trigger_receipt.apply_async(
                args=[dispatch.receipt_pk],
                task_id=dispatch.task_id,
            )
        return {"claimed": len(dispatches)}
    except BaseException as exc:
        self.smart_retry(exc)
        raise AssertionError("smart_retry must raise") from exc  # pragma: no cover


@register_task(
    queue=SCHEDULER_TICK,
    name="app.automation.tasks.dispatch_scheduled_automations",
)
def dispatch_scheduled_automations(self: TrackedTask) -> dict[str, int]:
    """Claim due persisted schedules and hand their exact receipts to live workers."""

    try:
        dispatches = run_async(_claim_scheduled_automations())
        for dispatch in dispatches:
            consume_automation_trigger_receipt.apply_async(
                args=[dispatch.receipt_pk],
                task_id=dispatch.task_id,
            )
        return {"claimed": len(dispatches)}
    except BaseException as exc:
        self.smart_retry(exc)
        raise AssertionError("smart_retry must raise") from exc  # pragma: no cover
