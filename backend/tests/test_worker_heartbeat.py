"""The worker registry must actually be written by a running worker.

`app.queue.heartbeat` held a complete registry — writer, reader, schema, TTL — and
`GET /api/v1/queues` read it, but nothing ever called the writer. No application code invoked
`beat()`, and no Celery signal handler existed, so the endpoint reported an empty fleet in every
deployment whether the workers were healthy or entirely dead. The deployment guide names that
endpoint the primary saturation signal and tells an operator to alert on dead workers with it.

`test_queue_engine.test_heartbeat_registers_with_ttl_and_lists_workers` passed throughout, because
it calls `beat()` itself. These tests check the part it could not: that becoming ready is what
writes the record.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.queue import heartbeat, worker_heartbeat


class _FakeSyncRedis:
    """Mirrors the handful of synchronous calls the publisher makes."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.closed = False

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    def close(self) -> None:
        self.closed = True


def test_importing_the_celery_app_wires_the_publisher() -> None:
    """The defect was a missing connection, so assert the connection itself.

    Run in a subprocess that imports *only* `app.queue.celery_app`. Asserting on signal state
    in-process would prove nothing: this module imports `worker_heartbeat` for the other tests,
    and that import connects the handlers by itself — so the check would pass even with the
    wiring removed, which is exactly the blind spot that let the original defect through.
    """
    probe = (
        "import app.queue.celery_app;"
        "from celery.signals import worker_ready, worker_shutdown;"
        "import sys;"
        "assert 'app.queue.worker_heartbeat' in sys.modules, 'celery app does not import it';"
        "assert worker_ready.has_listeners(), 'nothing writes the worker registry';"
        "assert worker_shutdown.has_listeners(), 'a stopped worker would linger';"
        "print('wired')"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr.strip()[-600:]
    assert "wired" in result.stdout


def test_a_ready_worker_writes_a_heartbeat_the_reader_understands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeSyncRedis()
    monkeypatch.setattr(worker_heartbeat.SyncRedis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("WORKER_QUEUES", "sends.bulk,sends.retry")
    # Write once and stop, rather than leaving the refresh loop running under the suite.
    monkeypatch.setattr(worker_heartbeat, "_refresh_interval", lambda: 0.01)

    publisher = worker_heartbeat._Publisher()
    publisher.start("bulk@host")
    try:
        key = heartbeat.heartbeat_key("bulk@host")
        deadline = 200
        while key not in fake.store and deadline:
            deadline -= 1
            import time

            time.sleep(0.01)
        assert key in fake.store, "a ready worker wrote no heartbeat"
        record = json.loads(fake.store[key])
        assert record["worker_id"] == "bulk@host"
        # The pool is derived from the queue registry, never re-declared beside it.
        assert record["pool"] == "send-bulk"
        assert record["queues"] == ["sends.bulk", "sends.retry"]
        assert fake.ttls[key] > 0
    finally:
        publisher.stop()

    assert key not in fake.store, "a cleanly stopped worker must not linger in the fleet view"
    assert fake.closed


def test_the_pool_comes_from_the_registry_and_degrades_honestly() -> None:
    assert worker_heartbeat._pool(["sends.bulk"]) == "send-bulk"
    assert worker_heartbeat._pool(["imports"]) != "unknown"
    # An unrecognised queue must not be reported as though it belonged to a real pool.
    assert worker_heartbeat._pool(["not-a-queue"]) == "unknown"
    assert worker_heartbeat._pool([]) == "unknown"


def test_queue_list_is_read_from_the_deployment_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_QUEUES", " imports , exports ,, media ")
    assert worker_heartbeat._queues() == ["imports", "exports", "media"]
    monkeypatch.delenv("WORKER_QUEUES", raising=False)
    assert worker_heartbeat._queues() == []


def test_both_writers_produce_the_same_record() -> None:
    """Two writers, one payload — so the sync path cannot drift from the async one."""
    fake = _FakeSyncRedis()
    heartbeat.beat_sync(
        fake,  # type: ignore[arg-type]
        worker_id="w1",
        pool="jobs",
        queues=["imports"],
        active_tasks=3,
    )
    record = json.loads(fake.store[heartbeat.heartbeat_key("w1")])
    assert set(record) == {
        "worker_id",
        "pool",
        "queues",
        "active_tasks",
        "started_at",
        "last_seen_at",
    }
    assert record["active_tasks"] == 3


def test_a_failing_heartbeat_never_takes_the_worker_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A monitoring signal must not be able to kill the thing it monitors."""

    class _Broken(_FakeSyncRedis):
        def set(self, *a: Any, **k: Any) -> None:
            raise RuntimeError("redis is unreachable")

    broken = _Broken()
    monkeypatch.setattr(worker_heartbeat.SyncRedis, "from_url", lambda *a, **k: broken)
    monkeypatch.setattr(worker_heartbeat, "_refresh_interval", lambda: 0.01)

    publisher = worker_heartbeat._Publisher()
    publisher.start("doomed@host")
    import time

    time.sleep(0.05)
    publisher.stop()  # must return normally rather than propagating
