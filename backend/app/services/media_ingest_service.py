"""Channel media plumbing (Doc 07 §17; Doc 06 §2.3 ``media``) — FR-WA-11.

The two directions an attachment travels, both ending at the **same** ``media_assets`` store:

- **Inbound** (§17.2): the channel hands us a reference, not bytes. Fetch → hash → dedup → store →
  link. Downloading is off the ingest path because a customer's 15 MB video must not hold up their
  message: the text is already in the ledger and the attachment catches up (§17.4 — "partial media
  never blocks the text message").
- **Outbound** (§17.3): reference a stored asset → upload it to the channel → send. Meta's media
  ids expire, so ``media_assets.meta_media_id``/``meta_media_expires_at`` cache the last one and
  re-upload only when it has lapsed (Doc 06 §2.3's "media-id refresh").

**Why not** :meth:`app.services.media_service.MediaService.upload`: that is the API path — an actor
uploads a file and the act is audited against them. This is system-driven (a customer sent it, no
user was involved), must not 409 on duplicate bytes, and links the result to a message. Both use
the same storage primitives — ``validate`` → ``scan_or_raise`` → ``sha256_of`` → dedup →
``StorageProvider`` — so the pipeline is shared even though the orchestration is not.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter
from app.channels.models import DownloadedAttachment
from app.core.config import settings
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.media import MediaAsset
from app.models.message import Message
from app.repositories.media import MediaRepository
from app.repositories.message import MessageRepository
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.media_service import sha256_of, storage_key_for
from app.services.waba_service import WabaService
from app.storage.base import get_provider
from app.storage.scanning import scan_or_raise
from app.storage.validation import MEDIA_TYPES, validate

logger = get_logger(__name__)

#: Doc 06 §2.3 — download inbound, upload outbound, media-id refresh.
MEDIA_QUEUE = "media"
MEDIA_TASK = "app.channels.tasks.download_inbound_media"

#: Meta media ids last 30 days; re-upload before the edge rather than on a rejected send.
META_MEDIA_TTL = timedelta(days=30)
META_MEDIA_SAFETY = timedelta(hours=1)


class MediaUnavailable(Exception):
    """The message carries no media reference this service can act on — never a retry."""


class MediaIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._media = MediaRepository(session)
        self._messages = MessageRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._wabas = WabaRepository(session)

    # --- Inbound (Doc 07 §17.2) ---------------------------------------------
    async def download_inbound(self, message_pk: int) -> dict[str, Any]:
        """Fetch a message's attachment and link it (FR-WA-11).

        Idempotent twice over (Doc 06 §2.3 keys on ``media_id``/sha256): a message that already
        has an asset is done, and identical bytes from any source resolve to the asset that
        already holds them.
        """
        message = await self._messages.get_by_id(message_pk)
        if message is None:
            logger.warning("media_message_missing", extra={"message_pk": message_pk})
            return {"status": "missing", "message_pk": message_pk}
        if message.media_asset_id is not None:
            return {"status": "already_linked", "message_pk": message_pk}

        reference = media_reference(message)
        if reference is None:
            raise MediaUnavailable(f"message {message_pk} carries no channel media id")

        adapter, close = await self._adapter_for(message)
        try:
            downloaded = await adapter.download_attachment(reference)
        finally:
            await close()

        asset, created = await self._store(
            organization_id=message.organization_id,
            downloaded=downloaded,
            media_type=message.message_type,
            file_name=(message.content_json or {}).get("media", {}).get("filename"),
        )
        await self._link(message, asset)
        await self._session.commit()
        return {
            "status": "linked",
            "message_pk": message_pk,
            "media_id": asset.public_id,
            "deduplicated": not created,
        }

    async def _store(
        self,
        *,
        organization_id: int,
        downloaded: DownloadedAttachment,
        media_type: str,
        file_name: str | None,
    ) -> tuple[MediaAsset, bool]:
        """Bytes from a channel → a stored asset. Returns ``(asset, created)``."""
        mime_type = downloaded.mime_type or "application/octet-stream"
        kind = media_type if media_type in MEDIA_TYPES else "document"
        # The same gate the API upload passes: nothing a channel sends is trusted more than a
        # file a user picked (Doc 04 §16).
        validate(media_type=kind, mime_type=mime_type, byte_size=len(downloaded.content))
        await scan_or_raise(downloaded.content, file_name=file_name)

        # Recompute rather than trust the channel's digest: dedup is only as sound as the hash.
        digest = downloaded.sha256 or sha256_of(downloaded.content)
        existing = await self._media.get_by_sha256(organization_id, digest)
        if existing is not None and existing.deleted_at is None:
            return existing, False

        key = storage_key_for(organization_id, digest, file_name)
        stored = await get_provider(settings.storage_backend).put(
            key, downloaded.content, content_type=mime_type
        )
        if existing is not None:
            # Revive rather than violate `uq_media_org_sha`, which spans soft-deleted rows.
            existing.deleted_at = None
            existing.storage_backend = stored.backend
            existing.storage_key = stored.storage_key
            existing.byte_size = stored.byte_size
            existing.mime_type = mime_type
            existing.media_type = kind
            existing.file_name = file_name
            await self._media.flush()
            return existing, True

        asset = MediaAsset(
            organization_id=organization_id,
            media_type=kind,
            mime_type=mime_type,
            file_name=file_name,
            byte_size=stored.byte_size,
            sha256=digest,
            storage_backend=stored.backend,
            storage_key=stored.storage_key,
            # No `created_by`: a customer sent this, and attributing it to an operator would be a
            # lie in a column the audit surface reads.
        )
        await self._media.add(asset)
        return asset, True

    async def _link(self, message: Message, asset: MediaAsset) -> None:
        message.media_asset_id = asset.id
        # `usage_count` is what stops an in-use asset being deleted (Doc 04 §16 → 409).
        asset.usage_count += 1
        await self._media.flush()

    # --- Outbound (Doc 07 §17.3) --------------------------------------------
    async def channel_media_id(self, asset: MediaAsset, adapter: ChannelAdapter) -> str:
        """The channel's id for a stored asset, uploading it only when it has to.

        Re-uploading the same bytes for every send would waste Meta's quota and ours; the cached
        id is reused until it is close enough to expiry that a send might race it.
        """
        if asset.meta_media_id and not self._meta_id_expired(asset):
            return asset.meta_media_id

        data = await get_provider(asset.storage_backend).get(asset.storage_key)
        attachment = await adapter.upload_attachment(
            data, mime_type=asset.mime_type, filename=asset.file_name
        )
        asset.meta_media_id = attachment.media_id
        asset.meta_media_expires_at = utcnow() + META_MEDIA_TTL
        await self._media.flush()
        return attachment.media_id

    @staticmethod
    def _meta_id_expired(asset: MediaAsset) -> bool:
        if asset.meta_media_expires_at is None:
            return True
        return asset.meta_media_expires_at - META_MEDIA_SAFETY <= utcnow()

    # --- Shared -------------------------------------------------------------
    async def _adapter_for(self, message: Message):
        number = await self._numbers.get_by_id(message.phone_number_id)
        waba = await self._wabas.get_by_id(number.waba_id) if number else None
        if number is None or waba is None:
            raise MediaUnavailable("the message's number is no longer connected")
        adapter = WabaService(self._session).adapter_for(
            waba, phone_number_id=number.phone_number_id
        )
        return adapter, adapter.close


def media_reference(message: Message) -> str | None:
    """The channel's media id carried by a message's canonical content (Doc 03 §9.2)."""
    media = (message.content_json or {}).get("media")
    if not isinstance(media, dict):
        return None
    reference = media.get("channel_media_id")
    return str(reference) if reference else None
