"""Template registry: templates & versions (Module 5 — Doc 03 §7.1).

**Expand** phase: creates ``message_templates`` and ``template_versions``. Additive and reversible.

``uq_tpl_waba_name_lang`` mirrors Meta's own uniqueness rule — one template per (WABA, name,
language) — which is what lets sync be an idempotent upsert.

Revision ID: 0017_message_templates
Revises: 0016_conversations_messages
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary

revision = "0017_message_templates"
down_revision = "0016_conversations_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "message_templates",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("waba_id", big_id(), nullable=False),
        sa.Column("meta_template_id", sa.String(40), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("quality_score", sa.String(16), nullable=True),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("variable_count", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("has_media_header", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_synced_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_tpl_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_tpl_org", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["waba_id"],
            ["whatsapp_business_accounts.id"],
            name="fk_tpl_waba",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "category IN ('marketing','utility','authentication')", name="ck_tpl_category"
        ),
        sa.CheckConstraint(
            "status IN ('draft','pending','approved','rejected','paused','disabled')",
            name="ck_tpl_status",
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_tpl_waba_name_lang",
        "message_templates",
        ["waba_id", "name", "language"],
        unique=True,
    )
    op.create_index("ix_tpl_org_status", "message_templates", ["organization_id", "status"])
    op.create_index("ix_tpl_category", "message_templates", ["organization_id", "category"])

    op.create_table(
        "template_versions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("template_id", big_id(), nullable=False),
        sa.Column("version_no", int_id(), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["message_templates.id"],
            name="fk_tplver_template",
            ondelete="CASCADE",
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_tplver_template_ver", "template_versions", ["template_id", "version_no"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_tplver_template_ver", table_name="template_versions")
    op.drop_table("template_versions")
    op.drop_index("ix_tpl_category", table_name="message_templates")
    op.drop_index("ix_tpl_org_status", table_name="message_templates")
    op.drop_index("uq_tpl_waba_name_lang", table_name="message_templates")
    op.drop_table("message_templates")
