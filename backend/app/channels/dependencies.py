"""Dependency-injection composition for the generic channel foundation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.flags import ChannelFeatureFlagResolver
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime_registry import ProviderRuntimeRegistry


@dataclass(frozen=True, slots=True)
class ChannelFoundation:
    """Provider-neutral control-plane dependencies; contains no provider implementation."""

    providers: ProviderRegistry
    capabilities: CapabilityRegistry
    runtimes: ProviderRuntimeRegistry


@lru_cache(maxsize=1)
def get_channel_foundation() -> ChannelFoundation:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    runtimes = ProviderRuntimeRegistry(providers)
    return ChannelFoundation(providers=providers, capabilities=capabilities, runtimes=runtimes)


def build_channel_feature_flag_resolver(
    session: AsyncSession,
) -> ChannelFeatureFlagResolver:
    return ChannelFeatureFlagResolver(session)
