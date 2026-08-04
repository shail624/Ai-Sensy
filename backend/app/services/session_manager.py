"""Provider-neutral durable Session Manager foundation for M13-04.

The manager coordinates lifecycle, ownership, discovery, health, expiry, recovery metadata,
restart policy, capability references, leases/fencing, heartbeats, tenant isolation, RBAC, feature
flags and audit evidence. It deliberately performs no provider I/O and exposes no API route.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import Capability
from app.channels.flags import ChannelFeatureFlagResolver, OmnichannelFeatureFlag
from app.channels.foundation import (
    ProviderHealthState,
    ProviderObservedState,
)
from app.channels.registry import ProviderRegistry
from app.channels.secrets import assert_no_secret_material
from app.channels.session import (
    SESSION_TERMINAL_STATES,
    SessionLease,
    SessionRestartPolicy,
    SessionState,
    can_transition,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.db.mixins import utcnow
from app.models.channel_connection import ChannelConnection, ChannelSecret
from app.models.channel_session import ChannelSession
from app.models.user import User
from app.repositories.channel_connection import (
    ChannelConnectionRepository,
    ChannelSecretRepository,
)
from app.repositories.channel_session import ChannelSessionRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.rbac_service import RBACService


class _VersionedRow(Protocol):
    row_version: int


_STATE_TO_CONNECTION: dict[SessionState, ProviderObservedState] = {
    SessionState.REGISTERED: ProviderObservedState.AUTHENTICATION_REQUIRED,
    SessionState.INITIALIZING: ProviderObservedState.AUTHENTICATION_REQUIRED,
    SessionState.WAITING_FOR_PAIRING: ProviderObservedState.AUTHENTICATION_REQUIRED,
    SessionState.ACTIVE: ProviderObservedState.READY,
    SessionState.DEGRADED: ProviderObservedState.DEGRADED,
    SessionState.RECONNECTING: ProviderObservedState.DEGRADED,
    SessionState.PAUSED: ProviderObservedState.UNAVAILABLE,
    SessionState.EXPIRED: ProviderObservedState.AUTHENTICATION_REQUIRED,
    SessionState.TERMINATED: ProviderObservedState.DISABLED,
}


class SessionManager:
    """Durable provider-neutral session control-plane coordinator."""

    READ_PERMISSION = "channels:read"
    MANAGE_PERMISSION = "channels:manage"
    DIAGNOSE_PERMISSION = "channels:diagnose"

    def __init__(
        self,
        session: AsyncSession,
        *,
        providers: ProviderRegistry | None = None,
    ) -> None:
        self._session = session
        self._connections = ChannelConnectionRepository(session)
        self._secrets = ChannelSecretRepository(session)
        self._sessions = ChannelSessionRepository(session)
        self._flags = ChannelFeatureFlagResolver(session)
        self._rbac = RBACService(session)
        self._audit = AuditService(session)
        self._providers = providers

    async def register_session(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        owner_user_id: int | None = None,
        secret_public_id: uuidlib.UUID | None = None,
        expires_at: datetime | None = None,
        restart_policy: SessionRestartPolicy | str = SessionRestartPolicy.NEVER,
        max_reconnect_attempts: int = 3,
        capability_references: list[str] | None = None,
        recovery_metadata: dict[str, Any] | None = None,
    ) -> ChannelSession:
        await self._require_write(organization_id, actor)
        connection = await self._get_connection(organization_id, connection_public_id)
        current = await self._sessions.get_current_for_connection(
            organization_id, connection.id, for_update=True
        )
        if current is not None:
            raise ConflictError("The channel connection already has a current session.")

        owner = await self._get_owner(organization_id, owner_user_id or actor.id)
        secret = await self._resolve_secret(organization_id, connection, secret_public_id)
        latest = await self._sessions.get_latest_revision(organization_id, connection.id)
        revision = 1 if latest is None else latest.session_revision + 1
        restart = SessionRestartPolicy(restart_policy)
        if max_reconnect_attempts < 0 or max_reconnect_attempts > 100:
            raise ValidationError("max_reconnect_attempts must be between 0 and 100.")
        now = utcnow()
        if expires_at is not None and expires_at <= now:
            raise ValidationError("expires_at must be in the future.")
        self._validate_metadata(recovery_metadata, "recovery_metadata")
        capabilities, provider_snapshot = self._resolve_provider_context(
            connection, capability_references
        )

        row = ChannelSession(
            organization_id=organization_id,
            connection_id=connection.id,
            owner_user_id=owner.id,
            secret_id=secret.id if secret is not None else None,
            session_revision=revision,
            state=SessionState.REGISTERED.value,
            state_changed_at=now,
            health_state=ProviderHealthState.UNKNOWN.value,
            restart_policy=restart.value,
            max_reconnect_attempts=max_reconnect_attempts,
            expires_at=expires_at,
            capability_references_json=capabilities,
            provider_metadata_json=provider_snapshot,
            recovery_metadata_json=recovery_metadata,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._sessions.add(row)
        self._sync_connection_state(connection, SessionState.REGISTERED, now, actor.id)
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_REGISTERED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            after={
                "connection_id": connection.id,
                "session_revision": revision,
                "owner_user_id": owner.id,
                "state": row.state,
                "restart_policy": row.restart_policy,
                "capability_references": capabilities,
                "has_secret_reference": secret is not None,
            },
        )
        await self._session.commit()
        return row

    async def discover_sessions(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID | None = None,
        states: frozenset[SessionState] | None = None,
    ) -> list[ChannelSession]:
        await self._require_read(organization_id, actor)
        connection_id: int | None = None
        if connection_public_id is not None:
            connection = await self._get_connection(organization_id, connection_public_id)
            connection_id = connection.id
        return await self._sessions.list_scoped(
            organization_id, connection_id=connection_id, states=states
        )

    async def get_session(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
    ) -> ChannelSession:
        await self._require_read(organization_id, actor)
        return await self._get_session(organization_id, public_id)

    async def assign_owner(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        owner_user_id: int,
        expected_row_version: int,
    ) -> ChannelSession:
        await self._require_write(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        owner = await self._get_owner(organization_id, owner_user_id)
        before = row.owner_user_id
        row.owner_user_id = owner.id
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_OWNER_CHANGED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before={"owner_user_id": before},
            after={"owner_user_id": owner.id, "row_version": row.row_version},
        )
        await self._session.commit()
        return row

    async def transition_session(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        target_state: SessionState | str,
        detail: str | None = None,
        next_restart_at: datetime | None = None,
        recovery_metadata: dict[str, Any] | None = None,
        at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_write(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        connection = await self._get_connection_by_id(organization_id, row.connection_id)
        current = SessionState(row.state)
        target = SessionState(target_state)
        if not can_transition(current, target):
            raise ValidationError(f"Illegal session transition: {current.value} -> {target.value}.")
        now = at or utcnow()
        self._assert_not_expired(row, now, allow_expired_target=target is SessionState.EXPIRED)
        if target in {SessionState.PAUSED, SessionState.EXPIRED, SessionState.TERMINATED}:
            self._assert_no_live_holder(row, now)
        if target is SessionState.RECONNECTING:
            if row.reconnect_attempts >= row.max_reconnect_attempts:
                raise ConflictError("The session reconnect budget is exhausted.")
            row.reconnect_attempts += 1
        if next_restart_at is not None:
            if SessionRestartPolicy(row.restart_policy) is SessionRestartPolicy.NEVER:
                raise ValidationError("next_restart_at requires a restart policy.")
            if next_restart_at <= now:
                raise ValidationError("next_restart_at must be in the future.")
        self._validate_metadata(recovery_metadata, "recovery_metadata")
        before_state = row.state
        row.state = target.value
        row.state_changed_at = now
        row.state_detail = self._optional_text(detail, "detail", 500)
        row.next_restart_at = next_restart_at
        if recovery_metadata is not None:
            row.recovery_metadata_json = recovery_metadata
        if target is SessionState.ACTIVE:
            row.last_activity_at = now
            row.next_restart_at = None
        if target in {SessionState.PAUSED, SessionState.EXPIRED, SessionState.TERMINATED}:
            self._clear_holder(row)
        if target is SessionState.TERMINATED:
            row.terminated_at = now
        row.updated_by = actor.id
        row.row_version += 1
        self._sync_connection_state(connection, target, now, actor.id, detail=detail)
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_TRANSITIONED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before={"state": before_state},
            after={
                "state": row.state,
                "row_version": row.row_version,
                "reconnect_attempts": row.reconnect_attempts,
            },
        )
        await self._session.commit()
        return row

    async def acquire_lock(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        runtime_id: str,
        lease_seconds: int,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> SessionLease:
        await self._require_diagnose(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        now = at or utcnow()
        self._assert_operable(row, now)
        holder = self._text(runtime_id, "runtime_id", 160)
        lease_duration = self._lease_seconds(lease_seconds)
        if (
            row.holder_runtime_id is not None
            and row.lease_expires_at is not None
            and row.lease_expires_at > now
        ):
            raise ConflictError("The session lease is held by another active runtime.")
        row.holder_runtime_id = holder
        row.fencing_token += 1
        row.last_heartbeat_at = now
        row.lease_expires_at = now + timedelta(seconds=lease_duration)
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_LOCK_ACQUIRED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            after={
                "holder_runtime_id": holder,
                "fencing_token": row.fencing_token,
                "lease_expires_at": (
                    row.lease_expires_at.isoformat() if row.lease_expires_at is not None else None
                ),
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return SessionLease(
            session_public_id=row.public_id,
            holder_runtime_id=holder,
            fencing_token=row.fencing_token,
            lease_expires_at=row.lease_expires_at,
            session_revision=row.session_revision,
        )

    async def heartbeat(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        lease_seconds: int,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_diagnose(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        now = at or utcnow()
        self._assert_holder(row, runtime_id, fencing_token, now)
        row.last_heartbeat_at = now
        row.last_activity_at = now
        row.lease_expires_at = now + timedelta(seconds=self._lease_seconds(lease_seconds))
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_HEARTBEAT,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            after={
                "holder_runtime_id": row.holder_runtime_id,
                "fencing_token": row.fencing_token,
                "last_heartbeat_at": (
                    row.last_heartbeat_at.isoformat() if row.last_heartbeat_at is not None else None
                ),
                "lease_expires_at": (
                    row.lease_expires_at.isoformat() if row.lease_expires_at is not None else None
                ),
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def release_lock(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_diagnose(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        now = at or utcnow()
        self._assert_holder(row, runtime_id, fencing_token, now, require_live_lease=False)
        before = {
            "holder_runtime_id": row.holder_runtime_id,
            "fencing_token": row.fencing_token,
        }
        self._clear_holder(row)
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_LOCK_RELEASED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before=before,
            after={"row_version": row.row_version},
        )
        await self._session.commit()
        return row

    async def record_health(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        health_state: ProviderHealthState | str,
        health_score: int | None,
        detail: str | None = None,
        error_code: str | None = None,
        error_summary: str | None = None,
        observed_at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_diagnose(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        connection = await self._get_connection_by_id(organization_id, row.connection_id)
        now = observed_at or utcnow()
        state = ProviderHealthState(health_state)
        score = self._score(health_score)
        row.health_state = state.value
        row.health_score = score
        row.health_detail = self._optional_text(detail, "detail", 500)
        row.health_observed_at = now
        row.last_error_code = self._optional_text(error_code, "error_code", 120)
        row.last_error_summary = self._optional_text(error_summary, "error_summary", 500)
        row.updated_by = actor.id
        row.row_version += 1
        connection.health_state = state.value
        connection.health_score = score
        connection.health_detail = row.health_detail
        connection.health_observed_at = now
        connection.last_error_code = row.last_error_code
        connection.last_error_summary = row.last_error_summary
        connection.updated_by = actor.id
        connection.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_HEALTH_OBSERVED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            after={
                "health_state": row.health_state,
                "health_score": row.health_score,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def update_recovery_metadata(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        recovery_metadata: dict[str, Any] | None,
    ) -> ChannelSession:
        await self._require_write(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        self._validate_metadata(recovery_metadata, "recovery_metadata")
        row.recovery_metadata_json = recovery_metadata
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_RECOVERY_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            after={
                "has_recovery_metadata": recovery_metadata is not None,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def update_restart_policy(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        restart_policy: SessionRestartPolicy | str,
        max_reconnect_attempts: int,
    ) -> ChannelSession:
        await self._require_write(organization_id, actor)
        row = await self._get_session(organization_id, public_id, for_update=True)
        self._check_version(row, expected_row_version)
        if max_reconnect_attempts < 0 or max_reconnect_attempts > 100:
            raise ValidationError("max_reconnect_attempts must be between 0 and 100.")
        before = {
            "restart_policy": row.restart_policy,
            "max_reconnect_attempts": row.max_reconnect_attempts,
        }
        row.restart_policy = SessionRestartPolicy(restart_policy).value
        row.max_reconnect_attempts = max_reconnect_attempts
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SESSION_RESTART_POLICY_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before=before,
            after={
                "restart_policy": row.restart_policy,
                "max_reconnect_attempts": row.max_reconnect_attempts,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def expire_due_sessions(
        self,
        *,
        organization_id: int,
        actor: User,
        at: datetime | None = None,
    ) -> list[ChannelSession]:
        await self._require_diagnose(organization_id, actor)
        now = at or utcnow()
        rows = await self._sessions.list_due_for_expiration(organization_id, now)
        for row in rows:
            connection = await self._get_connection_by_id(organization_id, row.connection_id)
            before_state = row.state
            row.state = SessionState.EXPIRED.value
            row.state_changed_at = now
            row.state_detail = "session_expired"
            self._clear_holder(row)
            row.updated_by = actor.id
            row.row_version += 1
            self._sync_connection_state(connection, SessionState.EXPIRED, now, actor.id)
            await self._audit.record(
                AuditAction.CHANNEL_SESSION_EXPIRED,
                actor_user_id=actor.id,
                organization_id=organization_id,
                entity_type="channel_session",
                entity_id=row.id,
                before={"state": before_state},
                after={"state": row.state, "row_version": row.row_version},
            )
        if rows:
            await self._session.commit()
        return rows

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
        if row is None or row.organization_id != organization_id or row.deleted_at is not None:
            raise NotFoundError("Channel connection not found.")
        return row

    async def _get_session(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
    ) -> ChannelSession:
        row = await self._sessions.get_scoped(organization_id, public_id, for_update=for_update)
        if row is None:
            raise NotFoundError("Channel session not found.")
        return row

    async def _get_owner(self, organization_id: int, user_id: int) -> User:
        row = await self._session.get(User, user_id)
        if (
            row is None
            or row.organization_id != organization_id
            or row.deleted_at is not None
            or not row.is_active
        ):
            raise NotFoundError("Session owner not found.")
        return row

    async def _resolve_secret(
        self,
        organization_id: int,
        connection: ChannelConnection,
        public_id: uuidlib.UUID | None,
    ) -> ChannelSecret | None:
        if public_id is None:
            return None
        row = await self._secrets.get_scoped(organization_id, public_id, for_update=True)
        if row is None or row.connection_id != connection.id or not row.is_active:
            raise NotFoundError("Active channel credential reference not found.")
        return row

    def _resolve_provider_context(
        self,
        connection: ChannelConnection,
        requested: list[str] | None,
    ) -> tuple[list[str], dict[str, Any]]:
        metadata = self._providers.get(connection.connector_type) if self._providers else None
        if metadata is not None:
            if not metadata.lifecycle_managed:
                raise ValidationError(
                    "Provider metadata does not declare managed session lifecycle."
                )
            allowed = frozenset(capability.value for capability in metadata.capabilities)
            snapshot: dict[str, Any] = {
                "connector_type": metadata.connector_type,
                "channel_type": metadata.channel_type.value,
                "display_name": metadata.display_name,
                "lifecycle_managed": metadata.lifecycle_managed,
                "health_managed": metadata.health_managed,
            }
        else:
            allowed = frozenset(connection.capability_snapshot_json or [])
            snapshot = {
                "connector_type": connection.connector_type,
                "channel_family": connection.channel_family,
                "metadata_source": "connection_snapshot",
            }
        if requested is None:
            normalized = sorted(allowed)
        else:
            normalized = sorted({Capability(value).value for value in requested})
            unsupported = set(normalized) - set(allowed)
            if unsupported:
                raise ValidationError(
                    "Session capabilities are not declared by the connection/provider: "
                    + ", ".join(sorted(unsupported))
                )
        assert_no_secret_material(snapshot, field_name="provider_metadata")
        return normalized, snapshot

    async def _require_read(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_READ):
            raise ForbiddenError("Omnichannel session reads are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.READ_PERMISSION}):
            raise ForbiddenError("The actor cannot read channel sessions.")

    async def _require_write(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_WRITE):
            raise ForbiddenError("Omnichannel session writes are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.MANAGE_PERMISSION}):
            raise ForbiddenError("The actor cannot manage channel sessions.")

    async def _require_diagnose(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_WRITE):
            raise ForbiddenError("Omnichannel session writes are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.DIAGNOSE_PERMISSION}):
            raise ForbiddenError("The actor cannot operate channel session health or leases.")

    @staticmethod
    def _assert_actor(organization_id: int, actor: User) -> None:
        if actor.organization_id != organization_id or actor.deleted_at is not None:
            raise ForbiddenError("The actor does not belong to the requested organization.")
        if not actor.is_active:
            raise ForbiddenError("The actor is inactive.")

    @staticmethod
    def _check_version(row: _VersionedRow, expected: int) -> None:
        if row.row_version != expected:
            raise VersionConflictError("The record changed; reload and retry.")

    @staticmethod
    def _assert_operable(row: ChannelSession, now: datetime) -> None:
        state = SessionState(row.state)
        if state in SESSION_TERMINAL_STATES:
            raise ConflictError("The session is terminal and cannot acquire a runtime lease.")
        if state is SessionState.PAUSED:
            raise ConflictError("The session is paused and cannot acquire a runtime lease.")
        SessionManager._assert_not_expired(row, now)

    @staticmethod
    def _assert_not_expired(
        row: ChannelSession, now: datetime, *, allow_expired_target: bool = False
    ) -> None:
        if row.expires_at is not None and row.expires_at <= now and not allow_expired_target:
            raise ConflictError(
                "The session has expired and must be marked expired before recovery."
            )

    @staticmethod
    def _assert_no_live_holder(row: ChannelSession, now: datetime) -> None:
        if (
            row.holder_runtime_id is not None
            and row.lease_expires_at is not None
            and row.lease_expires_at > now
        ):
            raise ConflictError("Release the active session lease before this transition.")

    @staticmethod
    def _assert_holder(
        row: ChannelSession,
        runtime_id: str,
        fencing_token: int,
        now: datetime,
        *,
        require_live_lease: bool = True,
    ) -> None:
        if row.holder_runtime_id != runtime_id or row.fencing_token != fencing_token:
            raise ConflictError("The session lease holder or fencing token is stale.")
        if require_live_lease and (row.lease_expires_at is None or row.lease_expires_at <= now):
            raise ConflictError("The session lease has expired.")

    @staticmethod
    def _clear_holder(row: ChannelSession) -> None:
        row.holder_runtime_id = None
        row.lease_expires_at = None

    @staticmethod
    def _sync_connection_state(
        connection: ChannelConnection,
        state: SessionState,
        at: datetime,
        actor_user_id: int,
        *,
        detail: str | None = None,
    ) -> None:
        connection.observed_state = _STATE_TO_CONNECTION[state].value
        connection.lifecycle_changed_at = at
        connection.lifecycle_detail = detail or f"session_{state.value}"
        connection.updated_by = actor_user_id
        connection.row_version += 1

    @staticmethod
    def _validate_metadata(value: dict[str, Any] | None, field_name: str) -> None:
        if value is None:
            return
        try:
            assert_no_secret_material(value, field_name=field_name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _lease_seconds(value: int) -> int:
        if value < 5 or value > 300:
            raise ValidationError("lease_seconds must be between 5 and 300.")
        return value

    @staticmethod
    def _score(value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValidationError("health_score must be between 0 and 100.")
        return value

    @staticmethod
    def _text(value: str, field_name: str, max_length: int) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} must not be empty.")
        if len(normalized) > max_length:
            raise ValidationError(f"{field_name} must be at most {max_length} characters.")
        return normalized

    @classmethod
    def _optional_text(cls, value: str | None, field_name: str, max_length: int) -> str | None:
        if value is None:
            return None
        return cls._text(value, field_name, max_length)
