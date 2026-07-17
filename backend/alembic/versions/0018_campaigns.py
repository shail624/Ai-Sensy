"""Campaign registry: campaigns & recipients (Phase 6 Step 1 — Doc 03 §8.1/§8.3).

**Expand** phase: creates ``campaigns`` and ``campaign_recipients``. Additive and reversible.

``campaign_recipients`` is a 100M+ table, partitioned monthly on MySQL, so it takes the composite
``(id, created_at)`` primary key that requires — which is also why its uniqueness key spans
``created_at`` (Doc 03 §8.3) and why it carries no foreign keys.

Revision ID: 0018_campaigns
Revises: 0017_message_templates
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, small_uint, uuid_binary

revision = "0018_campaigns"
down_revision = "0017_message_templates"
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
        "campaigns",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("phone_number_id", big_id(), nullable=False),
        sa.Column("template_id", big_id(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("audience_type", sa.String(16), nullable=False),
        sa.Column("audience_ref_json", sa.JSON(), nullable=True),
        sa.Column("variable_map_json", sa.JSON(), nullable=True),
        sa.Column("total_recipients", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("queued_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("delivered_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("read_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("replied_count", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("estimated_cost", sa.Numeric(14, 4), nullable=True),
        sa.Column("actual_cost", sa.Numeric(14, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_currency", sa.CHAR(3), nullable=True),
        sa.Column("send_rate_mps", small_uint(), nullable=True),
        sa.Column("started_at", datetime6(), nullable=True),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_campaigns_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_campaigns_org", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["phone_number_id"],
            ["phone_numbers.id"],
            name="fk_campaigns_number",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["message_templates.id"],
            name="fk_campaigns_template",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('draft','scheduled','queued','running','paused','completed',"
            "'cancelled','failed')",
            name="ck_campaigns_status",
        ),
        sa.CheckConstraint(
            "audience_type IN ('segment','tag','list','upload')", name="ck_campaigns_audience"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_campaigns_org_status", "campaigns", ["organization_id", "status", "created_at"]
    )
    op.create_index("ix_campaigns_template", "campaigns", ["template_id"])
    op.create_index("ix_campaigns_number", "campaigns", ["phone_number_id"])

    recipient_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("message_id", big_id(), nullable=True),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("variables_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(24), nullable=True),
        sa.Column("error_detail", sa.String(512), nullable=True),
        sa.Column("retry_count", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_amount", sa.Numeric(12, 6), nullable=True),
        sa.Column("batch_id", big_id(), nullable=True),
        sa.Column("queued_at", datetime6(), nullable=True),
        sa.Column("sent_at", datetime6(), nullable=True),
        sa.Column("delivered_at", datetime6(), nullable=True),
        sa.Column("read_at", datetime6(), nullable=True),
        sa.Column("failed_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
    ]
    if dialect == "mysql":
        op.create_table(
            "campaign_recipients",
            *recipient_columns,
            sa.PrimaryKeyConstraint("id", "created_at"),
            **mysql_args,
        )
        # The partition column must be part of every unique key (Doc 03 §8.3).
        op.create_index(
            "uq_crecip_campaign_contact",
            "campaign_recipients",
            ["campaign_id", "contact_id", "created_at"],
            unique=True,
        )
    else:
        op.create_table(
            "campaign_recipients", *recipient_columns, sa.PrimaryKeyConstraint("id")
        )
        op.create_index(
            "uq_crecip_campaign_contact",
            "campaign_recipients",
            ["campaign_id", "contact_id"],
            unique=True,
        )
    op.create_index(
        "ix_crecip_campaign_status", "campaign_recipients", ["campaign_id", "status"]
    )
    op.create_index("ix_crecip_status_created", "campaign_recipients", ["status", "created_at"])
    op.create_index("ix_crecip_wamid", "campaign_recipients", ["wamid"])
    op.create_index("ix_crecip_batch", "campaign_recipients", ["batch_id"])
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE campaign_recipients PARTITION BY RANGE COLUMNS (created_at) ("
            "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
            "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
            "PARTITION pmax VALUES LESS THAN (MAXVALUE))"
        )


def downgrade() -> None:
    for index in (
        "ix_crecip_batch",
        "ix_crecip_wamid",
        "ix_crecip_status_created",
        "ix_crecip_campaign_status",
        "uq_crecip_campaign_contact",
    ):
        op.drop_index(index, table_name="campaign_recipients")
    op.drop_table("campaign_recipients")
    op.drop_index("ix_campaigns_number", table_name="campaigns")
    op.drop_index("ix_campaigns_template", table_name="campaigns")
    op.drop_index("ix_campaigns_org_status", table_name="campaigns")
    op.drop_table("campaigns")
