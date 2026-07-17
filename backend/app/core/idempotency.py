"""Idempotency keys (Doc 04 §8; Doc 06 §12.2 ``idem:{key}``).

``Idempotency-Key`` is **required** on operations that send or create (Doc 04 §8): a client that
retries after a timeout must not cause a second WhatsApp message to reach a customer. The key maps
to the original response for 24 hours, so the retry is answered rather than re-executed.

**Fail-closed, unlike the rate limiter.** :mod:`app.core.rate_limit` fails open because a lost
counter costs a soft control; a lost idempotency record costs a **duplicate message to a real
person**, which cannot be taken back. If the store is unreachable the send is refused (``503``) and
the client retries — the one failure mode that is safe here.

The primitives take an injected client so the protocol is testable without a live Redis, matching
the rate limiter's shape.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import status
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

HEADER = "Idempotency-Key"
#: Doc 06 §12.2 — the idempotency namespace.
PREFIX = "idem:"
#: Marks a key claimed by a request that has not answered yet.
IN_FLIGHT = "__in_flight__"


class IdempotencyInFlight(ConflictError):
    """The same key is already being processed (Doc 04 §18.2 → 409).

    Not an error the client caused: it means the first attempt is still running. Retrying after it
    settles replays the original response.
    """

    code = "idempotency_in_flight"
    title = "Request In Flight"


class IdempotencyUnavailable(AppError):
    """The idempotency store is unreachable, so a send cannot be guaranteed to happen once."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "idempotency_unavailable"
    title = "Service Unavailable"


def require_key(request: Request) -> str:
    """FastAPI dependency: the ``Idempotency-Key`` header, or ``422`` (Doc 04 §8)."""
    key = request.headers.get(HEADER)
    if not key or not key.strip():
        raise ValidationError(
            f"{HEADER} is required for this operation.",
            errors=[{"field": HEADER, "code": "missing", "message": "Header is required."}],
        )
    return key.strip()[:128]


async def begin(redis: Any, key: str, *, ttl: int | None = None) -> dict[str, Any] | None:
    """Claim ``key``, or return the response a previous request already stored.

    The claim is atomic (``SET NX``): two concurrent retries cannot both proceed, which is the
    whole point — the window this protects is exactly the one where a client retries because it
    has not heard back yet.
    """
    seconds = ttl if ttl is not None else settings.idempotency_ttl_seconds
    try:
        claimed = await redis.set(f"{PREFIX}{key}", IN_FLIGHT, nx=True, ex=seconds)
        if claimed:
            return None
        stored = await redis.get(f"{PREFIX}{key}")
    except Exception as exc:  # noqa: BLE001 - fail closed: see the module docstring
        logger.error("idempotency_store_unavailable", extra={"error": type(exc).__name__})
        raise IdempotencyUnavailable(
            "Cannot guarantee this request runs once; retry shortly."
        ) from exc

    if stored is None:
        # The claim expired between the SET and the GET — a 24h race we resolve by proceeding.
        return None
    if _decoded(stored) == IN_FLIGHT:
        raise IdempotencyInFlight("A request with this Idempotency-Key is still in flight.")
    return json.loads(_decoded(stored))


async def complete(redis: Any, key: str, *, response: dict[str, Any], ttl: int | None = None) -> None:
    """Record the response this key answers with for the next 24 hours (Doc 04 §8)."""
    seconds = ttl if ttl is not None else settings.idempotency_ttl_seconds
    try:
        await redis.set(f"{PREFIX}{key}", json.dumps(response, default=str), ex=seconds)
    except Exception:  # noqa: BLE001 - the work succeeded; a lost record is not worth failing it
        logger.error("idempotency_record_failed", extra={"key": key[:16]})


async def release(redis: Any, key: str) -> None:
    """Drop a claim whose request failed, so the client's retry is allowed to act."""
    try:
        await redis.delete(f"{PREFIX}{key}")
    except Exception:  # noqa: BLE001 - the claim's TTL is the backstop
        logger.warning("idempotency_release_failed", extra={"key": key[:16]})


def _decoded(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)
