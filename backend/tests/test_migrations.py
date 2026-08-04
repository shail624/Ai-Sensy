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
    "job_metadata",
    "dead_letter",
    "media_assets",
    "imports",
    "exports",
    "bulk_jobs",
    "whatsapp_business_accounts",
    "phone_numbers",
    "webhook_events",
    "webhook_dead_letter",
    "conversations",
    "internal_notes",
    "quick_replies",
    "conversation_tags",
    "messages",
    "message_status_history",
    "message_templates",
    "template_versions",
    "campaigns",
    "campaign_recipients",
    "campaign_batches",
    "campaign_retry_queue",
    "campaign_schedules",
    "rate_cards",
    "tasks",
    "task_events",
    "analytics_message_rollups",
    "analytics_failure_rollups",
    "analytics_campaign_rollups",
    "analytics_conversation_rollups",
    "analytics_task_rollups",
    "analytics_contact_rollups",
    "analytics_rollup_runs",
    "contact_documents",
    "contact_document_versions",
    "contact_document_events",
    "automation_flows",
    "automation_flow_versions",
    "automation_runs",
    "automation_step_attempts",
    "business_event_types",
    "business_events",
    "automation_trigger_receipts",
    "reactivation_cases",
    "reactivation_case_labels",
    "reactivation_stage_events",
    "eligibility_checks",
    "kyc_cases",
    "kyc_decisions",
    "kyc_document_references",
    "sim_orders",
    "sim_order_events",
    "activation_records",
    "sla_policies",
    "sla_events",
    "notifications",
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
        assert version == "0036_customer_identity_resolution"
        task_columns = {row[1] for row in con.execute("PRAGMA table_info(tasks)").fetchall()}
        decision_columns = {
            row[1] for row in con.execute("PRAGMA table_info(kyc_decisions)").fetchall()
        }
        assert {
            "reference_type",
            "reference_id",
            "idempotency_key",
            "request_hash",
            "due_notified_at",
        } <= task_columns
        assert "reason_code" in decision_columns
        con.execute("PRAGMA foreign_keys=OFF")
        case_key = bytes.fromhex("10" * 16)
        event_key = bytes.fromhex("20" * 16)
        con.execute(
            "INSERT INTO reactivation_cases "
            "(uuid, organization_id, contact_id, stage, idempotency_key, request_hash) "
            "VALUES (?, 9001, 9002, 'lead_confirmed', ?, ?)",
            (case_key, case_key, "a" * 64),
        )
        case_id = con.execute(
            "SELECT id FROM reactivation_cases WHERE uuid = ?", (case_key,)
        ).fetchone()[0]
        con.execute(
            "INSERT INTO reactivation_stage_events "
            "(uuid, organization_id, case_id, contact_id, from_stage, to_stage, "
            "idempotency_key, request_hash) VALUES (?, 9001, ?, 9002, 'new_lead', "
            "'lead_confirmed', ?, ?)",
            (event_key, case_id, event_key, "b" * 64),
        )
        con.commit()
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
