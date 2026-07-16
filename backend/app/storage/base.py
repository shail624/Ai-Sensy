"""Storage abstraction + provider registry (Doc 08 §14, FR-MED-06, decision DD16).

The contract every backend implements. A **local volume** backend ships by default; an
**S3-compatible** backend is registered under ``"s3"`` by its own module and swaps in without
touching callers — the abstraction is what makes local↔external a config change, not a rewrite.

Selecting a backend that has no registered provider raises a clear configuration error rather
than silently degrading.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

BACKEND_LOCAL = "local"
BACKEND_S3 = "s3"


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Result of persisting bytes to a backend."""

    storage_key: str
    byte_size: int
    backend: str


class StorageError(RuntimeError):
    """Raised when a backend cannot satisfy a request."""


class StorageProvider(ABC):
    """The storage contract (Doc 08 §14)."""

    #: Backend identifier persisted on the asset (`media_assets.storage_backend`).
    backend: str

    @abstractmethod
    async def put(self, key: str, data: bytes, *, content_type: str) -> StoredObject:
        """Persist ``data`` at ``key``."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Read the object back. Raises :class:`StorageError` if missing."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove the object; returns False if it was already gone."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """True if the object is present."""

    @abstractmethod
    def signed_url(self, key: str, *, media_id: str, expires_in: int) -> str:
        """A signed, expiring URL for reading the object (FR-MED-09).

        Local storage signs a URL back to this application; an object-storage backend returns
        a provider-presigned URL instead — callers never care which.
        """


_PROVIDERS: dict[str, Callable[[], StorageProvider]] = {}


def register_provider(backend: str, factory: Callable[[], StorageProvider]) -> None:
    """Register a backend factory (e.g. an S3 module registering ``"s3"``)."""
    _PROVIDERS[backend] = factory


def available_backends() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


def get_provider(backend: str) -> StorageProvider:
    """Resolve a backend, or fail loudly if it is not registered/configured."""
    factory = _PROVIDERS.get(backend)
    if factory is None:
        raise StorageError(
            f"storage backend {backend!r} is not available; registered: {available_backends()}"
        )
    return factory()
