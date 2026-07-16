"""RBAC service — permission resolution and role management (Doc 01 FR-AUTH-05/06/08, Doc 04 §12.2).

Owns the **permission resolver** (the single place effective permissions are computed, with
the Owner superuser bypass) and the role lifecycle. All role mutations validate against the
seeded catalog (unknown code → 422), protect ``is_system`` presets, and are audited.
"""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.role import Permission, Role
from app.models.user import User
from app.rbac.catalog import all_permission_codes
from app.repositories.role import (
    PermissionRepository,
    RoleRepository,
    UserRoleRepository,
)
from app.services.audit_service import AuditAction, AuditService


class RBACService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = RoleRepository(session)
        self._perms = PermissionRepository(session)
        self._user_roles = UserRoleRepository(session)
        self._audit = AuditService(session)

    # --- Permission resolver -------------------------------------------------
    #: Self-scope permission held by every authenticated user (Doc 12 §58 — role "all").
    SELF_PERMISSION = "auth:self"

    async def effective_permissions(self, user: User) -> frozenset[str]:
        """The user's effective permission codes; the Owner superuser holds them all.

        ``auth:self`` is always included: every authenticated user may manage their own
        profile and sessions regardless of assigned roles (Doc 12 §58).
        """
        if user.is_superuser:
            return all_permission_codes()
        codes = set(await self._perms.codes_for_user(user.id))
        codes.add(self.SELF_PERMISSION)
        return frozenset(codes)

    async def has_permissions(self, user: User, required: set[str]) -> bool:
        if user.is_superuser:
            return True
        if not required:
            return True
        return required <= await self.effective_permissions(user)

    async def roles_for_user(self, user: User) -> list[Role]:
        return await self._user_roles.list_roles_for_user(user.id)

    # --- Catalog -------------------------------------------------------------
    async def list_permissions(self) -> list[Permission]:
        return await self._perms.list_all()

    async def _resolve_codes(self, codes: list[str]) -> list[Permission]:
        """Validate codes against the seeded catalog (422 on any unknown), return rows."""
        unique = list(dict.fromkeys(codes))  # de-dupe, preserve order
        known = await self._perms.existing_codes(unique)
        unknown = [c for c in unique if c not in known]
        if unknown:
            raise ValidationError(
                "One or more permission codes are not in the catalog.",
                errors=[
                    {"field": "permissions", "code": "unknown_permission", "message": c}
                    for c in unknown
                ],
            )
        return await self._perms.get_by_codes(unique)

    # --- Role lifecycle ------------------------------------------------------
    async def list_roles(self, organization_id: int) -> list[Role]:
        return await self._roles.list_by_organization(organization_id)

    async def get_role(self, organization_id: int, public_id: uuidlib.UUID) -> Role:
        role = await self._roles.get_by_uuid(public_id)
        if role is None or role.organization_id != organization_id or role.deleted_at is not None:
            raise NotFoundError("Role not found.")
        return role

    async def create_role(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        description: str | None,
        permission_codes: list[str],
    ) -> Role:
        if await self._roles.get_by_name(organization_id, name) is not None:
            raise ConflictError(f"A role named {name!r} already exists.")
        permissions = await self._resolve_codes(permission_codes)
        role = Role(
            organization_id=organization_id,
            name=name,
            description=description,
            is_system=False,
        )
        role.permissions = permissions
        await self._roles.add(role)
        await self._audit.record(
            AuditAction.ROLE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="role",
            entity_id=role.id,
            after={"name": name, "permissions": [p.code for p in permissions]},
        )
        await self._session.commit()
        return role

    async def update_role(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        name: str | None,
        description: str | None,
    ) -> Role:
        role = await self.get_role(organization_id, public_id)
        before = {"name": role.name, "description": role.description}
        if name is not None and name != role.name:
            if role.is_system:
                raise ForbiddenError("System roles cannot be renamed.")
            if await self._roles.get_by_name(organization_id, name) is not None:
                raise ConflictError(f"A role named {name!r} already exists.")
            role.name = name
        if description is not None:
            role.description = description
        await self._roles.flush()
        await self._audit.record(
            AuditAction.ROLE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="role",
            entity_id=role.id,
            before=before,
            after={"name": role.name, "description": role.description},
        )
        await self._session.commit()
        return role

    async def set_role_permissions(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        permission_codes: list[str],
    ) -> Role:
        role = await self.get_role(organization_id, public_id)
        before = [p.code for p in role.permissions]
        permissions = await self._resolve_codes(permission_codes)
        await self._roles.set_permissions(role, permissions)
        await self._audit.record(
            AuditAction.ROLE_PERMISSIONS_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="role",
            entity_id=role.id,
            before={"permissions": before},
            after={"permissions": [p.code for p in permissions]},
        )
        await self._session.commit()
        return role

    async def delete_role(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        role = await self.get_role(organization_id, public_id)
        if role.is_system:
            raise ForbiddenError("System roles cannot be deleted.")
        if await self._user_roles.count_users_with_role(role.id) > 0:
            raise ConflictError("Role is assigned to one or more users and cannot be deleted.")
        role_id, role_name = role.id, role.name
        await self._roles.delete(role)
        await self._audit.record(
            AuditAction.ROLE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="role",
            entity_id=role_id,
            before={"name": role_name},
        )
        await self._session.commit()

    async def assign_role(self, *, user: User, role: Role, actor_id: int | None) -> None:
        """Assign a role to a user (used by bootstrap/administration)."""
        await self._user_roles.assign(user.id, role.id, assigned_by=actor_id)
