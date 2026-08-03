"""Durable tenant-scoped Notification Center projection.

Revision ID: 0035_notification_center
Revises: 0034_reactivation_crm
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, uuid_binary
from app.models.notification import NOTIFICATION_TYPES

revision = "0035_notification_center"
down_revision = "0034_reactivation_crm"
branch_labels = None
depends_on = None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    args: dict[str, Any] = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        }
        if dialect == "mysql"
        else {}
    )
    op.create_table(
        "notifications",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("recipient_user_id", big_id(), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("contact_id", big_id(), nullable=True),
        sa.Column("reactivation_case_id", big_id(), nullable=True),
        sa.Column("task_id", big_id(), nullable=True),
        sa.Column("notification_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("dedup_key", sa.String(190), nullable=False),
        sa.Column("due_at", datetime6(), nullable=True),
        sa.Column("read_at", datetime6(), nullable=True),
        sa.Column("resolved_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_notifications_uuid"),
        sa.UniqueConstraint("organization_id", "dedup_key", name="uq_notifications_dedup"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reactivation_case_id"], ["reactivation_cases.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("notification_type", NOTIFICATION_TYPES), name="ck_notification_type"
        ),
        **args,
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["organization_id", "recipient_user_id", "read_at", "created_at"],
    )
    op.create_index(
        "ix_notifications_recipient_due_resolved",
        "notifications",
        ["organization_id", "recipient_user_id", "due_at", "resolved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_due_resolved", table_name="notifications")
    op.drop_index("ix_notifications_recipient_read_created", table_name="notifications")
    op.drop_table("notifications")
