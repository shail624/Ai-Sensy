"""Liveness and readiness probes.

- ``GET /health`` — cheap liveness (is the process up?).
- ``GET /ready``  — readiness: checks each dependency (database, Redis, storage) and returns
  ``503`` with a per-dependency breakdown when degraded.

Per Doc 04 §22 and Doc 01 FR-MON-09; readiness underpins graceful degradation
(Doc 01 NFR-DR-08) and orchestration health-gating (Doc 08 §24).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_ping
from app.db.session import get_session
from app.storage.base import get_provider

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    name: str
    status: Literal["up", "down"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: list[DependencyStatus]


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Liveness: the process is running. No dependency checks (Doc 04 §22)."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


async def _check_database(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_storage() -> bool:
    """Probe the configured storage backend with a cheap existence check.

    Exports and media are written through this provider, so a node that cannot reach storage is
    not ready to serve: an export would be accepted, queued, and then fail in a worker where the
    user cannot see it. Probing a key that will never exist keeps the check read-only.
    """
    try:
        await get_provider(settings.storage_backend).exists("__healthcheck__")
        return True
    except Exception:
        return False


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReadyResponse:
    """Readiness: verify each dependency; ``503`` if any is down (Doc 04 §22)."""
    checks = {
        "database": await _check_database(session),
        "redis": await redis_ping(),
        "storage": await _check_storage(),
    }
    dependencies = [
        DependencyStatus(name=name, status="up" if ok else "down")
        for name, ok in checks.items()
    ]
    all_up = all(checks.values())
    if not all_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ready" if all_up else "degraded", dependencies=dependencies
    )
