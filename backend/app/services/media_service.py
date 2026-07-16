"""Media upload/download service (Doc 04 §16, Doc 08 §14, FR-MED-01..06/09).

Upload pipeline: **validate → scan → hash → dedup → store → record**. Validation and scanning
happen *before* anything is persisted, so a rejected file leaves no trace. Dedup is by SHA-256
within the organization (FR-MED-05), so re-uploading identical bytes returns the existing asset
instead of a second blob. Download is only ever via a signed, expiring URL (FR-MED-09).
"""

from __future__ import annotations

import hashlib
import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.mixins import utcnow
from app.models.media import MediaAsset
from app.models.user import User
from app.repositories.media import MediaRepository
from app.services.audit_service import AuditAction, AuditService
from app.storage.base import StorageProvider, get_provider
from app.storage.scanning import scan_or_raise
from app.storage.validation import validate


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def storage_key_for(organization_id: int, digest: str, file_name: str | None) -> str:
    """Content-addressed, sharded key so one directory never holds millions of objects."""
    suffix = ""
    if file_name and "." in file_name:
        suffix = "." + file_name.rsplit(".", 1)[-1].lower()[:10]
    return f"org-{organization_id}/{digest[:2]}/{digest[2:4]}/{digest}{suffix}"


class MediaService:
    def __init__(self, session: AsyncSession, provider: StorageProvider | None = None) -> None:
        self._session = session
        self._media = MediaRepository(session)
        self._audit = AuditService(session)
        self._provider = provider or get_provider(settings.storage_backend)

    async def upload(
        self,
        *,
        organization_id: int,
        actor: User,
        data: bytes,
        media_type: str,
        mime_type: str,
        file_name: str | None,
    ) -> tuple[MediaAsset, bool]:
        """Store a file. Returns ``(asset, created)``; ``created=False`` means dedup hit."""
        validate(media_type=media_type, mime_type=mime_type, byte_size=len(data))
        await scan_or_raise(data, file_name=file_name)

        digest = sha256_of(data)
        existing = await self._media.get_by_sha256(organization_id, digest)
        if existing is not None and existing.deleted_at is None:
            return existing, False

        key = storage_key_for(organization_id, digest, file_name)
        stored = await self._provider.put(key, data, content_type=mime_type)

        if existing is not None:  # revive a soft-deleted asset rather than violating the uq
            existing.deleted_at = None
            existing.storage_backend = stored.backend
            existing.storage_key = stored.storage_key
            existing.byte_size = stored.byte_size
            existing.mime_type = mime_type
            existing.media_type = media_type
            existing.file_name = file_name
            asset = existing
            await self._media.flush()
        else:
            asset = MediaAsset(
                organization_id=organization_id,
                media_type=media_type,
                mime_type=mime_type,
                file_name=file_name,
                byte_size=stored.byte_size,
                sha256=digest,
                storage_backend=stored.backend,
                storage_key=stored.storage_key,
                created_by=actor.id,
            )
            await self._media.add(asset)

        await self._audit.record(
            AuditAction.MEDIA_UPLOADED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="media_asset",
            entity_id=asset.id,
            after={"media_type": media_type, "mime_type": mime_type, "bytes": stored.byte_size},
        )
        await self._session.commit()
        return asset, True

    async def list_media(
        self, organization_id: int, *, media_type: str | None, q: str | None, limit: int
    ) -> tuple[list[MediaAsset], int]:
        assets = await self._media.list_for_org(
            organization_id, media_type=media_type, q=q, limit=limit
        )
        total = await self._media.count(organization_id, media_type=media_type, q=q)
        return assets, total

    async def get_media(self, organization_id: int, public_id: uuidlib.UUID) -> MediaAsset:
        asset = await self._media.get_active_by_uuid(organization_id, public_id.bytes)
        if asset is None:
            raise NotFoundError("Media asset not found.")
        return asset

    async def signed_url(self, organization_id: int, public_id: uuidlib.UUID) -> tuple[str, int]:
        """A signed, expiring URL for the asset (FR-MED-09). Returns ``(url, ttl)``."""
        asset = await self.get_media(organization_id, public_id)
        ttl = settings.storage_signed_url_ttl_seconds
        provider = get_provider(asset.storage_backend)
        return provider.signed_url(asset.storage_key, media_id=asset.public_id, expires_in=ttl), ttl

    async def read_bytes(self, organization_id: int, public_id: uuidlib.UUID) -> tuple[MediaAsset, bytes]:
        asset = await self.get_media(organization_id, public_id)
        provider = get_provider(asset.storage_backend)
        return asset, await provider.get(asset.storage_key)

    async def delete(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        """Soft-delete an unused asset (Doc 04 §16 — 409 when in use)."""
        asset = await self.get_media(organization_id, public_id)
        if asset.usage_count > 0:
            raise ConflictError("Media is in use and cannot be deleted.")
        provider = get_provider(asset.storage_backend)
        await provider.delete(asset.storage_key)
        asset.deleted_at = utcnow()
        await self._media.flush()
        await self._audit.record(
            AuditAction.MEDIA_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="media_asset",
            entity_id=asset.id,
            before={"file_name": asset.file_name, "sha256": asset.sha256},
        )
        await self._session.commit()
