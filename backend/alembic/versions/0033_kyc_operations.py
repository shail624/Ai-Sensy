"""CORE-04 governed KYC operations persistence gaps.

Revision ID: 0033_kyc_operations
Revises: 0032_vi_domain_foundation
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.vi_domain import KYC_DOCUMENT_PURPOSES, KYC_REJECTION_REASON_CODES

revision = "0033_kyc_operations"
down_revision = "0032_vi_domain_foundation"
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

    with op.batch_alter_table("kyc_decisions") as batch:
        batch.add_column(sa.Column("reason_code", sa.String(40), nullable=True))
        batch.create_check_constraint(
            "ck_kyc_decision_reason_code",
            f"reason_code IS NULL OR {_in('reason_code', KYC_REJECTION_REASON_CODES)}",
        )

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("reference_type", sa.String(24), nullable=True))
        batch.add_column(sa.Column("reference_id", big_id(), nullable=True))
        batch.add_column(sa.Column("idempotency_key", uuid_binary(), nullable=True))
        batch.add_column(sa.Column("request_hash", sa.String(64), nullable=True))
        batch.create_unique_constraint(
            "uq_tasks_idempotency", ["organization_id", "idempotency_key"]
        )
        batch.create_check_constraint(
            "ck_tasks_reference_pair",
            "(reference_type IS NULL AND reference_id IS NULL) OR "
            "(reference_type = 'kyc_case' AND reference_id IS NOT NULL)",
        )
        batch.create_index(
            "ix_tasks_organization_reference_status_due",
            ["organization_id", "reference_type", "reference_id", "status", "due_at"],
        )

    op.create_table(
        "kyc_document_references",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("kyc_case_id", big_id(), nullable=False),
        sa.Column("document_id", big_id(), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_kyc_document_references_uuid"),
        sa.UniqueConstraint("kyc_case_id", "purpose", name="uq_kyc_document_ref_purpose"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kyc_case_id"], ["kyc_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["contact_documents.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            _in("purpose", KYC_DOCUMENT_PURPOSES), name="ck_kyc_document_ref_purpose"
        ),
        **args,
    )
    op.create_index(
        "ix_kyc_document_ref_org_case",
        "kyc_document_references",
        ["organization_id", "kyc_case_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_kyc_document_ref_org_case", table_name="kyc_document_references")
    op.drop_table("kyc_document_references")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_organization_reference_status_due")
        batch.drop_constraint("ck_tasks_reference_pair", type_="check")
        batch.drop_constraint("uq_tasks_idempotency", type_="unique")
        batch.drop_column("request_hash")
        batch.drop_column("idempotency_key")
        batch.drop_column("reference_id")
        batch.drop_column("reference_type")
    with op.batch_alter_table("kyc_decisions") as batch:
        batch.drop_constraint("ck_kyc_decision_reason_code", type_="check")
        batch.drop_column("reason_code")
