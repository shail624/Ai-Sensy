"""Tags, contact events & lead pipelines (Module 2 — Doc 03 §6.2/§6.5, Doc 07 §23.2).

**Expand** phase: creates ``tags``, ``contact_tags``, ``contact_events`` (monthly RANGE
partitioning on MySQL, Doc 03 §6.5), ``lead_pipelines`` and ``lead_stages``. Additive and
reversible. No data seeded — the default pipeline is provisioned by the bootstrap routine.

Revision ID: 0006_tags_events_leads
Revises: 0005_contacts
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary

revision = "0006_tags_events_leads"
down_revision = "0005_contacts"
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

    # --- tags (Doc 03 §6.2) ------------------------------------------------
    op.create_table(
        "tags",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("color", sa.CHAR(7), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("usage_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_tags_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_tags_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("uq_tags_org_name", "tags", ["organization_id", "name"], unique=True)

    # --- contact_tags (Doc 03 §6.2) ---------------------------------------
    op.create_table(
        "contact_tags",
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("tag_id", big_id(), nullable=False),
        sa.Column("tagged_at", datetime6(), nullable=False, server_default=created),
        sa.Column("tagged_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("contact_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name="fk_ct_contact", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], name="fk_ct_tag", ondelete="CASCADE"),
        **mysql_args,
    )
    op.create_index("ix_ct_tag", "contact_tags", ["tag_id", "contact_id"])

    # --- contact_events (Doc 03 §6.5) — partitioned on MySQL, no DB FK -----
    event_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("ref_type", sa.String(24), nullable=True),
        sa.Column("ref_id", big_id(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
    ]
    if dialect == "mysql":
        op.create_table(
            "contact_events",
            *event_columns,
            sa.PrimaryKeyConstraint("id", "created_at"),
            **mysql_args,
        )
    else:
        op.create_table("contact_events", *event_columns, sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_cevents_contact", "contact_events", ["contact_id", "created_at"])
    op.create_index(
        "ix_cevents_org_type", "contact_events", ["organization_id", "event_type", "created_at"]
    )
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE contact_events PARTITION BY RANGE COLUMNS (created_at) ("
            "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
            "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
            "PARTITION pmax VALUES LESS THAN (MAXVALUE))"
        )

    # --- lead_pipelines (Doc 07 §23.2) ------------------------------------
    op.create_table(
        "lead_pipelines",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_lead_pipelines_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_pipelines_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_lead_pipelines_org_name", "lead_pipelines", ["organization_id", "name"], unique=True
    )

    # --- lead_stages (Doc 07 §23.2) ---------------------------------------
    op.create_table(
        "lead_stages",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("pipeline_id", big_id(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_lead_stages_uuid"),
        sa.ForeignKeyConstraint(
            ["pipeline_id"], ["lead_pipelines.id"], name="fk_stages_pipeline", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index(
        "uq_lead_stages_pipeline_name", "lead_stages", ["pipeline_id", "name"], unique=True
    )
    op.create_index(
        "ix_lead_stages_pipeline_position", "lead_stages", ["pipeline_id", "position"]
    )


def downgrade() -> None:
    op.drop_index("ix_lead_stages_pipeline_position", table_name="lead_stages")
    op.drop_index("uq_lead_stages_pipeline_name", table_name="lead_stages")
    op.drop_table("lead_stages")
    op.drop_index("uq_lead_pipelines_org_name", table_name="lead_pipelines")
    op.drop_table("lead_pipelines")
    op.drop_index("ix_cevents_org_type", table_name="contact_events")
    op.drop_index("ix_cevents_contact", table_name="contact_events")
    op.drop_table("contact_events")
    op.drop_index("ix_ct_tag", table_name="contact_tags")
    op.drop_table("contact_tags")
    op.drop_index("uq_tags_org_name", table_name="tags")
    op.drop_table("tags")
