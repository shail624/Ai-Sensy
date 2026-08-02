"""CORE-02 tenant-scoped Vi domain foundation.

Revision ID: 0032_vi_domain_foundation
Revises: 0031_automation_trigger_receipts
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.vi_domain import (
    ACTIVATION_STATUSES,
    ELIGIBILITY_SOURCES,
    ELIGIBILITY_STATUSES,
    KYC_DECISION_TYPES,
    KYC_DECISIONS,
    KYC_STATUSES,
    REACTIVATION_STAGES,
    SIM_ORDER_STATUSES,
    SLA_DOMAINS,
    SLA_ENTITY_TYPES,
    SLA_EVENT_TYPES,
)

revision = "0032_vi_domain_foundation"
down_revision = "0031_automation_trigger_receipts"
branch_labels = None
depends_on = None

_PERMISSIONS = [
    ("reactivation:read", "View tenant reactivation cases and immutable history"),
    ("reactivation:write", "Create and update reactivation cases and ownership"),
    ("reactivation:transition", "Record eligibility and transition reactivation stages"),
    ("kyc:read", "View tenant KYC cases and immutable decisions"),
    ("kyc:write", "Create and update KYC case preparation"),
    ("kyc:decide", "Record KYC review decisions"),
    ("kyc:approve", "Record manager KYC approvals"),
    ("sim:read", "View tenant SIM orders and immutable fulfilment events"),
    ("sim:write", "Create and prepare SIM orders"),
    ("sim:manage", "Approve and transition SIM fulfilment"),
    ("activation:read", "View tenant activation records"),
    ("activation:write", "Create and prepare activation records"),
    ("activation:approve", "Approve and complete activations"),
    ("sla:read", "View tenant Vi SLA policies and events"),
    ("sla:manage", "Manage tenant Vi SLA policies and record events"),
]
_EVENT_TYPES = [
    ("reactivation.case.created", "lead", "reactivation_case"),
    ("reactivation.stage.transitioned", "lead", "reactivation_case"),
    ("reactivation.eligibility.decided", "lead", "reactivation_case"),
    ("kyc.decision.recorded", "kyc", "kyc_case"),
    ("sim.order.transitioned", "sim", "sim_order"),
    ("sim.activation.transitioned", "sim", "activation_record"),
    ("audit.sla.recorded", "audit", "sla_event"),
]


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
        "reactivation_cases",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False, server_default=sa.text("'new_lead'")),
        sa.Column("owner_user_id", big_id(), nullable=True),
        sa.Column("previous_vi_number", sa.String(24), nullable=True),
        sa.Column("active_delhi_number", sa.String(24), nullable=True),
        sa.Column("source", sa.String(40), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_reactivation_cases_uuid"),
        sa.UniqueConstraint("organization_id", "contact_id", name="uq_reactivation_org_contact"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_reactivation_idem"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(_in("stage", REACTIVATION_STAGES), name="ck_reactivation_stage"),
        **args,
    )
    op.create_index(
        "ix_reactivation_org_stage_updated",
        "reactivation_cases",
        ["organization_id", "stage", "updated_at"],
    )

    op.create_table(
        "reactivation_stage_events",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("case_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("from_stage", sa.String(32), nullable=True),
        sa.Column("to_stage", sa.String(32), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_reactivation_stage_events_uuid"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_reactivation_stage_idem"
        ),
        sa.ForeignKeyConstraint(["case_id"], ["reactivation_cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("to_stage", REACTIVATION_STAGES), name="ck_reactivation_event_to"),
        sa.CheckConstraint(
            f"from_stage IS NULL OR {_in('from_stage', REACTIVATION_STAGES)}",
            name="ck_reactivation_event_from",
        ),
        **args,
    )
    op.create_index(
        "ix_reactivation_stage_case_created", "reactivation_stage_events", ["case_id", "created_at"]
    )

    op.create_table(
        "eligibility_checks",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("case_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approval_reference", sa.String(120), nullable=True),
        sa.Column("checked_by", big_id(), nullable=True),
        sa.Column("checked_at", datetime6(), nullable=False, server_default=now),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_eligibility_checks_uuid"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_eligibility_idem"),
        sa.ForeignKeyConstraint(["case_id"], ["reactivation_cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("status", ELIGIBILITY_STATUSES), name="ck_eligibility_status"),
        sa.CheckConstraint(_in("source", ELIGIBILITY_SOURCES), name="ck_eligibility_source"),
        sa.CheckConstraint(
            "source != 'override' OR approval_reference IS NOT NULL",
            name="ck_eligibility_override_approval",
        ),
        **args,
    )
    op.create_index("ix_eligibility_case_created", "eligibility_checks", ["case_id", "created_at"])

    op.create_table(
        "kyc_cases",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("reactivation_case_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("owner_user_id", big_id(), nullable=True),
        sa.Column("holder_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "delhi_presence_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "active_delhi_number_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("appointment_at", datetime6(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_kyc_cases_uuid"),
        sa.UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_kyc_reactivation_case"
        ),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_kyc_idem"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reactivation_case_id"], ["reactivation_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("status", KYC_STATUSES), name="ck_kyc_status"),
        **args,
    )
    op.create_index(
        "ix_kyc_org_status_updated", "kyc_cases", ["organization_id", "status", "updated_at"]
    )

    op.create_table(
        "kyc_decisions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("kyc_case_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("decision_type", sa.String(24), nullable=False),
        sa.Column("decision", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_by", big_id(), nullable=True),
        sa.Column("decided_at", datetime6(), nullable=False, server_default=now),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_kyc_decisions_uuid"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_kyc_decision_idem"),
        sa.ForeignKeyConstraint(["kyc_case_id"], ["kyc_cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("decision_type", KYC_DECISION_TYPES), name="ck_kyc_decision_type"),
        sa.CheckConstraint(_in("decision", KYC_DECISIONS), name="ck_kyc_decision_value"),
        **args,
    )
    op.create_index("ix_kyc_decision_case_created", "kyc_decisions", ["kyc_case_id", "created_at"])

    op.create_table(
        "sim_orders",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("reactivation_case_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'requested'")),
        sa.Column("delivery_address", sa.Text(), nullable=False),
        sa.Column(
            "service_area", sa.String(80), nullable=False, server_default=sa.text("'Delhi NCR'")
        ),
        sa.Column("delivery_owner_user_id", big_id(), nullable=True),
        sa.Column("dispatched_at", datetime6(), nullable=True),
        sa.Column("delivered_at", datetime6(), nullable=True),
        sa.Column("failed_at", datetime6(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("sim_serial", sa.String(64), nullable=True),
        sa.Column("customer_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_sim_orders_uuid"),
        sa.UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_sim_reactivation_case"
        ),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_sim_order_idem"),
        sa.UniqueConstraint("organization_id", "sim_serial", name="uq_sim_order_serial"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reactivation_case_id"], ["reactivation_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("status", SIM_ORDER_STATUSES), name="ck_sim_order_status"),
        **args,
    )
    op.create_index(
        "ix_sim_order_org_status_updated", "sim_orders", ["organization_id", "status", "updated_at"]
    )

    op.create_table(
        "sim_order_events",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("sim_order_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_sim_order_events_uuid"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_sim_order_event_idem"),
        sa.ForeignKeyConstraint(["sim_order_id"], ["sim_orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("to_status", SIM_ORDER_STATUSES), name="ck_sim_event_status"),
        sa.CheckConstraint(
            f"from_status IS NULL OR {_in('from_status', SIM_ORDER_STATUSES)}",
            name="ck_sim_event_from",
        ),
        **args,
    )
    op.create_index(
        "ix_sim_order_event_order_created", "sim_order_events", ["sim_order_id", "created_at"]
    )

    op.create_table(
        "activation_records",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("reactivation_case_id", big_id(), nullable=False),
        sa.Column("sim_order_id", big_id(), nullable=True),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("owner_user_id", big_id(), nullable=True),
        sa.Column("approval_reference", sa.String(120), nullable=True),
        sa.Column("approved_by", big_id(), nullable=True),
        sa.Column("approved_at", datetime6(), nullable=True),
        sa.Column("completed_at", datetime6(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_activation_records_uuid"),
        sa.UniqueConstraint(
            "organization_id", "reactivation_case_id", name="uq_activation_reactivation_case"
        ),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_activation_idem"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reactivation_case_id"], ["reactivation_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sim_order_id"], ["sim_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("status", ACTIVATION_STATUSES), name="ck_activation_status"),
        **args,
    )
    op.create_index(
        "ix_activation_org_status_updated",
        "activation_records",
        ["organization_id", "status", "updated_at"],
    )

    op.create_table(
        "sla_policies",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("domain", sa.String(24), nullable=False),
        sa.Column("trigger_name", sa.String(64), nullable=False),
        sa.Column("target_minutes", int_id(), nullable=False),
        sa.Column("escalation_minutes", int_id(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_sla_policies_uuid"),
        sa.UniqueConstraint(
            "organization_id", "domain", "trigger_name", name="uq_sla_policy_scope"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.CheckConstraint(_in("domain", SLA_DOMAINS), name="ck_sla_policy_domain"),
        sa.CheckConstraint("target_minutes > 0", name="ck_sla_target_positive"),
        sa.CheckConstraint("escalation_minutes >= target_minutes", name="ck_sla_escalation_order"),
        **args,
    )
    op.create_index("ix_sla_policy_org_active", "sla_policies", ["organization_id", "is_active"])

    op.create_table(
        "sla_events",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("policy_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", big_id(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("due_at", datetime6(), nullable=False),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", uuid_binary(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_sla_events_uuid"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_sla_event_idem"),
        sa.ForeignKeyConstraint(["policy_id"], ["sla_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("entity_type", SLA_ENTITY_TYPES), name="ck_sla_entity_type"),
        sa.CheckConstraint(_in("event_type", SLA_EVENT_TYPES), name="ck_sla_event_type"),
        **args,
    )
    op.create_index(
        "ix_sla_event_entity_created", "sla_events", ["entity_type", "entity_id", "created_at"]
    )
    op.create_index(
        "ix_sla_event_org_type_due", "sla_events", ["organization_id", "event_type", "due_at"]
    )

    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    bind = op.get_bind()
    existing_permissions = set(
        bind.execute(sa.text("SELECT code FROM permissions")).scalars().all()
    )
    op.bulk_insert(
        permissions,
        [
            {
                "code": code,
                "resource": code.split(":", 1)[0],
                "action": code.split(":", 1)[1],
                "description": description,
            }
            for code, description in _PERMISSIONS
            if code not in existing_permissions
        ],
    )
    event_types = sa.table(
        "business_event_types",
        sa.column("event_type", sa.String),
        sa.column("event_version", sa.SmallInteger),
        sa.column("category", sa.String),
        sa.column("subject_type", sa.String),
        sa.column("description", sa.String),
        sa.column("schema_ref", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    existing_events = set(
        bind.execute(sa.text("SELECT event_type FROM business_event_types WHERE event_version = 1"))
        .scalars()
        .all()
    )
    op.bulk_insert(
        event_types,
        [
            {
                "event_type": name,
                "event_version": 1,
                "category": category,
                "subject_type": subject,
                "description": f"CORE-02 {name} domain fact.",
                "schema_ref": f"internal://events/{name}/v1",
                "is_active": True,
            }
            for name, category, subject in _EVENT_TYPES
            if name not in existing_events
        ],
    )


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String))
    event_types = sa.table("business_event_types", sa.column("event_type", sa.String))
    op.execute(
        event_types.delete().where(event_types.c.event_type.in_([row[0] for row in _EVENT_TYPES]))
    )
    op.execute(permissions.delete().where(permissions.c.code.in_([row[0] for row in _PERMISSIONS])))
    for table, indexes in (
        ("sla_events", ["ix_sla_event_org_type_due", "ix_sla_event_entity_created"]),
        ("sla_policies", ["ix_sla_policy_org_active"]),
        ("activation_records", ["ix_activation_org_status_updated"]),
        ("sim_order_events", ["ix_sim_order_event_order_created"]),
        ("sim_orders", ["ix_sim_order_org_status_updated"]),
        ("kyc_decisions", ["ix_kyc_decision_case_created"]),
        ("kyc_cases", ["ix_kyc_org_status_updated"]),
        ("eligibility_checks", ["ix_eligibility_case_created"]),
        ("reactivation_stage_events", ["ix_reactivation_stage_case_created"]),
        ("reactivation_cases", ["ix_reactivation_org_stage_updated"]),
    ):
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
