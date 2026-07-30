"""Unit tests for the queue engine: registry, retry framework, heartbeat, health (Doc 06)."""

from __future__ import annotations

import json
import random

import pytest

from app.queue import health, heartbeat, registry, retry
from app.queue.celery_app import apply_queue_timeouts, celery_app
from app.queue.retry import FailureClass


# --- Registry (Doc 06 §2.3) -------------------------------------------------
def test_registry_declares_every_documented_queue() -> None:
    names = set(registry.queue_names())
    assert {
        "campaigns.control", "sends.priority", "sends.bulk", "sends.retry",
        "webhooks.ingest", "webhooks.process", "inbound.process", "ai", "imports",
        "exports", "media", "templates.sync", "analytics.rollup", "notifications",
        "cleanup", "maintenance", "scheduler.tick", "automation.run", "default",
    } == names


def test_registry_specs_are_coherent() -> None:
    for spec in registry.QUEUES:
        assert spec.soft_timeout < spec.hard_timeout, spec.name  # soft fires before hard kill
        assert spec.purpose, spec.name  # every queue exists for a stated reason (§2.1)
        assert spec.failure_destination, spec.name  # no queue may swallow work (§2.5)


def test_control_and_transactional_outrank_bulk_and_background() -> None:
    prio = {s.name: int(s.priority) for s in registry.QUEUES}
    assert prio["campaigns.control"] < prio["sends.priority"] < prio["sends.bulk"]
    assert prio["sends.bulk"] < prio["cleanup"]


def test_pool_mapping(dummy=None) -> None:
    send_bulk = {s.name for s in registry.queues_for_pool(registry.Pool.SEND_BULK)}
    assert send_bulk == {"sends.bulk", "sends.retry"}
    assert registry.get_queue("nope") is None


def test_celery_app_declares_queues_and_safety_settings() -> None:
    assert {q.name for q in celery_app.conf.task_queues} == set(registry.queue_names())
    # at-least-once + no hoarding (Doc 06 §3.4, D7)
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.timezone == "UTC"


def test_queue_timeouts_come_from_the_spec() -> None:
    assert apply_queue_timeouts("t", "sends.priority") == {"soft_time_limit": 15, "time_limit": 30}
    assert apply_queue_timeouts("t", "unknown") == {}


# --- Retry framework (Doc 06 §6) --------------------------------------------
def test_terminal_classes_never_retry() -> None:
    for cls in (
        FailureClass.TERMINAL, FailureClass.TERMINAL_DATA,
        FailureClass.TERMINAL_POLICY, FailureClass.TERMINAL_CONFIG,
    ):
        assert retry.policy_for(cls).retryable is False
        assert retry.should_retry(cls, attempt=1) is False
        assert retry.backoff_seconds(cls, 1) == 0.0


def test_unknown_failures_are_poison_not_retried_blindly() -> None:
    # Unclassifiable work goes to a human via the DLQ (§7.2), not an infinite retry loop.
    assert retry.should_retry(FailureClass.UNKNOWN, attempt=1) is False


def test_attempt_caps_are_enforced() -> None:
    assert retry.should_retry(FailureClass.TRANSIENT, attempt=4) is True
    assert retry.should_retry(FailureClass.TRANSIENT, attempt=5) is False  # cap = 5
    assert retry.should_retry(FailureClass.TRANSIENT_META, attempt=4) is False  # cap = 4


def test_backoff_is_bounded_by_cap_and_uses_full_jitter() -> None:
    rng = random.Random(7)
    samples = [retry.backoff_seconds(FailureClass.TRANSIENT, 20, rng=rng) for _ in range(50)]
    cap = retry.policy_for(FailureClass.TRANSIENT).cap_seconds
    assert all(0.0 <= s <= cap for s in samples)
    assert len(set(samples)) > 1  # jittered, not a fixed curve (§6.3 anti-thundering-herd)


def test_backoff_grows_with_attempts() -> None:
    rng = random.Random(1)
    early = max(retry.backoff_seconds(FailureClass.TRANSIENT, 0, rng=rng) for _ in range(50))
    late = max(retry.backoff_seconds(FailureClass.TRANSIENT, 5, rng=rng) for _ in range(50))
    assert late > early


def test_classify_uses_registered_error_maps_then_builtins() -> None:
    # The registry is process-global and populated at import time (Meta's map, the webhook lane's,
    # the send lane's). Clearing it without putting it back would silently disable classification
    # for every test that happens to run after this one.
    saved = dict(retry._ERROR_MAPS)
    retry.clear_error_maps()
    try:
        assert retry.classify(TimeoutError("t")) is FailureClass.TRANSIENT
        assert retry.classify(ValueError("nope")) is FailureClass.UNKNOWN

        retry.register_error_map(
            "test", lambda exc: FailureClass.THROTTLE if isinstance(exc, ValueError) else None
        )
        assert retry.classify(ValueError("429")) is FailureClass.THROTTLE
        assert retry.classify(RuntimeError("x")) is FailureClass.UNKNOWN
    finally:
        retry.clear_error_maps()
        retry._ERROR_MAPS.update(saved)


# --- Heartbeat & health (Doc 06 §3.4, §13.2) --------------------------------
class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.lists: dict[str, int] = {}

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.ttls[key] = ex

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)

    async def llen(self, key):
        return self.lists.get(key, 0)

    async def scan_iter(self, match=None):
        prefix = (match or "").rstrip("*")
        for key in list(self.store):
            if key.startswith(prefix):
                yield key


async def test_heartbeat_registers_with_ttl_and_lists_workers() -> None:
    redis = _FakeRedis()
    await heartbeat.beat(redis, worker_id="w1", pool="jobs", queues=["imports"], active_tasks=2)
    key = heartbeat.heartbeat_key("w1")
    assert json.loads(redis.store[key])["pool"] == "jobs"
    # TTL'd so a crashed worker disappears without a reaper (§3.4).
    assert redis.ttls[key] > 0

    workers = await heartbeat.live_workers(redis)
    assert len(workers) == 1 and workers[0].active_tasks == 2

    await heartbeat.deregister(redis, "w1")
    assert await heartbeat.live_workers(redis) == []


async def test_live_workers_skips_corrupt_entries() -> None:
    redis = _FakeRedis()
    redis.store[heartbeat.heartbeat_key("bad")] = "not-json"
    assert await heartbeat.live_workers(redis) == []


async def test_queue_health_reports_depth_and_worker_coverage() -> None:
    redis = _FakeRedis()
    redis.lists["sends.bulk"] = 42
    await heartbeat.beat(redis, worker_id="w1", pool="send-bulk", queues=["sends.bulk"])

    report = {h.name: h for h in await health.collect(redis)}
    assert report["sends.bulk"].depth == 42
    assert report["sends.bulk"].workers == 1
    assert report["imports"].depth == 0
    assert report["imports"].workers == 0  # declared but unstaffed
    assert len(report) == len(registry.QUEUES)


async def test_queue_depth_is_zero_for_missing_key() -> None:
    assert await health.queue_depth(_FakeRedis(), "nothing") == 0


def test_register_task_rejects_unknown_queue() -> None:
    from app.queue.base_task import register_task

    with pytest.raises(ValueError, match="unknown queue"):
        register_task(queue="not.a.queue")(lambda self: None)
