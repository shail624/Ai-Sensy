"""Async database engine and session management.

Creates the process-wide async SQLAlchemy engine + session factory (Doc 08 §10) and
exposes a FastAPI dependency yielding a request-scoped :class:`AsyncSession`. All data
access flows through repositories over this session (Doc 01 §2.6 — repository pattern).
"""

from __future__ import annotations

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


def _build_engine() -> AsyncEngine:
    url = settings.sqlalchemy_database_uri
    is_sqlite = url.startswith("sqlite")
    # Pooling options are meaningful for MySQL; SQLite (tests) ignores them.
    kwargs: dict[str, object] = {"echo": settings.db_echo, "pool_pre_ping": settings.db_pool_pre_ping}
    if not is_sqlite:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(url, **kwargs)


def get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it on first use."""
    global _engine, _sessionmaker
    if _engine is None:
        _engine = _build_engine()
        _sessionmaker = async_sessionmaker(
            bind=_engine, expire_on_commit=False, autoflush=False
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the engine."""
    if _sessionmaker is None:
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
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
