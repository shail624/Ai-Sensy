"""Thread-safe runtime metadata registry over the existing provider registry.

The registry is process-local configuration, not durable runtime truth. Session ownership,
leases, fencing and health remain in ``channel_sessions``. No provider factory or second adapter
hierarchy is introduced; concrete execution continues through the existing ``ChannelAdapter`` seam.
"""

from __future__ import annotations

from threading import RLock

from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError
from app.channels.registry import ProviderRegistry
from app.channels.runtime import RuntimeMetadata
from app.channels.validation import validate_connector_type


class ProviderRuntimeRegistry:
    """Runtime-host metadata keyed by the connector already owned by ``ProviderRegistry``."""

    def __init__(self, providers: ProviderRegistry) -> None:
        self._lock = RLock()
        self._providers = providers
        self._runtimes: dict[str, RuntimeMetadata] = {}

    def register(self, metadata: RuntimeMetadata, *, replace: bool = False) -> None:
        provider = self._providers.require(metadata.connector_type)
        unsupported = metadata.capabilities - provider.capabilities
        if unsupported:
            names = ", ".join(sorted(capability.value for capability in unsupported))
            raise ChannelConfigError(
                f"Runtime capabilities are not declared by provider {metadata.connector_type!r}: "
                f"{names}"
            )
        lifecycle_capabilities = frozenset(
            {
                Capability.QR_AUTH,
                Capability.SESSION_STREAM,
                Capability.SESSION_RECONNECT,
                Capability.SESSION_LOGOUT,
            }
        )
        if metadata.capabilities & lifecycle_capabilities and not provider.lifecycle_managed:
            raise ChannelConfigError(
                "Runtime lifecycle capabilities require provider-managed lifecycle metadata"
            )
        if Capability.HEALTH in metadata.capabilities and not provider.health_managed:
            raise ChannelConfigError(
                "Runtime health capability requires provider-managed health metadata"
            )

        with self._lock:
            existing = self._runtimes.get(metadata.connector_type)
            if existing is not None and existing != metadata and not replace:
                raise ChannelConfigError(
                    f"Runtime metadata already registered for {metadata.connector_type!r}"
                )
            self._runtimes[metadata.connector_type] = metadata

    def get(self, connector_type: str) -> RuntimeMetadata | None:
        key = validate_connector_type(connector_type)
        with self._lock:
            return self._runtimes.get(key)

    def require(self, connector_type: str) -> RuntimeMetadata:
        key = validate_connector_type(connector_type)
        with self._lock:
            metadata = self._runtimes.get(key)
            if metadata is None:
                raise ChannelConfigError(f"No provider runtime registered for {key!r}")
            return metadata

    def available(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._runtimes))

    def registrations(self) -> tuple[RuntimeMetadata, ...]:
        with self._lock:
            return tuple(self._runtimes[key] for key in sorted(self._runtimes))
