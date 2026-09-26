"""M13-04 provider-neutral Session Manager foundation tests."""

from __future__ import annotations

import json
import uuid as uuidlib
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.channels.capabilities import Capability, ChannelType
from app.channels.flags import OmnichannelFeatureFlag
from app.channels.foundation import (
    ChannelMetadata,
    ProviderDesiredState,
    ProviderHealthState,
    ProviderObservedState,
)
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.session import SessionRestartPolicy, SessionState
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.channel_connection import ChannelConnection
from app.models.channel_session import ChannelSession
from app.models.organization import Organization
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.channel_connection_service import ChannelConnectionService
from app.services.session_manager import SessionManager


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


async def _create_connection(
    session,
    organization_id: int,
    actor: User,
    *,
    provider_connection_id: str = "provider-account-session-001",
) -> ChannelConnection:
    service = ChannelConnectionService(session)
    return await service.create_connection(
        organization_id=organization_id,
        actor=actor,
        channel_family="whatsapp",
        connector_type="generic_gateway",
        provider_connection_id=provider_connection_id,
        display_name="Provider-neutral session connection",
        desired_state=ProviderDesiredState.ENABLED,
        capability_snapshot=[Capability.TEXT.value, Capability.HEALTH.value],
        provider_configuration={"region": "in"},
        provider_metadata={"environment": "test"},
    )


def _provider_registry() -> ProviderRegistry:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    providers.register(
        ChannelMetadata(
            connector_type="generic_gateway",
            channel_type=ChannelType.WHATSAPP,
            display_name="Generic managed session provider",
            capabilities=frozenset({Capability.TEXT, Capability.HEALTH}),
            lifecycle_managed=True,
            health_managed=True,
        )
    )
    return providers


async def _create_other_tenant(session) -> tuple[Organization, User]:
    organization = Organization(name="Session Other Tenant", slug="session-other-tenant")
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        email="session-other@example.test",
        password_hash="not-used",
        full_name="Other Session Operator",
        is_superuser=True,
    )
    session.add(user)
    await session.flush()
    await _enable_flags(session, organization.id)
    return organization, user


async def test_session_flags_and_rbac_fail_closed(db_session, make_user, organization) -> None:
    admin = (
        await make_user(
            email="session-admin-flags@example.test",
            roles=("admin",),
        )
    ).user
    connection_actor = admin
    connection_service = ChannelConnectionService(db_session)

    with pytest.raises(ForbiddenError):
        await connection_service.create_connection(
            organization_id=organization.id,
            actor=connection_actor,
            channel_family="whatsapp",
            connector_type="generic_gateway",
            display_name="flags disabled",
        )

    await _enable_flags(db_session, organization.id)
    connection = await _create_connection(db_session, organization.id, connection_actor)
    unprivileged = (
        await make_user(
            email="session-unprivileged@example.test",
            roles=(),
        )
    ).user
    manager = SessionManager(db_session)
    with pytest.raises(ForbiddenError, match="cannot manage"):
        await manager.register_session(
            organization_id=organization.id,
            actor=unprivileged,
            connection_public_id=uuidlib.UUID(connection.public_id),
        )

    assert (await db_session.scalars(select(ChannelSession))).all() == []


async def test_session_registration_discovery_provider_metadata_and_secret_reference(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="session-register@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    connection = await _create_connection(db_session, organization.id, actor)
    connection_service = ChannelConnectionService(db_session)
    secret_plaintext = "session-provider-secret-that-must-not-leak"
    secret = await connection_service.store_secret(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_type="session_material",
        plaintext=secret_plaintext,
    )
    manager = SessionManager(db_session, providers=_provider_registry())
    session = await manager.register_session(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        secret_public_id=uuidlib.UUID(secret.public_id),
        restart_policy=SessionRestartPolicy.ON_FAILURE,
        capability_references=[Capability.HEALTH.value],
        recovery_metadata={"checkpoint_ref": "cold-start-1"},
    )

    assert session.state == SessionState.REGISTERED.value
    assert session.session_revision == 1
    assert session.owner_user_id == actor.id
    assert session.secret_id == secret.id
    assert session.capability_references_json == [Capability.HEALTH.value]
    assert session.provider_metadata_json == {
        "connector_type": "generic_gateway",
        "channel_type": "whatsapp",
        "display_name": "Generic managed session provider",
        "lifecycle_managed": True,
        "health_managed": True,
    }
    assert secret_plaintext not in repr(session)
    assert "reference-only" in repr(session)
    assert connection.observed_state == ProviderObservedState.AUTHENTICATION_REQUIRED.value

    discovered = await manager.discover_sessions(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
    )
    assert [row.id for row in discovered] == [session.id]

    with pytest.raises(ConflictError, match="already has a current session"):
        await manager.register_session(
            organization_id=organization.id,
            actor=actor,
            connection_public_id=uuidlib.UUID(connection.public_id),
        )
    with pytest.raises(ValidationError, match="plaintext credential"):
        await manager.update_recovery_metadata(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            expected_row_version=session.row_version,
            recovery_metadata={"access_token": "forbidden"},
        )

    other_organization, other_actor = await _create_other_tenant(db_session)
    with pytest.raises(NotFoundError):
        await manager.get_session(
            organization_id=other_organization.id,
            actor=other_actor,
            public_id=uuidlib.UUID(session.public_id),
        )

    from app.main import create_app

    openapi_text = json.dumps(create_app().openapi())
    assert "channel_sessions" not in openapi_text
    assert "holder_runtime_id" not in openapi_text
    assert secret_plaintext not in openapi_text


async def test_session_lifecycle_optimistic_locking_and_connection_state(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="session-lifecycle@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    connection = await _create_connection(db_session, organization.id, actor)
    manager = SessionManager(db_session)
    session = await manager.register_session(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        restart_policy=SessionRestartPolicy.ON_FAILURE,
        max_reconnect_attempts=2,
    )

    with pytest.raises(ValidationError, match="Illegal session transition"):
        await manager.transition_session(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            expected_row_version=session.row_version,
            target_state=SessionState.ACTIVE,
        )

    sequence = [
        SessionState.INITIALIZING,
        SessionState.WAITING_FOR_PAIRING,
        SessionState.ACTIVE,
        SessionState.DEGRADED,
        SessionState.RECONNECTING,
        SessionState.ACTIVE,
        SessionState.PAUSED,
        SessionState.INITIALIZING,
        SessionState.WAITING_FOR_PAIRING,
        SessionState.ACTIVE,
        SessionState.EXPIRED,
        SessionState.INITIALIZING,
        SessionState.TERMINATED,
    ]
    for target in sequence:
        expected = session.row_version
        session = await manager.transition_session(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            expected_row_version=expected,
            target_state=target,
            detail=f"state {target.value}",
        )
        assert session.state == target.value
        assert session.row_version == expected + 1

    assert session.terminated_at is not None
    assert connection.observed_state == ProviderObservedState.DISABLED.value
    with pytest.raises(VersionConflictError):
        await manager.assign_owner(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            owner_user_id=actor.id,
            expected_row_version=0,
        )


async def test_session_lock_heartbeat_fencing_and_concurrency_protection(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="session-lock@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    connection = await _create_connection(db_session, organization.id, actor)
    manager = SessionManager(db_session)
    session = await manager.register_session(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
    )
    session = await manager.transition_session(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        expected_row_version=session.row_version,
        target_state=SessionState.INITIALIZING,
    )
    now = utcnow()
    lease = await manager.acquire_lock(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        runtime_id="runtime-a",
        lease_seconds=30,
        expected_row_version=session.row_version,
        at=now,
    )
    assert lease.fencing_token == 1
    assert session.holder_runtime_id == "runtime-a"

    with pytest.raises(ConflictError, match="held by another"):
        await manager.acquire_lock(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            runtime_id="runtime-b",
            lease_seconds=30,
            expected_row_version=session.row_version,
            at=now + timedelta(seconds=1),
        )
    with pytest.raises(ConflictError, match="stale"):
        await manager.heartbeat(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            runtime_id="runtime-a",
            fencing_token=0,
            lease_seconds=30,
            expected_row_version=session.row_version,
            at=now + timedelta(seconds=2),
        )

    session = await manager.heartbeat(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        runtime_id="runtime-a",
        fencing_token=lease.fencing_token,
        lease_seconds=30,
        expected_row_version=session.row_version,
        at=now + timedelta(seconds=2),
    )
    with pytest.raises(ConflictError, match="Release the active"):
        await manager.transition_session(
            organization_id=organization.id,
            actor=actor,
            public_id=uuidlib.UUID(session.public_id),
            expected_row_version=session.row_version,
            target_state=SessionState.PAUSED,
            at=now + timedelta(seconds=3),
        )

    session = await manager.release_lock(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        runtime_id="runtime-a",
        fencing_token=lease.fencing_token,
        expected_row_version=session.row_version,
        at=now + timedelta(seconds=3),
    )
    lease_b = await manager.acquire_lock(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        runtime_id="runtime-b",
        lease_seconds=5,
        expected_row_version=session.row_version,
        at=now + timedelta(seconds=4),
    )
    assert lease_b.fencing_token == 2

    session = await manager.acquire_lock(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        runtime_id="runtime-c",
        lease_seconds=30,
        expected_row_version=session.row_version,
        at=lease_b.lease_expires_at + timedelta(microseconds=1),
    )
    assert session.fencing_token == 3
    assert session.holder_runtime_id == "runtime-c"

    actions = {row.action for row in (await db_session.scalars(select(AuditLog))).all()}
    assert {
        AuditAction.CHANNEL_SESSION_LOCK_ACQUIRED,
        AuditAction.CHANNEL_SESSION_HEARTBEAT,
        AuditAction.CHANNEL_SESSION_LOCK_RELEASED,
    } <= actions


async def test_session_health_recovery_restart_ownership_expiration_and_new_revision(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="session-recovery@example.test", roles=("admin",))).user
    new_owner = (await make_user(email="session-owner@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    connection = await _create_connection(db_session, organization.id, actor)
    manager = SessionManager(db_session)
    now = utcnow()
    session = await manager.register_session(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        expires_at=now + timedelta(minutes=5),
        recovery_metadata={"resume_checkpoint": "checkpoint-1"},
    )
    session = await manager.update_restart_policy(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        expected_row_version=session.row_version,
        restart_policy=SessionRestartPolicy.ALWAYS,
        max_reconnect_attempts=4,
    )
    session = await manager.record_health(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        expected_row_version=session.row_version,
        health_state=ProviderHealthState.DEGRADED,
        health_score=42,
        detail="provider-neutral health evidence",
        error_code="transient_unavailable",
        error_summary="No provider secret or provider-specific payload",
        observed_at=now + timedelta(seconds=1),
    )
    session = await manager.assign_owner(
        organization_id=organization.id,
        actor=actor,
        public_id=uuidlib.UUID(session.public_id),
        owner_user_id=new_owner.id,
        expected_row_version=session.row_version,
    )
    assert session.owner_user_id == new_owner.id
    assert session.restart_policy == SessionRestartPolicy.ALWAYS.value
    assert session.health_state == ProviderHealthState.DEGRADED.value
    assert connection.health_state == ProviderHealthState.DEGRADED.value

    expired = await manager.expire_due_sessions(
        organization_id=organization.id,
        actor=actor,
        at=now + timedelta(minutes=6),
    )
    assert [row.id for row in expired] == [session.id]
    assert session.state == SessionState.EXPIRED.value
    assert connection.observed_state == ProviderObservedState.AUTHENTICATION_REQUIRED.value

    replacement = await manager.register_session(
        organization_id=organization.id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        restart_policy=SessionRestartPolicy.ON_FAILURE,
    )
    assert replacement.session_revision == 2
    assert replacement.state == SessionState.REGISTERED.value

    audit_payload = json.dumps(
        [
            {
                "before": row.before_json,
                "after": row.after_json,
                "metadata": row.metadata_json,
            }
            for row in (await db_session.scalars(select(AuditLog))).all()
        ],
        default=str,
    )
    assert "access_token" not in audit_payload
    assert "encrypted_payload" not in audit_payload
    actions = {row.action for row in (await db_session.scalars(select(AuditLog))).all()}
    assert {
        AuditAction.CHANNEL_SESSION_REGISTERED,
        AuditAction.CHANNEL_SESSION_OWNER_CHANGED,
        AuditAction.CHANNEL_SESSION_HEALTH_OBSERVED,
        AuditAction.CHANNEL_SESSION_RESTART_POLICY_UPDATED,
        AuditAction.CHANNEL_SESSION_EXPIRED,
    } <= actions
