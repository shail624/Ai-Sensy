"""Tenant-scoped persistence queries for M13-02 identity records."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import func, select

from app.models.contact_identity import (
    ContactIdentity,
    IdentityConflict,
    IdentityMergeRecommendation,
)
from app.repositories.base import BaseRepository


class ContactIdentityRepository(BaseRepository[ContactIdentity]):
    model = ContactIdentity

    async def get_exact(
        self,
        organization_id: int,
        identity_namespace: str,
        identity_scope: str,
        normalized_value: str,
    ) -> ContactIdentity | None:
        stmt = select(ContactIdentity).where(
            ContactIdentity.organization_id == organization_id,
            ContactIdentity.identity_namespace == identity_namespace,
            ContactIdentity.identity_scope == identity_scope,
            ContactIdentity.normalized_value == normalized_value,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_contact(
        self, organization_id: int, contact_id: int
    ) -> list[ContactIdentity]:
        stmt = (
            select(ContactIdentity)
            .where(
                ContactIdentity.organization_id == organization_id,
                ContactIdentity.contact_id == contact_id,
            )
            .order_by(ContactIdentity.created_at.asc(), ContactIdentity.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def latest_routing_identity(
        self,
        *,
        organization_id: int,
        contact_id: int,
        connector_type: str,
        endpoint_ref: str,
    ) -> ContactIdentity | None:
        """Latest provider-observed direct address for one Contact on one owned endpoint."""

        stmt = (
            select(ContactIdentity)
            .where(
                ContactIdentity.organization_id == organization_id,
                ContactIdentity.contact_id == contact_id,
                ContactIdentity.connector_type == connector_type,
                ContactIdentity.endpoint_ref == endpoint_ref,
                ContactIdentity.identity_namespace.in_(("whatsapp_lid", "whatsapp_jid")),
            )
            .order_by(
                ContactIdentity.verified_at.desc(),
                ContactIdentity.created_at.desc(),
                ContactIdentity.id.desc(),
            )
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()


class IdentityConflictRepository(BaseRepository[IdentityConflict]):
    model = IdentityConflict

    async def get_scoped(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> IdentityConflict | None:
        stmt = select(IdentityConflict).where(
            IdentityConflict.organization_id == organization_id,
            IdentityConflict.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_fingerprint(
        self, organization_id: int, fingerprint: str
    ) -> IdentityConflict | None:
        stmt = select(IdentityConflict).where(
            IdentityConflict.organization_id == organization_id,
            IdentityConflict.fingerprint == fingerprint,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_scoped(
        self,
        organization_id: int,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[IdentityConflict]:
        stmt = select(IdentityConflict).where(IdentityConflict.organization_id == organization_id)
        if status is not None:
            stmt = stmt.where(IdentityConflict.status == status)
        stmt = stmt.order_by(IdentityConflict.created_at.desc(), IdentityConflict.id.desc())
        return list((await self.session.scalars(stmt.limit(limit).offset(offset))).all())

    async def count_scoped(self, organization_id: int, *, status: str | None) -> int:
        stmt = (
            select(func.count())
            .select_from(IdentityConflict)
            .where(IdentityConflict.organization_id == organization_id)
        )
        if status is not None:
            stmt = stmt.where(IdentityConflict.status == status)
        return int((await self.session.scalar(stmt)) or 0)


class IdentityRecommendationRepository(BaseRepository[IdentityMergeRecommendation]):
    model = IdentityMergeRecommendation

    async def get_scoped(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> IdentityMergeRecommendation | None:
        stmt = select(IdentityMergeRecommendation).where(
            IdentityMergeRecommendation.organization_id == organization_id,
            IdentityMergeRecommendation.uuid == public_id.bytes,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_conflict(
        self, organization_id: int, conflict_id: int
    ) -> list[IdentityMergeRecommendation]:
        stmt = (
            select(IdentityMergeRecommendation)
            .where(
                IdentityMergeRecommendation.organization_id == organization_id,
                IdentityMergeRecommendation.conflict_id == conflict_id,
            )
            .order_by(
                IdentityMergeRecommendation.created_at.asc(),
                IdentityMergeRecommendation.id.asc(),
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def pending_for_conflict(
        self, organization_id: int, conflict_id: int
    ) -> IdentityMergeRecommendation | None:
        stmt = select(IdentityMergeRecommendation).where(
            IdentityMergeRecommendation.organization_id == organization_id,
            IdentityMergeRecommendation.conflict_id == conflict_id,
            IdentityMergeRecommendation.status == "pending",
        )
        return (await self.session.scalars(stmt)).first()
