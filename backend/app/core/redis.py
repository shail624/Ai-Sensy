"""Async Redis client.

Provides the shared async Redis connection used as the Celery broker, cache, lock,
rate-limit and pub/sub store (Doc 06 §12; Doc 08 §11). Redis is a rebuildable
accelerator — never the source of truth (Doc 06 §12.6). A helper ``ping`` backs the
readiness probe (§/ready).
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None
#: The event loop the cached client's connection pool belongs to — same reasoning as
#: ``app.db.session._engine_loop``. A Celery worker runs each task under its own
#: ``asyncio.run(...)``, so a client cached across runs carries a pool bound to a closed loop.
#: The rate gate calls this on every send, so a stale client fails the send path, not just a probe.
_client_loop: asyncio.AbstractEventLoop | None = None


def _current_loop() -> asyncio.AbstractEventLoop | None:
    """The running loop, or ``None`` when called outside one."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def get_redis_client() -> Redis:
    """Return the async Redis client for the running loop, creating it on first use."""
    global _client, _client_loop
    loop = _current_loop()
    if _client is None or (loop is not None and _client_loop is not loop):
        _client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        _client_loop = loop
    return _client


async def redis_ping() -> bool:
    """Return True if Redis responds to PING (used by the readiness probe)."""
    try:
        return bool(await get_redis_client().ping())
    except Exception:
        return False


async def close_redis() -> None:
    """Close the Redis client and its pool (application shutdown)."""
    global _client, _client_loop
    if _client is not None:
        await _client.aclose()
        _client = None
        _client_loop = None
