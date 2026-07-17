"""The Meta Cloud API adapter — Channel 1 behind the seam (Doc 07 §5, decision CD1).

Meta is modelled as *an adapter like any other*, not as a special case: this module is the only
place that knows Graph payload shapes, and it translates them to and from the canonical objects in
:mod:`app.channels.models`. That is what makes Channel 2 (Support Connector, M7) a sibling rather
than a fork of the platform.

Declared capabilities follow Doc 07 §5.2's Meta column — text/media/interactive/template/bulk —
plus media transfer and the number-health signal (Doc 06 §28). Location, contact, reaction and
calls are **not** declared: the CRM checks the flag, so they surface as
:class:`~app.channels.errors.ChannelNotSupported` instead of a confusing provider error.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.channels.base import ChannelAdapter
from app.channels.capabilities import CONNECTOR_META_CLOUD, Capability, ChannelType
from app.channels.errors import ChannelConfigError
from app.channels.meta.client import MetaCloudClient, MetaCredentials
from app.channels.models import (
    Attachment,
    ChannelPhoneNumber,
    ChannelStatus,
    DownloadedAttachment,
    HealthSignal,
    InteractiveContent,
    MediaContent,
    MessageType,
    OutboundMessage,
    SendResult,
    TemplateContent,
    TextContent,
)

#: Graph's messaging envelope constant.
_PRODUCT = "whatsapp"
#: Fields that describe a number's sending health (Doc 06 §5/§28).
_HEALTH_FIELDS = (
    "display_phone_number,verified_name,quality_rating,throughput,"
    "messaging_limit_tier,platform_type"
)
#: Fields read when enumerating a WABA's numbers (Doc 03 §5.2 columns).
_NUMBER_FIELDS = (
    "id,display_phone_number,verified_name,quality_rating,throughput,"
    "messaging_limit_tier,code_verification_status,status"
)


class MetaChannelAdapter(ChannelAdapter):
    """Official Meta Cloud API adapter."""

    channel_type = ChannelType.WHATSAPP
    connector_type = CONNECTOR_META_CLOUD
    capabilities = frozenset(
        {
            Capability.TEXT,
            Capability.MEDIA,
            Capability.INTERACTIVE,
            Capability.TEMPLATE,
            Capability.BULK,
            Capability.CAMPAIGNS,
            Capability.MEDIA_UPLOAD,
            Capability.MEDIA_DOWNLOAD,
            Capability.HEALTH,
        }
    )

    def __init__(
        self,
        credentials: MetaCredentials | None = None,
        *,
        client: MetaCloudClient | None = None,
    ) -> None:
        self._client = client or MetaCloudClient(credentials)

    @property
    def client(self) -> MetaCloudClient:
        return self._client

    # --- Session / auth ------------------------------------------------------
    async def authenticate(self) -> ChannelStatus:
        """Verify the token by reading the configured number — cheap and side-effect free."""
        number = self._client.credentials.require_phone_number()
        body = await self._client.get(number, params={"fields": "display_phone_number,verified_name"})
        return ChannelStatus(
            connected=True,
            identity=body.get("display_phone_number"),
            detail=body.get("verified_name"),
        )

    async def status(self) -> ChannelStatus:
        """Meta is token-based and stateless: status is whether the credentials still work."""
        return await self.authenticate()

    # --- Outbound ------------------------------------------------------------
    def _payload(self, message: OutboundMessage) -> dict[str, Any]:
        """Canonical message → Graph payload. The only place Graph shapes are constructed."""
        base: dict[str, Any] = {
            "messaging_product": _PRODUCT,
            "recipient_type": "individual",
            "to": message.to,
        }
        content = message.content

        if message.type is MessageType.TEXT and isinstance(content, TextContent):
            return base | {
                "type": "text",
                "text": {"body": content.body, "preview_url": content.preview_url},
            }

        if message.type is MessageType.MEDIA and isinstance(content, MediaContent):
            if bool(content.media_id) == bool(content.link):
                raise ChannelConfigError(
                    "media requires exactly one of media_id or link"
                )
            obj: dict[str, Any] = (
                {"id": content.media_id} if content.media_id else {"link": content.link}
            )
            if content.caption:
                obj["caption"] = content.caption
            if content.filename:
                obj["filename"] = content.filename
            kind = content.kind.value
            return base | {"type": kind, kind: obj}

        if message.type is MessageType.TEMPLATE and isinstance(content, TemplateContent):
            template: dict[str, Any] = {
                "name": content.name,
                "language": {"code": content.language},
            }
            if content.components:
                template["components"] = content.components
            return base | {"type": "template", "template": template}

        if message.type is MessageType.INTERACTIVE and isinstance(content, InteractiveContent):
            return base | {"type": "interactive", "interactive": content.payload}

        raise ChannelConfigError(f"unsupported message content for type {message.type!r}")

    async def _dispatch(self, message: OutboundMessage) -> SendResult:
        number = self._client.credentials.require_phone_number()
        body = await self._client.post(f"{number}/messages", json=self._payload(message))
        messages = body.get("messages") or []
        wamid = messages[0].get("id") if messages else None
        return SendResult(to=message.to, channel_message_id=wamid, accepted=bool(wamid), raw=body)

    # --- Media ---------------------------------------------------------------
    async def upload_attachment(
        self, data: bytes, *, mime_type: str, filename: str | None = None
    ) -> Attachment:
        """Upload bytes to Meta and return the media id a send can reference."""
        self.require(Capability.MEDIA_UPLOAD)
        number = self._client.credentials.require_phone_number()
        body = await self._client.post(
            f"{number}/media",
            files={"file": (filename or "upload", data, mime_type)},
            data={"messaging_product": _PRODUCT, "type": mime_type},
        )
        media_id = body.get("id")
        if not media_id:
            raise ChannelConfigError("Meta accepted the upload but returned no media id")
        return Attachment(
            media_id=media_id,
            mime_type=mime_type,
            byte_size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            filename=filename,
        )

    async def download_attachment(self, media_id: str) -> DownloadedAttachment:
        """Resolve a media id to its (short-lived) URL, then fetch the bytes."""
        self.require(Capability.MEDIA_DOWNLOAD)
        meta = await self._client.get(media_id)
        url = meta.get("url")
        if not url:
            raise ChannelConfigError(f"Meta returned no download url for media {media_id!r}")
        response = await self._client.download(url)
        content = response.content
        return DownloadedAttachment(
            content=content,
            mime_type=meta.get("mime_type"),
            # Meta reports its own sha256; recompute so the caller trusts the bytes it holds.
            sha256=hashlib.sha256(content).hexdigest(),
            byte_size=len(content),
        )

    # --- Provisioning --------------------------------------------------------
    @staticmethod
    def _number(node: dict[str, Any]) -> ChannelPhoneNumber:
        return ChannelPhoneNumber(
            phone_number_id=str(node.get("id", "")),
            display_number=node.get("display_phone_number", ""),
            verified_name=node.get("verified_name"),
            quality_rating=node.get("quality_rating"),
            messaging_tier=node.get("messaging_limit_tier"),
            throughput_level=(node.get("throughput") or {}).get("level"),
            status=node.get("status") or node.get("code_verification_status"),
        )

    async def list_phone_numbers(self, waba_id: str | None = None) -> list[ChannelPhoneNumber]:
        """The numbers a WABA owns — what ``POST /waba/{uuid}/sync`` reconciles against.

        Meta-specific by nature: only a channel with accounts-and-numbers has this, so it lives on
        the adapter rather than the messaging interface. Callers still never touch Graph directly.
        """
        account = waba_id or self._client.credentials.waba_id
        if not account:
            raise ChannelConfigError("a WABA id is required to list phone numbers")
        body = await self._client.get(
            f"{account}/phone_numbers",
            params={"fields": _NUMBER_FIELDS, "limit": 100},
        )
        return [self._number(node) for node in body.get("data") or []]

    # --- Health --------------------------------------------------------------
    async def health_signal(self) -> HealthSignal:
        """Number quality/tier — what the rate gate and Queue Monitor read (Doc 06 §5/§28)."""
        self.require(Capability.HEALTH)
        number = self._client.credentials.require_phone_number()
        body = await self._client.get(number, params={"fields": _HEALTH_FIELDS})
        quality = body.get("quality_rating")
        throughput = (body.get("throughput") or {}).get("level")
        return HealthSignal(
            # Meta reports RED when a number is at risk of restriction (Doc 06 §28).
            healthy=quality not in ("RED", "FLAGGED"),
            quality_rating=quality,
            messaging_tier=body.get("messaging_limit_tier"),
            throughput_limit=throughput,
            detail=body.get("verified_name"),
        )

    async def close(self) -> None:
        await self._client.close()


def _factory(**kwargs: Any) -> MetaChannelAdapter:
    return MetaChannelAdapter(**kwargs)
