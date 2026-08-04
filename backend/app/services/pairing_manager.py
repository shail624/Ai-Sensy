"""Provider-neutral, no-store pairing lifecycle manager for M13-05.

Only lifecycle facts, expiry and constrained machine reason codes are persisted on the existing
``ChannelSession`` row. QR images, challenge bytes, login material and provider credentials are
deliberately absent. The active runtime must hold the current durable lease/fencing token for
interactive transitions; scheduled expiry is a separate audited maintenance operation.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError
from app.channels.flags import ChannelFeatureFlagResolver, OmnichannelFeatureFlag
from app.channels.runtime import (
    PairingState,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeMetadata,
    can_transition_pairing,
    validate_reason_code,
)
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.channels.session import SESSION_TERMINAL_STATES, SessionState
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

_PAIRING_SESSION_STATES = frozenset(
    {SessionState.INITIALIZING, SessionState.WAITING_FOR_PAIRING}
)


class PairingManager:
    READ_PERMISSION = "channels:read"
    AUTHENTICATE_PERMISSION = "channels:authenticate"

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

    async def get_pairing_session(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
    ) -> ChannelSession:
        await self._require_read(organization_id, actor)
        row = await self._sessions.get_scoped(organization_id, session_public_id)
        if row is None:
            raise NotFoundError("Channel session not found.")
        await self._require_pairing_runtime(organization_id, row)
        return row

    async def transition_pairing(
        self,
        *,
        organization_id: int,
        actor: User,
        session_public_id: uuidlib.UUID,
        runtime_id: str,
        fencing_token: int,
        expected_row_version: int,
        target_state: PairingState | str,
        expires_at: datetime | None = None,
        reason_code: str | None = None,
        at: datetime | None = None,
    ) -> ChannelSession:
        """Persist one legal runtime-owned pairing transition without storing a QR artifact."""

        await self._require_authenticate(organization_id, actor)
        now = at or utcnow()
        row = await self._session_manager.lock_runtime_owned_session(
            organization_id=organization_id,
            actor=actor,
            public_id=session_public_id,
            runtime_id=runtime_id,
            fencing_token=fencing_token,
            expected_row_version=expected_row_version,
            at=now,
        )
        runtime = await self._require_pairing_runtime(organization_id, row)
        current = PairingState(row.pairing_state)
        target = PairingState(target_state)
        if not can_transition_pairing(current, target):
            raise ValidationError(
                f"Illegal pairing transition: {current.value} -> {target.value}."
            )
        self._validate_session_state(row)
        expiry = self._validate_expiry(
            current=current,
            target=target,
            expires_at=expires_at,
            current_expires_at=row.pairing_expires_at,
            now=now,
            max_ttl_seconds=runtime.pairing_ttl_seconds,
        )
        safe_reason = self._reason_code(reason_code)
        before = {
            "pairing_state": row.pairing_state,
            "pairing_revision": row.pairing_revision,
            "pairing_expires_at": (
                row.pairing_expires_at.isoformat()
                if row.pairing_expires_at is not None
                else None
            ),
            "pairing_reason_code": row.pairing_reason_code,
        }
        if target is PairingState.PAIRING_REQUESTED:
            row.pairing_revision += 1
        row.pairing_state = target.value
        row.pairing_changed_at = now
        row.pairing_expires_at = expiry
        row.pairing_reason_code = safe_reason
        row.updated_by = actor.id
        row.row_version += 1
        await self._sessions.flush()
        event = RuntimeEvent(
            event_type=RuntimeEventType.PAIRING_STATE_CHANGED,
            organization_id=organization_id,
            session_public_id=row.public_id,
            runtime_id=runtime_id,
            occurred_at=now,
            state=target.value,
            reason_code=safe_reason,
        )
        await self._audit.record(
            AuditAction.CHANNEL_PAIRING_TRANSITIONED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_session",
            entity_id=row.id,
            before=before,
            after={
                **event.audit_payload(),
                "pairing_revision": row.pairing_revision,
                "pairing_expires_at": expiry.isoformat() if expiry is not None else None,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def expire_due_pairings(
        self,
        *,
        organization_id: int,
        actor: User,
        at: datetime | None = None,
        limit: int = 100,
    ) -> list[ChannelSession]:
        """Expire due pairing availability without requiring a now-dead runtime lease."""

        await self._require_authenticate(organization_id, actor)
        if limit < 1 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000.")
        now = at or utcnow()
        rows = await self._sessions.list_due_pairings(organization_id, now, limit=limit)
        for row in rows:
            await self._require_pairing_runtime(organization_id, row)
            before = {
                "pairing_state": row.pairing_state,
                "pairing_revision": row.pairing_revision,
                "pairing_expires_at": row.pairing_expires_at.isoformat()
                if row.pairing_expires_at is not None
                else None,
                "pairing_reason_code": row.pairing_reason_code,
            }
            row.pairing_state = PairingState.PAIRING_EXPIRED.value
            row.pairing_changed_at = now
            row.pairing_expires_at = None
            row.pairing_reason_code = "pairing_expired"
            row.updated_by = actor.id
            row.row_version += 1
            await self._audit.record(
                AuditAction.CHANNEL_PAIRING_TRANSITIONED,
                actor_user_id=actor.id,
                organization_id=organization_id,
                entity_type="channel_session",
                entity_id=row.id,
                before=before,
                after={
                    "event_type": RuntimeEventType.PAIRING_STATE_CHANGED.value,
                    "session_public_id": row.public_id,
                    "runtime_id": row.holder_runtime_id,
                    "occurred_at": now.isoformat(),
                    "state": row.pairing_state,
                    "reason_code": row.pairing_reason_code,
                    "pairing_revision": row.pairing_revision,
                    "row_version": row.row_version,
                },
            )
        if rows:
            await self._session.commit()
        return rows

    async def _require_pairing_runtime(
        self, organization_id: int, row: ChannelSession
    ) -> RuntimeMetadata:
        connection = await self._connection_for_session(organization_id, row)
        try:
            runtime = self._runtimes.require(connection.connector_type)
        except ChannelConfigError as exc:
            raise ValidationError(str(exc)) from exc
        if not runtime.pairing_managed or Capability.QR_AUTH not in runtime.capabilities:
            raise ValidationError("The registered provider runtime does not support pairing.")
        session_capabilities = frozenset(row.capability_references_json or [])
        if Capability.QR_AUTH.value not in session_capabilities:
            raise ValidationError("The channel session does not declare qr_auth.")
        return runtime

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
    def _validate_session_state(row: ChannelSession) -> None:
        session_state = SessionState(row.state)
        if session_state in SESSION_TERMINAL_STATES or session_state is SessionState.PAUSED:
            raise ConflictError("The session is not operable for pairing.")
        if session_state not in _PAIRING_SESSION_STATES:
            raise ConflictError(
                "Pairing transitions require an initializing or waiting-for-pairing session."
            )

    @staticmethod
    def _validate_expiry(
        *,
        current: PairingState,
        target: PairingState,
        expires_at: datetime | None,
        current_expires_at: datetime | None,
        now: datetime,
        max_ttl_seconds: int,
    ) -> datetime | None:
        if target is PairingState.PAIRING_AVAILABLE:
            if expires_at is None or expires_at <= now:
                raise ValidationError("pairing_available requires a future expires_at.")
            if (expires_at - now).total_seconds() > max_ttl_seconds:
                raise ValidationError(
                    "pairing_available exceeds the registered runtime pairing TTL."
                )
            return expires_at
        if expires_at is not None:
            raise ValidationError("expires_at is accepted only for pairing_available.")
        if (
            current is PairingState.PAIRING_AVAILABLE
            and target is PairingState.PAIRED
            and (current_expires_at is None or current_expires_at <= now)
        ):
            raise ConflictError("The pairing representation has expired.")
        return None

    @staticmethod
    def _reason_code(value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return validate_reason_code(value)
        except ChannelConfigError as exc:
            raise ValidationError(str(exc)) from exc

    async def _require_read(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER):
            raise ForbiddenError("Provider runtimes are disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_AUTH):
            raise ForbiddenError("Pairing is disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_READ):
            raise ForbiddenError("Omnichannel session reads are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.READ_PERMISSION}):
            raise ForbiddenError("The actor cannot read pairing state.")

    async def _require_authenticate(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_PROVIDER):
            raise ForbiddenError("Provider runtimes are disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.QR_AUTH):
            raise ForbiddenError("Pairing is disabled for this organization.")
        if not snapshot.is_enabled(OmnichannelFeatureFlag.SESSIONS_WRITE):
            raise ForbiddenError("Omnichannel session writes are disabled for this organization.")
        if not await self._rbac.has_permissions(actor, {self.AUTHENTICATE_PERMISSION}):
            raise ForbiddenError("The actor cannot manage channel pairing.")

    @staticmethod
    def _assert_actor(organization_id: int, actor: User) -> None:
        if actor.organization_id != organization_id or actor.deleted_at is not None:
            raise ForbiddenError("The actor does not belong to the requested organization.")
        if not actor.is_active:
            raise ForbiddenError("The actor is inactive.")
