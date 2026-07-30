"""Governed customer documents (Design Book 19, Phase 4A).

Creates the customer-document aggregate, immutable media-backed versions and lifecycle history.
The existing media and contact-event storage contracts are reused without alteration. Permission
insertion is idempotent; system-role realignment remains the deploy-time sync step.

Revision ID: 0028_contact_documents
Revises: 0027_analytics
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.contact_document import DOCUMENT_STATUSES, DOCUMENT_TYPES

revision = "0028_contact_documents"
down_revision = "0027_analytics"
branch_labels = None
depends_on = None

_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "documents:read",
        "resource": "documents",
        "action": "read",
        "description": "View customer documents, versions and verification history",
    },
    {
        "code": "documents:write",
        "resource": "documents",
        "action": "write",
        "description": "Create, version and archive customer documents",
    },
    {
        "code": "documents:verify",
        "resource": "documents",
        "action": "verify",
        "description": "Verify, reject and expire customer documents",
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
        "contact_documents",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("document_type", sa.String(24), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'submitted'")),
        sa.Column("expires_at", datetime6(), nullable=True),
        sa.Column("verified_at", datetime6(), nullable=True),
        sa.Column("verified_by", big_id(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("archived_at", datetime6(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_contact_documents_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_contact_documents_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_contact_documents_contact",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in_clause("document_type", DOCUMENT_TYPES), name="ck_contact_documents_type"
        ),
        sa.CheckConstraint(
            _in_clause("status", DOCUMENT_STATUSES), name="ck_contact_documents_status"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_contact_documents_org_contact_updated",
        "contact_documents",
        ["organization_id", "contact_id", "updated_at"],
    )
    op.create_index(
        "ix_contact_documents_org_status_expiry",
        "contact_documents",
        ["organization_id", "status", "expires_at"],
    )

    op.create_table(
        "contact_document_versions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("document_id", big_id(), nullable=False),
        sa.Column("version_no", int_id(), nullable=False),
        sa.Column("media_asset_id", big_id(), nullable=False),
        sa.Column("uploaded_by", big_id(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_contact_document_versions_uuid"),
        sa.UniqueConstraint("document_id", "version_no", name="uq_contact_document_version_no"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["contact_documents.id"],
            name="fk_contact_document_versions_doc",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_contact_document_versions_media",
            ondelete="RESTRICT",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_contact_document_versions_document_created",
        "contact_document_versions",
        ["document_id", "created_at"],
    )

    op.create_table(
        "contact_document_events",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("document_id", big_id(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("from_json", sa.JSON(), nullable=True),
        sa.Column("to_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["contact_documents.id"],
            name="fk_contact_document_events_doc",
            ondelete="CASCADE",
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_contact_document_events_document_created",
        "contact_document_events",
        ["document_id", "created_at"],
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
        "ix_contact_document_events_document_created", table_name="contact_document_events"
    )
    op.drop_table("contact_document_events")
    op.drop_index(
        "ix_contact_document_versions_document_created", table_name="contact_document_versions"
    )
    op.drop_table("contact_document_versions")
    op.drop_index("ix_contact_documents_org_status_expiry", table_name="contact_documents")
    op.drop_index("ix_contact_documents_org_contact_updated", table_name="contact_documents")
    op.drop_table("contact_documents")
