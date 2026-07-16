"""Service-layer tests: RBAC resolver + role lifecycle, and authentication flows."""

from __future__ import annotations

import uuid as uuidlib

import pytest

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    LockedError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService

PASSWORD = "Sup3r-Secret-Pass!"


# ======================= RBAC / permission resolver =========================
async def test_resolver_superuser_holds_all(db_session, organization, make_user) -> None:
    created = await make_user(email="owner@vi.test", is_superuser=True)
    rbac = RBACService(db_session)
    from app.rbac.catalog import all_permission_codes

    assert await rbac.effective_permissions(created.user) == all_permission_codes()
    assert await rbac.has_permissions(created.user, {"users:manage", "system:manage"}) is True


async def test_resolver_normal_user_from_roles(db_session, organization, make_user) -> None:
    created = await make_user(email="agent@vi.test", roles=("agent",))
    rbac = RBACService(db_session)
    perms = await rbac.effective_permissions(created.user)
    assert "inbox:read" in perms and "users:manage" not in perms
    assert await rbac.has_permissions(created.user, {"inbox:read"}) is True
    assert await rbac.has_permissions(created.user, {"users:manage"}) is False


async def test_create_role_validates_and_persists(db_session, organization, make_user) -> None:
    actor = (await make_user(email="admin@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    role = await rbac.create_role(
        organization_id=organization.id,
        actor=actor,
        name="reviewer",
        description="Reviews campaigns",
        permission_codes=["campaigns:read", "analytics:read"],
    )
    assert {p.code for p in role.permissions} == {"campaigns:read", "analytics:read"}


async def test_create_role_rejects_duplicate_name(db_session, organization, make_user) -> None:
    actor = (await make_user(email="a@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    with pytest.raises(ConflictError):
        await rbac.create_role(
            organization_id=organization.id,
            actor=actor,
            name="admin",  # preset system role name
            description=None,
            permission_codes=[],
        )


async def test_create_role_rejects_unknown_permission(db_session, organization, make_user) -> None:
    actor = (await make_user(email="a@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    with pytest.raises(ValidationError):
        await rbac.create_role(
            organization_id=organization.id,
            actor=actor,
            name="broken",
            description=None,
            permission_codes=["not:a:real:code"],
        )


async def test_system_role_cannot_be_renamed_or_deleted(db_session, organization, make_user) -> None:
    actor = (await make_user(email="a@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    admin = await RoleRepository(db_session).get_by_name(organization.id, "admin")
    with pytest.raises(ForbiddenError):
        await rbac.update_role(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(bytes=admin.uuid),
            name="superadmin",
            description=None,
        )
    with pytest.raises(ForbiddenError):
        await rbac.delete_role(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(bytes=admin.uuid),
        )


async def test_delete_role_blocked_when_in_use(db_session, organization, make_user) -> None:
    actor = (await make_user(email="a@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    role = await rbac.create_role(
        organization_id=organization.id,
        actor=actor,
        name="temp",
        description=None,
        permission_codes=["contacts:read"],
    )
    # Assign it to a user, then deletion must be blocked (409).
    member = (await make_user(email="member@vi.test")).user
    await rbac.assign_role(user=member, role=role, actor_id=actor.id)
    await db_session.commit()
    with pytest.raises(ConflictError):
        await rbac.delete_role(
            organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(bytes=role.uuid)
        )


async def test_delete_unused_custom_role(db_session, organization, make_user) -> None:
    actor = (await make_user(email="a@vi.test", is_superuser=True)).user
    rbac = RBACService(db_session)
    role = await rbac.create_role(
        organization_id=organization.id,
        actor=actor,
        name="disposable",
        description=None,
        permission_codes=[],
    )
    await rbac.delete_role(
        organization_id=organization.id, actor=actor, public_id=uuidlib.UUID(bytes=role.uuid)
    )
    assert await RoleRepository(db_session).get_by_name(organization.id, "disposable") is None


# ============================ Authentication ================================
async def test_login_success_issues_tokens(db_session, organization, make_user) -> None:
    await make_user(email="u@vi.test", password=PASSWORD, roles=("agent",))
    auth = AuthService(db_session)
    result = await auth.authenticate(
        email="u@vi.test", password=PASSWORD, ip="203.0.113.9", user_agent="pytest"
    )
    assert result.token_type == "bearer"
    assert result.access_token and result.refresh_token
    assert result.expires_in > 0


async def test_login_wrong_password_counts_and_locks(db_session, organization, make_user) -> None:
    await make_user(email="lock@vi.test", password=PASSWORD)
    auth = AuthService(db_session)
    users = UserRepository(db_session)
    # 4 failures below threshold → Unauthorized.
    for _ in range(4):
        with pytest.raises(UnauthorizedError):
            await auth.authenticate(
                email="lock@vi.test", password="wrong", ip=None, user_agent=None
            )
    assert (await users.get_by_email("lock@vi.test")).failed_logins == 4
    # 5th failure crosses the threshold → Locked.
    with pytest.raises(LockedError):
        await auth.authenticate(email="lock@vi.test", password="wrong", ip=None, user_agent=None)
    # Even the correct password is refused while locked.
    with pytest.raises(LockedError):
        await auth.authenticate(email="lock@vi.test", password=PASSWORD, ip=None, user_agent=None)


async def test_login_unknown_email_is_generic(db_session, organization) -> None:
    auth = AuthService(db_session)
    with pytest.raises(UnauthorizedError):
        await auth.authenticate(
            email="ghost@vi.test", password="whatever", ip=None, user_agent=None
        )


async def test_refresh_rotates_and_detects_reuse(db_session, organization, make_user) -> None:
    await make_user(email="rot@vi.test", password=PASSWORD)
    auth = AuthService(db_session)
    login = await auth.authenticate(
        email="rot@vi.test", password=PASSWORD, ip=None, user_agent=None
    )

    rotated = await auth.refresh(refresh_token=login.refresh_token, ip=None, user_agent=None)
    assert rotated.refresh_token != login.refresh_token

    # Re-presenting the original (now rotated) refresh token = reuse → rejected...
    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=login.refresh_token, ip=None, user_agent=None)
    # ...and the whole family is burned, so the rotated token no longer works either.
    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=rotated.refresh_token, ip=None, user_agent=None)


async def test_change_password_revokes_sessions(db_session, organization, make_user) -> None:
    await make_user(email="cp@vi.test", password=PASSWORD)
    auth = AuthService(db_session)
    login = await auth.authenticate(
        email="cp@vi.test", password=PASSWORD, ip=None, user_agent=None
    )
    user = await UserRepository(db_session).get_by_email("cp@vi.test")

    with pytest.raises(UnauthorizedError):
        await auth.change_password(user=user, current_password="nope", new_password="NewPass-123456")

    await auth.change_password(
        user=user, current_password=PASSWORD, new_password="NewPass-123456"
    )
    # Old refresh token is now invalid.
    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=login.refresh_token, ip=None, user_agent=None)
    # New password logs in.
    assert await auth.authenticate(
        email="cp@vi.test", password="NewPass-123456", ip=None, user_agent=None
    )


async def test_logout_and_session_revocation(db_session, organization, make_user) -> None:
    await make_user(email="lo@vi.test", password=PASSWORD)
    auth = AuthService(db_session)
    login = await auth.authenticate(
        email="lo@vi.test", password=PASSWORD, ip=None, user_agent=None
    )
    user = await UserRepository(db_session).get_by_email("lo@vi.test")

    sessions = await auth.list_sessions(user=user)
    assert len(sessions) == 1

    await auth.revoke_session(user=user, session_public_id=uuidlib.UUID(bytes=sessions[0].uuid))
    assert await auth.list_sessions(user=user) == []
    # Its refresh token is revoked too.
    with pytest.raises(UnauthorizedError):
        await auth.refresh(refresh_token=login.refresh_token, ip=None, user_agent=None)


async def test_revoke_unknown_session_404(db_session, organization, make_user) -> None:
    created = await make_user(email="rs@vi.test")
    auth = AuthService(db_session)
    with pytest.raises(NotFoundError):
        await auth.revoke_session(user=created.user, session_public_id=uuidlib.uuid4())
