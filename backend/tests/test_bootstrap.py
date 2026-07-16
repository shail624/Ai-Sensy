"""Tests for the bootstrap CLI (Doc 03 §4.1, Doc 11)."""

from __future__ import annotations

import pytest

from app.cli import bootstrap_owner
from app.rbac.catalog import all_permission_codes
from app.repositories.user import UserRepository
from app.services.rbac_service import RBACService

OWNER_PASSWORD = "Owner-Bootstrap-123"


async def test_bootstrap_creates_org_roles_and_owner(session_factory) -> None:
    """A clean database gets an org, preset roles, and an Owner superuser."""
    result = await bootstrap_owner(
        session_factory, email="Owner@Company.com", full_name="Owner", password=OWNER_PASSWORD
    )
    assert result.organization_created is True
    assert result.owner_created is True
    assert result.owner_email == "owner@company.com"  # normalized

    async with session_factory() as session:
        owner = await UserRepository(session).get_by_email("owner@company.com")
        assert owner is not None and owner.is_superuser is True
        # Superuser resolves to every catalog permission (Doc 01 FR-AUTH-06).
        assert await RBACService(session).effective_permissions(owner) == all_permission_codes()
        roles = await RBACService(session).roles_for_user(owner)
        assert [r.name for r in roles] == ["owner"]


async def test_bootstrap_is_idempotent(session_factory) -> None:
    first = await bootstrap_owner(
        session_factory, email="owner@company.com", full_name="Owner", password=OWNER_PASSWORD
    )
    second = await bootstrap_owner(
        session_factory, email="owner@company.com", full_name="Owner", password=OWNER_PASSWORD
    )
    assert first.owner_created is True
    assert second.owner_created is False
    assert second.organization_created is False

    async with session_factory() as session:
        users = await UserRepository(session).list_by_organization(
            (await UserRepository(session).get_by_email("owner@company.com")).organization_id
        )
        assert len([u for u in users if u.email == "owner@company.com"]) == 1


async def test_bootstrap_rejects_weak_password(session_factory) -> None:
    with pytest.raises(ValueError):
        await bootstrap_owner(
            session_factory, email="owner@company.com", full_name="Owner", password="weak"
        )
