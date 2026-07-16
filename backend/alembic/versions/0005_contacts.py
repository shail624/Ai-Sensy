"""Contacts (Module 2 — Doc 03 §6.1).

**Expand** phase: creates the ``contacts`` table with its dedup unique key, segmentation/
search indexes, opt-in CHECK constraint, and org foreign key. Additive and reversible.

Revision ID: 0005_contacts
Revises: 0004_api_keys
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0005_contacts"
down_revision = "0004_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    created = (
        sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    )
    updated = (
        sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)")
        if dialect == "mysql"
        else sa.text("CURRENT_TIMESTAMP")
    )
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "contacts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("wa_id", sa.String(24), nullable=False),
        sa.Column("phone_e164", sa.String(24), nullable=False),
        sa.Column("country_code", sa.CHAR(2), nullable=True),
        sa.Column("full_name", sa.String(160), nullable=True),
        sa.Column("first_name", sa.String(80), nullable=True),
        sa.Column("last_name", sa.String(80), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("locale", sa.String(10), nullable=True),
        sa.Column("profile_name", sa.String(160), nullable=True),
        sa.Column(
            "opt_in_status", sa.String(16), nullable=False, server_default=sa.text("'unknown'")
        ),
        sa.Column("opt_in_at", datetime6(), nullable=True),
        sa.Column("opt_out_at", datetime6(), nullable=True),
        sa.Column("is_active_on_wa", sa.Boolean(), nullable=True),
        sa.Column("last_inbound_at", datetime6(), nullable=True),
        sa.Column("last_outbound_at", datetime6(), nullable=True),
        sa.Column("last_contacted_at", datetime6(), nullable=True),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column("attributes_cache", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_contacts_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_contacts_org", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "opt_in_status IN ('unknown','opted_in','opted_out')", name="ck_contacts_optin"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_contacts_org_waid", "contacts", ["organization_id", "wa_id"], unique=True
    )
    op.create_index("ix_contacts_org_created", "contacts", ["organization_id", "created_at"])
    op.create_index("ix_contacts_org_optin", "contacts", ["organization_id", "opt_in_status"])
    op.create_index("ix_contacts_last_inbound", "contacts", ["organization_id", "last_inbound_at"])
    op.create_index("ix_contacts_email", "contacts", ["email"])
    op.create_index("ix_contacts_name", "contacts", ["organization_id", "full_name"])


def downgrade() -> None:
    for index in (
        "ix_contacts_name",
        "ix_contacts_email",
        "ix_contacts_last_inbound",
        "ix_contacts_org_optin",
        "ix_contacts_org_created",
        "uq_contacts_org_waid",
    ):
        op.drop_index(index, table_name="contacts")
    op.drop_table("contacts")
