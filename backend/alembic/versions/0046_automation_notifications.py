"""Automation attention deliveries in the existing Notification Center.

Revision ID: 0046_automation_notifications
Revises: 0045_automation_live_conditions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.notification import (
    NOTIFICATION_AUTOMATION_ATTENTION,
    NOTIFICATION_TYPES,
)

revision = "0046_automation_notifications"
down_revision = "0045_automation_live_conditions"
branch_labels = None
depends_on = None


def _in_clause(values: tuple[str, ...]) -> str:
    return "notification_type IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notification_type", type_="check")
        batch.create_check_constraint("ck_notification_type", _in_clause(NOTIFICATION_TYPES))


def downgrade() -> None:
    notifications = sa.table("notifications", sa.column("notification_type", sa.String))
    op.execute(
        notifications.delete().where(
            notifications.c.notification_type == NOTIFICATION_AUTOMATION_ATTENTION
        )
    )
    legacy_types = tuple(
        value for value in NOTIFICATION_TYPES if value != NOTIFICATION_AUTOMATION_ATTENTION
    )
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notification_type", type_="check")
        batch.create_check_constraint("ck_notification_type", _in_clause(legacy_types))
