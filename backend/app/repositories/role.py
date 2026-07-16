"""RBAC repositories — roles, permissions, and user-role assignments (Doc 03 §4.3)."""

from __future__ import annotations

from sqlalchemy import delete, func, select

from app.models.role import Permission, Role, UserRole, role_permissions
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_name(self, organization_id: int, name: str) -> Role | None:
        stmt = select(Role).where(
            Role.organization_id == organization_id,
            Role.name == name,
            Role.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def list_by_organization(self, organization_id: int) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.organization_id == organization_id, Role.deleted_at.is_(None))
            .order_by(Role.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_by_names(self, organization_id: int, names: list[str]) -> list[Role]:
        if not names:
            return []
        stmt = select(Role).where(
            Role.organization_id == organization_id,
            Role.name.in_(names),
            Role.deleted_at.is_(None),
        )
        return list((await self.session.scalars(stmt)).all())

    async def set_permissions(self, role: Role, permissions: list[Permission]) -> None:
        """Replace a role's permission set (Doc 04 §12.2 — PUT /roles/{id}/permissions)."""
        role.permissions = permissions
        await self.session.flush()


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def list_all(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.code)
        return list((await self.session.scalars(stmt)).all())

    async def get_by_codes(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list((await self.session.scalars(stmt)).all())

    async def existing_codes(self, codes: list[str]) -> set[str]:
        """Subset of ``codes`` that exist in the seeded catalog (validation, Doc 04 §12.2)."""
        if not codes:
            return set()
        stmt = select(Permission.code).where(Permission.code.in_(codes))
        return set((await self.session.scalars(stmt)).all())

    async def codes_for_user(self, user_id: int) -> set[str]:
        """Resolve a user's effective permission codes via user_roles → role_permissions."""
        stmt = (
            select(Permission.code)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == role_permissions.c.role_id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        return set((await self.session.scalars(stmt)).all())


class UserRoleRepository(BaseRepository[UserRole]):
    model = UserRole

    async def list_roles_for_user(self, user_id: int) -> list[Role]:
        """The user's assigned, non-deleted roles (permissions eager-loaded)."""
        stmt = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.deleted_at.is_(None))
            .order_by(Role.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def assign(self, user_id: int, role_id: int, assigned_by: int | None) -> UserRole:
        """Idempotently assign a role to a user."""
        existing = await self.session.get(UserRole, (user_id, role_id))
        if existing is not None:
            return existing
        link = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        return await self.add(link)

    async def count_users_with_role(self, role_id: int) -> int:
        """How many users hold a role — blocks deleting a role in use (Doc 04 §12.2 → 409)."""
        stmt = select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def set_roles(self, user_id: int, role_ids: list[int], assigned_by: int | None) -> None:
        """Replace a user's role assignments with ``role_ids`` (Doc 04 §12.1)."""
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for role_id in dict.fromkeys(role_ids):
            self.session.add(
                UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
            )
        await self.session.flush()
