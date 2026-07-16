"""RBAC models (Doc 03 §4.3).

Many-to-many both ways: users↔roles (``user_roles``) and roles↔permissions
(``role_permissions``) — Doc 01 FR-AUTH-05. ``permissions`` is a fixed seeded catalog
(Doc 04 §4.3); ``roles`` are fully customizable (FR-AUTH-08) with ``is_system`` presets
that cannot be deleted or renamed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import (
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
    utcnow,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

# --- roles ↔ permissions junction (pure link table, composite PK) -------------
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        big_id(),
        ForeignKey("roles.id", name="fk_rp_role", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "permission_id",
        int_id(),
        ForeignKey("permissions.id", name="fk_rp_perm", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Index("ix_rp_permission", "permission_id"),
    **MYSQL_TABLE_ARGS,
)


class Permission(Base):
    """A granular ``resource:action`` permission (Doc 03 §4.3; catalog in Doc 04 §4.3)."""

    __tablename__ = "permissions"
    __table_args__ = (
        Index("ix_permissions_resource", "resource"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = mapped_column(int_id(), primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Permission {self.code!r}>"


class Role(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base
):
    """A named set of permissions within an organization (Doc 03 §4.3)."""

    __tablename__ = "roles"
    __table_args__ = (
        Index("uq_roles_org_name", "organization_id", "name", unique=True),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_roles_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Effective permission set for the role; eager-loaded so a fetched Role always
    # carries its permissions (async-safe selectin, Doc 03 §4.3 resolution note).
    permissions: Mapped[list[Permission]] = relationship(
        Permission,
        secondary=role_permissions,
        lazy="selectin",
        order_by=Permission.code,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Role id={self.id} name={self.name!r}>"


class UserRole(Base):
    """User↔role assignment with provenance (Doc 03 §4.3 ``user_roles``)."""

    __tablename__ = "user_roles"
    __table_args__ = (
        Index("ix_ur_role", "role_id"),
        MYSQL_TABLE_ARGS,
    )

    user_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_ur_user", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("roles.id", name="fk_ur_role", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    assigned_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"
