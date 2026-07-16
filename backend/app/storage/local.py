"""Local volume storage provider (Doc 08 §14, FR-MED-06 default backend).

Objects live under ``settings.storage_local_path``, sharded by the first bytes of the key so a
single directory never accumulates millions of entries. Signed URLs point back at this
application's download route (an object-storage backend would return a provider-presigned URL
instead — see :mod:`app.storage.base`).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import settings
from app.storage.base import (
    BACKEND_LOCAL,
    StorageError,
    StorageProvider,
    StoredObject,
    register_provider,
)
from app.storage.signing import issue


class LocalStorageProvider(StorageProvider):
    backend = BACKEND_LOCAL

    def __init__(self, root: str | None = None) -> None:
        self._root = Path(root or settings.storage_local_path)

    def _path(self, key: str) -> Path:
        """Resolve ``key`` inside the storage root, refusing any escape.

        Stripping ``..`` textually is not enough (it can still yield an absolute path that
        re-roots the join); the only safe check is to resolve the candidate and require it to
        stay under the root.
        """
        safe = key.strip().strip("/").strip("\\")
        if not safe:
            raise StorageError("empty storage key")
        root = self._root.resolve()
        candidate = (root / safe).resolve()
        if not candidate.is_relative_to(root):
            raise StorageError(f"storage key escapes the storage root: {key!r}")
        return candidate

    async def put(self, key: str, data: bytes, *, content_type: str) -> StoredObject:
        path = self._path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return StoredObject(storage_key=key, byte_size=len(data), backend=self.backend)

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        if not await asyncio.to_thread(path.is_file):
            raise StorageError(f"object not found: {key}")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> bool:
        path = self._path(key)

        def _unlink() -> bool:
            if not path.is_file():
                return False
            path.unlink()
            return True

        return await asyncio.to_thread(_unlink)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._path(key).is_file)

    def signed_url(self, key: str, *, media_id: str, expires_in: int) -> str:
        expires_at, signature = issue(media_id, expires_in=expires_in)
        base = settings.storage_public_base_url.rstrip("/")
        path = f"{settings.api_v1_prefix}/media/{media_id}/download"
        return f"{base}{path}?expires={expires_at}&signature={signature}"


register_provider(BACKEND_LOCAL, LocalStorageProvider)
