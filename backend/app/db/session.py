"""Async database engine and session management.

Creates the process-wide async SQLAlchemy engine + session factory (Doc 08 §10) and
exposes a FastAPI dependency yielding a request-scoped :class:`AsyncSession`. All data
access flows through repositories over this session (Doc 01 §2.6 — repository pattern).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
#: The event loop the cached engine's pool belongs to.
#:
#: An async engine's connection pool holds asyncio primitives owned by the loop that created them.
#: The API keeps one loop for the process lifetime, so this never changes there. A Celery worker
#: does not: every task runs under its own ``asyncio.run(...)``, which creates a loop and closes it
#: on return. Caching the engine across those runs hands the second task a pool whose futures
#: belong to a closed loop, and every async task in the process fails from then on with
#: ``got Future attached to a different loop``. Rebuilding when the loop changes keeps the
#: singleton behaviour the API relies on while making the worker correct.
_engine_loop: asyncio.AbstractEventLoop | None = None


def _build_engine() -> AsyncEngine:
    url = settings.sqlalchemy_database_uri
    is_sqlite = url.startswith("sqlite")
    # Pooling options are meaningful for MySQL; SQLite (tests) ignores them.
    kwargs: dict[str, object] = {"echo": settings.db_echo, "pool_pre_ping": settings.db_pool_pre_ping}
    if not is_sqlite:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(url, **kwargs)


def _current_loop() -> asyncio.AbstractEventLoop | None:
    """The running loop, or ``None`` when called outside one (e.g. at import time)."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def get_engine() -> AsyncEngine:
    """Return the async engine for the running loop, creating it on first use.

    Rebuilt when the running loop differs from the one that built the cached engine — see
    ``_engine_loop``. The previous engine is dropped rather than disposed: its loop has already
    closed, so awaiting ``dispose()`` on it is impossible and its sockets are dead already.
    """
    global _engine, _sessionmaker, _engine_loop
    loop = _current_loop()
    if _engine is None or (loop is not None and _engine_loop is not loop):
        _engine = _build_engine()
        _engine_loop = loop
        _sessionmaker = async_sessionmaker(
            bind=_engine, expire_on_commit=False, autoflush=False
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the engine for the running loop."""
    # Always route through get_engine(): it owns the loop check, and a factory cached against a
    # previous loop is exactly the stale object this module exists to avoid handing out.
    get_engine()
    assert _sessionmaker is not None  # noqa: S101 — guaranteed by get_engine()
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a request-scoped session, rolling back on error.

    The service layer owns explicit commits (transaction boundaries, Doc 01 §2.6).
    """
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine and its connection pool (application shutdown)."""
    global _engine, _sessionmaker, _engine_loop
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        _engine_loop = None
