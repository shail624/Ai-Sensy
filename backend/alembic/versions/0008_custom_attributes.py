"""Custom attributes (Module 2 — Doc 03 §6.3).

**Expand** phase: creates ``custom_attribute_definitions`` and the typed EAV table
``contact_attribute_values``. Additive and reversible. The string value index uses a MySQL
prefix length (VARCHAR(1024) cannot be fully indexed); SQLite indexes the column plainly.

Revision ID: 0008_custom_attributes
Revises: 0007_segments
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary

revision = "0008_custom_attributes"
down_revision = "0007_segments"
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
        "custom_attribute_definitions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("key_name", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("data_type", sa.String(16), nullable=False),
        sa.Column("enum_values_json", sa.JSON(), nullable=True),
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_pii", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_cad_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_cad_org", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "data_type IN ('string','number','datetime','boolean','enum')", name="ck_cad_type"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_cad_org_key", "custom_attribute_definitions", ["organization_id", "key_name"],
        unique=True,
    )

    op.create_table(
        "contact_attribute_values",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("attribute_id", big_id(), nullable=False),
        sa.Column("value_string", sa.String(1024), nullable=True),
        sa.Column("value_number", sa.Numeric(20, 6), nullable=True),
        sa.Column("value_datetime", datetime6(), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name="fk_cav_contact", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["custom_attribute_definitions.id"],
            name="fk_cav_attr",
            ondelete="CASCADE",
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_cav_contact_attr", "contact_attribute_values", ["contact_id", "attribute_id"],
        unique=True,
    )
    op.create_index(
        "ix_cav_attr_string",
        "contact_attribute_values",
        ["attribute_id", "value_string"],
        mysql_length={"value_string": 191},
    )
    op.create_index(
        "ix_cav_attr_number", "contact_attribute_values", ["attribute_id", "value_number"]
    )
    op.create_index(
        "ix_cav_attr_datetime", "contact_attribute_values", ["attribute_id", "value_datetime"]
    )


def downgrade() -> None:
    for index in (
        "ix_cav_attr_datetime",
        "ix_cav_attr_number",
        "ix_cav_attr_string",
        "uq_cav_contact_attr",
    ):
        op.drop_index(index, table_name="contact_attribute_values")
    op.drop_table("contact_attribute_values")
    op.drop_index("uq_cad_org_key", table_name="custom_attribute_definitions")
    op.drop_table("custom_attribute_definitions")
