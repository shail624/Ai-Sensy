"""Analytics & Reporting foundation (Doc 15 — Phase 8).

**Expand** phase: creates the six rollup fact tables and the rollup-run control table, and inserts
the two new analytics permissions. Additive and reversible; no existing table is touched.

These tables are **not partitioned** (Doc 15 §21.2) — at hourly grain the row counts are small — so
unlike the partitioned sources they aggregate they keep real foreign keys to ``organizations``.

The permission insert is **idempotent** (guarded by a code existence check): on a fresh migrate the
dynamic catalog seed (0002) already inserted them, so this skips; on an existing database it adds
the two rows. Role realignment is the idempotent deploy-time ``sync_system_roles`` step
(Doc 12 §58), not this migration.

Revision ID: 0027_analytics
Revises: 0026_tasks
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id

revision = "0027_analytics"
down_revision = "0026_tasks"
branch_labels = None
depends_on = None

# Static snapshot of the permissions this revision introduces (Doc 15 §15).
_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "analytics:export",
        "resource": "analytics",
        "action": "export",
        "description": "Export analytics reports (CSV/Excel/JSON)",
    },
    {
        "code": "analytics:executive",
        "resource": "analytics",
        "action": "executive",
        "description": "View cost analytics, spend and the executive dashboard",
    },
]

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)

#: Every fact table drops rows past retention by this key, and serves reads by it (Doc 15 §21.1).
_TABLES = (
    "analytics_message_rollups",
    "analytics_failure_rollups",
    "analytics_campaign_rollups",
    "analytics_conversation_rollups",
    "analytics_task_rollups",
    "analytics_contact_rollups",
    "analytics_rollup_runs",
)


def _common_columns() -> list[sa.Column]:
    """Scope, bucket and timestamp columns shared by every fact table (Doc 15 §9)."""
    return [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("grain", sa.String(8), nullable=False, server_default=sa.text("'hour'")),
        sa.Column("bucket_start", datetime6(), nullable=False),
    ]


def _audit_columns(now: sa.TextClause) -> list[sa.Column]:
    return [
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
    ]


def _counter(name: str) -> sa.Column:
    return sa.Column(name, int_id(), nullable=False, server_default=sa.text("0"))


def _accumulator(name: str) -> sa.Column:
    return sa.Column(name, big_id(), nullable=False, server_default=sa.text("0"))


def _org_fk(name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id"], ["organizations.id"], name=name, ondelete="CASCADE"
    )


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        }
        if dialect == "mysql"
        else {}
    )

    # --- Messages (Doc 15 §9.1) ----------------------------------------------------------------
    op.create_table(
        "analytics_message_rollups",
        *_common_columns(),
        sa.Column("phone_number_id", big_id(), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("message_type", sa.String(24), nullable=False),
        _counter("accepted_count"),
        _counter("sent_count"),
        _counter("delivered_count"),
        _counter("read_count"),
        _counter("failed_count"),
        _accumulator("cost_micros"),
        _accumulator("delivery_latency_ms_sum"),
        _counter("delivery_latency_count"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "direction",
            "message_type",
            name="uq_amr_grain",
        ),
        _org_fk("fk_amr_organization_id"),
        **mysql_args,
    )
    op.create_index(
        "ix_amr_org_bucket",
        "analytics_message_rollups",
        ["organization_id", "grain", "bucket_start"],
    )

    # --- Failures (Doc 15 §9.2) ----------------------------------------------------------------
    op.create_table(
        "analytics_failure_rollups",
        *_common_columns(),
        sa.Column("phone_number_id", big_id(), nullable=True),
        sa.Column("error_code", sa.String(24), nullable=False),
        _counter("failure_count"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "error_code",
            name="uq_afr_grain",
        ),
        _org_fk("fk_afr_organization_id"),
        **mysql_args,
    )
    op.create_index(
        "ix_afr_org_bucket_code",
        "analytics_failure_rollups",
        ["organization_id", "grain", "bucket_start", "error_code"],
    )

    # --- Campaigns (Doc 15 §9.3) ---------------------------------------------------------------
    op.create_table(
        "analytics_campaign_rollups",
        *_common_columns(),
        sa.Column("campaign_id", big_id(), nullable=False),
        _counter("targeted_count"),
        _counter("sent_count"),
        _counter("delivered_count"),
        _counter("read_count"),
        _counter("failed_count"),
        _counter("skipped_count"),
        _counter("click_count"),
        _accumulator("cost_micros"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "grain", "bucket_start", "campaign_id", name="uq_acr_grain"
        ),
        _org_fk("fk_acr_organization_id"),
        **mysql_args,
    )
    op.create_index(
        "ix_acr_org_campaign_bucket",
        "analytics_campaign_rollups",
        ["organization_id", "campaign_id", "bucket_start"],
    )

    # --- Conversations (Doc 15 §9.4) -----------------------------------------------------------
    op.create_table(
        "analytics_conversation_rollups",
        *_common_columns(),
        sa.Column("phone_number_id", big_id(), nullable=True),
        sa.Column("assigned_user_id", big_id(), nullable=True),
        _counter("opened_count"),
        _counter("resolved_count"),
        _counter("inbound_message_count"),
        _counter("outbound_message_count"),
        _counter("handled_count"),
        _accumulator("first_response_seconds_sum"),
        _counter("first_response_count"),
        _accumulator("resolution_seconds_sum"),
        _counter("resolution_count"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "assigned_user_id",
            name="uq_acvr_grain",
        ),
        _org_fk("fk_acvr_organization_id"),
        **mysql_args,
    )
    op.create_index(
        "ix_acvr_org_bucket_user",
        "analytics_conversation_rollups",
        ["organization_id", "grain", "bucket_start", "assigned_user_id"],
    )

    # --- Tasks (Doc 15 §9.5) -------------------------------------------------------------------
    op.create_table(
        "analytics_task_rollups",
        *_common_columns(),
        sa.Column("assigned_agent_id", big_id(), nullable=True),
        sa.Column("task_type", sa.String(24), nullable=False),
        _counter("created_count"),
        _counter("completed_count"),
        _counter("completed_on_time_count"),
        _counter("skipped_count"),
        _counter("cancelled_count"),
        _counter("reopened_count"),
        _counter("overdue_entered_count"),
        _accumulator("time_to_complete_seconds_sum"),
        _counter("time_to_complete_count"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "assigned_agent_id",
            "task_type",
            name="uq_atr_grain",
        ),
        _org_fk("fk_atr_organization_id"),
        **mysql_args,
    )
    op.create_index(
        "ix_atr_org_bucket_agent",
        "analytics_task_rollups",
        ["organization_id", "grain", "bucket_start", "assigned_agent_id"],
    )

    # --- Contacts (Doc 15 §9.6) ----------------------------------------------------------------
    op.create_table(
        "analytics_contact_rollups",
        *_common_columns(),
        _counter("created_count"),
        _counter("opted_in_count"),
        _counter("opted_out_count"),
        _counter("reactivated_count"),
        _counter("active_count"),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "grain", "bucket_start", name="uq_actr_grain"
        ),
        _org_fk("fk_actr_organization_id"),
        **mysql_args,
    )

    # --- Rollup runs / watermarks (Doc 15 §9.7) ------------------------------------------------
    op.create_table(
        "analytics_rollup_runs",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("watermark_at", datetime6(), nullable=True),
        sa.Column("last_run_at", datetime6(), nullable=True),
        sa.Column("last_status", sa.String(16), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("duration_ms", int_id(), nullable=True),
        *_audit_columns(now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "kind", name="uq_arr_org_kind"),
        _org_fk("fk_arr_organization_id"),
        **mysql_args,
    )

    # Idempotent permission insert (Doc 15 §15; governance Doc 12 §58).
    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
    op.drop_index("ix_atr_org_bucket_agent", table_name="analytics_task_rollups")
    op.drop_index("ix_acvr_org_bucket_user", table_name="analytics_conversation_rollups")
    op.drop_index("ix_acr_org_campaign_bucket", table_name="analytics_campaign_rollups")
    op.drop_index("ix_afr_org_bucket_code", table_name="analytics_failure_rollups")
    op.drop_index("ix_amr_org_bucket", table_name="analytics_message_rollups")
    for table in reversed(_TABLES):
        op.drop_table(table)
