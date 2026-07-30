"""Queue registry — the master queue specification (Doc 06 §2.3) as data.

Every queue exists for a stated reason and carries its own priority, worker pool, retry
policy, timeouts and failure destination. Encoding the taxonomy as data (rather than
scattering it across task decorators) means routing, worker pools, autoscaling and the Queue
Monitor all read one source of truth, and new work classes are **added as rows** (Doc 06 §2.5).

Queues whose domain tasks are not built yet are still declared here: the registry is the
contract those modules bind to, and the worker pools/routing are derived from it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Priority(IntEnum):
    """P0 = highest (control/urgent) … P4 = lowest (background) — Doc 06 §2.3."""

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


class Pool(str):
    """Worker pool names (Doc 06 §3.2)."""

    CONTROL = "control"
    SEND_PRIORITY = "send-priority"
    SEND_BULK = "send-bulk"
    WEBHOOK = "webhook"
    AI = "ai"
    JOBS = "jobs"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True, slots=True)
class QueueSpec:
    """One row of the master queue specification (Doc 06 §2.3)."""

    name: str
    purpose: str
    priority: Priority
    pool: str
    max_attempts: int
    soft_timeout: int
    hard_timeout: int
    failure_destination: str


#: Canonical queue names (Doc 06 §2.3).
CAMPAIGNS_CONTROL = "campaigns.control"
SENDS_PRIORITY = "sends.priority"
SENDS_BULK = "sends.bulk"
SENDS_RETRY = "sends.retry"
WEBHOOKS_INGEST = "webhooks.ingest"
WEBHOOKS_PROCESS = "webhooks.process"
INBOUND_PROCESS = "inbound.process"
AI = "ai"
IMPORTS = "imports"
EXPORTS = "exports"
MEDIA = "media"
TEMPLATES_SYNC = "templates.sync"
ANALYTICS_ROLLUP = "analytics.rollup"
NOTIFICATIONS = "notifications"
CLEANUP = "cleanup"
MAINTENANCE = "maintenance"
SCHEDULER_TICK = "scheduler.tick"
AUTOMATION_RUN = "automation.run"
DEFAULT = "default"

DEST_DLQ = "dead_letter"
DEST_RETRY = "sends.retry"
DEST_PARK = "park+alert"
DEST_JOB_FAILED = "job=failed"

QUEUES: tuple[QueueSpec, ...] = (
    QueueSpec(CAMPAIGNS_CONTROL, "Orchestrate campaigns (audience, batches, pause/resume).",
              Priority.P0, Pool.CONTROL, 5, 60, 120, DEST_PARK),
    QueueSpec(SENDS_PRIORITY, "Transactional/agent sends; a user is waiting.",
              Priority.P1, Pool.SEND_PRIORITY, 5, 15, 30, DEST_RETRY),
    QueueSpec(SENDS_BULK, "Campaign per-recipient sends; throughput-oriented.",
              Priority.P2, Pool.SEND_BULK, 5, 15, 30, DEST_RETRY),
    QueueSpec(SENDS_RETRY, "Delayed re-attempt of retryable send failures.",
              Priority.P2, Pool.SEND_BULK, 5, 15, 30, DEST_DLQ),
    QueueSpec(WEBHOOKS_INGEST, "Turn persisted webhook rows into processing tasks.",
              Priority.P1, Pool.WEBHOOK, 5, 10, 20, DEST_DLQ),
    QueueSpec(WEBHOOKS_PROCESS, "Apply status callbacks + route inbound idempotently.",
              Priority.P1, Pool.WEBHOOK, 5, 15, 30, DEST_DLQ),
    QueueSpec(INBOUND_PROCESS, "Conversation upsert, active detection, auto-reply, notifications.",
              Priority.P1, Pool.WEBHOOK, 5, 20, 40, DEST_DLQ),
    QueueSpec(AI, "AI generation/summarization/embeddings; provider-rate-bound.",
              Priority.P2, Pool.AI, 3, 60, 180, DEST_PARK),
    QueueSpec(IMPORTS, "Chunked contact import: parse, validate, dedup, upsert.",
              Priority.P3, Pool.JOBS, 3, 300, 600, DEST_JOB_FAILED),
    QueueSpec(EXPORTS, "Generate CSV/Excel/JSON exports (streamed).",
              Priority.P3, Pool.JOBS, 3, 300, 600, DEST_JOB_FAILED),
    QueueSpec(MEDIA, "Download/upload media, thumbnails, media-id refresh.",
              Priority.P2, Pool.JOBS, 5, 60, 120, DEST_DLQ),
    QueueSpec(TEMPLATES_SYNC, "Sync templates + approval status from Meta.",
              Priority.P3, Pool.MAINTENANCE, 3, 60, 120, DEST_PARK),
    QueueSpec(ANALYTICS_ROLLUP, "Build pre-aggregated dashboard/report rollups.",
              Priority.P3, Pool.MAINTENANCE, 3, 120, 300, DEST_PARK),
    QueueSpec(NOTIFICATIONS, "Dispatch in-app/email/outbound-webhook notifications.",
              Priority.P2, Pool.MAINTENANCE, 5, 30, 60, DEST_DLQ),
    QueueSpec(CLEANUP, "Retention enforcement: archive/purge per policy.",
              Priority.P4, Pool.MAINTENANCE, 3, 300, 900, DEST_PARK),
    QueueSpec(MAINTENANCE, "Partitions, backups, counter reconciliation, health sweeps.",
              Priority.P4, Pool.MAINTENANCE, 3, 300, 900, DEST_PARK),
    QueueSpec(SCHEDULER_TICK, "Beat ticks that scan schedules and enqueue due work.",
              Priority.P0, Pool.CONTROL, 1, 30, 60, DEST_PARK),
    QueueSpec(AUTOMATION_RUN, "Execute checkpointed automation runs from immutable versions.",
              Priority.P2, Pool.JOBS, 5, 60, 120, DEST_DLQ),
    QueueSpec(DEFAULT, "Small miscellaneous tasks without a dedicated queue.",
              Priority.P3, Pool.JOBS, 3, 30, 60, DEST_DLQ),
)

_BY_NAME: dict[str, QueueSpec] = {spec.name: spec for spec in QUEUES}


def queue_names() -> tuple[str, ...]:
    return tuple(spec.name for spec in QUEUES)


def get_queue(name: str) -> QueueSpec | None:
    return _BY_NAME.get(name)


def queues_for_pool(pool: str) -> tuple[QueueSpec, ...]:
    """The queues a worker pool consumes (Doc 06 §3.2)."""
    return tuple(spec for spec in QUEUES if spec.pool == pool)
