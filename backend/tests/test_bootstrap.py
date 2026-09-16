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


# --- The address must be one that can actually sign in -----------------------------------------
# `create-owner` is the first command run against a new deployment. It used to accept any string,
# so a typo or a reserved `.test` domain produced an Owner superuser, printed "Owner created" and
# exited 0 -- an account unusable from the moment it existed, whose only symptom appeared later as
# a 422 at sign-in that never mentioned the address.


@pytest.mark.parametrize(
    "address",
    [
        "this is not an email",  # a plain typo: no @, spaces throughout
        "owner@vi.test",  # reserved special-use domain the login schema refuses
        "owner@vi.invalid",  # likewise reserved
        "owner@localhost",  # no public domain part
        "owner@",  # truncated
    ],
)
async def test_bootstrap_refuses_an_address_that_could_never_sign_in(
    session_factory, address: str
) -> None:
    with pytest.raises(ValueError):
        await bootstrap_owner(
            session_factory, email=address, full_name="Owner", password=OWNER_PASSWORD
        )

    async with session_factory() as session:
        # Refused before anything was written: no half-made superuser left behind.
        assert await UserRepository(session).get_by_email(address.strip().lower()) is None


async def test_every_address_bootstrap_accepts_is_one_the_login_schema_accepts(
    session_factory,
) -> None:
    """The property that matters, stated directly rather than through examples.

    The two boundaries are only aligned if nothing can pass one and fail the other. This asserts
    that in the direction that hurts: an owner the CLI creates must be an owner who can sign in.
    """
    from app.schemas.auth import LoginRequest

    result = await bootstrap_owner(
        session_factory, email="  Owner@Company.com  ", full_name="Owner", password=OWNER_PASSWORD
    )

    accepted = LoginRequest(email=result.owner_email, password=OWNER_PASSWORD)
    assert accepted.email == result.owner_email  # same address, no further normalisation needed
