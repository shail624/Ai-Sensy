"""FastAPI application factory and entry point.

Composes the application: logging, middleware (request-id, security headers, CORS),
RFC 7807 error handlers, the health/readiness probes, and the versioned API router.
Long-lived resources (DB engine, Redis) are opened lazily and disposed on shutdown
via the lifespan handler. See Doc 04 (API), Doc 06 (async), Doc 08 (deployment).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.core.redis import close_redis
from app.db.session import dispose_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup/shutdown resources (Doc 08)."""
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    logger.info(
        "application_startup",
        extra={"environment": settings.environment, "version": settings.app_version},
    )
    try:
        yield
    finally:
        await dispose_engine()
        await close_redis()
        logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Middleware — order matters: request-id (outermost) → security headers → CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    # Root-level probes for orchestration (Doc 04 §22 / Doc 01 FR-MON-09).
    app.include_router(health_router)
    # Versioned API surface (Doc 04 §2).
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
