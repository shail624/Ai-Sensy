"""Provider-neutral history-sync and media-reference state vocabulary.

These types describe repository-owned control-plane facts only. They do not connect to a provider,
fetch history, download media, ingest live events, or imply that any provider is certified.
"""

from __future__ import annotations

from enum import StrEnum


class ChannelSyncType(StrEnum):
    """Bounded synchronization work represented by a durable checkpoint."""

    HISTORY = "history"


class ChannelSyncStatus(StrEnum):
    """Lifecycle of a durable provider-neutral synchronization checkpoint."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


SYNC_TERMINAL_STATUSES = frozenset(
    {
        ChannelSyncStatus.SUCCEEDED,
        ChannelSyncStatus.FAILED,
        ChannelSyncStatus.CANCELLED,
    }
)


class MediaTransferState(StrEnum):
    """Observed provider-reference transfer state without performing a transfer."""

    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    AVAILABLE = "available"
    FAILED = "failed"
    EXPIRED = "expired"
