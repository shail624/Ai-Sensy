"""Tenant-scoped persistence queries for channel connections, endpoints, and secrets."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import select

from app.models.channel_connection import ChannelConnection, ChannelEndpoint, ChannelSecret
from app.repositories.base import BaseRepository


class ChannelConnectionRepository(BaseRepository[ChannelConnection]):
    model = ChannelConnection

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        include_deleted: bool = False,
    ) -> ChannelConnection | None:
        stmt = select(ChannelConnection).where(
            ChannelConnection.organization_id == organization_id,
            ChannelConnection.uuid == public_id.bytes,
        )
        if not include_deleted:
            stmt = stmt.where(ChannelConnection.deleted_at.is_(None))
        return (await self.session.scalars(stmt)).first()

    async def list_scoped(
        self, organization_id: int, *, include_deleted: bool = False
    ) -> list[ChannelConnection]:
        stmt = select(ChannelConnection).where(ChannelConnection.organization_id == organization_id)
        if not include_deleted:
            stmt = stmt.where(ChannelConnection.deleted_at.is_(None))
        stmt = stmt.order_by(ChannelConnection.created_at.asc(), ChannelConnection.id.asc())
        return list((await self.session.scalars(stmt)).all())


class ChannelEndpointRepository(BaseRepository[ChannelEndpoint]):
    model = ChannelEndpoint

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        include_deleted: bool = False,
    ) -> ChannelEndpoint | None:
        stmt = select(ChannelEndpoint).where(
            ChannelEndpoint.organization_id == organization_id,
            ChannelEndpoint.uuid == public_id.bytes,
        )
        if not include_deleted:
            stmt = stmt.where(ChannelEndpoint.deleted_at.is_(None))
        return (await self.session.scalars(stmt)).first()

    async def list_for_connection(
        self,
        organization_id: int,
        connection_id: int,
        *,
        include_deleted: bool = False,
    ) -> list[ChannelEndpoint]:
        stmt = select(ChannelEndpoint).where(
            ChannelEndpoint.organization_id == organization_id,
            ChannelEndpoint.connection_id == connection_id,
        )
        if not include_deleted:
            stmt = stmt.where(ChannelEndpoint.deleted_at.is_(None))
        stmt = stmt.order_by(ChannelEndpoint.created_at.asc(), ChannelEndpoint.id.asc())
        return list((await self.session.scalars(stmt)).all())

    async def connector_type_for_id(self, endpoint_id: int) -> str | None:
        """Resolve connector identity from the endpoint's persisted connection ownership.

        Workers deliberately receive no connector argument.  The durable endpoint/connection
        relationship is the one routing authority after a webhook request has been acknowledged.
        """

        stmt = (
            select(ChannelConnection.connector_type)
            .join(ChannelEndpoint, ChannelEndpoint.connection_id == ChannelConnection.id)
            .where(ChannelEndpoint.id == endpoint_id)
        )
        return (await self.session.scalars(stmt)).first()


class ChannelSecretRepository(BaseRepository[ChannelSecret]):
    model = ChannelSecret

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> ChannelSecret | None:
        stmt = select(ChannelSecret).where(
            ChannelSecret.organization_id == organization_id,
            ChannelSecret.uuid == public_id.bytes,
            ChannelSecret.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def get_active(
        self,
        organization_id: int,
        connection_id: int,
        secret_type: str,
        *,
        for_update: bool = False,
    ) -> ChannelSecret | None:
        stmt = select(ChannelSecret).where(
            ChannelSecret.organization_id == organization_id,
            ChannelSecret.connection_id == connection_id,
            ChannelSecret.secret_type == secret_type,
            ChannelSecret.status == "active",
            ChannelSecret.revoked_at.is_(None),
            ChannelSecret.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def get_latest(
        self, organization_id: int, connection_id: int, secret_type: str
    ) -> ChannelSecret | None:
        stmt = (
            select(ChannelSecret)
            .where(
                ChannelSecret.organization_id == organization_id,
                ChannelSecret.connection_id == connection_id,
                ChannelSecret.secret_type == secret_type,
            )
            .order_by(ChannelSecret.secret_version.desc(), ChannelSecret.id.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_connection(
        self, organization_id: int, connection_id: int
    ) -> list[ChannelSecret]:
        stmt = (
            select(ChannelSecret)
            .where(
                ChannelSecret.organization_id == organization_id,
                ChannelSecret.connection_id == connection_id,
            )
            .order_by(
                ChannelSecret.secret_type.asc(),
                ChannelSecret.secret_version.asc(),
            )
        )
        return list((await self.session.scalars(stmt)).all())
