"""Queue health (Doc 06 §13.2; Doc 04 §22 ``GET /queues``).

Depth is read **live from the broker** (each Celery queue is a Redis list, so depth is its
length) rather than from a mirror table — the broker is the source of truth for backlog and a
stale copy would be worse than none. Worker liveness comes from the heartbeat registry (§3.4).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.queue.heartbeat import WorkerStatus, live_workers
from app.queue.registry import QUEUES, QueueSpec


@dataclass(frozen=True, slots=True)
class QueueHealth:
    """Health of one queue (Doc 06 §13.2)."""

    name: str
    purpose: str
    priority: int
    pool: str
    depth: int
    workers: int
    failure_destination: str


async def queue_depth(redis, queue_name: str) -> int:
    """Pending task count for a queue (its Redis list length); 0 if absent."""
    try:
        return int(await redis.llen(queue_name))
    except Exception:  # noqa: BLE001 - a missing/typed key is simply an empty queue
        return 0


def _worker_count(workers: list[WorkerStatus], spec: QueueSpec) -> int:
    return sum(1 for worker in workers if spec.name in worker.queues)


async def collect(redis) -> list[QueueHealth]:
    """Depth + worker coverage for every declared queue (Doc 06 §2.3/§13.2)."""
    workers = await live_workers(redis)
    return [
        QueueHealth(
            name=spec.name,
            purpose=spec.purpose,
            priority=int(spec.priority),
            pool=spec.pool,
            depth=await queue_depth(redis, spec.name),
            workers=_worker_count(workers, spec),
            failure_destination=spec.failure_destination,
        )
        for spec in QUEUES
    ]
