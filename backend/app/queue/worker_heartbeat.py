"""Publish each Celery worker's heartbeat, so the fleet view reports live workers.

``app.queue.heartbeat`` has always held a complete worker registry -- a TTL'd Redis key per
worker, a reader, a schema, a settings-driven TTL -- and ``GET /api/v1/queues`` reads it to report
the fleet. Nothing ever *wrote* to it. No application code called ``beat()``, and no Celery signal
handler existed anywhere, so ``live_workers()`` returned an empty list in every deployment and the
endpoint reported zero workers whether the fleet was healthy or entirely dead.

That matters because the deployment guide names that endpoint the primary saturation signal and
tells an operator to alert on dead workers with it. A signal that reads the same in both states
carries no information. The unit test passed throughout, because it calls ``beat()`` itself.

The heartbeat runs on a daemon thread with its own **synchronous** Redis client. It deliberately
does not reuse ``run_async``/``get_redis_client()``: those cache a client in a module-level global
keyed by the running loop, so calling them from a second thread swaps out the client a running
task is using, and the send path's rate gate reaches for that client on every message.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime

from celery.signals import worker_ready, worker_shutdown
from redis import Redis as SyncRedis

from app.core.config import settings
from app.db.mixins import utcnow
from app.queue.heartbeat import beat_sync, deregister_sync
from app.queue.registry import get_queue

logger = logging.getLogger(__name__)

#: Refresh well inside the TTL so a single slow or dropped write does not read as a dead worker.
_REFRESH_DIVISOR = 3
_MIN_REFRESH_SECONDS = 5


def _refresh_interval() -> float:
    return max(_MIN_REFRESH_SECONDS, settings.worker_heartbeat_ttl_seconds / _REFRESH_DIVISOR)


def _queues() -> list[str]:
    """The queues this worker consumes, as the deployment configured them."""
    raw = os.environ.get("WORKER_QUEUES", "")
    return [name.strip() for name in raw.split(",") if name.strip()]


def _pool(queues: list[str]) -> str:
    """The pool this worker belongs to, derived from the registry rather than re-declared."""
    for name in queues:
        spec = get_queue(name)
        if spec is not None:
            return spec.pool
    return "unknown"


class _Publisher:
    """Owns the thread, its client and its stop flag, so shutdown is deterministic."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._client: SyncRedis | None = None
        self._worker_id: str | None = None

    def start(self, worker_id: str) -> None:
        if self._thread is not None:
            return
        self._worker_id = worker_id
        self._client = SyncRedis.from_url(settings.redis_url, decode_responses=True)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="worker-heartbeat", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        queues = _queues()
        pool = _pool(queues)
        started_at: datetime = utcnow()
        interval = _refresh_interval()
        while not self._stop.is_set():
            try:
                if self._client is not None and self._worker_id is not None:
                    beat_sync(
                        self._client,
                        worker_id=self._worker_id,
                        pool=pool,
                        queues=queues,
                        started_at=started_at,
                    )
            except Exception:  # noqa: BLE001 - a heartbeat must never take the worker down
                logger.warning("worker_heartbeat_failed", exc_info=True)
            self._stop.wait(interval)

    def stop(self) -> None:
        self._stop.set()
        thread, client, worker_id = self._thread, self._client, self._worker_id
        self._thread = None
        if thread is not None:
            thread.join(timeout=5)
        if client is not None and worker_id is not None:
            try:
                deregister_sync(client, worker_id)
            except Exception:  # noqa: BLE001 - the TTL removes it anyway
                logger.warning("worker_deregister_failed", exc_info=True)
            finally:
                client.close()
        self._client = None
        self._worker_id = None


_publisher = _Publisher()


def _start_heartbeat(sender: object = None, **_: object) -> None:
    hostname = getattr(sender, "hostname", None)
    worker_id = hostname.strip() if isinstance(hostname, str) and hostname.strip() else str(sender)
    _publisher.start(worker_id)
    logger.info("worker_heartbeat_started", extra={"heartbeat_worker_id": worker_id})


def _stop_heartbeat(**_: object) -> None:
    _publisher.stop()


# Connected explicitly rather than with the `@signal.connect` decorator: Celery's decorator is
# untyped, and applying it erases the annotations the strict type gate checks.
worker_ready.connect(_start_heartbeat)
worker_shutdown.connect(_stop_heartbeat)
