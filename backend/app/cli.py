"""Administrative CLI — one-time bootstrap of the platform (Doc 03 §4.1, Doc 11).

Usage (run after ``alembic upgrade head``)::

    OWNER_PASSWORD=... python -m app.cli create-owner --email owner@company.com --name "Owner"

Creates the single-tenant organization (if absent), realigns the preset system roles, and
creates the Owner superuser. The owner password is read from ``OWNER_PASSWORD`` and is never
logged, defaulted, or stored in code. The operation is **idempotent** — re-running it does
not duplicate the organization, roles, or user.

Also hosts two development-only subcommands, ``seed-dev-fixtures``/``reset-dev-fixtures``, that
delegate to :mod:`app.dev_fixtures` — see that module for the safety model. They are refused
outright unless ``ENVIRONMENT`` is ``development``/``test`` and ``ALLOW_DEV_FIXTURES=true``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password, validate_password_policy
from app.crm.seeding import sync_default_pipeline
from app.db.session import dispose_engine, get_sessionmaker
from app.dev_fixtures import (
    FIXTURE_AGENT_EMAILS,
    DevFixturesNotAllowed,
    FixtureSummary,
    ResetSummary,
    reset_chat_history_preview,
    seed_chat_history_preview,
)
from app.models.organization import Organization
from app.models.user import User
from app.rbac.catalog import ROLE_OWNER
from app.rbac.seeding import sync_permissions, sync_system_roles
from app.repositories.organization import OrganizationRepository
from app.repositories.role import UserRoleRepository
from app.repositories.user import UserRepository


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    organization_created: bool
    owner_created: bool
    owner_email: str


async def bootstrap_owner(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    full_name: str,
    password: str,
) -> BootstrapResult:
    """Ensure the org, preset roles, and Owner superuser exist. Idempotent."""
    validate_password_policy(password)
    normalized_email = email.strip().lower()

    async with session_factory() as session:
        org_repo = OrganizationRepository(session)
        organization = await org_repo.get_default()
        org_created = False
        if organization is None:
            organization = Organization(
                name=settings.bootstrap_org_name, slug=settings.bootstrap_org_slug
            )
            await org_repo.add(organization)
            org_created = True

        await sync_permissions(session)
        roles = await sync_system_roles(session, organization.id)
        owner_role = next(role for role in roles if role.name == ROLE_OWNER)
        # The platform ships a default lead pipeline (Doc 07 §19.2).
        await sync_default_pipeline(session, organization.id)

        user_repo = UserRepository(session)
        existing = await user_repo.get_by_email(normalized_email)
        owner_created = False
        if existing is None:
            owner = User(
                organization_id=organization.id,
                email=normalized_email,
                password_hash=hash_password(password),
                full_name=full_name,
                is_superuser=True,
            )
            await user_repo.add(owner)
            await UserRoleRepository(session).assign(owner.id, owner_role.id, assigned_by=None)
            owner_created = True

        await session.commit()
        return BootstrapResult(
            organization_created=org_created,
            owner_created=owner_created,
            owner_email=normalized_email,
        )


async def _run_create_owner(email: str, full_name: str, password: str) -> BootstrapResult:
    try:
        return await bootstrap_owner(
            get_sessionmaker(), email=email, full_name=full_name, password=password
        )
    finally:
        await dispose_engine()


async def _run_seed_dev_fixtures() -> FixtureSummary:
    try:
        return await seed_chat_history_preview(get_sessionmaker())
    finally:
        await dispose_engine()


async def _run_reset_dev_fixtures() -> ResetSummary:
    try:
        return await reset_chat_history_preview(get_sessionmaker())
    finally:
        await dispose_engine()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Platform administration CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    owner = sub.add_parser("create-owner", help="Create/ensure the Owner superuser")
    owner.add_argument("--email", default=os.environ.get("OWNER_EMAIL"))
    owner.add_argument("--name", default=os.environ.get("OWNER_FULL_NAME", "Owner"))

    sub.add_parser(
        "seed-dev-fixtures",
        help=(
            "Development-only: populate Chat History with fictional preview data. "
            "Refused unless ENVIRONMENT=development|test and ALLOW_DEV_FIXTURES=true."
        ),
    )
    sub.add_parser(
        "reset-dev-fixtures",
        help="Development-only: remove only the rows seed-dev-fixtures created.",
    )

    args = parser.parse_args(argv)

    if args.command == "create-owner":
        password = os.environ.get("OWNER_PASSWORD")
        if not args.email:
            parser.error("owner email is required (--email or OWNER_EMAIL)")
        if not password:
            parser.error("owner password is required via the OWNER_PASSWORD environment variable")
        try:
            result = asyncio.run(
                _run_create_owner(args.email, args.name, password)
            )
        except ValueError as exc:  # password policy violation
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if result.owner_created:
            print(f"Owner created: {result.owner_email}")
        else:
            print(f"Owner already exists: {result.owner_email} (no changes)")
        return 0

    if args.command == "seed-dev-fixtures":
        try:
            summary = asyncio.run(_run_seed_dev_fixtures())
        except DevFixturesNotAllowed as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Dev fixtures seeded: {summary}")
        print(
            "Preview agent login (development-only, not a real credential): "
            f"{FIXTURE_AGENT_EMAILS[0]} / see app.dev_fixtures.FIXTURE_AGENT_PASSWORD"
        )
        return 0

    if args.command == "reset-dev-fixtures":
        try:
            reset_summary = asyncio.run(_run_reset_dev_fixtures())
        except DevFixturesNotAllowed as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Dev fixtures reset: {reset_summary}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
