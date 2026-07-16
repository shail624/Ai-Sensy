"""Celery application (Doc 06 §1, §2, §3).

Broker and result backend are Redis (Doc 06 §12; Doc 08 §11). Queues, priorities and timeouts
are derived from the registry (§2.3) so the taxonomy has exactly one source of truth.

Key settings and why:
- ``worker_prefetch_multiplier = 1`` — a worker never hoards messages it cannot promptly
  process; critical for even load distribution and fast rebalancing (Doc 06 §3.4, decision D7).
- ``task_acks_late = True`` + ``task_reject_on_worker_lost = True`` — a task is acknowledged
  only after it completes, so a crashed worker's in-flight task is redelivered rather than lost
  (at-least-once; idempotency keys make that safe — Doc 06 §8).
- ``task_track_started = True`` — powers the ``started`` job status (Doc 03 §11.7).
- UTC everywhere (Doc 03 §1.3).
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from app.core.config import settings
from app.queue.registry import QUEUES, get_queue


def _queue_definitions() -> tuple[Queue, ...]:
    return tuple(
        Queue(spec.name, routing_key=spec.name, queue_arguments={"x-priority": int(spec.priority)})
        for spec in QUEUES
    )


def create_celery_app() -> Celery:
    """Build the configured Celery application."""
    app = Celery("wa_platform", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.update(
        task_default_queue="default",
        task_queues=_queue_definitions(),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        result_expires=settings.celery_result_expires_seconds,
        # Tasks declare their queue; unknown tasks fall back to `default`.
        task_routes={},
        task_send_sent_event=True,
        worker_send_task_events=True,
    )
    return app


celery_app = create_celery_app()


def apply_queue_timeouts(task_name: str, queue_name: str) -> dict[str, int]:
    """Soft/hard timeouts for a task, taken from its queue's spec (Doc 06 §2.3/§2.4)."""
    spec = get_queue(queue_name)
    if spec is None:
        return {}
    return {"soft_time_limit": spec.soft_timeout, "time_limit": spec.hard_timeout}
