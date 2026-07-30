"""Versioned automation definitions (Design Book 22, MD5 Phase 2A).

Revision ID: 0029_automation_definitions
Revises: 0028_contact_documents
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.automation import AUTOMATION_STATUSES

revision = "0029_automation_definitions"
down_revision = "0028_contact_documents"
branch_labels = None
depends_on = None

_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "automations:read",
        "resource": "automations",
        "action": "read",
        "description": "View automation drafts and publication history",
    },
    {
        "code": "automations:write",
        "resource": "automations",
        "action": "write",
        "description": "Create and edit automation drafts and restore versions",
    },
    {
        "code": "automations:publish",
        "resource": "automations",
        "action": "publish",
        "description": "Publish, enable and disable automation definitions",
    },
]

_permissions = sa.table(
    "permissions",
    sa.column("code", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("description", sa.String),
)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{value}'" for value in values) + ")"


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

    op.create_table(
        "automation_flows",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("draft_graph_json", sa.JSON(), nullable=False),
        sa.Column("draft_content_hash", sa.CHAR(64), nullable=False),
        sa.Column("active_version_no", int_id(), nullable=True),
        sa.Column("active_content_hash", sa.CHAR(64), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_flows_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_automation_flows_org",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            _in_clause("status", AUTOMATION_STATUSES), name="ck_automation_flows_status"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_automation_flows_org_updated", "automation_flows", ["organization_id", "updated_at"]
    )
    op.create_index(
        "ix_automation_flows_org_status_updated",
        "automation_flows",
        ["organization_id", "status", "updated_at"],
    )

    op.create_table(
        "automation_flow_versions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("flow_id", big_id(), nullable=False),
        sa.Column("version_no", int_id(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("graph_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("published_by", big_id(), nullable=True),
        sa.Column("published_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_automation_flow_versions_uuid"),
        sa.UniqueConstraint("flow_id", "version_no", name="uq_automation_flow_version_no"),
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["automation_flows.id"],
            name="fk_automation_flow_versions_flow",
            ondelete="CASCADE",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_automation_flow_versions_flow_published",
        "automation_flow_versions",
        ["flow_id", "published_at"],
    )

    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
    op.drop_index(
        "ix_automation_flow_versions_flow_published", table_name="automation_flow_versions"
    )
    op.drop_table("automation_flow_versions")
    op.drop_index("ix_automation_flows_org_status_updated", table_name="automation_flows")
    op.drop_index("ix_automation_flows_org_updated", table_name="automation_flows")
    op.drop_table("automation_flows")
