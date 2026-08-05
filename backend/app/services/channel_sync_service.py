"""Provider-neutral checkpoint and media-reference lifecycle management for M13-06B.

The service coordinates only repository-owned control-plane facts created by M13-06A. It performs
no provider I/O, creates no queue task, fetches no history, transfers no media, ingests no event and
exposes no API route. A future certified adapter/runtime may report factual progress through this
service after the separately gated provider milestone.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import Capability
from app.channels.flags import ChannelFeatureFlagResolver, OmnichannelFeatureFlag
from app.channels.sync import (
    SYNC_TERMINAL_STATUSES,
    ChannelSyncStatus,
    ChannelSyncType,
    MediaTransferState,
    can_transition_sync,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.db.mixins import utcnow
from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.channel_sync import ChannelSyncCheckpoint, MediaChannelReference
from app.models.media import MediaAsset
from app.models.user import User
from app.repositories.channel_connection import (
    ChannelConnectionRepository,
    ChannelEndpointRepository,
)
from app.repositories.channel_sync import (
    ChannelSyncCheckpointRepository,
    MediaChannelReferenceRepository,
)
from app.repositories.media import MediaRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.rbac_service import RBACService


class _VersionedRow(Protocol):
    row_version: int


class ChannelSyncService:
    """Manage inert history checkpoints and provider media-reference observations."""

    READ_PERMISSION = "channels:read"
    HISTORY_PERMISSION = "channels:history_sync"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._connections = ChannelConnectionRepository(session)
        self._endpoints = ChannelEndpointRepository(session)
        self._checkpoints = ChannelSyncCheckpointRepository(session)
        self._references = MediaChannelReferenceRepository(session)
        self._media = MediaRepository(session)
        self._flags = ChannelFeatureFlagResolver(session)
        self._rbac = RBACService(session)
        self._audit = AuditService(session)

    async def prepare_history_checkpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        endpoint_public_id: uuidlib.UUID,
        cutover_at: datetime | None = None,
        expected_row_version: int | None = None,
    ) -> ChannelSyncCheckpoint:
        """Create or reopen the durable checkpoint without dispatching provider work."""

        await self._require_write(organization_id, actor)
        connection, endpoint = await self._scope(
            organization_id,
            connection_public_id=connection_public_id,
            endpoint_public_id=endpoint_public_id,
        )
        self._require_history_capability(connection)
        boundary = self._database_datetime(cutover_at or utcnow(), "cutover_at")
        row = await self._checkpoints.get_for_scope(
            organization_id,
            connection.id,
            endpoint.id,
            ChannelSyncType.HISTORY,
            for_update=True,
        )
        if row is None:
            row = ChannelSyncCheckpoint(
                organization_id=organization_id,
                connection_id=connection.id,
                endpoint_id=endpoint.id,
                sync_type=ChannelSyncType.HISTORY.value,
                status=ChannelSyncStatus.PENDING.value,
                cutover_at=boundary,
                processed_count=0,
                failed_count=0,
                created_by=actor.id,
                updated_by=actor.id,
            )
            await self._checkpoints.add(row)
            await self._audit.record(
                AuditAction.CHANNEL_HISTORY_CHECKPOINT_CREATED,
                actor_user_id=actor.id,
                organization_id=organization_id,
                entity_type="channel_sync_checkpoint",
                entity_id=row.id,
                after={
                    "connection_id": connection.id,
                    "endpoint_id": endpoint.id,
                    "sync_type": row.sync_type,
                    "status": row.status,
                    "cutover_at": boundary.isoformat(),
                },
            )
            await self._session.commit()
            return row

        current = ChannelSyncStatus(row.status)
        if current is ChannelSyncStatus.PENDING:
            await self._session.commit()
            return row
        if current not in SYNC_TERMINAL_STATUSES:
            raise ConflictError("The history checkpoint is already active.")
        if expected_row_version is None:
            raise VersionConflictError(
                "expected_row_version is required to reopen a terminal checkpoint."
            )
        self._check_version(row, expected_row_version)
        if (
            current is not ChannelSyncStatus.SUCCEEDED
            and cutover_at is not None
            and row.cutover_at is not None
            and boundary < row.cutover_at
        ):
            raise ValidationError("cutover_at must not move backwards when resuming a checkpoint.")
        before = current.value
        row.status = ChannelSyncStatus.PENDING.value
        if current is ChannelSyncStatus.SUCCEEDED:
            row.cutover_at = boundary
            row.cursor_json = None
            row.watermark_at = None
            row.processed_count = 0
            row.failed_count = 0
            row.total_count = None
            row.started_at = None
            row.last_progress_at = None
            row.job_id = None
        elif cutover_at is not None:
            row.cutover_at = boundary
        row.completed_at = None
        row.error_code = None
        row.error_summary = None
        row.updated_by = actor.id
        row.row_version += 1
        await self._checkpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_HISTORY_CHECKPOINT_TRANSITIONED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_sync_checkpoint",
            entity_id=row.id,
            before={"status": before},
            after={
                "status": row.status,
                "cutover_at": row.cutover_at.isoformat() if row.cutover_at else None,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def get_checkpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
    ) -> ChannelSyncCheckpoint:
        await self._require_read(organization_id, actor)
        return await self._get_checkpoint(organization_id, public_id)

    async def list_checkpoints(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID | None = None,
        endpoint_public_id: uuidlib.UUID | None = None,
        statuses: frozenset[ChannelSyncStatus] | None = None,
        limit: int = 100,
    ) -> list[ChannelSyncCheckpoint]:
        await self._require_read(organization_id, actor)
        connection_id: int | None = None
        endpoint_id: int | None = None
        if connection_public_id is not None:
            connection = await self._get_connection(organization_id, connection_public_id)
            connection_id = connection.id
        if endpoint_public_id is not None:
            endpoint = await self._get_endpoint(organization_id, endpoint_public_id)
            endpoint_id = endpoint.id
            if connection_id is not None and endpoint.connection_id != connection_id:
                raise NotFoundError("Channel endpoint not found.")
        return await self._checkpoints.list_scoped(
            organization_id,
            connection_id=connection_id,
            endpoint_id=endpoint_id,
            statuses=statuses,
            limit=limit,
        )

    async def transition_checkpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        target_status: ChannelSyncStatus | str,
        error_code: str | None = None,
        error_summary: str | None = None,
        at: datetime | None = None,
    ) -> ChannelSyncCheckpoint:
        """Apply one legal repository-owned lifecycle transition; execute no synchronization."""

        await self._require_write(organization_id, actor)
        row = await self._get_checkpoint(
            organization_id, public_id, for_update=True
        )
        self._check_version(row, expected_row_version)
        current = ChannelSyncStatus(row.status)
        target = ChannelSyncStatus(target_status)
        if not can_transition_sync(current, target):
            raise ValidationError(
                f"Illegal history checkpoint transition: {current.value} -> {target.value}."
            )
        now = self._database_datetime(at or utcnow(), "at")
        code = self._optional_text(error_code, "error_code", 120)
        summary = self._optional_text(error_summary, "error_summary", 500)
        if target is ChannelSyncStatus.FAILED and code is None and summary is None:
            raise ValidationError("A failed checkpoint requires an error code or summary.")
        if target is ChannelSyncStatus.SUCCEEDED:
            if row.failed_count:
                raise ConflictError("A checkpoint with failed items cannot be marked succeeded.")
            if row.total_count is not None and row.processed_count != row.total_count:
                raise ConflictError(
                    "A checkpoint cannot succeed before its declared total is processed."
                )
        before = current.value
        row.status = target.value
        if target is ChannelSyncStatus.RUNNING:
            row.started_at = row.started_at or now
            row.completed_at = None
            row.last_progress_at = now
            row.error_code = None
            row.error_summary = None
        elif target is ChannelSyncStatus.PAUSED:
            row.last_progress_at = now
        elif target in SYNC_TERMINAL_STATUSES:
            row.completed_at = now
            row.last_progress_at = now
            row.error_code = code if target is ChannelSyncStatus.FAILED else None
            row.error_summary = summary if target is ChannelSyncStatus.FAILED else None
        elif target is ChannelSyncStatus.PENDING:
            row.cursor_json = None
            row.watermark_at = None
            row.cutover_at = now
            row.processed_count = 0
            row.failed_count = 0
            row.total_count = None
            row.started_at = None
            row.completed_at = None
            row.last_progress_at = None
            row.error_code = None
            row.error_summary = None
            row.job_id = None
        row.updated_by = actor.id
        row.row_version += 1
        await self._checkpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_HISTORY_CHECKPOINT_TRANSITIONED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_sync_checkpoint",
            entity_id=row.id,
            before={"status": before},
            after={
                "status": row.status,
                "processed_count": row.processed_count,
                "failed_count": row.failed_count,
                "total_count": row.total_count,
                "error_code": row.error_code,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def record_progress(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        processed_count: int,
        failed_count: int,
        total_count: int | None = None,
        cursor: dict[str, Any] | None = None,
        watermark_at: datetime | None = None,
        at: datetime | None = None,
    ) -> ChannelSyncCheckpoint:
        """Record monotonic checkpoint facts reported by a future certified executor."""

        await self._require_write(organization_id, actor)
        row = await self._get_checkpoint(
            organization_id, public_id, for_update=True
        )
        self._check_version(row, expected_row_version)
        if ChannelSyncStatus(row.status) is not ChannelSyncStatus.RUNNING:
            raise ConflictError("Progress can be recorded only while the checkpoint is running.")
        self._validate_counts(
            row,
            processed_count=processed_count,
            failed_count=failed_count,
            total_count=total_count,
        )
        now = self._database_datetime(at or utcnow(), "at")
        watermark = (
            self._database_datetime(watermark_at, "watermark_at")
            if watermark_at is not None
            else None
        )
        if watermark is not None:
            if row.watermark_at is not None and watermark < row.watermark_at:
                raise ValidationError("watermark_at must not move backwards.")
            if row.cutover_at is not None and watermark > row.cutover_at:
                raise ValidationError("watermark_at must not pass the live cutover boundary.")
        if cursor is not None:
            try:
                row.cursor_json = cursor
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        row.processed_count = processed_count
        row.failed_count = failed_count
        row.total_count = total_count if total_count is not None else row.total_count
        row.watermark_at = watermark if watermark is not None else row.watermark_at
        row.last_progress_at = now
        row.updated_by = actor.id
        row.row_version += 1
        await self._checkpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_HISTORY_PROGRESS_RECORDED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_sync_checkpoint",
            entity_id=row.id,
            after={
                "processed_count": row.processed_count,
                "failed_count": row.failed_count,
                "total_count": row.total_count,
                "watermark_at": row.watermark_at.isoformat() if row.watermark_at else None,
                "has_cursor": row.cursor_json is not None,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def register_media_reference(
        self,
        *,
        organization_id: int,
        actor: User,
        endpoint_public_id: uuidlib.UUID,
        media_public_id: uuidlib.UUID,
        provider_media_id: str,
        provider_metadata: dict[str, Any] | None = None,
    ) -> MediaChannelReference:
        """Register an observed provider identifier; transfer no bytes."""

        await self._require_write(organization_id, actor)
        endpoint = await self._get_endpoint(organization_id, endpoint_public_id)
        if not endpoint.enabled:
            raise ConflictError("The channel endpoint is disabled.")
        connection = await self._get_connection_by_id(organization_id, endpoint.connection_id)
        self._require_media_capability(connection)
        media = await self._get_media(organization_id, media_public_id)
        provider_id = self._text(provider_media_id, "provider_media_id", 190)
        existing = await self._references.get_by_provider_media_id(
            organization_id,
            endpoint.id,
            provider_id,
            for_update=True,
        )
        if existing is not None:
            if existing.media_asset_id != media.id:
                raise ConflictError(
                    "The provider media identifier already belongs to another media asset."
                )
            await self._session.commit()
            return existing
        row = MediaChannelReference(
            organization_id=organization_id,
            media_asset_id=media.id,
            endpoint_id=endpoint.id,
            provider_media_id=provider_id,
            upload_state=MediaTransferState.NOT_REQUESTED.value,
            download_state=MediaTransferState.NOT_REQUESTED.value,
            created_by=actor.id,
            updated_by=actor.id,
        )
        try:
            row.provider_metadata_json = provider_metadata
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        await self._references.add(row)
        await self._audit.record(
            AuditAction.CHANNEL_MEDIA_REFERENCE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="media_channel_reference",
            entity_id=row.id,
            after={
                "endpoint_id": endpoint.id,
                "media_asset_id": media.id,
                "provider_media_id": provider_id,
                "metadata_keys": sorted((provider_metadata or {}).keys()),
            },
        )
        await self._session.commit()
        return row

    async def get_media_reference(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
    ) -> MediaChannelReference:
        await self._require_read(organization_id, actor)
        return await self._get_media_reference(organization_id, public_id)

    async def record_media_observation(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        upload_state: MediaTransferState | str,
        download_state: MediaTransferState | str,
        observed_at: datetime,
        expires_at: datetime | None = None,
        provider_metadata: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> MediaChannelReference:
        """Persist a factual transfer observation supplied by a future certified runtime."""

        await self._require_write(organization_id, actor)
        row = await self._get_media_reference(
            organization_id, public_id, for_update=True
        )
        self._check_version(row, expected_row_version)
        observed = self._database_datetime(observed_at, "observed_at")
        expiry = (
            self._database_datetime(expires_at, "expires_at")
            if expires_at is not None
            else None
        )
        upload = MediaTransferState(upload_state)
        download = MediaTransferState(download_state)
        code = self._optional_text(error_code, "error_code", 120)
        summary = self._optional_text(error_summary, "error_summary", 500)
        if MediaTransferState.FAILED in {upload, download} and code is None and summary is None:
            raise ValidationError("A failed media observation requires an error code or summary.")
        if expiry is not None and expiry <= observed and (
            MediaTransferState.AVAILABLE in {upload, download}
        ):
            raise ValidationError("An available media reference must expire after observed_at.")
        if provider_metadata is not None:
            try:
                row.provider_metadata_json = provider_metadata
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        before = {
            "upload_state": row.upload_state,
            "download_state": row.download_state,
        }
        row.upload_state = upload.value
        row.download_state = download.value
        if expiry is not None:
            row.expires_at = expiry
        row.last_verified_at = observed
        row.last_error_code = code if MediaTransferState.FAILED in {upload, download} else None
        row.last_error_summary = (
            summary if MediaTransferState.FAILED in {upload, download} else None
        )
        row.updated_by = actor.id
        row.row_version += 1
        await self._references.flush()
        await self._audit.record(
            AuditAction.CHANNEL_MEDIA_REFERENCE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="media_channel_reference",
            entity_id=row.id,
            before=before,
            after={
                "upload_state": row.upload_state,
                "download_state": row.download_state,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "error_code": row.last_error_code,
                "metadata_keys": sorted((row.provider_metadata_json or {}).keys()),
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def list_media_references_for_endpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        endpoint_public_id: uuidlib.UUID,
        limit: int = 100,
    ) -> list[MediaChannelReference]:
        await self._require_read(organization_id, actor)
        endpoint = await self._get_endpoint(organization_id, endpoint_public_id)
        return await self._references.list_for_endpoint(
            organization_id, endpoint.id, limit=limit
        )

    async def _scope(
        self,
        organization_id: int,
        *,
        connection_public_id: uuidlib.UUID,
        endpoint_public_id: uuidlib.UUID,
    ) -> tuple[ChannelConnection, ChannelEndpoint]:
        connection = await self._get_connection(organization_id, connection_public_id)
        endpoint = await self._get_endpoint(organization_id, endpoint_public_id)
        if endpoint.connection_id != connection.id:
            raise NotFoundError("Channel endpoint not found.")
        if not endpoint.enabled:
            raise ConflictError("The channel endpoint is disabled.")
        return connection, endpoint

    async def _get_connection(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> ChannelConnection:
        row = await self._connections.get_scoped(organization_id, public_id)
        if row is None:
            raise NotFoundError("Channel connection not found.")
        return row


    async def _get_connection_by_id(
        self, organization_id: int, connection_id: int
    ) -> ChannelConnection:
        row = await self._connections.get_by_id(connection_id)
        if (
            row is None
            or row.organization_id != organization_id
            or row.deleted_at is not None
        ):
            raise NotFoundError("Channel connection not found.")
        return row

    async def _get_endpoint(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> ChannelEndpoint:
        row = await self._endpoints.get_scoped(organization_id, public_id)
        if row is None:
            raise NotFoundError("Channel endpoint not found.")
        return row

    async def _get_checkpoint(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> ChannelSyncCheckpoint:
        row = await self._checkpoints.get_scoped(
            organization_id, public_id, for_update=for_update
        )
        if row is None:
            raise NotFoundError("Channel history checkpoint not found.")
        return row

    async def _get_media(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> MediaAsset:
        row = await self._media.get_active_by_uuid(organization_id, public_id.bytes)
        if row is None:
            raise NotFoundError("Media asset not found.")
        return row

    async def _get_media_reference(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> MediaChannelReference:
        row = await self._references.get_scoped(
            organization_id, public_id, for_update=for_update
        )
        if row is None:
            raise NotFoundError("Channel media reference not found.")
        return row

    async def _require_read(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.HISTORY_SYNC):
            raise ForbiddenError("Omnichannel history synchronization is disabled.")
        if not await self._rbac.has_permissions(actor, {self.READ_PERMISSION}):
            raise ForbiddenError("The actor cannot read channel history checkpoints.")

    async def _require_write(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.HISTORY_SYNC):
            raise ForbiddenError("Omnichannel history synchronization is disabled.")
        if not await self._rbac.has_permissions(actor, {self.HISTORY_PERMISSION}):
            raise ForbiddenError("The actor cannot manage channel history synchronization.")

    @staticmethod
    def _assert_actor(organization_id: int, actor: User) -> None:
        if actor.organization_id != organization_id or actor.deleted_at is not None:
            raise ForbiddenError("The actor does not belong to the requested organization.")
        if not actor.is_active:
            raise ForbiddenError("The actor is inactive.")

    @staticmethod
    def _require_history_capability(connection: ChannelConnection) -> None:
        capabilities = frozenset(connection.capability_snapshot_json or [])
        if Capability.HISTORY_SYNC.value not in capabilities:
            raise ConflictError(
                "The channel connection does not declare history synchronization capability."
            )


    @staticmethod
    def _require_media_capability(connection: ChannelConnection) -> None:
        capabilities = frozenset(connection.capability_snapshot_json or [])
        if not capabilities.intersection(
            {Capability.MEDIA_UPLOAD.value, Capability.MEDIA_DOWNLOAD.value}
        ):
            raise ConflictError(
                "The channel connection does not declare media transfer capability."
            )

    @staticmethod
    def _check_version(row: _VersionedRow, expected: int) -> None:
        if row.row_version != expected:
            raise VersionConflictError("The record changed; reload and retry.")


    @staticmethod
    def _database_datetime(value: datetime, field_name: str) -> datetime:
        """Return the repository's canonical naive-UTC database representation."""

        if value.tzinfo is None:
            return value
        try:
            if value.utcoffset() is None:
                raise ValueError("timezone offset is undefined")
            return value.astimezone(UTC).replace(tzinfo=None)
        except (OverflowError, ValueError) as exc:
            raise ValidationError(f"{field_name} has an invalid timezone offset.") from exc

    @staticmethod
    def _validate_counts(
        row: ChannelSyncCheckpoint,
        *,
        processed_count: int,
        failed_count: int,
        total_count: int | None,
    ) -> None:
        if processed_count < row.processed_count:
            raise ValidationError("processed_count must not move backwards.")
        if failed_count < row.failed_count:
            raise ValidationError("failed_count must not move backwards.")
        if processed_count < 0 or failed_count < 0 or failed_count > processed_count:
            raise ValidationError("Checkpoint counts are invalid.")
        effective_total = total_count if total_count is not None else row.total_count
        if effective_total is not None:
            if effective_total < 0 or processed_count > effective_total:
                raise ValidationError("processed_count must not exceed total_count.")
            if row.total_count is not None and effective_total < row.total_count:
                raise ValidationError("total_count must not move backwards.")

    @staticmethod
    def _text(value: str, field_name: str, max_length: int) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} must not be empty.")
        if len(normalized) > max_length:
            raise ValidationError(f"{field_name} must be at most {max_length} characters.")
        return normalized

    @classmethod
    def _optional_text(
        cls, value: str | None, field_name: str, max_length: int
    ) -> str | None:
        if value is None:
            return None
        return cls._text(value, field_name, max_length)
