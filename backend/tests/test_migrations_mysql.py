"""Live-MySQL migration regression (Doc 10 §9) — the exact class of failure this repairs.

The hermetic default suite runs entirely against SQLite and never depends on this file (per
``tests/conftest.py``'s own stated discipline: "external services are never contacted from
tests"). The tests decorated with ``@_live_mysql_required`` are the deliberate, clearly-scoped
exception: they prove the repair for ``0035a_widen_version_table`` against a *real* MySQL 8
server, using the repository's own approved local infrastructure (``docker compose up -d`` from
the repository root).

Reachability is classified into three states, not two:

- **unreachable** — nothing answered at ``DB_HOST:DB_PORT`` (connection refused, timed out,
  unknown host). This is the ordinary "no MySQL running" case every developer without Docker
  hits, and the live-MySQL tests skip cleanly for it — never fail.
- **misconfigured** — a MySQL server *did* answer but rejected the configured credentials
  (wrong ``MYSQL_ROOT_PASSWORD``, wrong user, etc.). This is not "MySQL absent" and must not be
  reported as a skip: it usually means ``DB_HOST``/``DB_PORT`` is pointed at a real, differently
  configured server, and silently skipping would hide that. Live-MySQL tests fail loudly instead,
  with a message that names the environment variables to check but never the credential value
  itself.
- **ok** — a MySQL server answered and accepted the configured credentials; the live tests run
  for real.

The classification logic (``_classify_connection_error``) is a pure function of the raised
exception and is unit-tested below without touching the network, so the skip/fail decision itself
has coverage even when no MySQL server is available in this environment.

Each MySQL-backed test creates and drops its own throwaway MySQL database (mirroring the SQLite
suite's ``tmp_path`` throwaway file), so nothing here touches a developer's own ``wa_platform`` dev
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


class MySQLUnavailable(Exception):
    """No MySQL server answered — legitimate to skip the live-MySQL suite for."""


class MySQLMisconfigured(Exception):
    """A MySQL server answered but rejected the configured credentials/config.

    This is deliberately **not** a subclass of ``MySQLUnavailable``: it must never be treated as
    "MySQL absent" and silently skipped, since a real, reachable server that rejects the
    configured connection details is a configuration bug, not a missing dependency.
    """


# pymysql/MySQL client error codes raised when no server ever answered the TCP/protocol
# handshake — i.e. genuinely nothing is listening there (connection refused, timed out, unknown
# host, or the connection dropped before a handshake completed). Every other error — most
# commonly 1045 "Access denied for user" — means a server *did* respond, so the failure is a live
# misconfiguration, not an absent server.
_UNREACHABLE_ERROR_CODES = frozenset(
    {
        2002,  # CR_CONNECTION_ERROR -- can't connect via socket
        2003,  # CR_CONN_HOST_ERROR -- can't connect to server (refused / timed out / DNS failure)
        2005,  # CR_UNKNOWN_HOST
        2013,  # CR_SERVER_LOST -- connection dropped mid-handshake
    }
)


def _classify_connection_error(exc: Exception) -> MySQLUnavailable | MySQLMisconfigured:
    """Classify a connection failure without ever including the configured password.

    pymysql's own error text for authentication failures already omits the password value
    (it reports only ``using password: YES/NO``), and this function never interpolates
    ``_ROOT_PASSWORD`` into a message, so the result is always safe to print in a test failure.
    """
    if isinstance(exc, pymysql.err.OperationalError) and exc.args:
        code = exc.args[0]
        if code in _UNREACHABLE_ERROR_CODES:
            return MySQLUnavailable(f"no MySQL server answered at {_ROOT_HOST}:{_ROOT_PORT} (error {code})")
        return MySQLMisconfigured(
            f"a MySQL server is reachable at {_ROOT_HOST}:{_ROOT_PORT} but rejected the configured "
            f"root credentials (MySQL error {code}) — check DB_HOST/DB_PORT/MYSQL_ROOT_PASSWORD, "
            "or stop pointing tests at this server"
        )
    if isinstance(exc, OSError):
        # Socket-level failure before the MySQL protocol even started (platform-specific
        # connection errors) -- also "nobody is listening there".
        return MySQLUnavailable(f"no MySQL server answered at {_ROOT_HOST}:{_ROOT_PORT} ({type(exc).__name__})")
    return MySQLMisconfigured(f"unexpected error probing MySQL at {_ROOT_HOST}:{_ROOT_PORT}: {type(exc).__name__}")


def _probe_mysql_state() -> tuple[str, str]:
    """One connection attempt, classified into ``"ok"``, ``"unreachable"``, or ``"misconfigured"``.

    Never raises. Returns ``(state, message)`` — ``message`` is empty for ``"ok"``.
    """
    try:
        conn = pymysql.connect(
            host=_ROOT_HOST,
            port=_ROOT_PORT,
            user="root",
            password=_ROOT_PASSWORD,
            connect_timeout=2,
        )
    except Exception as exc:  # noqa: BLE001 - classified immediately below, never swallowed silently
        classified = _classify_connection_error(exc)
        if isinstance(classified, MySQLUnavailable):
            return "unreachable", str(classified)
        return "misconfigured", str(classified)
    conn.close()
    return "ok", ""


_MYSQL_STATE, _MYSQL_STATE_MESSAGE = _probe_mysql_state()

_live_mysql_required = pytest.mark.skipif(
    _MYSQL_STATE == "unreachable",
    reason=(
        f"{_MYSQL_STATE_MESSAGE} — run `docker compose up -d` from the repository root; "
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
    """A freshly created, uniquely named MySQL database, dropped again on teardown.

    Fails loudly (never skips) if MySQL is reachable but misconfigured — see module docstring.
    """
    if _MYSQL_STATE == "misconfigured":
        pytest.fail(_MYSQL_STATE_MESSAGE, pytrace=False)

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


def _version_column_type(db_name: str) -> str:
    """The real, live ``information_schema`` column type for ``alembic_version.version_num``.

    Inspects the database directly (not migration source text), so this actually proves the
    ``ALTER TABLE`` in ``0035a_widen_version_table`` took effect on MySQL.
    """
    conn = pymysql.connect(
        host=_ROOT_HOST, port=_ROOT_PORT, user="root", password=_ROOT_PASSWORD, database=db_name
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'alembic_version' "
                "AND COLUMN_NAME = 'version_num'",
                (db_name,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "alembic_version.version_num column not found"
    return row[0]


def _user_row_count(db_name: str, email: str) -> int:
    """Real row count in ``users`` for ``email`` — proves create-owner idempotency at the DB level,
    independent of what ``bootstrap_owner``'s return value claims."""
    conn = pymysql.connect(
        host=_ROOT_HOST, port=_ROOT_PORT, user="root", password=_ROOT_PASSWORD, database=db_name
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    return int(row[0])


@_live_mysql_required
def test_fresh_mysql_database_upgrades_base_to_head(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand-new MySQL 8 database walks the entire chain, including the repaired 0035→0036 step,
    and ``alembic_version.version_num`` is genuinely widened to ``VARCHAR(255)`` on real MySQL."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()

    command.upgrade(cfg, "head")

    assert _current_version(throwaway_database) == "0043_conversation_channel_endpoints"
    assert _version_column_type(throwaway_database) == "varchar(255)"
    asyncio.run(dispose_engine())


@_live_mysql_required
def test_mysql_database_at_0035_upgrades_to_head(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduces the exact historical failure: a database already stamped at the last revision
    every real MySQL deployment could actually reach, upgrading through the repaired step to head,
    with the version column genuinely narrow before and genuinely widened after."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()

    command.upgrade(cfg, "0035_notification_center")
    assert _current_version(throwaway_database) == "0035_notification_center"
    assert _version_column_type(throwaway_database) == "varchar(32)"

    # This is the transition that raised `DataError: Data too long for column 'version_num'`
    # before 0035a_widen_version_table existed.
    command.upgrade(cfg, "head")

    assert _current_version(throwaway_database) == "0043_conversation_channel_endpoints"
    assert _version_column_type(throwaway_database) == "varchar(255)"
    asyncio.run(dispose_engine())


@_live_mysql_required
def test_create_owner_after_mysql_upgrade_is_idempotent_on_rerun(
    throwaway_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`python -m app.cli create-owner` (via the same `bootstrap_owner` it calls) succeeds against
    a freshly migrated, real MySQL database, and a second invocation is a clean no-op — verified
    against the real `users` table, not just the returned dataclass."""
    _point_settings_at(monkeypatch, throwaway_database)
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    email = "owner@migration-test.example"
    password = "MigrationTest123!"
    validate_password_policy(password)  # fails loudly here, not inside bootstrap_owner, if ever violated

    async def _bootstrap() -> object:
        return await bootstrap_owner(
            get_sessionmaker(),
            email=email,
            full_name="Migration Test Owner",
            password=password,
        )

    async def _bootstrap_twice() -> tuple[object, object]:
        try:
            first = await _bootstrap()
            second = await _bootstrap()
            return first, second
        finally:
            await dispose_engine()

    first_result, second_result = asyncio.run(_bootstrap_twice())

    assert first_result.owner_created is True
    assert first_result.organization_created is True
    assert first_result.owner_email == email
    assert _user_row_count(throwaway_database, email) == 1

    assert second_result.owner_created is False
    assert second_result.organization_created is False
    assert second_result.owner_email == email
    assert _user_row_count(throwaway_database, email) == 1


# --- Reachability classification: hermetic, no network access, always run -------------------
#
# These test the skip/fail decision logic itself with synthetic exceptions matching real pymysql
# error codes (verified empirically against a live MySQL 8 server: 2003 for connection-refused,
# 1045 for access-denied). They deliberately have no `@_live_mysql_required` marker so they run
# in the default hermetic suite regardless of whether MySQL is available here.


def test_classify_connection_error_is_unreachable_for_connection_refused() -> None:
    exc = pymysql.err.OperationalError(2003, "Can't connect to MySQL server on 'x' (timed out)")
    assert isinstance(_classify_connection_error(exc), MySQLUnavailable)


def test_classify_connection_error_is_unreachable_for_unknown_host() -> None:
    exc = pymysql.err.OperationalError(2005, "Unknown MySQL server host 'x'")
    assert isinstance(_classify_connection_error(exc), MySQLUnavailable)


def test_classify_connection_error_is_unreachable_for_generic_os_error() -> None:
    assert isinstance(_classify_connection_error(OSError("network unreachable")), MySQLUnavailable)


def test_classify_connection_error_is_misconfigured_for_access_denied() -> None:
    exc = pymysql.err.OperationalError(1045, "Access denied for user 'root'@'x' (using password: YES)")
    assert isinstance(_classify_connection_error(exc), MySQLMisconfigured)


def test_classify_connection_error_is_misconfigured_for_unrecognised_error() -> None:
    """Any MySQL protocol-level error not in the known-unreachable set is treated as a live
    misconfiguration, not silently folded into 'MySQL absent' — the bug this hardening fixes."""
    exc = pymysql.err.OperationalError(1130, "Host 'x' is not allowed to connect to this MySQL server")
    assert isinstance(_classify_connection_error(exc), MySQLMisconfigured)


def test_classify_connection_error_never_leaks_the_configured_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.test_migrations_mysql._ROOT_PASSWORD", "super-secret-value-must-not-leak"
    )
    exc = pymysql.err.OperationalError(1045, "Access denied for user 'root'@'x' (using password: YES)")
    message = str(_classify_connection_error(exc))
    assert "super-secret-value-must-not-leak" not in message


@_live_mysql_required
def test_probe_reports_ok_against_the_real_configured_mysql_server() -> None:
    """When MySQL is genuinely reachable and correctly configured, the probe reports 'ok' — the
    third of the three required states, confirmed against real infrastructure, not a mock."""
    state, message = _probe_mysql_state()
    assert state == "ok"
    assert message == ""


@_live_mysql_required
def test_probe_reports_misconfigured_for_a_real_wrong_password_against_the_live_server() -> None:
    """End-to-end confirmation (not just the unit-level classifier) that a live, reachable MySQL
    server rejecting the wrong password is classified as misconfigured, not unreachable."""
    try:
        conn = pymysql.connect(
            host=_ROOT_HOST,
            port=_ROOT_PORT,
            user="root",
            password="deliberately-wrong-password-for-this-test",
            connect_timeout=2,
        )
        conn.close()
    except Exception as exc:  # noqa: BLE001 - classified immediately, the point of this test
        assert isinstance(_classify_connection_error(exc), MySQLMisconfigured)
    else:
        pytest.fail("expected the deliberately wrong password to be rejected by the live server")
