"""M13-03 provider-neutral connection, endpoint, and encrypted-secret persistence tests."""

from __future__ import annotations

import json
import uuid as uuidlib

import pytest
from sqlalchemy import select

from app.channels.flags import OmnichannelFeatureFlag
from app.channels.foundation import (
    ProviderDesiredState,
    ProviderHealthState,
    ProviderObservedState,
)
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError, VersionConflictError
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.channel_connection import ChannelConnection, ChannelSecret
from app.models.organization import Organization
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.channel_connection_service import ChannelConnectionService


async def _enable_flags(session, organization_id: int) -> None:
    for flag in OmnichannelFeatureFlag:
        session.add(
            FeatureFlag(
                key_name=flag.value,
                organization_id=organization_id,
                is_enabled=True,
            )
        )
    await session.commit()


async def _create_other_tenant(session) -> tuple[Organization, User]:
    organization = Organization(name="Other Tenant", slug="other-tenant")
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        email="other@example.test",
        password_hash="not-used",
        full_name="Other Operator",
        is_superuser=True,
    )
    session.add(user)
    await session.flush()
    await _enable_flags(session, organization.id)
    return organization, user


async def _create_connection(service, organization_id: int, actor: User) -> ChannelConnection:
    return await service.create_connection(
        organization_id=organization_id,
        actor=actor,
        channel_family="rcs",
        connector_type="generic_gateway",
        provider_connection_id="provider-account-001",
        display_name="Provider-neutral test connection",
        desired_state=ProviderDesiredState.DISABLED,
        capability_snapshot=["health", "text", "health"],
        provider_configuration={"region": "in", "delivery_mode": "manual"},
        provider_metadata={"account_tier": "test", "source": "provider"},
    )


async def test_feature_flags_fail_closed_for_connection_storage(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(is_superuser=True)).user
    service = ChannelConnectionService(db_session)

    with pytest.raises(ForbiddenError):
        await _create_connection(service, organization.id, actor)

    assert (await db_session.scalars(select(ChannelConnection))).all() == []


async def test_connections_and_endpoints_are_tenant_scoped_versioned_and_provider_neutral(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    service = ChannelConnectionService(db_session)
    connection = await _create_connection(service, organization.id, actor)

    assert connection.channel_family == "rcs"
    assert connection.connector_type == "generic_gateway"
    assert connection.capability_snapshot_json == ["health", "text"]
    assert connection.observed_state == ProviderObservedState.UNCONFIGURED.value
    assert connection.health_state == ProviderHealthState.UNKNOWN.value
    assert connection.row_version == 0

    endpoint = await service.create_endpoint(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_type="business_address",
        normalized_address="business-42",
        provider_endpoint_id="endpoint-native-42",
        display_address="Business 42",
        enabled=False,
        endpoint_metadata={"locale": "en-IN"},
        provider_limits={"daily_messages": 50},
    )
    assert endpoint.organization_id == organization.id
    assert endpoint.connection_id == connection.id
    assert endpoint.observed_state == ProviderObservedState.UNCONFIGURED.value

    with pytest.raises(ValueError, match="connector_type is immutable"):
        connection.connector_type = "different_provider"
    with pytest.raises(ValueError, match="provider_connection_id is immutable"):
        connection.provider_connection_id = "changed-account"
    with pytest.raises(ValueError, match="provider_endpoint_id is immutable"):
        endpoint.provider_endpoint_id = "changed-endpoint"

    with pytest.raises(VersionConflictError):
        await service.update_connection(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(connection.public_id),
            expected_row_version=0,
            changes={"display_name": "stale write"},
        )

    connection = await service.update_connection(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(connection.public_id),
        expected_row_version=1,
        changes={
            "display_name": "Updated neutral connection",
            "desired_state": ProviderDesiredState.ENABLED.value,
        },
    )
    assert connection.display_name == "Updated neutral connection"
    assert connection.desired_state == ProviderDesiredState.ENABLED.value
    assert connection.row_version == 2

    observed_at = utcnow()
    endpoint = await service.record_endpoint_observation(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(endpoint.public_id),
        expected_row_version=0,
        observed_state=ProviderObservedState.READY,
        health_state=ProviderHealthState.HEALTHY,
        health_score=97,
        health_detail="Factual provider observation",
        observed_at=observed_at,
    )
    assert endpoint.observed_state == "ready"
    assert endpoint.health_state == "healthy"
    assert endpoint.health_score == 97

    with pytest.raises(ValidationError, match="plaintext credential"):
        await service.update_connection(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(connection.public_id),
            expected_row_version=connection.row_version,
            changes={
                "provider_configuration_json": {"nested": {"access_token": "must-never-be-here"}}
            },
        )

    other_organization, other_actor = await _create_other_tenant(db_session)
    with pytest.raises(NotFoundError):
        await service.get_connection(
            organization_id=other_organization.id,
            actor=other_actor,
            public_id=uuidlib.UUID(connection.public_id),
        )
    with pytest.raises(NotFoundError):
        await service.get_endpoint(
            organization_id=other_organization.id,
            actor=other_actor,
            public_id=uuidlib.UUID(endpoint.public_id),
        )


async def test_credentials_are_encrypted_versioned_rotatable_revocable_and_not_in_openapi(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    service = ChannelConnectionService(db_session)
    connection = await _create_connection(service, organization.id, actor)
    plaintext = "provider-secret-value-that-must-not-leak"

    first = await service.store_secret(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_type="api_token",
        plaintext=plaintext,
    )
    assert first.secret_version == 1
    assert first.key_version == 1
    assert plaintext.encode() not in first.encrypted_payload
    assert plaintext not in repr(first)
    assert "<redacted>" in repr(first)

    revealed = await service.reveal_active_secret(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_type="api_token",
        purpose="provider authentication",
    )
    assert revealed == plaintext

    replacement_plaintext = "rotated-provider-secret"
    second = await service.rotate_secret(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_type="api_token",
        plaintext=replacement_plaintext,
        expected_row_version=first.row_version,
    )
    assert second.secret_version == 2
    assert second.rotated_from_id == first.id
    assert first.status == "revoked"
    assert first.revoked_at is not None
    assert replacement_plaintext.encode() not in second.encrypted_payload
    assert second.encrypted_payload != first.encrypted_payload

    with pytest.raises(VersionConflictError):
        await service.rotate_secret(
            organization_id=organization.id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            secret_type="api_token",
            plaintext="stale-rotation",
            expected_row_version=first.row_version,
        )

    await service.revoke_secret(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(second.public_id),
        expected_row_version=second.row_version,
        reason="credential retired",
    )
    with pytest.raises(NotFoundError):
        await service.reveal_active_secret(
            organization_id=organization.id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
            secret_type="api_token",
            purpose="provider authentication",
        )

    secrets = list((await db_session.scalars(select(ChannelSecret))).all())
    assert [row.secret_version for row in secrets] == [1, 2]
    assert all(row.status == "revoked" for row in secrets)

    audit_rows = list((await db_session.scalars(select(AuditLog))).all())
    audit_payload = json.dumps(
        [
            {
                "before": row.before_json,
                "after": row.after_json,
                "metadata": row.metadata_json,
            }
            for row in audit_rows
        ],
        default=str,
    )
    assert plaintext not in audit_payload
    assert replacement_plaintext not in audit_payload
    actions = {row.action for row in audit_rows}
    assert {
        AuditAction.CHANNEL_SECRET_CREATED,
        AuditAction.CHANNEL_SECRET_ACCESSED,
        AuditAction.CHANNEL_SECRET_ROTATED,
        AuditAction.CHANNEL_SECRET_REVOKED,
    } <= actions

    from app.main import create_app

    openapi_text = json.dumps(create_app().openapi())
    assert "encrypted_payload" not in openapi_text
    assert "channel_secrets" not in openapi_text


async def test_connection_soft_delete_cascades_logical_endpoint_and_secret_shutdown(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(is_superuser=True)).user
    await _enable_flags(db_session, organization.id)
    service = ChannelConnectionService(db_session)
    connection = await _create_connection(service, organization.id, actor)
    endpoint = await service.create_endpoint(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        endpoint_type="business_address",
        normalized_address="business-99",
        provider_endpoint_id="endpoint-native-99",
        enabled=True,
    )
    secret = await service.store_secret(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_type="api_token",
        plaintext="delete-test-secret",
    )

    await service.delete_connection(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(connection.public_id),
        expected_row_version=connection.row_version,
    )

    assert connection.deleted_at is not None
    assert connection.desired_state == ProviderDesiredState.DISABLED.value
    assert connection.observed_state == ProviderObservedState.DISABLED.value
    assert endpoint.deleted_at is not None and endpoint.enabled is False
    assert secret.deleted_at is not None and secret.status == "revoked"

    with pytest.raises(NotFoundError):
        await service.get_connection(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(connection.public_id),
        )
    assert await service.list_connections(organization_id=organization.id, actor=actor) == []
