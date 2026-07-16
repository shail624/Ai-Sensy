"""Unit tests for the rate-limit hook algorithm (Doc 04 §9)."""

from __future__ import annotations

import pytest

from app.core.exceptions import RateLimitError
from app.core.rate_limit import enforce


class _FakeRedis:
    """Minimal async Redis stand-in for the fixed-window counter."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.expiries[key] = ttl
        return True


async def test_enforce_allows_up_to_limit_then_blocks() -> None:
    redis = _FakeRedis()
    for _ in range(3):
        await enforce(redis, identifier="auth:1.2.3.4", limit=3, window=60, now=1000.0)
    with pytest.raises(RateLimitError) as excinfo:
        await enforce(redis, identifier="auth:1.2.3.4", limit=3, window=60, now=1000.0)
    assert excinfo.value.headers == {"Retry-After": "60"}
    assert excinfo.value.status_code == 429


async def test_enforce_sets_window_expiry_once() -> None:
    redis = _FakeRedis()
    await enforce(redis, identifier="auth:9.9.9.9", limit=5, window=300, now=0.0)
    assert list(redis.expiries.values()) == [300]


async def test_enforce_separate_windows_reset() -> None:
    redis = _FakeRedis()
    await enforce(redis, identifier="auth:5.5.5.5", limit=1, window=60, now=0.0)
    # A later window uses a different key, so the counter resets.
    await enforce(redis, identifier="auth:5.5.5.5", limit=1, window=60, now=120.0)
