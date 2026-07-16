"""Rate limiting hook (Doc 04 §9).

A Redis fixed-window limiter fronting brute-force-sensitive endpoints (login, refresh —
the ``auth`` bucket, 10 requests / 5 min / IP). Exposed as a FastAPI dependency factory so
routes declare ``Depends(rate_limit("auth"))``.

Design choices:
- **Fail-open:** if Redis is unavailable the request proceeds (availability over a soft
  control) — the limiter is defense-in-depth, not the auth boundary. A warning is logged.
- **Disabled in tests / when turned off:** keeps the hermetic suite deterministic; a
  dedicated test exercises the algorithm directly.
- The core algorithm (:func:`enforce`) takes an injected client, so it is unit-testable
  without a live Redis.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)

# bucket -> (max_requests, window_seconds)
_BUCKETS: dict[str, tuple[int, int]] = {
    "auth": (settings.rate_limit_auth_max, settings.rate_limit_auth_window_seconds),
}


async def _incr_window(redis: object, key: str, window: int) -> int:
    """Increment the current window counter and ensure it expires. Returns the count."""
    count = int(await redis.incr(key))  # type: ignore[attr-defined]
    if count == 1:
        await redis.expire(key, window)  # type: ignore[attr-defined]
    return count


async def enforce(
    redis: object, *, identifier: str, limit: int, window: int, now: float | None = None
) -> None:
    """Raise :class:`RateLimitError` (429 + Retry-After) if ``identifier`` exceeds ``limit``."""
    epoch = now if now is not None else time.time()
    window_start = int(epoch // window)
    key = f"ratelimit:{identifier}:{window_start}"
    count = await _incr_window(redis, key, window)
    if count > limit:
        raise RateLimitError(
            "Too many requests. Please retry later.",
            headers={"Retry-After": str(window)},
        )


def rate_limit(bucket: str) -> Callable[[Request], Awaitable[None]]:
    """Dependency factory: enforce the named rate-limit bucket, keyed by client IP."""
    limit, window = _BUCKETS[bucket]

    async def _dependency(request: Request) -> None:
        if not settings.rate_limit_enabled or settings.environment == "test":
            return
        client_ip = request.client.host if request.client else "unknown"
        try:
            await enforce(
                get_redis_client(),
                identifier=f"{bucket}:{client_ip}",
                limit=limit,
                window=window,
            )
        except RateLimitError:
            raise
        except Exception:  # noqa: BLE001 - fail open on limiter/Redis errors
            logger.warning("rate_limit_unavailable", extra={"bucket": bucket})

    return _dependency
