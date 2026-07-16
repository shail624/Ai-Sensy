"""Segments & segment rules (Module 2 — Doc 03 §6.4).

**Expand** phase: creates ``segments`` (saved dynamic filters) and ``segment_rules`` (the
normalized rule tree). Additive and reversible.

Revision ID: 0007_segments
Revises: 0006_tags_events_leads
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary

revision = "0007_segments"
down_revision = "0006_tags_events_leads"
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
        "segments",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("match_type", sa.String(8), nullable=False, server_default=sa.text("'all'")),
        sa.Column("compiled_json", sa.JSON(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("cached_count", int_id(), nullable=True),
        sa.Column("last_evaluated_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_segments_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_segments_org", ondelete="CASCADE"
        ),
        sa.CheckConstraint("match_type IN ('all','any')", name="ck_segments_match"),
        **mysql_args,
    )
    op.create_index("uq_segments_org_name", "segments", ["organization_id", "name"], unique=True)

    op.create_table(
        "segment_rules",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("segment_id", big_id(), nullable=False),
        sa.Column("group_index", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("field_source", sa.String(24), nullable=False),
        sa.Column("field_key", sa.String(60), nullable=False),
        sa.Column("operator", sa.String(24), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["segment_id"], ["segments.id"], name="fk_segrules_segment", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "field_source IN ('contact','attribute','tag','engagement')",
            name="ck_segrules_source",
        ),
        **mysql_args,
    )
    op.create_index("ix_segrules_segment", "segment_rules", ["segment_id", "group_index"])


def downgrade() -> None:
    op.drop_index("ix_segrules_segment", table_name="segment_rules")
    op.drop_table("segment_rules")
    op.drop_index("uq_segments_org_name", table_name="segments")
    op.drop_table("segments")
