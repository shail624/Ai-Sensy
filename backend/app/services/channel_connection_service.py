"""Persistence-only service for provider-neutral channel control-plane records.

This service owns durable configuration, lifecycle observations, endpoint metadata, encrypted
credential rotation, tenant isolation, feature gates, optimistic locking, soft deletion, and audit
evidence. It intentionally performs no provider I/O and exposes no API route.
"""

from __future__ import annotations

import re
import uuid as uuidlib
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.flags import (
    ChannelFeatureFlagResolver,
    OmnichannelFeatureFlag,
)
from app.channels.foundation import (
    ProviderDesiredState,
    ProviderHealthState,
    ProviderObservedState,
)
from app.channels.secrets import AesGcmSecretCipher, SecretCipher, assert_no_secret_material
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.db.mixins import utcnow
from app.models.channel_connection import (
    CHANNEL_SECRET_ACTIVE,
    CHANNEL_SECRET_REVOKED,
    ChannelConnection,
    ChannelEndpoint,
    ChannelSecret,
)
from app.models.user import User
from app.repositories.channel_connection import (
    ChannelConnectionRepository,
    ChannelEndpointRepository,
    ChannelSecretRepository,
)
from app.services.audit_service import AuditAction, AuditService


class _VersionedRow(Protocol):
    row_version: int


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_CONNECTION_PATCH_FIELDS = frozenset(
    {
        "display_name",
        "desired_state",
        "provider_configuration_json",
        "provider_metadata_json",
        "capability_snapshot_json",
    }
)
_ENDPOINT_PATCH_FIELDS = frozenset(
    {
        "display_address",
        "display_name",
        "enabled",
        "is_default",
        "endpoint_metadata_json",
        "provider_metadata_json",
        "provider_limits_json",
    }
)


class ChannelConnectionService:
    def __init__(self, session: AsyncSession, *, cipher: SecretCipher | None = None) -> None:
        self._session = session
        self._connections = ChannelConnectionRepository(session)
        self._endpoints = ChannelEndpointRepository(session)
        self._secrets = ChannelSecretRepository(session)
        self._flags = ChannelFeatureFlagResolver(session)
        self._audit = AuditService(session)
        self._cipher = cipher or AesGcmSecretCipher()

    async def create_connection(
        self,
        *,
        organization_id: int,
        actor: User,
        channel_family: str,
        connector_type: str,
        display_name: str,
        provider_connection_id: str | None = None,
        desired_state: ProviderDesiredState | str = ProviderDesiredState.DISABLED,
        capability_snapshot: list[str] | None = None,
        provider_configuration: dict[str, Any] | None = None,
        provider_metadata: dict[str, Any] | None = None,
    ) -> ChannelConnection:
        await self._require_write(organization_id, actor)
        family = self._identifier(channel_family, "channel_family")
        connector = self._identifier(connector_type, "connector_type")
        name = self._text(display_name, "display_name", 160)
        provider_id = self._optional_text(provider_connection_id, "provider_connection_id", 190)
        desired = ProviderDesiredState(desired_state).value
        self._validate_json(provider_configuration, "provider_configuration")
        self._validate_json(provider_metadata, "provider_metadata")
        capabilities = self._capabilities(capability_snapshot)

        row = ChannelConnection(
            organization_id=organization_id,
            channel_family=family,
            connector_type=connector,
            provider_connection_id=provider_id,
            display_name=name,
            desired_state=desired,
            observed_state=ProviderObservedState.UNCONFIGURED.value,
            health_state=ProviderHealthState.UNKNOWN.value,
            capability_snapshot_json=capabilities,
            provider_configuration_json=provider_configuration,
            provider_metadata_json=provider_metadata,
            lifecycle_changed_at=utcnow(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._connections.add(row)
        await self._audit.record(
            AuditAction.CHANNEL_CONNECTION_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_connection",
            entity_id=row.id,
            after={
                "channel_family": family,
                "connector_type": connector,
                "provider_connection_id": provider_id,
                "desired_state": desired,
                "configuration_keys": sorted((provider_configuration or {}).keys()),
                "metadata_keys": sorted((provider_metadata or {}).keys()),
            },
        )
        await self._session.commit()
        return row

    async def get_connection(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> ChannelConnection:
        await self._require_read(organization_id, actor)
        return await self._get_connection(organization_id, public_id)

    async def list_connections(
        self, *, organization_id: int, actor: User
    ) -> list[ChannelConnection]:
        await self._require_read(organization_id, actor)
        return await self._connections.list_scoped(organization_id)

    async def update_connection(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        changes: Mapping[str, object],
    ) -> ChannelConnection:
        await self._require_write(organization_id, actor)
        row = await self._get_connection(organization_id, public_id)
        self._check_version(row, expected_row_version)
        unknown = set(changes) - _CONNECTION_PATCH_FIELDS
        if unknown:
            raise ValidationError(f"Unsupported connection fields: {', '.join(sorted(unknown))}.")

        applied: list[str] = []
        for key, raw in changes.items():
            if key == "display_name":
                row.display_name = self._text(str(raw), key, 160)
            elif key == "desired_state":
                row.desired_state = ProviderDesiredState(str(raw)).value
                row.lifecycle_changed_at = utcnow()
            elif key in {"provider_configuration_json", "provider_metadata_json"}:
                if raw is not None and not isinstance(raw, dict):
                    raise ValidationError(f"{key} must be an object or null.")
                value = raw if isinstance(raw, dict) else None
                self._validate_json(value, key)
                setattr(row, key, value)
            elif key == "capability_snapshot_json":
                if raw is not None and not isinstance(raw, list):
                    raise ValidationError(f"{key} must be an array or null.")
                row.capability_snapshot_json = self._capabilities(raw)
            applied.append(key)

        if not applied:
            return row
        row.updated_by = actor.id
        row.row_version += 1
        await self._connections.flush()
        await self._audit.record(
            AuditAction.CHANNEL_CONNECTION_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_connection",
            entity_id=row.id,
            after={"fields": sorted(applied), "row_version": row.row_version},
        )
        await self._session.commit()
        return row

    async def record_connection_observation(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        observed_state: ProviderObservedState | str,
        health_state: ProviderHealthState | str,
        observed_at: datetime,
        health_score: int | None = None,
        lifecycle_detail: str | None = None,
        health_detail: str | None = None,
        last_error_code: str | None = None,
        last_error_summary: str | None = None,
    ) -> ChannelConnection:
        """Persist a factual observation supplied by a future adapter/runtime; perform no I/O."""
        await self._require_write(organization_id, actor)
        row = await self._get_connection(organization_id, public_id)
        self._check_version(row, expected_row_version)
        score = self._score(health_score)
        row.observed_state = ProviderObservedState(observed_state).value
        row.health_state = ProviderHealthState(health_state).value
        row.lifecycle_changed_at = observed_at
        row.health_observed_at = observed_at
        row.lifecycle_detail = self._optional_text(lifecycle_detail, "lifecycle_detail", 500)
        row.health_detail = self._optional_text(health_detail, "health_detail", 500)
        row.health_score = score
        row.last_error_code = self._optional_text(last_error_code, "last_error_code", 120)
        row.last_error_summary = self._optional_text(last_error_summary, "last_error_summary", 500)
        row.updated_by = actor.id
        row.row_version += 1
        await self._connections.flush()
        await self._audit.record(
            AuditAction.CHANNEL_CONNECTION_OBSERVED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_connection",
            entity_id=row.id,
            after={
                "observed_state": row.observed_state,
                "health_state": row.health_state,
                "health_score": row.health_score,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def delete_connection(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
    ) -> None:
        await self._require_write(organization_id, actor)
        row = await self._get_connection(organization_id, public_id)
        self._check_version(row, expected_row_version)
        now = utcnow()
        endpoints = await self._endpoints.list_for_connection(organization_id, row.id)
        secrets = await self._secrets.list_for_connection(organization_id, row.id)
        for endpoint in endpoints:
            endpoint.deleted_at = now
            endpoint.enabled = False
            endpoint.updated_by = actor.id
            endpoint.row_version += 1
        for secret in secrets:
            if secret.is_active:
                self._revoke_secret_row(secret, actor=actor, reason="connection_deleted", now=now)
            secret.deleted_at = now
            secret.updated_by = actor.id
            secret.row_version += 1
        row.deleted_at = now
        row.desired_state = ProviderDesiredState.DISABLED.value
        row.observed_state = ProviderObservedState.DISABLED.value
        row.lifecycle_changed_at = now
        row.updated_by = actor.id
        row.row_version += 1
        await self._session.flush()
        await self._audit.record(
            AuditAction.CHANNEL_CONNECTION_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_connection",
            entity_id=row.id,
            before={
                "active_endpoints": len(endpoints),
                "credential_versions": len(secrets),
            },
        )
        await self._session.commit()

    async def create_endpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        endpoint_type: str,
        normalized_address: str,
        provider_endpoint_id: str,
        display_address: str | None = None,
        display_name: str | None = None,
        enabled: bool = False,
        is_default: bool = False,
        endpoint_metadata: dict[str, Any] | None = None,
        provider_metadata: dict[str, Any] | None = None,
        provider_limits: dict[str, Any] | None = None,
    ) -> ChannelEndpoint:
        await self._require_write(organization_id, actor)
        connection = await self._get_connection(organization_id, connection_public_id)
        kind = self._identifier(endpoint_type, "endpoint_type")
        address = self._text(normalized_address, "normalized_address", 190)
        provider_id = self._text(provider_endpoint_id, "provider_endpoint_id", 190)
        for name, value in (
            ("endpoint_metadata", endpoint_metadata),
            ("provider_metadata", provider_metadata),
            ("provider_limits", provider_limits),
        ):
            self._validate_json(value, name)

        row = ChannelEndpoint(
            organization_id=organization_id,
            connection_id=connection.id,
            endpoint_type=kind,
            normalized_address=address,
            display_address=self._optional_text(display_address, "display_address", 190),
            display_name=self._optional_text(display_name, "display_name", 160),
            provider_endpoint_id=provider_id,
            enabled=enabled,
            is_default=is_default,
            observed_state=ProviderObservedState.UNCONFIGURED.value,
            health_state=ProviderHealthState.UNKNOWN.value,
            endpoint_metadata_json=endpoint_metadata,
            provider_metadata_json=provider_metadata,
            provider_limits_json=provider_limits,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._endpoints.add(row)
        connection.updated_by = actor.id
        connection.row_version += 1
        await self._audit.record(
            AuditAction.CHANNEL_ENDPOINT_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_endpoint",
            entity_id=row.id,
            after={
                "connection_id": connection.id,
                "endpoint_type": kind,
                "provider_endpoint_id": provider_id,
            },
        )
        await self._session.commit()
        return row

    async def get_endpoint(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> ChannelEndpoint:
        await self._require_read(organization_id, actor)
        return await self._get_endpoint(organization_id, public_id)

    async def update_endpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        changes: Mapping[str, object],
    ) -> ChannelEndpoint:
        await self._require_write(organization_id, actor)
        row = await self._get_endpoint(organization_id, public_id)
        self._check_version(row, expected_row_version)
        unknown = set(changes) - _ENDPOINT_PATCH_FIELDS
        if unknown:
            raise ValidationError(f"Unsupported endpoint fields: {', '.join(sorted(unknown))}.")

        applied: list[str] = []
        for key, raw in changes.items():
            if key in {"display_address", "display_name"}:
                max_length = 190 if key == "display_address" else 160
                setattr(
                    row,
                    key,
                    self._optional_text(
                        raw if isinstance(raw, str) else None,
                        key,
                        max_length,
                    ),
                )
            elif key in {"enabled", "is_default"}:
                if not isinstance(raw, bool):
                    raise ValidationError(f"{key} must be a boolean.")
                setattr(row, key, raw)
            else:
                if raw is not None and not isinstance(raw, dict):
                    raise ValidationError(f"{key} must be an object or null.")
                value = raw if isinstance(raw, dict) else None
                self._validate_json(value, key)
                setattr(row, key, value)
            applied.append(key)

        if not applied:
            return row
        row.updated_by = actor.id
        row.row_version += 1
        await self._endpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_ENDPOINT_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_endpoint",
            entity_id=row.id,
            after={"fields": sorted(applied), "row_version": row.row_version},
        )
        await self._session.commit()
        return row

    async def record_endpoint_observation(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        observed_state: ProviderObservedState | str,
        health_state: ProviderHealthState | str,
        observed_at: datetime,
        health_score: int | None = None,
        health_detail: str | None = None,
    ) -> ChannelEndpoint:
        await self._require_write(organization_id, actor)
        row = await self._get_endpoint(organization_id, public_id)
        self._check_version(row, expected_row_version)
        row.observed_state = ProviderObservedState(observed_state).value
        row.health_state = ProviderHealthState(health_state).value
        row.health_observed_at = observed_at
        row.health_score = self._score(health_score)
        row.health_detail = self._optional_text(health_detail, "health_detail", 500)
        row.updated_by = actor.id
        row.row_version += 1
        await self._endpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_ENDPOINT_OBSERVED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_endpoint",
            entity_id=row.id,
            after={
                "observed_state": row.observed_state,
                "health_state": row.health_state,
                "health_score": row.health_score,
                "row_version": row.row_version,
            },
        )
        await self._session.commit()
        return row

    async def delete_endpoint(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
    ) -> None:
        await self._require_write(organization_id, actor)
        row = await self._get_endpoint(organization_id, public_id)
        self._check_version(row, expected_row_version)
        row.deleted_at = utcnow()
        row.enabled = False
        row.updated_by = actor.id
        row.row_version += 1
        await self._endpoints.flush()
        await self._audit.record(
            AuditAction.CHANNEL_ENDPOINT_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_endpoint",
            entity_id=row.id,
            before={"provider_endpoint_id": row.provider_endpoint_id},
        )
        await self._session.commit()

    async def store_secret(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        secret_type: str,
        plaintext: str,
        expires_at: datetime | None = None,
    ) -> ChannelSecret:
        await self._require_write(organization_id, actor)
        connection = await self._get_connection(organization_id, connection_public_id)
        kind = self._identifier(secret_type, "secret_type")
        active = await self._secrets.get_active(
            organization_id, connection.id, kind, for_update=True
        )
        if active is not None:
            raise ConflictError("An active credential already exists; rotate it instead.")
        latest = await self._secrets.get_latest(organization_id, connection.id, kind)
        sealed = self._cipher.seal(plaintext)
        row = ChannelSecret(
            organization_id=organization_id,
            connection_id=connection.id,
            secret_type=kind,
            secret_version=1 if latest is None else latest.secret_version + 1,
            encrypted_payload=sealed.ciphertext,
            key_version=sealed.key_version,
            status=CHANNEL_SECRET_ACTIVE,
            expires_at=expires_at,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._secrets.add(row)
        await self._audit.record(
            AuditAction.CHANNEL_SECRET_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_secret",
            entity_id=row.id,
            after={
                "connection_id": connection.id,
                "secret_type": kind,
                "secret_version": row.secret_version,
                "key_version": row.key_version,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        await self._session.commit()
        return row

    async def rotate_secret(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        secret_type: str,
        plaintext: str,
        expected_row_version: int,
        expires_at: datetime | None = None,
    ) -> ChannelSecret:
        await self._require_write(organization_id, actor)
        connection = await self._get_connection(organization_id, connection_public_id)
        kind = self._identifier(secret_type, "secret_type")
        active = await self._secrets.get_active(
            organization_id, connection.id, kind, for_update=True
        )
        if active is None:
            raise NotFoundError("No active credential exists to rotate.")
        self._check_version(active, expected_row_version)
        now = utcnow()
        self._revoke_secret_row(active, actor=actor, reason="rotated", now=now)
        active.rotated_at = now
        active.row_version += 1
        sealed = self._cipher.seal(plaintext)
        replacement = ChannelSecret(
            organization_id=organization_id,
            connection_id=connection.id,
            secret_type=kind,
            secret_version=active.secret_version + 1,
            encrypted_payload=sealed.ciphertext,
            key_version=sealed.key_version,
            status=CHANNEL_SECRET_ACTIVE,
            expires_at=expires_at,
            rotated_from_id=active.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._secrets.add(replacement)
        await self._audit.record(
            AuditAction.CHANNEL_SECRET_ROTATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_secret",
            entity_id=replacement.id,
            before={"secret_version": active.secret_version},
            after={
                "secret_type": kind,
                "secret_version": replacement.secret_version,
                "key_version": replacement.key_version,
                "rotated_from_id": active.id,
            },
        )
        await self._session.commit()
        return replacement

    async def revoke_secret(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int,
        reason: str,
    ) -> None:
        await self._require_write(organization_id, actor)
        row = await self._secrets.get_scoped(organization_id, public_id, for_update=True)
        if row is None:
            raise NotFoundError("Channel credential not found.")
        self._check_version(row, expected_row_version)
        if not row.is_active:
            raise ConflictError("Channel credential is already revoked.")
        now = utcnow()
        self._revoke_secret_row(
            row,
            actor=actor,
            reason=self._text(reason, "reason", 1000),
            now=now,
        )
        row.row_version += 1
        await self._secrets.flush()
        await self._audit.record(
            AuditAction.CHANNEL_SECRET_REVOKED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_secret",
            entity_id=row.id,
            after={
                "secret_type": row.secret_type,
                "secret_version": row.secret_version,
                "reason": row.revocation_reason,
            },
        )
        await self._session.commit()

    async def reveal_active_secret(
        self,
        *,
        organization_id: int,
        actor: User,
        connection_public_id: uuidlib.UUID,
        secret_type: str,
        purpose: str,
    ) -> str:
        """Internal-only decryption boundary; intentionally not wired to an API endpoint."""
        await self._require_read(organization_id, actor)
        connection = await self._get_connection(organization_id, connection_public_id)
        kind = self._identifier(secret_type, "secret_type")
        row = await self._secrets.get_active(organization_id, connection.id, kind)
        if row is None:
            raise NotFoundError("Active channel credential not found.")
        if row.expires_at is not None and row.expires_at <= utcnow():
            raise ConflictError("Channel credential has expired.")
        plaintext = self._cipher.open(
            row.encrypted_payload,
            key_version=row.key_version,
        )
        row.last_accessed_at = utcnow()
        row.updated_by = actor.id
        await self._audit.record(
            AuditAction.CHANNEL_SECRET_ACCESSED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="channel_secret",
            entity_id=row.id,
            metadata={
                "secret_type": row.secret_type,
                "secret_version": row.secret_version,
                "purpose": self._text(purpose, "purpose", 160),
            },
        )
        await self._session.commit()
        return plaintext

    async def _get_connection(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> ChannelConnection:
        row = await self._connections.get_scoped(organization_id, public_id)
        if row is None:
            raise NotFoundError("Channel connection not found.")
        return row

    async def _get_endpoint(self, organization_id: int, public_id: uuidlib.UUID) -> ChannelEndpoint:
        row = await self._endpoints.get_scoped(organization_id, public_id)
        if row is None:
            raise NotFoundError("Channel endpoint not found.")
        return row

    async def _require_read(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.CONNECTIONS_READ):
            raise ForbiddenError("Omnichannel connection reads are disabled for this organization.")

    async def _require_write(self, organization_id: int, actor: User) -> None:
        self._assert_actor(organization_id, actor)
        snapshot = await self._flags.resolve(organization_id)
        if not snapshot.is_enabled(OmnichannelFeatureFlag.CONNECTIONS_WRITE):
            raise ForbiddenError(
                "Omnichannel connection writes are disabled for this organization."
            )

    @staticmethod
    def _assert_actor(organization_id: int, actor: User) -> None:
        if actor.organization_id != organization_id or actor.deleted_at is not None:
            raise ForbiddenError("The actor does not belong to the requested organization.")
        if not actor.is_active:
            raise ForbiddenError("The actor is inactive.")

    @staticmethod
    def _check_version(row: _VersionedRow, expected: int) -> None:
        actual = row.row_version
        if actual != expected:
            raise VersionConflictError("The record changed; reload and retry.")

    @staticmethod
    def _revoke_secret_row(row: ChannelSecret, *, actor: User, reason: str, now: datetime) -> None:
        row.status = CHANNEL_SECRET_REVOKED
        row.revoked_at = now
        row.revoked_by = actor.id
        row.revocation_reason = reason
        row.updated_by = actor.id

    @staticmethod
    def _identifier(value: str, field_name: str) -> str:
        normalized = value.strip().lower()
        if not _IDENTIFIER.fullmatch(normalized):
            raise ValidationError(
                f"{field_name} must be 2-64 lowercase letters, digits or underscores."
            )
        return normalized

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

    @staticmethod
    def _validate_json(value: dict[str, Any] | None, field_name: str) -> None:
        if value is None:
            return
        try:
            assert_no_secret_material(value, field_name=field_name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @classmethod
    def _capabilities(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValidationError("capability_snapshot must be an array of strings.")
        return sorted({cls._identifier(item, "capability") for item in value})

    @staticmethod
    def _score(value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValidationError("health_score must be between 0 and 100.")
        return value
