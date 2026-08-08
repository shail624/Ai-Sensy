"""Dependency-injection composition for the generic channel foundation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.flags import ChannelFeatureFlagResolver
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.runtime_registry import ProviderRuntimeRegistry
from app.core.config import settings


@dataclass(frozen=True, slots=True)
class ChannelFoundation:
    """Provider-neutral control-plane dependencies; contains no provider implementation."""

    providers: ProviderRegistry
    capabilities: CapabilityRegistry
    runtimes: ProviderRuntimeRegistry


@lru_cache(maxsize=1)
def get_channel_foundation() -> ChannelFoundation:
    """Build the process-wide control-plane registries.

    The WAHA runtime is registered here — and only here — when the deployment is fully
    configured (``WAHA_BASE_URL``, ``WAHA_API_KEY``, ``WAHA_SESSION_NAME`` all set). This is the
    explicit opt-in QR-06 left for exactly this composition root: importing
    ``app.channels.waha`` still registers nothing on its own (asserted by test), and an
    unconfigured deployment gets the same empty registry every milestone through QR-06 verified.
    """
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    runtimes = ProviderRuntimeRegistry(providers)
    if settings.waha_base_url and settings.waha_api_key and settings.waha_session_name:
        from app.channels.waha import register_waha_runtime

        register_waha_runtime(providers, runtimes)
    return ChannelFoundation(providers=providers, capabilities=capabilities, runtimes=runtimes)


def build_channel_feature_flag_resolver(
    session: AsyncSession,
) -> ChannelFeatureFlagResolver:
    return ChannelFeatureFlagResolver(session)
