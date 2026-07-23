"""Task & Activity Management (Doc 14 — CRM Follow-up Engine).

**Expand** phase: creates ``tasks`` and ``task_events`` and inserts the three new task
permissions. Additive and reversible; no existing table is touched. Timeline reuse needs no
DDL — task lifecycle projects onto the existing partitioned ``contact_events`` via new
``event_type`` string constants only (Doc 14 §5.3).

The permission insert is **idempotent** (guarded by a code existence check): on a fresh migrate
the dynamic catalog seed (0002) already inserted them, so this skips; on an existing database it
adds the three rows. Role realignment is the idempotent deploy-time ``sync_system_roles`` step
(Doc 12 §58), not this migration.

NOTE: filename is ``0024_tasks.py`` for delete-restriction reasons in the authoring
environment; the authoritative revision id below is ``0026_tasks`` (Alembic keys off the
in-file id, not the filename). Rename the file to ``0026_tasks.py`` when convenient — cosmetic
only, no content change.

Revision ID: 0026_tasks
Revises: 0025_conversation_tags
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.task import TASK_PRIORITIES, TASK_STATUSES, TASK_TYPES

revision = "0026_tasks"
down_revision = "0025_conversation_tags"
branch_labels = None
depends_on = None

# Static snapshot of the permissions this revision introduces (Doc 14 §6).
_NEW_PERMISSIONS: list[dict[str, str]] = [
    {
        "code": "tasks:read",
        "resource": "tasks",
        "action": "read",
        "description": "View tasks, work queue, history and stats",
    },
    {
        "code": "tasks:write",
        "resource": "tasks",
        "action": "write",
        "description": "Create and edit tasks; complete/skip/cancel/reopen/reschedule",
    },
    {
        "code": "tasks:assign",
        "resource": "tasks",
        "action": "assign",
        "description": "Assign or reassign a task to another agent",
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
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    op.create_table(
        "tasks",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("conversation_id", big_id(), nullable=True),
        sa.Column("assigned_agent_id", big_id(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("priority", sa.String(12), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("due_at", datetime6(), nullable=False),
        sa.Column("has_time", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("reminder_at", datetime6(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.Column("completed_by", big_id(), nullable=True),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_tasks_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_tasks_organization_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name="fk_tasks_contact_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name="fk_tasks_conversation_id", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"], ["users.id"],
            name="fk_tasks_assigned_agent_id", ondelete="RESTRICT",
        ),
        sa.CheckConstraint(_in_clause("task_type", TASK_TYPES), name="ck_tasks_task_type"),
        sa.CheckConstraint(_in_clause("status", TASK_STATUSES), name="ck_tasks_status"),
        sa.CheckConstraint(_in_clause("priority", TASK_PRIORITIES), name="ck_tasks_priority"),
        **mysql_args,
    )
    op.create_index(
        "ix_tasks_organization_id_assigned_agent_id_status_due_at",
        "tasks",
        ["organization_id", "assigned_agent_id", "status", "due_at"],
    )
    op.create_index(
        "ix_tasks_organization_id_status_due_at",
        "tasks",
        ["organization_id", "status", "due_at"],
    )
    op.create_index(
        "ix_tasks_organization_id_contact_id_created_at",
        "tasks",
        ["organization_id", "contact_id", "created_at"],
    )
    op.create_index(
        "ix_tasks_organization_id_conversation_id",
        "tasks",
        ["organization_id", "conversation_id"],
    )
    op.create_index(
        "ix_tasks_organization_id_created_by_status",
        "tasks",
        ["organization_id", "created_by", "status"],
    )

    op.create_table(
        "task_events",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("task_id", big_id(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("from_json", sa.JSON(), nullable=True),
        sa.Column("to_json", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name="fk_task_events_task_id", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index(
        "ix_task_events_task_id_created_at", "task_events", ["task_id", "created_at"]
    )

    # Idempotent permission insert (Doc 14 §6; governance Doc 12 §58).
    bind = op.get_bind()
    existing = set(bind.execute(sa.text("SELECT code FROM permissions")).scalars().all())
    missing = [row for row in _NEW_PERMISSIONS if row["code"] not in existing]
    if missing:
        op.bulk_insert(_permissions, missing)


def downgrade() -> None:
    codes = [row["code"] for row in _NEW_PERMISSIONS]
    op.execute(_permissions.delete().where(_permissions.c.code.in_(codes)))
    op.drop_index("ix_task_events_task_id_created_at", table_name="task_events")
    op.drop_table("task_events")
    for index_name in (
        "ix_tasks_organization_id_created_by_status",
        "ix_tasks_organization_id_conversation_id",
        "ix_tasks_organization_id_contact_id_created_at",
        "ix_tasks_organization_id_status_due_at",
        "ix_tasks_organization_id_assigned_agent_id_status_due_at",
    ):
        op.drop_index(index_name, table_name="tasks")
    op.drop_table("tasks")
