"""Meta Cloud API adapter package (Channel 1 — Doc 01 CMP-01, Doc 07 §5).

Importing this package registers the ``meta_cloud`` adapter and installs Meta's error map into the
retry engine — the same self-registration pattern the storage providers use, so wiring a channel in
is an import, not an edit to the engine (Doc 07 §5.4).
"""

from __future__ import annotations

from app.channels.base import register_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD
from app.channels.meta.adapter import MetaChannelAdapter, _factory
from app.channels.meta.client import MetaCloudClient, MetaCredentials
from app.channels.meta.errors import MetaApiError, classify_meta, install

register_adapter(CONNECTOR_META_CLOUD, _factory)
install()

__all__ = [
    "MetaApiError",
    "MetaChannelAdapter",
    "MetaCloudClient",
    "MetaCredentials",
    "classify_meta",
]
