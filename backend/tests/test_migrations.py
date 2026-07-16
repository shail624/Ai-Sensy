"""Migration tests (Doc 10 §9 — schema is created only via migrations).

Exercises the real Alembic pipeline end-to-end against a throwaway SQLite file:
``upgrade head`` builds the full Identity/Audit schema and seeds the permission catalog;
``downgrade base`` removes everything; a re-``upgrade`` proves idempotent reversibility.

These are **synchronous** tests on purpose: the Alembic env runs ``asyncio.run`` internally,
which cannot be nested inside pytest-asyncio's running loop.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.rbac.catalog import PERMISSION_CATALOG

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_EXPECTED_TABLES = {
    "organizations",
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "refresh_tokens",
    "user_sessions",
    "audit_logs",
    "settings",
    "feature_flags",
    "api_keys",
    "contacts",
    "tags",
    "contact_tags",
    "contact_events",
    "lead_pipelines",
    "lead_stages",
    "segments",
    "segment_rules",
    "custom_attribute_definitions",
    "contact_attribute_values",
}


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return cfg


def _table_names(db_path: Path) -> set[str]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    finally:
        con.close()
    return {r[0] for r in rows}


def test_migrations_upgrade_downgrade_roundtrip(tmp_path: Path, monkeypatch) -> None:
    """upgrade head → full schema + seed; downgrade base → clean; re-upgrade → works."""
    db_path = tmp_path / "migration_test.db"
    # Point the Alembic env (which reads app settings) at the throwaway file DB.
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    cfg = _alembic_config()

    command.upgrade(cfg, "head")

    tables = _table_names(db_path)
    assert tables >= _EXPECTED_TABLES
    assert "alembic_version" in tables

    con = sqlite3.connect(db_path)
    try:
        # The full catalog is seeded (Doc 04 §4.3).
        count = con.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        assert count == len(PERMISSION_CATALOG)
        version = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert version == "0008_custom_attributes"
    finally:
        con.close()

    command.downgrade(cfg, "base")
    remaining = _table_names(db_path)
    assert not (_EXPECTED_TABLES & remaining), "all domain tables must be dropped on downgrade"

    # Reversible and repeatable.
    command.upgrade(cfg, "head")
    assert _table_names(db_path) >= _EXPECTED_TABLES


def test_first_migration_is_base_revision() -> None:
    """The initial schema migration is the root of the history (down_revision is None)."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    assert list(script.get_bases()) == ["0001_identity_and_audit"]
