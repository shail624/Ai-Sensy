"""Provider and capability catalogues over the existing ChannelAdapter registry.

This module owns control-plane metadata only. Adapter factories remain exclusively owned by
:mod:`app.channels.base`; resolving an adapter delegates to that existing registry.
"""

from __future__ import annotations

from threading import RLock
from typing import Any

from app.channels.base import ChannelAdapter, get_adapter
from app.channels.capabilities import Capability
from app.channels.errors import ChannelConfigError
from app.channels.foundation import ChannelMetadata
from app.channels.validation import normalize_capabilities, validate_connector_type


class CapabilityRegistry:
    """Thread-safe capability metadata keyed by connector type."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._capabilities: dict[str, frozenset[Capability]] = {}

    def register(
        self,
        connector_type: str,
        capabilities: frozenset[Capability],
        *,
        replace: bool = False,
    ) -> None:
        key = validate_connector_type(connector_type)
        normalized = normalize_capabilities(capabilities)
        with self._lock:
            existing = self._capabilities.get(key)
            if existing is not None and existing != normalized and not replace:
                raise ChannelConfigError(f"Capability metadata already registered for {key!r}")
            self._capabilities[key] = normalized

    def get(self, connector_type: str) -> frozenset[Capability]:
        key = validate_connector_type(connector_type)
        with self._lock:
            return self._capabilities.get(key, frozenset())

    def require(self, connector_type: str) -> frozenset[Capability]:
        key = validate_connector_type(connector_type)
        with self._lock:
            if key not in self._capabilities:
                raise ChannelConfigError(f"No capability metadata registered for {key!r}")
            return self._capabilities[key]

    def supports(self, connector_type: str, capability: Capability) -> bool:
        return capability in self.get(connector_type)

    def available(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._capabilities))


class ProviderRegistry:
    """Provider metadata catalogue integrated with the existing adapter factory seam."""

    def __init__(self, capabilities: CapabilityRegistry) -> None:
        self._lock = RLock()
        self._providers: dict[str, ChannelMetadata] = {}
        self._capabilities = capabilities

    def register(self, metadata: ChannelMetadata, *, replace: bool = False) -> None:
        with self._lock:
            existing = self._providers.get(metadata.connector_type)
            if existing is not None and existing != metadata and not replace:
                raise ChannelConfigError(
                    f"Provider metadata already registered for {metadata.connector_type!r}"
                )
            self._capabilities.register(
                metadata.connector_type,
                metadata.capabilities,
                replace=replace,
            )
            self._providers[metadata.connector_type] = metadata

    def get(self, connector_type: str) -> ChannelMetadata | None:
        key = validate_connector_type(connector_type)
        with self._lock:
            return self._providers.get(key)

    def require(self, connector_type: str) -> ChannelMetadata:
        key = validate_connector_type(connector_type)
        with self._lock:
            metadata = self._providers.get(key)
            if metadata is None:
                raise ChannelConfigError(f"No provider metadata registered for {key!r}")
            return metadata

    def available(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._providers))

    def resolve_adapter(self, connector_type: str, **kwargs: Any) -> ChannelAdapter:
        """Resolve through the existing registry and verify declared metadata parity."""
        metadata = self.require(connector_type)
        adapter = get_adapter(metadata.connector_type, **kwargs)
        if adapter.connector_type != metadata.connector_type:
            raise ChannelConfigError("Resolved adapter connector_type does not match metadata")
        if adapter.channel_type != metadata.channel_type:
            raise ChannelConfigError("Resolved adapter channel_type does not match metadata")
        if adapter.capabilities != metadata.capabilities:
            raise ChannelConfigError("Resolved adapter capabilities do not match metadata")
        return adapter
