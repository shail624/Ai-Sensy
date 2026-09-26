"""M13-06B provider-neutral history/media control-plane service tests."""

from __future__ import annotations

import json
import uuid as uuidlib
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.channels.capabilities import Capability
from app.channels.flags import OmnichannelFeatureFlag
from app.channels.sync import (
    ChannelSyncStatus,
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
from app.models.audit import AuditLog
from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.media import MediaAsset
from app.models.organization import Organization
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.channel_sync_service import ChannelSyncService


async def _enable_history(session, organization_id: int) -> None:
    session.add(
        FeatureFlag(
            key_name=OmnichannelFeatureFlag.HISTORY_SYNC.value,
            organization_id=organization_id,
            is_enabled=True,
        )
    )
    await session.commit()


async def _foundation(
    session,
    organization_id: int,
    actor_id: int,
    *,
    capabilities: list[str] | None = None,
    suffix: str = "001",
) -> tuple[ChannelConnection, ChannelEndpoint, MediaAsset]:
    connection = ChannelConnection(
        organization_id=organization_id,
        channel_family="whatsapp",
        connector_type="certification_mock",
        provider_connection_id=f"mock-connection-{suffix}",
        display_name="Provider-neutral history connection",
        capability_snapshot_json=capabilities
        if capabilities is not None
        else [Capability.HISTORY_SYNC.value, Capability.MEDIA_DOWNLOAD.value],
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(connection)
    await session.flush()
    endpoint = ChannelEndpoint(
        organization_id=organization_id,
        connection_id=connection.id,
        endpoint_type="phone",
        normalized_address=f"+91999900{suffix}",
        display_address=f"+91 99990 0{suffix}",
        provider_endpoint_id=f"mock-endpoint-{suffix}",
        enabled=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    media = MediaAsset(
        organization_id=organization_id,
        media_type="image",
        mime_type="image/png",
        file_name=f"history-{suffix}.png",
        byte_size=128,
        sha256=(suffix[-1] or "a") * 64,
        storage_backend="local",
        storage_key=f"tests/history-{suffix}.png",
        created_by=actor_id,
    )
    session.add_all([endpoint, media])
    await session.commit()
    return connection, endpoint, media


async def _other_tenant(session) -> tuple[Organization, User]:
    organization = Organization(
        name="Sync Other Tenant",
        slug=f"sync-other-{uuidlib.uuid4().hex[:8]}",
    )
    session.add(organization)
    await session.flush()
    actor = User(
        organization_id=organization.id,
        email=f"sync-other-{uuidlib.uuid4().hex[:8]}@example.test",
        password_hash="not-used",
        full_name="Other Sync Operator",
        is_superuser=True,
    )
    session.add(actor)
    await session.flush()
    await _enable_history(session, organization.id)
    return organization, actor


def test_sync_transition_vocabulary_is_bounded() -> None:
    assert can_transition_sync(ChannelSyncStatus.PENDING, ChannelSyncStatus.RUNNING)
    assert can_transition_sync(ChannelSyncStatus.RUNNING, ChannelSyncStatus.PAUSED)
    assert can_transition_sync(ChannelSyncStatus.PAUSED, ChannelSyncStatus.RUNNING)
    assert can_transition_sync(ChannelSyncStatus.SUCCEEDED, ChannelSyncStatus.PENDING)
    assert not can_transition_sync(ChannelSyncStatus.PENDING, ChannelSyncStatus.SUCCEEDED)
    assert not can_transition_sync(ChannelSyncStatus.CANCELLED, ChannelSyncStatus.RUNNING)
    assert OmnichannelFeatureFlag.HISTORY_SYNC.value == "omnichannel_qr_history"


async def test_history_checkpoint_flags_rbac_capability_and_tenant_fail_closed(
    db_session, make_user, organization
) -> None:
    admin = (await make_user(email="sync-admin@example.test", roles=("admin",))).user
    unprivileged = (await make_user(email="sync-none@example.test", roles=())).user
    connection, endpoint, _ = await _foundation(
        db_session,
        organization.id,
        admin.id,
        capabilities=[],
        suffix="101",
    )
    service = ChannelSyncService(db_session)

    with pytest.raises(ForbiddenError, match="disabled"):
        await service.prepare_history_checkpoint(
            organization_id=organization.id,
            actor=admin,
            connection_public_id=uuidlib.UUID(connection.public_id),
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        )

    await _enable_history(db_session, organization.id)
    with pytest.raises(ForbiddenError, match="cannot manage"):
        await service.prepare_history_checkpoint(
            organization_id=organization.id,
            actor=unprivileged,
            connection_public_id=uuidlib.UUID(connection.public_id),
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        )
    with pytest.raises(ConflictError, match="does not declare"):
        await service.prepare_history_checkpoint(
            organization_id=organization.id,
            actor=admin,
            connection_public_id=uuidlib.UUID(connection.public_id),
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        )

    connection.capability_snapshot_json = [Capability.HISTORY_SYNC.value]
    await db_session.commit()
    checkpoint = await service.prepare_history_checkpoint(
        organization_id=organization.id,
        actor=admin,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
    )
    other_org, other_actor = await _other_tenant(db_session)
    with pytest.raises(NotFoundError):
        await service.get_checkpoint(
            organization_id=other_org.id,
            actor=other_actor,
            public_id=uuidlib.UUID(checkpoint.public_id),
        )


async def test_history_checkpoint_lifecycle_progress_and_audit(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="sync-lifecycle@example.test", roles=("admin",))).user
    await _enable_history(db_session, organization.id)
    connection, endpoint, _ = await _foundation(
        db_session, organization.id, actor.id, suffix="202"
    )
    service = ChannelSyncService(db_session)
    cutover = utcnow()
    checkpoint = await service.prepare_history_checkpoint(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        cutover_at=cutover,
    )
    duplicate = await service.prepare_history_checkpoint(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
    )
    assert duplicate.id == checkpoint.id
    assert checkpoint.status == ChannelSyncStatus.PENDING.value

    checkpoint = await service.transition_checkpoint(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(checkpoint.public_id),
        expected_row_version=checkpoint.row_version,
        target_status=ChannelSyncStatus.RUNNING,
    )
    checkpoint = await service.record_progress(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(checkpoint.public_id),
        expected_row_version=checkpoint.row_version,
        processed_count=3,
        failed_count=0,
        total_count=5,
        cursor={"opaque": "page-3"},
        watermark_at=cutover - timedelta(minutes=1),
    )
    assert checkpoint.processed_count == 3
    assert checkpoint.cursor_json == {"opaque": "page-3"}

    with pytest.raises(ValidationError, match="must not move backwards"):
        await service.record_progress(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(checkpoint.public_id),
            expected_row_version=checkpoint.row_version,
            processed_count=2,
            failed_count=0,
        )
    aware_at = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    checkpoint = await service.record_progress(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(checkpoint.public_id),
        expected_row_version=checkpoint.row_version,
        processed_count=3,
        failed_count=0,
        at=aware_at,
    )
    assert checkpoint.last_progress_at == aware_at.astimezone(UTC).replace(
        tzinfo=None
    )
    with pytest.raises(ValidationError, match="plaintext credential"):
        await service.record_progress(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(checkpoint.public_id),
            expected_row_version=checkpoint.row_version,
            processed_count=4,
            failed_count=0,
            cursor={"access_token": "forbidden"},
        )
    with pytest.raises(ConflictError, match="declared total"):
        await service.transition_checkpoint(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(checkpoint.public_id),
            expected_row_version=checkpoint.row_version,
            target_status=ChannelSyncStatus.SUCCEEDED,
        )

    checkpoint = await service.record_progress(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(checkpoint.public_id),
        expected_row_version=checkpoint.row_version,
        processed_count=5,
        failed_count=0,
        total_count=5,
        cursor={"opaque": "page-5"},
        watermark_at=cutover,
    )
    checkpoint = await service.transition_checkpoint(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(checkpoint.public_id),
        expected_row_version=checkpoint.row_version,
        target_status=ChannelSyncStatus.SUCCEEDED,
    )
    terminal_version = checkpoint.row_version
    with pytest.raises(VersionConflictError):
        await service.prepare_history_checkpoint(
            organization_id=organization.id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
            expected_row_version=terminal_version - 1,
        )
    checkpoint = await service.prepare_history_checkpoint(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        expected_row_version=terminal_version,
    )
    assert checkpoint.status == ChannelSyncStatus.PENDING.value
    assert checkpoint.processed_count == 0
    assert checkpoint.cursor_json is None
    assert checkpoint.watermark_at is None

    actions = set(
        (
            await db_session.scalars(
                select(AuditLog.action).where(
                    AuditLog.entity_type == "channel_sync_checkpoint",
                    AuditLog.entity_id == checkpoint.id,
                )
            )
        ).all()
    )
    assert {
        AuditAction.CHANNEL_HISTORY_CHECKPOINT_CREATED,
        AuditAction.CHANNEL_HISTORY_CHECKPOINT_TRANSITIONED,
        AuditAction.CHANNEL_HISTORY_PROGRESS_RECORDED,
    } <= actions


async def test_media_reference_lifecycle_is_idempotent_tenant_scoped_and_secret_safe(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="media-ref@example.test", roles=("admin",))).user
    await _enable_history(db_session, organization.id)
    _, endpoint, media = await _foundation(
        db_session, organization.id, actor.id, suffix="303"
    )
    other_media = MediaAsset(
        organization_id=organization.id,
        media_type="image",
        mime_type="image/png",
        file_name="other.png",
        byte_size=64,
        sha256="f" * 64,
        storage_backend="local",
        storage_key="tests/other.png",
        created_by=actor.id,
    )
    db_session.add(other_media)
    await db_session.commit()
    service = ChannelSyncService(db_session)
    no_media_connection, no_media_endpoint, no_media = await _foundation(
        db_session,
        organization.id,
        actor.id,
        capabilities=[Capability.HISTORY_SYNC.value],
        suffix="304",
    )
    assert no_media_connection.capability_snapshot_json == [Capability.HISTORY_SYNC.value]
    with pytest.raises(ConflictError, match="does not declare media"):
        await service.register_media_reference(
            organization_id=organization.id,
            actor=actor,
            endpoint_public_id=uuidlib.UUID(no_media_endpoint.public_id),
            media_public_id=uuidlib.UUID(no_media.public_id),
            provider_media_id="provider-media-no-capability",
        )

    reference = await service.register_media_reference(
        organization_id=organization.id,
        actor=actor,
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        media_public_id=uuidlib.UUID(media.public_id),
        provider_media_id="provider-media-303",
        provider_metadata={"source": "certification-fixture"},
    )
    duplicate = await service.register_media_reference(
        organization_id=organization.id,
        actor=actor,
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
        media_public_id=uuidlib.UUID(media.public_id),
        provider_media_id="provider-media-303",
    )
    assert duplicate.id == reference.id
    with pytest.raises(ConflictError, match="another media asset"):
        await service.register_media_reference(
            organization_id=organization.id,
            actor=actor,
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
            media_public_id=uuidlib.UUID(other_media.public_id),
            provider_media_id="provider-media-303",
        )
    with pytest.raises(ValidationError, match="plaintext credential"):
        await service.register_media_reference(
            organization_id=organization.id,
            actor=actor,
            endpoint_public_id=uuidlib.UUID(endpoint.public_id),
            media_public_id=uuidlib.UUID(media.public_id),
            provider_media_id="provider-media-secret",
            provider_metadata={"credentials": {"value": "forbidden"}},
        )

    observed_at = utcnow()
    reference = await service.record_media_observation(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(reference.public_id),
        expected_row_version=reference.row_version,
        upload_state=MediaTransferState.NOT_REQUESTED,
        download_state=MediaTransferState.AVAILABLE,
        observed_at=observed_at,
        expires_at=observed_at + timedelta(hours=1),
        provider_metadata={"content_type": "image/png"},
    )
    assert reference.download_state == MediaTransferState.AVAILABLE.value
    assert reference.last_error_code is None
    with pytest.raises(ValidationError, match="requires an error"):
        await service.record_media_observation(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(reference.public_id),
            expected_row_version=reference.row_version,
            upload_state=MediaTransferState.NOT_REQUESTED,
            download_state=MediaTransferState.FAILED,
            observed_at=utcnow(),
        )

    listed = await service.list_media_references_for_endpoint(
        organization_id=organization.id,
        actor=actor,
        endpoint_public_id=uuidlib.UUID(endpoint.public_id),
    )
    assert [row.id for row in listed] == [reference.id]
    other_org, other_actor = await _other_tenant(db_session)
    with pytest.raises(NotFoundError):
        await service.get_media_reference(
            organization_id=other_org.id,
            actor=other_actor,
            public_id=uuidlib.UUID(reference.public_id),
        )

    actions = set(
        (
            await db_session.scalars(
                select(AuditLog.action).where(
                    AuditLog.entity_type == "media_channel_reference",
                    AuditLog.entity_id == reference.id,
                )
            )
        ).all()
    )
    assert {
        AuditAction.CHANNEL_MEDIA_REFERENCE_CREATED,
        AuditAction.CHANNEL_MEDIA_REFERENCE_UPDATED,
    } <= actions


def test_m13_06b_exposes_no_api_or_provider_execution_surface() -> None:
    from app.main import create_app

    openapi = json.dumps(create_app().openapi())
    assert "channel_sync_checkpoints" not in openapi
    assert "media_channel_references" not in openapi
    assert "/history-sync" not in openapi
