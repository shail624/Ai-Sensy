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
    "channel_connections",
    "channel_endpoints",
    "channel_secrets",
    "channel_sessions",
    "channel_sync_checkpoints",
    "media_channel_references",
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
        assert version == "0041_channel_sync_control_plane"
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
        connection_columns = {
            row[1] for row in con.execute("PRAGMA table_info(channel_connections)").fetchall()
        }
        endpoint_columns = {
            row[1] for row in con.execute("PRAGMA table_info(channel_endpoints)").fetchall()
        }
        secret_columns = {
            row[1] for row in con.execute("PRAGMA table_info(channel_secrets)").fetchall()
        }
        assert {
            "connector_type",
            "provider_connection_id",
            "provider_configuration_json",
            "provider_metadata_json",
            "desired_state",
            "observed_state",
            "health_state",
            "row_version",
            "deleted_at",
        } <= connection_columns
        assert {
            "connection_id",
            "provider_endpoint_id",
            "endpoint_metadata_json",
            "provider_metadata_json",
            "row_version",
            "deleted_at",
        } <= endpoint_columns
        assert {
            "encrypted_payload",
            "key_version",
            "secret_version",
            "rotated_from_id",
            "revoked_at",
            "revoked_by",
            "row_version",
            "deleted_at",
        } <= secret_columns
        assert not {"plaintext", "secret_value", "token"} & secret_columns
        session_columns = {
            row[1] for row in con.execute("PRAGMA table_info(channel_sessions)").fetchall()
        }
        assert {
            "connection_id",
            "owner_user_id",
            "secret_id",
            "session_revision",
            "state",
            "pairing_state",
            "pairing_revision",
            "pairing_changed_at",
            "pairing_expires_at",
            "pairing_reason_code",
            "health_state",
            "restart_policy",
            "holder_runtime_id",
            "lease_expires_at",
            "fencing_token",
            "last_heartbeat_at",
            "expires_at",
            "capability_references_json",
            "runtime_capabilities_json",
            "provider_metadata_json",
            "recovery_metadata_json",
            "row_version",
            "deleted_at",
        } <= session_columns
        assert not {"plaintext", "secret_value", "token", "encrypted_payload"} & session_columns
        checkpoint_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info(channel_sync_checkpoints)").fetchall()
        }
        media_reference_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info(media_channel_references)").fetchall()
        }
        assert {
            "organization_id",
            "connection_id",
            "endpoint_id",
            "job_id",
            "sync_type",
            "status",
            "cursor_json",
            "watermark_at",
            "cutover_at",
            "processed_count",
            "failed_count",
            "total_count",
            "row_version",
        } <= checkpoint_columns
        assert {
            "organization_id",
            "media_asset_id",
            "endpoint_id",
            "provider_media_id",
            "upload_state",
            "download_state",
            "expires_at",
            "last_verified_at",
            "provider_metadata_json",
            "row_version",
        } <= media_reference_columns
        assert not {"plaintext", "secret_value", "token", "encrypted_payload"} & (
            checkpoint_columns | media_reference_columns
        )
        channel_permissions = {
            row[0]
            for row in con.execute(
                "SELECT code FROM permissions WHERE resource = 'channels'"
            ).fetchall()
        }
        assert channel_permissions == {
            "channels:read",
            "channels:manage",
            "channels:authenticate",
            "channels:diagnose",
            "channels:history_sync",
        }
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


def test_single_migration_head() -> None:
    """Exactly one head exists — no branch or merge was introduced in the migration graph."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    assert script.get_heads() == ["0041_channel_sync_control_plane"]


def test_revision_chain_is_linear() -> None:
    """No revision has more than one parent — the history never branches or merges (Doc 10 §9)."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    for rev in script.walk_revisions():
        assert not isinstance(rev.down_revision, tuple), (
            f"{rev.revision} has multiple parents {rev.down_revision!r} — "
            "the chain must stay linear"
        )


def test_revision_ids_fit_the_widened_version_table_column() -> None:
    """Guards the exact MySQL failure ``0035a_widen_version_table`` repairs.

    ``alembic_version.version_num`` is Alembic's own ``VARCHAR(32)`` default until that revision
    widens it to 255 characters on MySQL (SQLite has no such enforcement — this check is dialect-
    independent by design, so it catches the regression before anyone touches a real database).
    A second, tighter margin flags drift toward the limit long before any identifier could hit it.
    """
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    max_len = max(len(rev.revision) for rev in script.walk_revisions())
    assert max_len <= 255, (
        f"longest revision id is {max_len} chars — exceeds the widened "
        "alembic_version.version_num column (see 0035a_widen_version_table.py)"
    )
    assert max_len <= 100, (
        f"longest revision id is {max_len} chars — well past historical norms; "
        "a new naming convention may be worth reconsidering before it approaches the column limit"
    )
