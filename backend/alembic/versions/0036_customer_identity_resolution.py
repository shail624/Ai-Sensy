"""Provider-independent Customer identity resolution records.

Revision ID: 0036_customer_identity_resolution
Revises: 0035_notification_center
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

from app.db.types import big_id, datetime6, int_id, uuid_binary
from app.models.contact_identity import (
    IDENTITY_CONFIDENCES,
    IDENTITY_CONFLICT_STATUSES,
    IDENTITY_KINDS,
    IDENTITY_RECOMMENDATION_STATUSES,
    IDENTITY_SOURCES,
)

revision = "0036_customer_identity_resolution"
down_revision = "0035_notification_center"
branch_labels = None
depends_on = None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _table_args(dialect: str) -> dict[str, Any]:
    if dialect != "mysql":
        return {}
    return {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    now = sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")
    args = _table_args(dialect)

    op.create_table(
        "contact_identities",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("contact_id", big_id(), nullable=False),
        sa.Column("identity_namespace", sa.String(64), nullable=False),
        sa.Column("identity_scope", sa.String(190), nullable=False),
        sa.Column("normalized_value", sa.String(190), nullable=False),
        sa.Column("identity_kind", sa.String(16), nullable=False),
        sa.Column("connector_type", sa.String(64), nullable=True),
        sa.Column("connection_ref", sa.String(120), nullable=True),
        sa.Column("endpoint_ref", sa.String(120), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("verified_at", datetime6(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_contact_identities_uuid"),
        sa.UniqueConstraint(
            "organization_id",
            "identity_namespace",
            "identity_scope",
            "normalized_value",
            name="uq_contact_identity_exact_key",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_in("identity_kind", IDENTITY_KINDS), name="ck_identity_kind"),
        sa.CheckConstraint(_in("confidence", IDENTITY_CONFIDENCES), name="ck_identity_confidence"),
        sa.CheckConstraint(_in("source", IDENTITY_SOURCES), name="ck_identity_source"),
        **args,
    )
    op.create_index(
        "ix_contact_identities_org_contact_created",
        "contact_identities",
        ["organization_id", "contact_id", "created_at"],
    )
    op.create_index(
        "ix_contact_identities_org_endpoint",
        "contact_identities",
        ["organization_id", "connection_ref", "endpoint_ref"],
    )

    op.create_table(
        "identity_conflicts",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("assertion_keys_json", sa.JSON(), nullable=False),
        sa.Column("candidate_contact_ids_json", sa.JSON(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("detected_at", datetime6(), nullable=False, server_default=now),
        sa.Column("decision_at", datetime6(), nullable=True),
        sa.Column("decision_by", big_id(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_identity_conflicts_uuid"),
        sa.UniqueConstraint(
            "organization_id", "fingerprint", name="uq_identity_conflict_fingerprint"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("status", IDENTITY_CONFLICT_STATUSES), name="ck_identity_conflict_status"
        ),
        sa.CheckConstraint(
            _in("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_conflict_confidence",
        ),
        **args,
    )
    op.create_index(
        "ix_identity_conflicts_org_status_created",
        "identity_conflicts",
        ["organization_id", "status", "created_at"],
    )

    op.create_table(
        "identity_merge_recommendations",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("conflict_id", big_id(), nullable=False),
        sa.Column("primary_contact_id", big_id(), nullable=False),
        sa.Column("duplicate_contact_id", big_id(), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decided_at", datetime6(), nullable=True),
        sa.Column("decided_by", big_id(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=now),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=now),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_identity_merge_recommendations_uuid"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conflict_id"], ["identity_conflicts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["duplicate_contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            _in("status", IDENTITY_RECOMMENDATION_STATUSES),
            name="ck_identity_recommendation_status",
        ),
        sa.CheckConstraint(
            _in("confidence", IDENTITY_CONFIDENCES),
            name="ck_identity_recommendation_confidence",
        ),
        sa.CheckConstraint(
            "primary_contact_id <> duplicate_contact_id",
            name="ck_identity_recommendation_distinct_contacts",
        ),
        **args,
    )
    op.create_index(
        "ix_identity_recommendations_org_conflict_status",
        "identity_merge_recommendations",
        ["organization_id", "conflict_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_recommendations_org_conflict_status",
        table_name="identity_merge_recommendations",
    )
    op.drop_table("identity_merge_recommendations")
    op.drop_index("ix_identity_conflicts_org_status_created", table_name="identity_conflicts")
    op.drop_table("identity_conflicts")
    op.drop_index("ix_contact_identities_org_endpoint", table_name="contact_identities")
    op.drop_index("ix_contact_identities_org_contact_created", table_name="contact_identities")
    op.drop_table("contact_identities")
