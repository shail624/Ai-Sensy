"""Live-MySQL migration regression (Doc 10 §9) — the exact class of failure this repairs.

The hermetic default suite runs entirely against SQLite and never depends on this file (per
``tests/conftest.py``'s own stated discipline: "external services are never contacted from
tests"). These tests are the one deliberate, clearly-scoped exception: they prove the repair for
``0035a_widen_version_table`` against a *real* MySQL 8 server, using the repository's own approved
local infrastructure (``docker compose up -d`` from the repository root). When no such server is
reachable, every test here is skipped — never failed — so the default ``pytest`` run stays
hermetic and this module adds no new external dependency to CI.

Each test creates and drops its own throwaway MySQL database (mirroring the SQLite suite's
``tmp_path`` throwaway file), so nothing here touches a developer's own ``wa_platform`` dev
database. Alembic's ``command.upgrade``/``command.downgrade`` internally call ``asyncio.run`` (see
``alembic/env.py``), which cannot nest inside a running event loop — so, like
``tests/test_migrations.py``, these are plain synchronous test functions that call
``asyncio.run(...)`` explicitly wherever an async application call (``bootstrap_owner``,
``dispose_engine``) is needed.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pymysql
import pytest
from alembic import command
from alembic.config import Config

from app.cli import bootstrap_owner
from app.core.config import settings
from app.core.security import validate_password_policy
from app.db.session import dispose_engine, get_sessionmaker

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

_ROOT_HOST = os.environ.get("DB_HOST", "localhost")
_ROOT_PORT = int(os.environ.get("DB_PORT", "3306"))
_ROOT_PASSWORD = os.environ.get("MYSQL_ROOT_PASSWORD", "root")


def _mysql_reachable() -> bool:
    try:
        conn = pymysql.connect(
            host=_ROOT_HOST,
            port=_ROOT_PORT,
            user="root",
            password=_ROOT_PASSWORD,
            connect_timeout=2,
        )
    except Exception:
        return False
    conn.close()
    return True


pytestmark = pytest.mark.skipif(
    not _mysql_reachable(),
    reason=(
        "requires a live MySQL 8 instance — run `docker compose up -d` from the repository root; "
        "the hermetic suite does not depend on this"
    ),
)


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return cfg


def _root_connection() -> pymysql.connections.Connection:
    return pymysql.connect(host=_ROOT_HOST, port=_ROOT_PORT, user="root", password=_ROOT_PASSWORD)


@pytest.fixture
def throwaway_database() -> str:
    """A freshly created, uniquely named MySQL database, dropped again on teardown."""
    name = f"wa_migration_test_{uuid.uuid4().hex[:12]}"
    conn = _root_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE `{name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
        conn.commit()
    finally:
        conn.close()

    yield name

    conn = _root_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
        conn.commit()
    finally:
        conn.close()


def _point_settings_at(monkeypatch: pytest.MonkeyPatch, db_name: str) -> None:
    url = (
        f"mysql+aiomysql://root:{_ROOT_PASSWORD}@{_ROOT_HOST}:{_ROOT_PORT}"
        f"/{db_name}?charset=utf8mb4"
    )
    monkeypatch.setattr(settings, "database_url", url)
    asyncio.run(dispose_engine())


def _current_version(db_name: str) -> str:
    conn = pymysql.connect(
        host=_ROOT_HOST, port=_ROOT_PORT, user="root", password=_ROOT_PASSWORD, database=db_name
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    return row[0]


def test_fresh_mysql_database_upgrades_base_to_head(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand-new MySQL 8 database walks the entire chain, including the repaired 0035→0036 step."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()

    command.upgrade(cfg, "head")

    assert _current_version(throwaway_database) == "0041_channel_sync_control_plane"
    asyncio.run(dispose_engine())


def test_mysql_database_at_0035_upgrades_to_head(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduces the exact historical failure: a database already stamped at the last revision
    every real MySQL deployment could actually reach, upgrading through the repaired step to head."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()

    command.upgrade(cfg, "0035_notification_center")
    assert _current_version(throwaway_database) == "0035_notification_center"

    # This is the transition that raised `DataError: Data too long for column 'version_num'`
    # before 0035a_widen_version_table existed.
    command.upgrade(cfg, "head")

    assert _current_version(throwaway_database) == "0041_channel_sync_control_plane"
    asyncio.run(dispose_engine())


def test_create_owner_after_mysql_upgrade(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`python -m app.cli create-owner` (via the same `bootstrap_owner` it calls) succeeds against
    a freshly migrated, real MySQL database."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    password = "MigrationTest123!"
    validate_password_policy(password)  # fails loudly here, not inside bootstrap_owner, if ever violated

    async def _bootstrap() -> object:
        try:
            return await bootstrap_owner(
                get_sessionmaker(),
                email="owner@migration-test.example",
                full_name="Migration Test Owner",
                password=password,
            )
        finally:
            await dispose_engine()

    result = asyncio.run(_bootstrap())

    assert result.owner_created is True
    assert result.organization_created is True
    assert result.owner_email == "owner@migration-test.example"
