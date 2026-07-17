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
# Inbound webhook secrets (Doc 04 §23). Part of the environment, like the keys above: the public
# endpoint is configured in every test, and the tests that exercise a *missing* secret unset it.
META_APP_SECRET = "meta-app-secret-for-tests"
META_WEBHOOK_VERIFY_TOKEN = "verify-token-for-tests"
os.environ.setdefault("META_APP_SECRET", META_APP_SECRET)
os.environ.setdefault("META_WEBHOOK_VERIFY_TOKEN", META_WEBHOOK_VERIFY_TOKEN)

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
def dispatched(monkeypatch):
    """Capture what the webhook endpoint hands to the broker instead of enqueueing it.

    Shared: every test that posts a delivery needs the ack path to stop at the broker's edge.
    """
    import app.channels.tasks as tasks

    calls: list[list[int]] = []
    monkeypatch.setattr(
        tasks.ingest_webhook_events, "apply_async", lambda args: calls.append(args[0])
    )
    return calls


class FakeIdempotencyStore:
    """Minimal async Redis stand-in for `SET NX` + `GET` + `DELETE` (Doc 04 §8)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key: str):
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return int(self.store.pop(key, None) is not None)


@pytest.fixture
def idem(monkeypatch) -> FakeIdempotencyStore:
    """The send path fails closed without an idempotency store, so every send test needs one."""
    import app.api.v1.endpoints.messages as endpoint

    store = FakeIdempotencyStore()
    monkeypatch.setattr(endpoint, "get_redis_client", lambda: store)
    return store


@pytest.fixture
def sent(monkeypatch) -> list[int]:
    """Capture what the send endpoint hands to `sends.priority`."""
    import app.channels.tasks as tasks

    calls: list[int] = []
    monkeypatch.setattr(tasks.send_message, "apply_async", lambda args: calls.append(args[0]))
    return calls


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
