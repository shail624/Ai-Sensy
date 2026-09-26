"""Provider-neutral runtime control-plane orchestration for M13-05.

The manager adds runtime registration/capability validation and the QR-provider rollout gate around
the existing Session Manager. It does not create a second adapter hierarchy, provider process,
message path, QR artifact, or durable runtime table. Session leases, fencing, lifecycle, health,
restart and recovery remain authoritative in ``channel_sessions``.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError
from app.channels.flags import ChannelFeatureFlagResolver, OmnichannelFeatureFlag
from app.channels.foundation import ProviderHealthState
from app.channels.runtime import (
    PairingState,
    RuntimeDiagnostics,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeMetadata,
)
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SessionLease, SessionRestartPolicy, SessionState
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.mixins import utcnow
from app.models.channel_connection import ChannelConnection
from app.models.channel_session import ChannelSession
from app.models.user import User
from app.repositories.channel_connection import ChannelConnectionRepository
from app.repositories.channel_session import ChannelSessionRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.rbac_service import RBACService
from app.services.session_manager import SessionManager


class ProviderRuntimeManager:
    """Coordinate registered runtime metadata with durable provider-neutral sessions."""

    READ_PERMISSION = "channels:read"
    DIAGNOSE_PERMISSION = "channels:diagnose"

    def __init__(
        self,
        session: AsyncSession,
        *,
        runtimes: ProviderRuntimeRegistry,
    ) -> None:
        self._session = session
        self._runtimes = runtimes
        self._sessions = ChannelSessionRepository(session)
        self._connections = ChannelConnectionRepository(session)
        self._session_manager = SessionManager(session)
        self._flags = ChannelFeatureFlagResolver(session)
        self._rbac = RBACService(session)
        self._audit = AuditService(session)

    async def discover_runtime_types(
        self, *, organization_id: int, actor: User
    ) -> tuple[RuntimeMetadata, ...]:
        """Return configured runtime types after tenant, flag and RBAC checks."""

        await self._require_read(organization_id, actor)
        return self._runtimes.registrations()

    async def diagnostics(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
    ) -> RuntimeDiagnostics:
        """Return factual, redacted diagnostics without provider payloads or credentials."""

        await self._require_operate(organization_id, actor)
        row, connection, _ = await self._runtime_context(organization_id, session_public_id)
        return RuntimeDiagnostics(
            connector_type=connection.connector_type,
            session_public_id=row.public_id,
            session_revision=row.session_revision,
            session_state=row.state,
            pairing_state=row.pairing_state,
            pairing_revision=row.pairing_revision,
            runtime_id=row.holder_runtime_id,
            fencing_token=row.fencing_token,
            lease_expires_at=row.lease_expires_at,
            last_heartbeat_at=row.last_heartbeat_at,
            health_state=row.health_state,
            health_score=row.health_score,
            reconnect_attempts=row.reconnect_attempts,
            max_reconnect_attempts=row.max_reconnect_attempts,
            restart_policy=row.restart_policy,
            runtime_capabilities=tuple(row.runtime_capabilities_json or ()),
            last_error_code=row.last_error_code,
        )

    async def claim_session(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> SessionLease:
        """Acquire the existing durable lease for a registered runtime type."""

        await self._require_operate(organization_id, actor)
        _, _, runtime = await self._runtime_context(organization_id, session_public_id)
        return await self._session_manager.acquire_lock(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            runtime_id=runtime_id,
            lease_seconds=runtime.lease_seconds,
            expected_row_version=expected_row_version,
            at=at,
        )

    async def heartbeat(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> ChannelSession:
        """Extend the durable lease using the registered runtime's bounded default."""

        await self._require_operate(organization_id, actor)
        _, _, runtime = await self._runtime_context(organization_id, session_public_id)
        return await self._session_manager.heartbeat(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
            lease_seconds=runtime.lease_seconds,
            expected_row_version=expected_row_version,
            at=at,
        )

    async def release_session(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_operate(organization_id, actor)
        await self._runtime_context(organization_id, session_public_id)
        return await self._session_manager.release_lock(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
            expected_row_version=expected_row_version,
            at=at,
        )

    async def transition_runtime(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        target_state: SessionState | str,
        detail: str | None = None,
        next_restart_at: datetime | None = None,
        recovery_metadata: dict[str, object] | None = None,
        at: datetime | None = None,
    ) -> ChannelSession:
        """Apply a fenced runtime observation through the existing session lifecycle."""

        await self._require_operate(organization_id, actor)
        row, _, runtime = await self._runtime_context(organization_id, session_public_id)
        current = SessionState(row.state)
        target = SessionState(target_state)
        if target is SessionState.RECONNECTING:
            self._require_capability(runtime, Capability.SESSION_RECONNECT)
        if target is SessionState.TERMINATED:
            self._require_capability(runtime, Capability.SESSION_LOGOUT)
        if (
            runtime.pairing_managed
            and target is SessionState.ACTIVE
            and PairingState(row.pairing_state) is not PairingState.PAIRED
        ):
            raise ConflictError("The session cannot become active before pairing succeeds.")
        if (
            runtime.pairing_managed
            and current is SessionState.EXPIRED
            and target is SessionState.INITIALIZING
        ):
            raise ConflictError(
                "Pairing-managed re-authentication requires a new session revision."
            )
        return await self._session_manager.transition_session(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            expected_row_version=expected_row_version,
            target_state=target,
            detail=detail,
            next_restart_at=next_restart_at,
            recovery_metadata=recovery_metadata,
            at=at,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
        )

    async def record_health(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        health_state: ProviderHealthState | str,
        health_score: int | None,
        detail: str | None = None,
        error_code: str | None = None,
        error_summary: str | None = None,
        observed_at: datetime | None = None,
    ) -> ChannelSession:
        await self._require_operate(organization_id, actor)
        _, _, runtime = await self._runtime_context(organization_id, session_public_id)
        self._require_capability(runtime, Capability.HEALTH)
        return await self._session_manager.record_health(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            expected_row_version=expected_row_version,
            health_state=health_state,
            health_score=health_score,
            detail=detail,
            error_code=error_code,
            error_summary=error_summary,
            observed_at=observed_at,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
        )

    async def publish_capabilities(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        capabilities: list[Capability | str],
        at: datetime | None = None,
    ) -> ChannelSession:
        """Persist the runtime-observed subset of already declared session capabilities."""

        await self._require_operate(organization_id, actor)
        row = await self._session_manager.lock_runtime_owned_session(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
            expected_row_version=expected_row_version,
            at=at,
        )
        connection = await self._connection_for_session(organization_id, row)
        runtime = self._require_runtime(connection.connector_type)
        published = self._capability_set(capabilities, field_name="runtime capabilities")
        declared = self._capability_set(
            row.capability_references_json or [], field_name="session capabilities"
        )
        unsupported = published - runtime.capabilities
        undeclared = published - declared
        if unsupported or undeclared:
            rejected = unsupported | undeclared
            names = ", ".join(sorted(capability.value for capability in rejected))
            raise ValidationError(
                "Runtime capabilities must be declared by both the runtime and session: " + names
            )
        normalized = sorted(capability.value for capability in published)
        if normalized == (row.runtime_capabilities_json or []):
            return row

        now = at or utcnow()
        before = list(row.runtime_capabilities_json or [])
        row.runtime_capabilities_json = normalized
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        event = RuntimeEvent(
            event_type=RuntimeEventType.CAPABILITIES_PUBLISHED,
            organization_id=organization_id,
            session_public_id=row.public_id,
            runtime_id=runtime_id,
            occurred_at=now,
            state=row.state,
            capabilities=tuple(normalized),
        )
        await self._audit.record(
            AuditAction.CHANNEL_RUNTIME_CAPABILITIES_PUBLISHED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before={"capabilities": before},
            after={**event.audit_payload(), "row_version": row.row_version},
        )
        await self._session.commit()
        return row

    async def update_restart_policy(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        expected_row_version: int,
        restart_policy: SessionRestartPolicy | str,
        max_reconnect_attempts: int,
    ) -> ChannelSession:
        await self._require_operate(organization_id, actor)
        await self._runtime_context(organization_id, session_public_id)
        return await self._session_manager.update_restart_policy(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            expected_row_version=expected_row_version,
            restart_policy=restart_policy,
            max_reconnect_attempts=max_reconnect_attempts,
        )

    async def update_recovery_metadata(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        expected_row_version: int,
        recovery_metadata: dict[str, object] | None,
    ) -> ChannelSession:
        await self._require_operate(organization_id, actor)
        await self._runtime_context(organization_id, session_public_id)
        return await self._session_manager.update_recovery_metadata(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            expected_row_version=expected_row_version,
            recovery_metadata=recovery_metadata,
        )

    async def _runtime_context(
        self, organization_id: int, session_public_id: uuidlib.UUID
    ) -> tuple[ChannelSession, ChannelConnection, RuntimeMetadata]:
        row = await self._sessions.get_scoped(organization_id, session_public_id)
        if row is None:
            raise NotFoundError("Channel session not found.")
        connection = await self._connection_for_session(organization_id, row)
        runtime = self._require_runtime(connection.connector_type)
        return row, connection, runtime

    async def _connection_for_session(
        self, organization_id: int, row: ChannelSession
    ) -> ChannelConnection:
        connection = await self._connections.get_by_id(row.connection_id)
        if (
            connection is None
            or connection.organization_id != organization_id
            or connection.deleted_at is not None
        ):
            raise NotFoundError("Channel connection not found.")
        return connection

    @staticmethod
    def _capability_set(
        values: list[Capability | str], *, field_name: str
    ) -> frozenset[Capability]:
        try:
            return frozenset(Capability(value) for value in values)
        except ValueError as exc:
            raise ValidationError(f"Unknown {field_name}: {exc}") from exc

    @staticmethod
    def _require_capability(runtime: RuntimeMetadata, capability: Capability) -> None:
        if capability not in runtime.capabilities:
            raise ValidationError(
                f"The registered provider runtime does not declare {capability.value}."
            )

    def _require_runtime(self, connector_type: str) -> RuntimeMetadata:
        try:
            return self._runtimes.require(connector_type)
        except ChannelConfigError as exc:
            raise ValidationError(str(exc)) from exc

    async def _require_read(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER):
            raise ForbiddenError("Provider runtimes are disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_READ):
            raise ForbiddenError("Omnichannel session reads are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.READ_PERMISSION}):
            raise ForbiddenError("The actor cannot discover provider runtimes.")

    async def _require_operate(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER):
            raise ForbiddenError("Provider runtimes are disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_WRITE):
            raise ForbiddenError("Omnichannel session writes are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.DIAGNOSE_PERMISSION}):
            raise ForbiddenError("The actor cannot operate provider runtimes.")

    @staticmethod
    def _assert_actor(organization_id: int, actor: User) -> None:
        if actor.organization_id != organization_id or actor.deleted_at is not None:
            raise ForbiddenError("The actor does not belong to the requested organization.")
        if not actor.is_active:
            raise ForbiddenError("The actor is inactive.")
