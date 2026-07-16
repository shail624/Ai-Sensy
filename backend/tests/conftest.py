"""Pytest fixtures.

Tests run hermetically against an in-memory SQLite database (Doc 10 §8/§9 — external
services are never contacted from tests). Environment overrides are set **before** the
application is imported so the settings singleton picks them up.

The database uses a single shared connection (``StaticPool``) so data seeded through one
session is visible to the ASGI app's request-scoped sessions in the same test. Each test
gets a freshly created schema and a clean disposal.
"""

from __future__ import annotations

import os

# Configure a hermetic test environment before importing application modules.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("LOG_JSON", "false")
# Rate limiting is exercised in its own dedicated test; keep other tests deterministic.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# Fast Argon2id parameters for tests only (production uses the secure defaults).
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_MEMORY_COST", "512")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

from collections.abc import AsyncIterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402,F401  (registers tables on Base.metadata)
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.role import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.rbac.seeding import sync_permissions, sync_system_roles  # noqa: E402


@pytest.fixture
async def engine() -> AsyncIterator[object]:
    """A fresh in-memory SQLite engine with the full schema, one per test."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    """A session for repository/service tests (the test controls commit/rollback)."""
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    """ASGI HTTP client whose request sessions share the test database."""
    app = create_app()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
async def organization(session_factory) -> Organization:
    """A seeded organization with the full permission catalog and preset system roles."""
    async with session_factory() as session:
        org = Organization(name="Vi Reactivation Team", slug="vi-reactivation")
        session.add(org)
        await session.flush()
        await sync_permissions(session)
        await sync_system_roles(session, org.id)
        await session.commit()
        return org


@dataclass
class CreatedUser:
    """A created test user plus its plaintext password (for login tests)."""

    user: User
    password: str


@pytest.fixture
def make_user(session_factory, organization):
    """Factory: create a user, optionally superuser, optionally assigned named roles."""
    from sqlalchemy import select

    from app.models.role import Role

    async def _make(
        *,
        email: str = "user@vi.test",
        password: str = "Sup3r-Secret-Pass!",
        full_name: str = "Test User",
        is_superuser: bool = False,
        roles: tuple[str, ...] = (),
    ) -> CreatedUser:
        async with session_factory() as session:
            user = User(
                organization_id=organization.id,
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                is_superuser=is_superuser,
            )
            session.add(user)
            await session.flush()
            for role_name in roles:
                role = (
                    await session.scalars(
                        select(Role).where(
                            Role.organization_id == organization.id, Role.name == role_name
                        )
                    )
                ).first()
                if role is not None:
                    session.add(UserRole(user_id=user.id, role_id=role.id))
            await session.commit()
            return CreatedUser(user=user, password=password)

    return _make
