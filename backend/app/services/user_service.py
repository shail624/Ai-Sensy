"""User management service (Doc 04 §12.1).

Administrative user CRUD, activation/deactivation, and role assignment. Enforces unique
email, catalog-valid roles, optimistic concurrency (``row_version`` → 409), and self-action
guards (an admin cannot deactivate/delete their own account). Deactivation and deletion
revoke the target's sessions and refresh tokens. Every mutation is audited.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.core.security import hash_password
from app.db.mixins import utcnow
from app.models.role import Role
from app.models.user import User
from app.repositories.role import RoleRepository, UserRoleRepository
from app.repositories.token import RefreshTokenRepository, SessionRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService


@dataclass(slots=True)
class UserListPage:
    users: list[User]
    roles_by_user: dict[int, list[Role]]
    has_more: bool
    total: int


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._user_roles = UserRoleRepository(session)
        self._refresh = RefreshTokenRepository(session)
        self._sessions = SessionRepository(session)
        self._audit = AuditService(session)

    async def _roles_for(self, user: User) -> list[Role]:
        return await self._user_roles.list_roles_for_user(user.id)

    async def _resolve_role_ids(self, organization_id: int, names: list[str]) -> list[int]:
        unique = list(dict.fromkeys(names))
        found = await self._roles.get_by_names(organization_id, unique)
        by_name = {role.name: role for role in found}
        unknown = [name for name in unique if name not in by_name]
        if unknown:
            raise ValidationError(
                "One or more roles do not exist.",
                errors=[{"field": "roles", "code": "unknown_role", "message": n} for n in unknown],
            )
        return [by_name[name].id for name in unique]

    async def _get_or_404(self, organization_id: int, public_id: uuidlib.UUID) -> User:
        user = await self._users.get_by_uuid(public_id)
        if user is None or user.organization_id != organization_id or user.deleted_at is not None:
            raise NotFoundError("User not found.")
        return user

    async def _revoke_all(self, user_id: int, now: datetime) -> None:
        await self._refresh.revoke_all_for_user(user_id, now)
        await self._sessions.revoke_all_for_user(user_id, now)

    # --- Queries -------------------------------------------------------------
    async def list_users(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        is_active: bool | None,
        role_name: str | None,
        q: str | None,
    ) -> UserListPage:
        users, has_more = await self._users.paginate(
            organization_id,
            limit=limit,
            cursor=cursor,
            is_active=is_active,
            role_name=role_name,
            q=q,
        )
        total = await self._users.count(
            organization_id, is_active=is_active, role_name=role_name, q=q
        )
        roles_by_user = {user.id: await self._roles_for(user) for user in users}
        return UserListPage(users=users, roles_by_user=roles_by_user, has_more=has_more, total=total)

    async def get_user(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> tuple[User, list[Role]]:
        user = await self._get_or_404(organization_id, public_id)
        return user, await self._roles_for(user)

    # --- Mutations -----------------------------------------------------------
    async def create_user(
        self,
        *,
        organization_id: int,
        actor: User,
        email: str,
        full_name: str,
        password: str,
        phone: str | None,
        timezone: str,
        locale: str,
        roles: list[str],
    ) -> tuple[User, list[Role]]:
        normalized = email.strip().lower()
        if await self._users.email_exists(normalized):
            raise ConflictError("A user with this email already exists.")
        role_ids = await self._resolve_role_ids(organization_id, roles)
        user = User(
            organization_id=organization_id,
            email=normalized,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
            timezone=timezone,
            locale=locale,
            is_active=True,
            is_superuser=False,
            created_by=actor.id,
        )
        await self._users.add(user)
        await self._user_roles.set_roles(user.id, role_ids, assigned_by=actor.id)
        await self._audit.record(
            AuditAction.USER_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="user",
            entity_id=user.id,
            after={"email": normalized, "roles": roles},
        )
        await self._session.commit()
        return user, await self._roles_for(user)

    async def update_user(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        full_name: str | None,
        phone: str | None,
        timezone: str | None,
        locale: str | None,
        is_active: bool | None,
        roles: list[str] | None,
        expected_version: int | None,
    ) -> tuple[User, list[Role]]:
        user = await self._get_or_404(organization_id, public_id)
        if expected_version is not None and expected_version != user.row_version:
            raise VersionConflictError("The user was modified by someone else; reload and retry.")

        if is_active is False and user.id == actor.id:
            raise ConflictError("You cannot deactivate your own account.")

        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone
        if timezone is not None:
            user.timezone = timezone
        if locale is not None:
            user.locale = locale

        now = utcnow()
        deactivated = is_active is False and user.is_active
        if is_active is not None:
            user.is_active = is_active
        if roles is not None:
            role_ids = await self._resolve_role_ids(organization_id, roles)
            await self._user_roles.set_roles(user.id, role_ids, assigned_by=actor.id)

        user.updated_by = actor.id
        user.row_version += 1
        await self._users.flush()
        if deactivated:
            await self._revoke_all(user.id, now)
        await self._audit.record(
            AuditAction.USER_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="user",
            entity_id=user.id,
            after={"is_active": user.is_active, "roles": roles},
        )
        await self._session.commit()
        return user, await self._roles_for(user)

    async def set_active(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, active: bool
    ) -> tuple[User, list[Role]]:
        user = await self._get_or_404(organization_id, public_id)
        if not active and user.id == actor.id:
            raise ConflictError("You cannot deactivate your own account.")
        now = utcnow()
        user.is_active = active
        user.updated_by = actor.id
        user.row_version += 1
        await self._users.flush()
        if not active:
            await self._revoke_all(user.id, now)
        await self._audit.record(
            AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="user",
            entity_id=user.id,
        )
        await self._session.commit()
        return user, await self._roles_for(user)

    async def delete_user(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        user = await self._get_or_404(organization_id, public_id)
        if user.id == actor.id:
            raise ConflictError("You cannot delete your own account.")
        now = utcnow()
        user.deleted_at = now
        user.is_active = False
        # Anonymize the unique email so it can be reused (Doc 03 §1.5).
        user.email = f"deleted+{user.public_id}@deleted.invalid"
        user.updated_by = actor.id
        user.row_version += 1
        await self._users.flush()
        await self._revoke_all(user.id, now)
        await self._audit.record(
            AuditAction.USER_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="user",
            entity_id=user.id,
        )
        await self._session.commit()
