"""ORM model registry.

Importing this package registers every table on :data:`app.db.base.Base.metadata`.
The Alembic environment and the test schema builder import it so migrations and
``create_all`` see the full schema. Import models from here (or their modules); never
rely on import side effects elsewhere.
"""

from __future__ import annotations

from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.role import Permission, Role, UserRole, role_permissions
from app.models.token import RefreshToken, UserSession
from app.models.user import User

__all__ = [
    "AuditLog",
    "Organization",
    "Permission",
    "RefreshToken",
    "Role",
    "User",
    "UserRole",
    "UserSession",
    "role_permissions",
]
