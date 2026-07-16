"""Identity & Access + Audit schema (Module 1 — Doc 03 §4, §11.2).

First production migration. **Expand** phase of the expand→migrate→contract discipline
(Doc 03 §1.10 / Doc 08 §20): it only creates new tables, so it is purely additive and
safe to apply online. The reverse (``downgrade``) drops them in FK-dependency order.

Physical types match Doc 03 exactly on MySQL (BINARY(16), VARBINARY, BIGINT UNSIGNED,
DATETIME(6)) and degrade to portable equivalents on SQLite (test suite, Doc 10). The
``audit_logs`` table uses a composite ``(id, created_at)`` primary key and monthly RANGE
partitioning on MySQL (Doc 03 §11.2); on SQLite it is a plain surrogate-key table.

Revision ID: 0001_identity_and_audit
Revises: (base)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import (
    big_id,
    datetime6,
    int_id,
    packed_ip,
    small_uint,
    uuid_binary,
    varbinary,
)

# revision identifiers, used by Alembic.
revision = "0001_identity_and_audit"
down_revision = None
branch_labels = None
depends_on = None


def _created_default(dialect: str) -> sa.sql.elements.TextClause:
    """Server DEFAULT for created_at — microsecond precision on MySQL (Doc 03 §1.3)."""
    return sa.text("CURRENT_TIMESTAMP(6)") if dialect == "mysql" else sa.text("CURRENT_TIMESTAMP")


def _updated_default(dialect: str) -> sa.sql.elements.TextClause:
    """Server DEFAULT + ON UPDATE for updated_at (Doc 03 §1.3)."""
    if dialect == "mysql":
        return sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    created = _created_default(dialect)
    updated = _updated_default(dialect)
    mysql_args: dict[str, str] = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
        if dialect == "mysql"
        else {}
    )

    # --- organizations (Doc 03 §4.1) --------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("default_locale", sa.String(10), nullable=False, server_default=sa.text("'en'")),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_organizations_uuid"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        **mysql_args,
    )

    # --- users (Doc 03 §4.2) ----------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("locale", sa.String(10), nullable=False, server_default=sa.text("'en'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("mfa_secret_enc", varbinary(255), nullable=True),
        sa.Column("failed_logins", small_uint(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", datetime6(), nullable=True),
        sa.Column("last_login_at", datetime6(), nullable=True),
        sa.Column("password_changed_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("created_by", big_id(), nullable=True),
        sa.Column("updated_by", big_id(), nullable=True),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_users_uuid"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_users_org", ondelete="RESTRICT"
        ),
        **mysql_args,
    )
    op.create_index("ix_users_org", "users", ["organization_id"])
    op.create_index("ix_users_active", "users", ["organization_id", "is_active"])

    # --- roles (Doc 03 §4.3) ----------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("organization_id", big_id(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("updated_at", datetime6(), nullable=False, server_default=updated),
        sa.Column("deleted_at", datetime6(), nullable=True),
        sa.Column("row_version", int_id(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_roles_uuid"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_roles_org", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("uq_roles_org_name", "roles", ["organization_id", "name"], unique=True)

    # --- permissions (Doc 03 §4.3) — fixed seeded catalog -----------------
    op.create_table(
        "permissions",
        sa.Column("id", int_id(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("resource", sa.String(40), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        **mysql_args,
    )
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    # --- role_permissions (Doc 03 §4.3) — M:N junction --------------------
    op.create_table(
        "role_permissions",
        sa.Column("role_id", big_id(), nullable=False),
        sa.Column("permission_id", int_id(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_rp_role", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], name="fk_rp_perm", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_rp_permission", "role_permissions", ["permission_id"])

    # --- user_roles (Doc 03 §4.3) — M:N junction with provenance ----------
    op.create_table(
        "user_roles",
        sa.Column("user_id", big_id(), nullable=False),
        sa.Column("role_id", big_id(), nullable=False),
        sa.Column("assigned_at", datetime6(), nullable=False, server_default=created),
        sa.Column("assigned_by", big_id(), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ur_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_ur_role", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_ur_role", "user_roles", ["role_id"])

    # --- refresh_tokens (Doc 03 §4.4) -------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("user_id", big_id(), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("jti", sa.CHAR(36), nullable=False),
        sa.Column("parent_id", big_id(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", packed_ip(), nullable=True),
        sa.Column("expires_at", datetime6(), nullable=False),
        sa.Column("revoked_at", datetime6(), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_rt_uuid"),
        sa.UniqueConstraint("token_hash", name="uq_rt_token_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_rt_user", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_rt_user_active", "refresh_tokens", ["user_id", "revoked_at", "expires_at"])
    op.create_index("ix_rt_jti", "refresh_tokens", ["jti"])

    # --- user_sessions (Doc 03 §4.4) --------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("uuid", uuid_binary(), nullable=False),
        sa.Column("user_id", big_id(), nullable=False),
        sa.Column("refresh_token_id", big_id(), nullable=True),
        sa.Column("ip_address", packed_ip(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("last_seen_at", datetime6(), nullable=False, server_default=created),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
        sa.Column("revoked_at", datetime6(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_sessions_uuid"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user", ondelete="CASCADE"
        ),
        **mysql_args,
    )
    op.create_index("ix_sessions_user", "user_sessions", ["user_id", "revoked_at"])

    # --- audit_logs (Doc 03 §11.2) — immutable, partitioned on MySQL ------
    audit_columns = [
        sa.Column("id", big_id(), autoincrement=True, nullable=False),
        sa.Column("organization_id", big_id(), nullable=True),
        sa.Column("actor_user_id", big_id(), nullable=True),
        sa.Column("actor_type", sa.String(12), nullable=False, server_default=sa.text("'user'")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=True),
        sa.Column("entity_id", big_id(), nullable=True),
        sa.Column("ip_address", packed_ip(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.CHAR(64), nullable=True),
        sa.Column("row_hash", sa.CHAR(64), nullable=True),
        sa.Column("created_at", datetime6(), nullable=False, server_default=created),
    ]
    if dialect == "mysql":
        # Composite PK includes the partition column (Doc 03 §11.2 requirement).
        op.create_table("audit_logs", *audit_columns, sa.PrimaryKeyConstraint("id", "created_at"), **mysql_args)
    else:
        op.create_table("audit_logs", *audit_columns, sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_audit_actor", "audit_logs", ["actor_user_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id", "created_at"])
    op.create_index("ix_audit_action", "audit_logs", ["action", "created_at"])
    op.create_index("ix_audit_org", "audit_logs", ["organization_id", "created_at"])
    if dialect == "mysql":
        # Monthly RANGE partitioning with a catch-all (Doc 03 §11.2). New monthly
        # partitions are provisioned by the maintenance job (Doc 06 §10 / Doc 11).
        op.execute(
            "ALTER TABLE audit_logs PARTITION BY RANGE COLUMNS (created_at) ("
            "PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'), "
            "PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'), "
            "PARTITION pmax VALUES LESS THAN (MAXVALUE))"
        )


def downgrade() -> None:
    # Drop in reverse FK-dependency order (children before parents).
    op.drop_table("audit_logs")
    op.drop_table("user_sessions")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("organizations")
