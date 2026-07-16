"""Idempotent RBAC seeding (Doc 04 §4.3, Doc 01 §2.4).

Reusable by the bootstrap CLI (``python -m app.cli``) and the test suite so there is one
definition of "what the seeded catalog and preset roles are". Both operations are
idempotent — safe to run on every deploy: missing permissions are inserted, preset roles
are created or realigned to their catalog permission set (Doc 12 §58 governance).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role
from app.rbac.catalog import PERMISSION_CATALOG, SYSTEM_ROLES


async def sync_permissions(session: AsyncSession) -> int:
    """Insert any catalog permissions missing from the DB. Returns the number added."""
    existing = set((await session.scalars(select(Permission.code))).all())
    added = 0
    for code, description in PERMISSION_CATALOG:
        if code in existing:
            continue
        resource, _, action = code.partition(":")
        session.add(
            Permission(code=code, resource=resource, action=action, description=description)
        )
        added += 1
    await session.flush()
    return added


async def sync_system_roles(session: AsyncSession, organization_id: int) -> list[Role]:
    """Create/realign the preset system roles for an organization. Returns the roles."""
    permissions = {p.code: p for p in (await session.scalars(select(Permission))).all()}
    roles: list[Role] = []
    for spec in SYSTEM_ROLES:
        name = str(spec["name"])
        role = (
            await session.scalars(
                select(Role).where(
                    Role.organization_id == organization_id,
                    Role.name == name,
                    Role.deleted_at.is_(None),
                )
            )
        ).first()
        if role is None:
            role = Role(organization_id=organization_id, name=name, is_system=True)
            session.add(role)
        role.description = str(spec["description"])
        role.is_system = True
        role.permissions = [
            permissions[code] for code in spec["permissions"] if code in permissions  # type: ignore[operator]
        ]
        roles.append(role)
    await session.flush()
    return roles
