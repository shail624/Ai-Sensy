"""Tenant-scoped queries for provider-neutral sync checkpoints and media references."""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy import Select, select
from sqlalchemy.sql.elements import ColumnElement

from app.channels.sync import ChannelSyncStatus, ChannelSyncType
from app.models.channel_sync import ChannelSyncCheckpoint, MediaChannelReference
from app.repositories.base import BaseRepository


class ChannelSyncCheckpointRepository(BaseRepository[ChannelSyncCheckpoint]):
    model = ChannelSyncCheckpoint

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> ChannelSyncCheckpoint | None:
        stmt = select(ChannelSyncCheckpoint).where(
            ChannelSyncCheckpoint.organization_id == organization_id,
            ChannelSyncCheckpoint.uuid == public_id.bytes,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def get_for_scope(
        self,
        organization_id: int,
        connection_id: int,
        endpoint_id: int,
        sync_type: ChannelSyncType,
        *,
        for_update: bool = False,
    ) -> ChannelSyncCheckpoint | None:
        stmt = select(ChannelSyncCheckpoint).where(
            ChannelSyncCheckpoint.organization_id == organization_id,
            ChannelSyncCheckpoint.connection_id == connection_id,
            ChannelSyncCheckpoint.endpoint_id == endpoint_id,
            ChannelSyncCheckpoint.sync_type == sync_type.value,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def list_scoped(
        self,
        organization_id: int,
        *,
        connection_id: int | None = None,
        endpoint_id: int | None = None,
        statuses: frozenset[ChannelSyncStatus] | None = None,
        limit: int = 100,
    ) -> list[ChannelSyncCheckpoint]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        stmt: Select[tuple[ChannelSyncCheckpoint]] = select(ChannelSyncCheckpoint).where(
            ChannelSyncCheckpoint.organization_id == organization_id
        )
        if connection_id is not None:
            stmt = stmt.where(ChannelSyncCheckpoint.connection_id == connection_id)
        if endpoint_id is not None:
            stmt = stmt.where(ChannelSyncCheckpoint.endpoint_id == endpoint_id)
        if statuses:
            stmt = stmt.where(
                ChannelSyncCheckpoint.status.in_(tuple(status.value for status in statuses))
            )
        stmt = stmt.order_by(
            ChannelSyncCheckpoint.updated_at.desc(),
            ChannelSyncCheckpoint.id.desc(),
        ).limit(limit)
        return list((await self.session.scalars(stmt)).all())


class MediaChannelReferenceRepository(BaseRepository[MediaChannelReference]):
    model = MediaChannelReference

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> MediaChannelReference | None:
        stmt = select(MediaChannelReference).where(
            MediaChannelReference.organization_id == organization_id,
            MediaChannelReference.uuid == public_id.bytes,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def get_by_provider_media_id(
        self,
        organization_id: int,
        endpoint_id: int,
        provider_media_id: str,
        *,
        for_update: bool = False,
    ) -> MediaChannelReference | None:
        stmt = select(MediaChannelReference).where(
            MediaChannelReference.organization_id == organization_id,
            MediaChannelReference.endpoint_id == endpoint_id,
            MediaChannelReference.provider_media_id == provider_media_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def list_for_asset(
        self,
        organization_id: int,
        media_asset_id: int,
        *,
        limit: int = 100,
    ) -> list[MediaChannelReference]:
        return await self._list_scoped(
            organization_id,
            MediaChannelReference.media_asset_id == media_asset_id,
            limit=limit,
        )

    async def list_for_endpoint(
        self,
        organization_id: int,
        endpoint_id: int,
        *,
        limit: int = 100,
    ) -> list[MediaChannelReference]:
        return await self._list_scoped(
            organization_id,
            MediaChannelReference.endpoint_id == endpoint_id,
            limit=limit,
        )

    async def _list_scoped(
        self,
        organization_id: int,
        predicate: ColumnElement[bool],
        *,
        limit: int,
    ) -> list[MediaChannelReference]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        stmt = (
            select(MediaChannelReference)
            .where(
                MediaChannelReference.organization_id == organization_id,
                predicate,
            )
            .order_by(
                MediaChannelReference.updated_at.desc(),
                MediaChannelReference.id.desc(),
            )
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())
