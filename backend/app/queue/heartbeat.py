"""Worker registry & heartbeat (Doc 06 §3.4, §13.2 "Worker status").

Workers register in a **Redis** registry and refresh a TTL'd heartbeat key; liveness is then
simply "does the key still exist" — a crashed worker disappears on its own without a reaper,
and the fleet view survives an API restart because it lives in the broker, not process memory.
The durable record of *work* is ``job_metadata``; this registry is deliberately ephemeral.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings
from app.db.mixins import utcnow

_KEY_PREFIX = "worker:heartbeat:"


def heartbeat_key(worker_id: str) -> str:
    return f"{_KEY_PREFIX}{worker_id}"


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    worker_id: str
    pool: str
    queues: list[str]
    active_tasks: int
    started_at: datetime | None
    last_seen_at: datetime | None


async def beat(
    redis,
    *,
    worker_id: str,
    pool: str,
    queues: list[str],
    active_tasks: int = 0,
    started_at: datetime | None = None,
) -> None:
    """Publish/refresh this worker's heartbeat with a TTL (Doc 06 §3.4)."""
    payload = {
        "worker_id": worker_id,
        "pool": pool,
        "queues": queues,
        "active_tasks": active_tasks,
        "started_at": (started_at or utcnow()).isoformat(),
        "last_seen_at": utcnow().isoformat(),
    }
    await redis.set(
        heartbeat_key(worker_id),
        json.dumps(payload),
        ex=settings.worker_heartbeat_ttl_seconds,
    )


async def deregister(redis, worker_id: str) -> None:
    """Remove a worker from the registry (graceful shutdown, Doc 06 §3.5)."""
    await redis.delete(heartbeat_key(worker_id))


def _parse(raw: str | bytes) -> WorkerStatus | None:
    try:
        data = json.loads(raw)
        return WorkerStatus(
            worker_id=data["worker_id"],
            pool=data.get("pool", ""),
            queues=list(data.get("queues", [])),
            active_tasks=int(data.get("active_tasks", 0)),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            last_seen_at=(
                datetime.fromisoformat(data["last_seen_at"]) if data.get("last_seen_at") else None
            ),
        )
    except (ValueError, KeyError, TypeError):
        return None


async def live_workers(redis) -> list[WorkerStatus]:
    """Every worker with an unexpired heartbeat (Doc 06 §13.2 fleet health)."""
    workers: list[WorkerStatus] = []
    async for key in redis.scan_iter(match=f"{_KEY_PREFIX}*"):
        raw = await redis.get(key)
        if raw is None:
            continue
        status = _parse(raw)
        if status is not None:
            workers.append(status)
    return sorted(workers, key=lambda w: w.worker_id)
