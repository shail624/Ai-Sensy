"""M13-05 provider-neutral runtime registry and no-store pairing foundation tests."""

from __future__ import annotations

import json
import uuid as uuidlib
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.channels.capabilities import Capability, ChannelType
from app.channels.errors import ChannelConfigError
from app.channels.flags import OmnichannelFeatureFlag
from app.channels.foundation import (
    ChannelMetadata,
    ProviderDesiredState,
    ProviderHealthState,
)
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime import PairingState, RuntimeMetadata
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionRestartPolicy, SessionState
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.mixins import utcnow
from app.models.audit import AuditLog
from app.models.channel_connection import ChannelConnection
from app.models.organization import Organization
from app.models.role import Permission, Role, UserRole
from app.models.settings import FeatureFlag
from app.models.user import User
from app.services.audit_service import AuditAction
from app.services.channel_connection_service import ChannelConnectionService
from app.services.pairing_manager import PairingManager
from app.services.provider_runtime_manager import ProviderRuntimeManager
from app.services.session_manager import SessionManager

_RUNTIME_CAPABILITIES = frozenset(
    {
        Capability.QR_AUTH,
        Capability.SESSION_STREAM,
        Capability.SESSION_RECONNECT,
        Capability.SESSION_LOGOUT,
        Capability.HEALTH,
    }
)


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


def _registries() -> tuple[ProviderRegistry, ProviderRuntimeRegistry]:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    providers.register(
        ChannelMetadata(
            connector_type="managed_runtime",
            channel_type=ChannelType.WHATSAPP,
            display_name="Managed provider-neutral runtime",
            capabilities=_RUNTIME_CAPABILITIES,
            lifecycle_managed=True,
            health_managed=True,
        )
    )
    runtimes = ProviderRuntimeRegistry(providers)
    runtimes.register(
        RuntimeMetadata(
            connector_type="managed_runtime",
            display_name="Managed runtime host",
            capabilities=_RUNTIME_CAPABILITIES,
            pairing_managed=True,
            pairing_ttl_seconds=60,
            heartbeat_interval_seconds=15,
            lease_seconds=45,
        )
    )
    return providers, runtimes


async def _create_connection(
    session,
    organization_id: int,
    actor: User,
    *,
    provider_connection_id: str = "runtime-connection-001",
) -> ChannelConnection:
    return await ChannelConnectionService(session).create_connection(
        organization_id=organization_id,
        actor=actor,
        channel_family="whatsapp",
        connector_type="managed_runtime",
        provider_connection_id=provider_connection_id,
        display_name="Provider runtime connection",
        desired_state=ProviderDesiredState.ENABLED,
        capability_snapshot=[capability.value for capability in _RUNTIME_CAPABILITIES],
        provider_configuration={"region": "in"},
        provider_metadata={"runtime_mode": "managed"},
    )


async def _create_session(session, organization_id: int, actor: User, providers: ProviderRegistry):
    connection = await _create_connection(session, organization_id, actor)
    row = await SessionManager(session, providers=providers).register_session(
        organization_id=organization_id,
        actor=actor,
        connection_public_id=uuidlib.UUID(connection.public_id),
        restart_policy=SessionRestartPolicy.ON_FAILURE,
        capability_references=[capability.value for capability in _RUNTIME_CAPABILITIES],
        recovery_metadata={"checkpoint_ref": "runtime-cold-start"},
    )
    return connection, row


async def _create_other_tenant(session) -> tuple[Organization, User]:
    organization = Organization(name="Runtime Other Tenant", slug="runtime-other-tenant")
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        email="runtime-other@example.test",
        password_hash="not-used",
        full_name="Other Runtime Operator",
        is_superuser=True,
    )
    session.add(user)
    await session.flush()
    await _enable_flags(session, organization.id)
    return organization, user


def test_runtime_registry_reuses_provider_capability_authority() -> None:
    providers, runtimes = _registries()

    assert runtimes.available() == ("managed_runtime",)
    assert runtimes.require("managed_runtime").capabilities == _RUNTIME_CAPABILITIES
    assert providers.require("managed_runtime").capabilities == _RUNTIME_CAPABILITIES

    with pytest.raises(ChannelConfigError, match="not declared by provider"):
        runtimes.register(
            RuntimeMetadata(
                connector_type="managed_runtime",
                display_name="Invalid expanded runtime",
                capabilities=_RUNTIME_CAPABILITIES | {Capability.TEXT},
                pairing_managed=True,
            ),
            replace=True,
        )
    with pytest.raises(ChannelConfigError, match="pairing_ttl_seconds"):
        RuntimeMetadata(
            connector_type="managed_runtime",
            display_name="Unsafe long pairing lifetime",
            capabilities=_RUNTIME_CAPABILITIES,
            pairing_managed=True,
            pairing_ttl_seconds=301,
        )
    with pytest.raises(ChannelConfigError, match="already registered"):
        runtimes.register(
            RuntimeMetadata(
                connector_type="managed_runtime",
                display_name="Conflicting runtime",
                capabilities=_RUNTIME_CAPABILITIES,
                pairing_managed=True,
            )
        )


async def test_runtime_and_pairing_flags_and_rbac_fail_closed(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="runtime-flags@example.test", roles=("admin",))).user
    providers, runtimes = _registries()

    with pytest.raises(ForbiddenError):
        await _create_connection(db_session, organization.id, actor)

    await _enable_flags(db_session, organization.id)
    _, row = await _create_session(db_session, organization.id, actor, providers)
    unprivileged = (
        await make_user(email="runtime-unprivileged@example.test", roles=())
    ).user
    manager = ProviderRuntimeManager(db_session, runtimes=runtimes)
    pairing = PairingManager(db_session, runtimes=runtimes)

    with pytest.raises(ForbiddenError, match="cannot discover"):
        await manager.discover_runtime_types(
            organization_id=organization.id,
            actor=unprivileged,
        )
    with pytest.raises(ForbiddenError, match="cannot manage channel pairing"):
        await pairing.transition_pairing(
            organization_id=organization.id,
            actor=unprivileged,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-a",
            fencing_token=1,
            expected_row_version=row.row_version,
            target_state=PairingState.PAIRING_REQUESTED,
        )

    auth_only = (
        await make_user(email="runtime-auth-only@example.test", roles=())
    ).user
    permission = (
        await db_session.scalars(
            select(Permission).where(Permission.code == "channels:authenticate")
        )
    ).one()
    role = Role(
        organization_id=organization.id,
        name="pairing-auth-only",
        description="Pairing without diagnostics access",
    )
    role.permissions = [permission]
    db_session.add(role)
    await db_session.flush()
    db_session.add(UserRole(user_id=auth_only.id, role_id=role.id, assigned_by=actor.id))
    await db_session.commit()

    lease = await manager.claim_session(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-auth",
        expected_row_version=row.row_version,
    )
    row = await manager.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-auth",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.INITIALIZING,
    )
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=auth_only,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-auth",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_REQUESTED,
    )
    assert row.pairing_state == PairingState.PAIRING_REQUESTED.value


async def test_runtime_claim_heartbeat_health_capabilities_restart_and_recovery(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="runtime-manager@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    connection, row = await _create_session(db_session, organization.id, actor, providers)
    manager = ProviderRuntimeManager(db_session, runtimes=runtimes)
    now = utcnow()

    assert [item.connector_type for item in await manager.discover_runtime_types(
        organization_id=organization.id,
        actor=actor,
    )] == ["managed_runtime"]

    lease = await manager.claim_session(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-a",
        expected_row_version=row.row_version,
        at=now,
    )
    assert lease.lease_expires_at == now + timedelta(seconds=45)
    assert row.holder_runtime_id == "runtime-a"

    row = await manager.heartbeat(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-a",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        at=now + timedelta(seconds=10),
    )
    row = await manager.publish_capabilities(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-a",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        capabilities=[Capability.QR_AUTH, Capability.HEALTH],
        at=now + timedelta(seconds=11),
    )
    assert row.capability_references_json == sorted(
        capability.value for capability in _RUNTIME_CAPABILITIES
    )
    assert row.runtime_capabilities_json == [Capability.HEALTH.value, Capability.QR_AUTH.value]

    with pytest.raises(ConflictError, match="stale"):
        await manager.record_health(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-a",
            fencing_token=lease.fencing_token + 1,
            expected_row_version=row.row_version,
            health_state=ProviderHealthState.HEALTHY,
            health_score=98,
        )
    with pytest.raises(ConflictError, match="stale"):
        await manager.transition_runtime(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-a",
            fencing_token=lease.fencing_token + 1,
            expected_row_version=row.row_version,
            target_state=SessionState.INITIALIZING,
        )

    row = await manager.record_health(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-a",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        health_state=ProviderHealthState.HEALTHY,
        health_score=98,
        detail="runtime control-plane healthy",
        observed_at=now + timedelta(seconds=12),
    )
    row = await manager.update_restart_policy(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        expected_row_version=row.row_version,
        restart_policy=SessionRestartPolicy.ALWAYS,
        max_reconnect_attempts=5,
    )
    row = await manager.update_recovery_metadata(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        expected_row_version=row.row_version,
        recovery_metadata={"resume_ref": "runtime-resume-2"},
    )

    assert row.health_state == ProviderHealthState.HEALTHY.value
    assert connection.health_state == ProviderHealthState.HEALTHY.value
    assert row.restart_policy == SessionRestartPolicy.ALWAYS.value
    assert row.recovery_metadata_json == {"resume_ref": "runtime-resume-2"}
    diagnostics = await manager.diagnostics(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
    )
    assert diagnostics.connector_type == "managed_runtime"
    assert diagnostics.runtime_id == "runtime-a"
    assert diagnostics.runtime_capabilities == (
        Capability.HEALTH.value,
        Capability.QR_AUTH.value,
    )
    with pytest.raises(ValidationError, match="declared by both"):
        await manager.publish_capabilities(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-a",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            capabilities=[Capability.TEXT],
        )


async def test_pairing_lifecycle_is_runtime_owned_persisted_and_no_store(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="pairing-lifecycle@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    _, row = await _create_session(db_session, organization.id, actor, providers)
    runtime = ProviderRuntimeManager(db_session, runtimes=runtimes)
    pairing = PairingManager(db_session, runtimes=runtimes)
    now = utcnow()

    lease = await runtime.claim_session(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        expected_row_version=row.row_version,
        at=now,
    )
    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.INITIALIZING,
        at=now + timedelta(seconds=1),
    )
    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.WAITING_FOR_PAIRING,
        at=now + timedelta(seconds=2),
    )

    with pytest.raises(ValidationError, match="reason_code"):
        await pairing.transition_pairing(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-pairing",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            target_state=PairingState.PAIRING_REQUESTED,
            reason_code="qr://must-not-be-persisted",
        )

    sequence = [
        (PairingState.PAIRING_REQUESTED, None),
        (PairingState.PAIRING_AVAILABLE, now + timedelta(seconds=32)),
        (PairingState.PAIRED, None),
    ]
    for offset, (target, expires_at) in enumerate(sequence, start=3):
        row = await pairing.transition_pairing(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-pairing",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            target_state=target,
            expires_at=expires_at,
            reason_code=f"pairing_{target.value}",
            at=now + timedelta(seconds=offset),
        )
    assert row.pairing_revision == 1
    assert row.pairing_state == PairingState.PAIRED.value

    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.ACTIVE,
        at=now + timedelta(seconds=7),
    )
    assert row.state == SessionState.ACTIVE.value
    assert row.pairing_state == PairingState.PAIRED.value
    assert row.pairing_expires_at is None

    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.RECONNECTING,
        at=now + timedelta(seconds=8),
    )
    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.ACTIVE,
        at=now + timedelta(seconds=9),
    )
    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-pairing",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.EXPIRED,
        detail="reauthentication_required",
        at=now + timedelta(seconds=10),
    )
    assert row.holder_runtime_id is None
    assert row.runtime_capabilities_json is None
    with pytest.raises(ConflictError, match="new session revision"):
        await runtime.transition_runtime(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-pairing",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            target_state=SessionState.INITIALIZING,
        )

    from app.main import create_app

    openapi = json.dumps(create_app().openapi())
    # QR-07 intentionally builds the first public surface over this pairing state machine
    # (`/channels/whatsapp-qr/*`, 6 routes) — the path count and `pairing_state` appearing are
    # therefore expected from this milestone on, not a regression. What must still never appear
    # is a raw secret shape: no QR bytes, no provider credential, no internal reason code.
    assert len(create_app().openapi()["paths"]) == 206
    assert "qr_payload" not in openapi
    assert "pairing_secret" not in openapi
    assert "pairing_reason_code" not in openapi


async def test_pairing_expiration_retry_cancel_and_stale_runtime_protection(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="pairing-expiry@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    _, row = await _create_session(db_session, organization.id, actor, providers)
    runtime = ProviderRuntimeManager(db_session, runtimes=runtimes)
    pairing = PairingManager(db_session, runtimes=runtimes)
    now = utcnow()

    lease = await runtime.claim_session(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        expected_row_version=row.row_version,
        at=now,
    )
    row = await runtime.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.INITIALIZING,
    )
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_REQUESTED,
    )
    with pytest.raises(ValidationError, match="pairing TTL"):
        await pairing.transition_pairing(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-expiry",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            target_state=PairingState.PAIRING_AVAILABLE,
            expires_at=now + timedelta(seconds=61),
            at=now,
        )
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_AVAILABLE,
        expires_at=now + timedelta(seconds=20),
        at=now,
    )

    with pytest.raises(ConflictError, match="stale"):
        await pairing.transition_pairing(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-expiry",
            fencing_token=lease.fencing_token + 1,
            expected_row_version=row.row_version,
            target_state=PairingState.PAIRED,
        )

    with pytest.raises(ConflictError, match="has expired"):
        await pairing.transition_pairing(
            organization_id=organization.id,
            actor=actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-expiry",
            fencing_token=lease.fencing_token,
            expected_row_version=row.row_version,
            target_state=PairingState.PAIRED,
            at=now + timedelta(seconds=21),
        )

    with pytest.raises(ValidationError, match="limit"):
        await pairing.expire_due_pairings(
            organization_id=organization.id,
            actor=actor,
            at=now + timedelta(seconds=21),
            limit=0,
        )

    expired = await pairing.expire_due_pairings(
        organization_id=organization.id,
        actor=actor,
        at=now + timedelta(seconds=21),
    )
    assert [item.id for item in expired] == [row.id]
    assert row.pairing_state == PairingState.PAIRING_EXPIRED.value
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_REQUESTED,
    )
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-expiry",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_CANCELLED,
    )
    assert row.pairing_revision == 2
    assert row.pairing_state == PairingState.PAIRING_CANCELLED.value


async def test_runtime_tenant_isolation_and_audit_redaction(
    db_session, make_user, organization
) -> None:
    actor = (await make_user(email="runtime-isolation@example.test", roles=("admin",))).user
    await _enable_flags(db_session, organization.id)
    providers, runtimes = _registries()
    _, row = await _create_session(db_session, organization.id, actor, providers)
    other_org, other_actor = await _create_other_tenant(db_session)
    manager = ProviderRuntimeManager(db_session, runtimes=runtimes)
    pairing = PairingManager(db_session, runtimes=runtimes)

    with pytest.raises(NotFoundError):
        await pairing.get_pairing_session(
            organization_id=other_org.id,
            actor=other_actor,
            session_public_id=uuidlib.UUID(row.public_id),
        )
    with pytest.raises(NotFoundError):
        await manager.claim_session(
            organization_id=other_org.id,
            actor=other_actor,
            session_public_id=uuidlib.UUID(row.public_id),
            runtime_id="runtime-foreign",
            expected_row_version=row.row_version,
        )

    lease = await manager.claim_session(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-redaction",
        expected_row_version=row.row_version,
    )
    row = await manager.transition_runtime(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-redaction",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=SessionState.INITIALIZING,
    )
    row = await pairing.transition_pairing(
        organization_id=organization.id,
        actor=actor,
        session_public_id=uuidlib.UUID(row.public_id),
        runtime_id="runtime-redaction",
        fencing_token=lease.fencing_token,
        expected_row_version=row.row_version,
        target_state=PairingState.PAIRING_REQUESTED,
        reason_code="pairing_requested",
    )

    audit_rows = list((await db_session.scalars(select(AuditLog))).all())
    payload = json.dumps(
        [
            {
                "action": item.action,
                "before": item.before_json,
                "after": item.after_json,
                "metadata": item.metadata_json,
            }
            for item in audit_rows
        ],
        default=str,
    )
    assert "qr_payload" not in payload
    assert "session_material" not in payload
    assert "access_token" not in payload
    actions = {item.action for item in audit_rows}
    assert {
        AuditAction.CHANNEL_SESSION_LOCK_ACQUIRED,
        AuditAction.CHANNEL_SESSION_TRANSITIONED,
        AuditAction.CHANNEL_PAIRING_TRANSITIONED,
    } <= actions
