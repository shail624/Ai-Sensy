"""Repository-layer tests (Doc 01 §2.6, Doc 10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.rbac.catalog import PERMISSION_CATALOG
from app.repositories._result import affected_rows
from app.repositories.audit import AuditRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.role import (
    PermissionRepository,
    RoleRepository,
    UserRoleRepository,
)
from app.repositories.token import RefreshTokenRepository, SessionRepository
from app.repositories.user import UserRepository


def _now() -> datetime:
    return datetime.now(UTC)


async def test_affected_rows_rejects_non_cursor_result(db_session) -> None:
    result = await db_session.execute(select(1))

    with pytest.raises(RuntimeError, match="did not return a cursor result"):
        affected_rows(result.scalars())


# --- Organization -----------------------------------------------------------
async def test_organization_get_by_slug_and_default(db_session, organization) -> None:
    repo = OrganizationRepository(db_session)
    assert (await repo.get_by_slug("vi-reactivation")).id == organization.id
    assert (await repo.get_default()).id == organization.id
    assert await repo.get_by_slug("missing") is None


# --- User -------------------------------------------------------------------
async def test_user_lookup_is_case_insensitive(db_session, organization, make_user) -> None:
    created = await make_user(email="Owner@Vi.Test")
    repo = UserRepository(db_session)
    found = await repo.get_by_email("owner@vi.test")
    assert found is not None and found.id == created.user.id
    assert await repo.email_exists("OWNER@vi.test") is True
    assert await repo.email_exists("nobody@vi.test") is False


async def test_user_get_by_uuid_and_list(db_session, organization, make_user) -> None:
    created = await make_user(email="a@vi.test")
    repo = UserRepository(db_session)
    by_uuid = await repo.get_by_uuid(created.user.uuid)
    assert by_uuid is not None and by_uuid.email == "a@vi.test"
    users = await repo.list_by_organization(organization.id)
    assert any(u.id == created.user.id for u in users)


# --- Permissions ------------------------------------------------------------
async def test_permission_catalog_seeded(db_session, organization) -> None:
    repo = PermissionRepository(db_session)
    perms = await repo.list_all()
    assert len(perms) == len(PERMISSION_CATALOG)


async def test_permission_existing_codes_filters_unknown(db_session, organization) -> None:
    repo = PermissionRepository(db_session)
    known = await repo.existing_codes(["users:read", "not:real", "roles:write"])
    assert known == {"users:read", "roles:write"}


async def test_permission_codes_for_user_resolves_roles(db_session, organization, make_user) -> None:
    created = await make_user(email="agent@vi.test", roles=("agent",))
    repo = PermissionRepository(db_session)
    codes = await repo.codes_for_user(created.user.id)
    assert "inbox:read" in codes  # granted to the agent preset (Doc 01 §2.4)
    assert "users:manage" not in codes  # not an agent permission


# --- Roles ------------------------------------------------------------------
async def test_role_get_by_name_and_permissions_eager(db_session, organization) -> None:
    repo = RoleRepository(db_session)
    admin = await repo.get_by_name(organization.id, "admin")
    assert admin is not None and admin.is_system is True
    assert len(admin.permissions) == len(PERMISSION_CATALOG)  # admin holds the full set


async def test_role_set_permissions_replaces(db_session, organization) -> None:
    role_repo = RoleRepository(db_session)
    perm_repo = PermissionRepository(db_session)
    role = await role_repo.get_by_name(organization.id, "analyst")
    only = await perm_repo.get_by_codes(["contacts:read"])
    await role_repo.set_permissions(role, only)
    refreshed = await role_repo.get_by_name(organization.id, "analyst")
    assert [p.code for p in refreshed.permissions] == ["contacts:read"]


# --- User-role assignments --------------------------------------------------
async def test_user_role_assign_is_idempotent(db_session, organization, make_user) -> None:
    created = await make_user(email="m@vi.test")
    role = await RoleRepository(db_session).get_by_name(organization.id, "manager")
    repo = UserRoleRepository(db_session)
    await repo.assign(created.user.id, role.id, assigned_by=None)
    await repo.assign(created.user.id, role.id, assigned_by=None)  # no duplicate
    assert await repo.count_users_with_role(role.id) == 1
    roles = await repo.list_roles_for_user(created.user.id)
    assert [r.name for r in roles] == ["manager"]


# --- Refresh tokens ---------------------------------------------------------
async def test_refresh_token_lifecycle_and_family_revoke(db_session, organization, make_user) -> None:
    created = await make_user(email="rt@vi.test")
    repo = RefreshTokenRepository(db_session)
    exp = _now() + timedelta(days=14)
    t1 = await repo.create(user_id=created.user.id, token_hash="h1", jti="fam", expires_at=exp)
    await repo.create(
        user_id=created.user.id, token_hash="h2", jti="fam", expires_at=exp, parent_id=t1.id
    )
    assert await repo.get_by_hash("h1") is not None
    active = await repo.list_active_for_user(created.user.id, _now())
    assert len(active) == 2

    revoked = await repo.revoke_family("fam", _now())
    assert revoked == 2
    assert await repo.list_active_for_user(created.user.id, _now()) == []


async def test_refresh_token_revoke_all_for_user(db_session, organization, make_user) -> None:
    created = await make_user(email="rt2@vi.test")
    repo = RefreshTokenRepository(db_session)
    exp = _now() + timedelta(days=14)
    await repo.create(user_id=created.user.id, token_hash="a", jti="f1", expires_at=exp)
    await repo.create(user_id=created.user.id, token_hash="b", jti="f2", expires_at=exp)
    assert await repo.revoke_all_for_user(created.user.id, _now()) == 2


# --- Sessions ---------------------------------------------------------------
async def test_session_lifecycle(db_session, organization, make_user) -> None:
    created = await make_user(email="s@vi.test")
    repo = SessionRepository(db_session)
    s1 = await repo.create(user_id=created.user.id, user_agent="pytest")
    assert len(await repo.list_active_for_user(created.user.id)) == 1
    assert (await repo.get_active_by_uuid(created.user.id, s1.uuid)).id == s1.id

    await repo.revoke(s1, _now())
    assert await repo.list_active_for_user(created.user.id) == []


# --- Audit ------------------------------------------------------------------
async def test_audit_record_is_appended(db_session, organization, make_user) -> None:
    created = await make_user(email="au@vi.test")
    repo = AuditRepository(db_session)
    await repo.record(
        AuditLog(
            action="user.login",
            actor_user_id=created.user.id,
            organization_id=organization.id,
            actor_type="user",
        )
    )
    recent = await repo.list_recent(limit=10)
    assert any(entry.action == "user.login" for entry in recent)
