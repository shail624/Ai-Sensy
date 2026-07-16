"""Async Redis client.

Provides the shared async Redis connection used as the Celery broker, cache, lock,
rate-limit and pub/sub store (Doc 06 §12; Doc 08 §11). Redis is a rebuildable
accelerator — never the source of truth (Doc 06 §12.6). A helper ``ping`` backs the
readiness probe (§/ready).
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the singleton async Redis client, creating it on first use."""
    global _client
    if _client is None:
        _client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


async def redis_ping() -> bool:
    """Return True if Redis responds to PING (used by the readiness probe)."""
    try:
        return bool(await get_redis_client().ping())
    except Exception:
        return False


async def close_redis() -> None:
    """Close the Redis client and its pool (application shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
