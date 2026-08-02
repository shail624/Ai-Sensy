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
from celery.schedules import crontab
from kombu import Queue

from app.core.config import settings
from app.queue.registry import ANALYTICS_ROLLUP, QUEUES, SCHEDULER_TICK, get_queue


def _queue_definitions() -> tuple[Queue, ...]:
    return tuple(
        Queue(spec.name, routing_key=spec.name, queue_arguments={"x-priority": int(spec.priority)})
        for spec in QUEUES
    )


#: **Beat schedule** (Doc 15 §8.1; Doc 06 §10.2).
#:
#: Declared in code rather than deployment config so the cadence ships with the tasks it drives and
#: cannot drift from them. Entries are declarative and keyed by name, so re-reading this module or
#: restarting Beat re-registers the *same* entries — scheduling is idempotent, and no duplicate
#: entry can accumulate.
#:
#: **Beat must run as a single replica.** Celery Beat is a ticker, not a worker: two instances
#: would fire every slot twice. The tasks below are individually idempotent (a rollup re-run
#: converges by delete-then-insert, Doc 15 §6.3; a scheduler tick claims each row before handing
#: it over), so a duplicate tick is survivable — but it doubles work for no benefit. Run one.
#:
#: All times are **UTC**: the app sets ``timezone="UTC"`` and ``enable_utc=True`` below, and every
#: bucket the analytics pipeline writes is a UTC hour (Doc 15 §6.1). Local-day presentation is a
#: read-time concern, never a scheduling one.
def _beat_schedule() -> dict[str, dict[str, object]]:
    return {
        # Campaign schedules that have come due (FR-CAM-03/04; Doc 06 §10.2). Beat's heartbeat,
        # not Beat's schedule — the schedules themselves live in the database.
        "campaign-scheduler-tick": {
            "task": "app.crm.campaign_tasks.scheduler_tick",
            "schedule": crontab(minute="*"),
            "options": {"queue": SCHEDULER_TICK, "expires": 55},
        },
        "reactivation-reminder-notifications": {
            "task": "app.crm.reactivation_tasks.dispatch_due_reminders",
            "schedule": crontab(minute="*"),
            "options": {"queue": SCHEDULER_TICK, "expires": 55},
        },
        # Recompute the trailing 6 closed hours, absorbing late delivery receipts (Doc 15 §8.2).
        "analytics-rollup-incremental": {
            "task": "app.analytics.tasks.rollup_incremental",
            "schedule": crontab(minute="*/15"),
            # A missed run is recomputed by the next one, so an expired message is simply dropped
            # rather than piling up behind a slow worker.
            "options": {"queue": ANALYTICS_ROLLUP, "expires": 14 * 60},
        },
        # Wider 48 h pass plus daily consolidation, for data later than the trailing window.
        "analytics-rollup-nightly": {
            "task": "app.analytics.tasks.rollup_nightly",
            "schedule": crontab(hour=2, minute=15),
            "options": {"queue": ANALYTICS_ROLLUP, "expires": 3600},
        },
        # Retention: 90 days hourly, ~26 months daily (Doc 15 §21.3).
        "analytics-rollup-prune": {
            "task": "app.analytics.tasks.rollup_prune",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": ANALYTICS_ROLLUP, "expires": 3600},
        },
    }


#: Modules that define tasks, imported by the worker at startup.
#:
#: **A worker only executes tasks it has registered, and it registers only what it imports.**
#: `celery -A app.queue.celery_app.celery_app worker` imports this module and nothing else, so
#: without this list every pool starts clean and rejects everything sent to it with
#: "Received unregistered task of type ..." — campaign dispatch, webhook processing, imports,
#: exports, media downloads and the analytics rollups all silently stop, while every container
#: still reports healthy. The API process never noticed because the code that calls `.delay()`
#: imports the task module itself; only the consumer side was empty.
#:
#: Listed explicitly rather than via `autodiscover_tasks`, so adding a task module is a visible
#: one-line change here instead of depending on a package-layout convention.
TASK_MODULES: tuple[str, ...] = (
    "app.analytics.tasks",
    "app.automation.tasks",
    "app.channels.tasks",
    "app.crm.campaign_tasks",
    "app.crm.reactivation_tasks",
    "app.crm.tasks",
)


def create_celery_app() -> Celery:
    """Build the configured Celery application."""
    app = Celery("wa_platform", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.update(
        include=list(TASK_MODULES),
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
        # Periodic work (Doc 15 §8.1). Beat reads this; workers ignore it.
        beat_schedule=_beat_schedule(),
    )
    return app


celery_app = create_celery_app()


def apply_queue_timeouts(task_name: str, queue_name: str) -> dict[str, int]:
    """Soft/hard timeouts for a task, taken from its queue's spec (Doc 06 §2.3/§2.4)."""
    spec = get_queue(queue_name)
    if spec is None:
        return {}
    return {"soft_time_limit": spec.soft_timeout, "time_limit": spec.hard_timeout}
