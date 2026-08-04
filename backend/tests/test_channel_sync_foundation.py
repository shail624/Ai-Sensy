"""M13-06A provider-neutral sync checkpoint and media-reference foundation tests."""

from __future__ import annotations

import uuid as uuidlib

import pytest
from sqlalchemy.exc import IntegrityError

from app.channels.capabilities import Capability
from app.channels.sync import ChannelSyncStatus, ChannelSyncType, MediaTransferState
from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.channel_sync import ChannelSyncCheckpoint, MediaChannelReference
from app.models.media import MediaAsset
from app.models.organization import Organization
from app.repositories.channel_sync import (
    ChannelSyncCheckpointRepository,
    MediaChannelReferenceRepository,
)


async def _foundation_rows(db_session, organization_id: int, actor_id: int):
    connection = ChannelConnection(
        organization_id=organization_id,
        channel_family="whatsapp",
        connector_type="certification_mock",
        provider_connection_id="mock-connection-001",
        display_name="Certification-only mock connection",
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(connection)
    await db_session.flush()
    endpoint = ChannelEndpoint(
        organization_id=organization_id,
        connection_id=connection.id,
        endpoint_type="phone",
        normalized_address="+919999000001",
        display_address="+91 99990 00001",
        provider_endpoint_id="mock-endpoint-001",
        created_by=actor_id,
        updated_by=actor_id,
    )
    media = MediaAsset(
        organization_id=organization_id,
        media_type="image",
        mime_type="image/png",
        file_name="certification-fixture.png",
        byte_size=128,
        sha256="a" * 64,
        storage_backend="local",
        storage_key="tests/certification-fixture.png",
        created_by=actor_id,
    )
    db_session.add_all([endpoint, media])
    await db_session.flush()
    return connection, endpoint, media


def test_provider_neutral_sync_vocabulary_and_secret_rejection() -> None:
    assert Capability.HISTORY_SYNC.value == "history_sync"
    assert ChannelSyncType.HISTORY.value == "history"
    assert ChannelSyncStatus.PENDING.value == "pending"
    assert MediaTransferState.AVAILABLE.value == "available"

    with pytest.raises(ValueError, match="plaintext credential"):
        ChannelSyncCheckpoint(
            organization_id=1,
            connection_id=2,
            endpoint_id=3,
            cursor_json={"access_token": "must-not-persist"},
        )
    with pytest.raises(ValueError, match="plaintext credential"):
        MediaChannelReference(
            organization_id=1,
            media_asset_id=2,
            endpoint_id=3,
            provider_media_id="provider-media-1",
            provider_metadata_json={"credentials": {"value": "must-not-persist"}},
        )


async def test_sync_and_media_repositories_are_tenant_scoped(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="sync-foundation@example.test", roles=("admin",))).user
    connection, endpoint, media = await _foundation_rows(
        db_session, organization.id, actor.id
    )
    checkpoint = ChannelSyncCheckpoint(
        organization_id=organization.id,
        connection_id=connection.id,
        endpoint_id=endpoint.id,
        sync_type=ChannelSyncType.HISTORY.value,
        status=ChannelSyncStatus.PENDING.value,
        cursor_json={"page": "opaque-1"},
        processed_count=0,
        failed_count=0,
        total_count=10,
        created_by=actor.id,
        updated_by=actor.id,
    )
    reference = MediaChannelReference(
        organization_id=organization.id,
        media_asset_id=media.id,
        endpoint_id=endpoint.id,
        provider_media_id="provider-media-001",
        upload_state=MediaTransferState.AVAILABLE.value,
        download_state=MediaTransferState.NOT_REQUESTED.value,
        provider_metadata_json={"source": "repository-test"},
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add_all([checkpoint, reference])
    await db_session.commit()

    other = Organization(name="Other Sync Tenant", slug="other-sync-tenant")
    db_session.add(other)
    await db_session.commit()

    checkpoint_repo = ChannelSyncCheckpointRepository(db_session)
    reference_repo = MediaChannelReferenceRepository(db_session)

    assert (
        await checkpoint_repo.get_scoped(
            organization.id, uuidlib.UUID(checkpoint.public_id)
        )
        is checkpoint
    )
    assert (
        await checkpoint_repo.get_scoped(other.id, uuidlib.UUID(checkpoint.public_id))
        is None
    )
    assert (
        await checkpoint_repo.get_for_scope(
            organization.id,
            connection.id,
            endpoint.id,
            ChannelSyncType.HISTORY,
        )
        is checkpoint
    )
    assert await checkpoint_repo.list_scoped(
        organization.id,
        statuses=frozenset({ChannelSyncStatus.PENDING}),
    ) == [checkpoint]
    assert (
        await reference_repo.get_by_provider_media_id(
            organization.id,
            endpoint.id,
            reference.provider_media_id,
        )
        is reference
    )
    assert (
        await reference_repo.get_by_provider_media_id(
            other.id,
            endpoint.id,
            reference.provider_media_id,
        )
        is None
    )
    assert await reference_repo.list_for_asset(organization.id, media.id) == [reference]
    assert await reference_repo.list_for_endpoint(organization.id, endpoint.id) == [
        reference
    ]

    with pytest.raises(ValueError, match="between 1 and 1000"):
        await checkpoint_repo.list_scoped(organization.id, limit=0)
    with pytest.raises(ValueError, match="between 1 and 1000"):
        await reference_repo.list_for_endpoint(organization.id, endpoint.id, limit=1001)


async def test_checkpoint_progress_and_provider_media_identity_fail_closed(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="sync-constraints@example.test", roles=("admin",))).user
    connection, endpoint, media = await _foundation_rows(
        db_session, organization.id, actor.id
    )
    invalid = ChannelSyncCheckpoint(
        organization_id=organization.id,
        connection_id=connection.id,
        endpoint_id=endpoint.id,
        processed_count=1,
        failed_count=2,
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add(invalid)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    connection, endpoint, media = await _foundation_rows(
        db_session, organization.id, actor.id
    )
    first = MediaChannelReference(
        organization_id=organization.id,
        media_asset_id=media.id,
        endpoint_id=endpoint.id,
        provider_media_id="provider-media-duplicate",
        created_by=actor.id,
        updated_by=actor.id,
    )
    second = MediaChannelReference(
        organization_id=organization.id,
        media_asset_id=media.id,
        endpoint_id=endpoint.id,
        provider_media_id="provider-media-duplicate",
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        await db_session.flush()
