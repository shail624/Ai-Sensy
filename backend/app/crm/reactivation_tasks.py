"""Periodic adapters for Task-backed Reactivation follow-up notifications."""

from __future__ import annotations

from typing import Any

from app.db.session import get_sessionmaker
from app.queue.base_task import TrackedTask, register_task, run_async
from app.queue.registry import SCHEDULER_TICK
from app.services.task_service import TaskService


async def _dispatch_due() -> dict[str, int]:
    async with get_sessionmaker()() as session:
        return await TaskService(session).dispatch_due_notifications()


@register_task(queue=SCHEDULER_TICK, name="app.crm.reactivation_tasks.dispatch_due_reminders")
def dispatch_due_reminders(self: TrackedTask) -> dict[str, Any]:
    """Idempotent scan: each current due-date revision is marked exactly once."""
    try:
        return run_async(_dispatch_due())
    except Exception as exc:  # noqa: BLE001 - the shared retry classifier owns retry policy
        self.smart_retry(exc)
        raise
