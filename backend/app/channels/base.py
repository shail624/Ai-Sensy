"""The channel adapter contract + registry (Doc 07 §5.2/§5.4).

One interface, declared capabilities, and a registry that resolves a connector type to an adapter —
so dispatch is a **lookup, not a code branch** (§5.4), and adding a channel means registering an
adapter rather than editing the engine (decision CD1).

Shape note: adapters implement a single :meth:`ChannelAdapter._dispatch`; the named outbound
operations of §5.2 (``send_text``/``send_media``/``send_interactive``/``send_template``) are
concrete helpers here that build a canonical :class:`~app.channels.models.OutboundMessage` and route
it through :meth:`ChannelAdapter.send`, which enforces the capability check. Every adapter therefore
gets the capability gate for free and cannot forget it, and a new content type is one enum member
plus one branch inside the adapter — not a new abstract method on every channel.

Operations an adapter does not declare raise :class:`~app.channels.errors.ChannelNotSupported`
rather than failing obscurely at the provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.channels.capabilities import Capability, ChannelType
from app.channels.errors import ChannelError, ChannelNotSupported
from app.channels.models import (
    CAPABILITY_FOR_TYPE,
    Attachment,
    ChannelStatus,
    DownloadedAttachment,
    HealthSignal,
    InteractiveContent,
    MediaContent,
    MediaKind,
    MessageType,
    OutboundMessage,
    SendResult,
    TemplateContent,
    TextContent,
)


class ChannelAdapter(ABC):
    """What every channel — Meta included — looks like to the platform (Doc 07 §5.2)."""

    #: Canonical channel (Doc 03 ``channel_type``).
    channel_type: ChannelType
    #: Which implementation of that channel this is (Doc 07 §5.2 "Identity").
    connector_type: str
    #: Declared capabilities; the platform checks these instead of the channel's identity.
    capabilities: frozenset[Capability] = frozenset()

    # --- Identity ------------------------------------------------------------
    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def require(self, capability: Capability) -> None:
        """Guard an operation behind its declared capability (Doc 07 §5.2)."""
        if not self.supports(capability):
            raise ChannelNotSupported(
                f"{self.connector_type!r} does not support {capability.value!r}"
            )

    # --- Session / auth (§5.2) ----------------------------------------------
    async def connect(self) -> None:  # noqa: B027 - optional: token channels have no session
        """Establish a session. A no-op for token-based channels like Meta."""

    async def disconnect(self) -> None:  # noqa: B027 - optional, as above
        """Tear down a session. A no-op for token-based channels like Meta."""

    @abstractmethod
    async def authenticate(self) -> ChannelStatus:
        """Prove the credentials work, without sending anything."""

    @abstractmethod
    async def status(self) -> ChannelStatus:
        """Current session/auth state."""

    # --- Outbound messaging (§5.2) ------------------------------------------
    @abstractmethod
    async def _dispatch(self, message: OutboundMessage) -> SendResult:
        """Deliver a canonical message. Called only after the capability gate passes."""

    async def send(self, message: OutboundMessage) -> SendResult:
        """Send a canonical message, enforcing the capability the type requires."""
        self.require(CAPABILITY_FOR_TYPE[message.type])
        return await self._dispatch(message)

    async def send_text(self, to: str, body: str, *, preview_url: bool = False) -> SendResult:
        return await self.send(
            OutboundMessage(to=to, type=MessageType.TEXT, content=TextContent(body, preview_url))
        )

    async def send_media(
        self,
        to: str,
        kind: MediaKind,
        *,
        media_id: str | None = None,
        link: str | None = None,
        caption: str | None = None,
        filename: str | None = None,
    ) -> SendResult:
        return await self.send(
            OutboundMessage(
                to=to,
                type=MessageType.MEDIA,
                content=MediaContent(
                    kind=kind, media_id=media_id, link=link, caption=caption, filename=filename
                ),
            )
        )

    async def send_interactive(self, to: str, payload: dict[str, Any]) -> SendResult:
        return await self.send(
            OutboundMessage(
                to=to, type=MessageType.INTERACTIVE, content=InteractiveContent(payload)
            )
        )

    async def send_template(
        self, to: str, name: str, language: str, components: list[dict[str, Any]] | None = None
    ) -> SendResult:
        return await self.send(
            OutboundMessage(
                to=to,
                type=MessageType.TEMPLATE,
                content=TemplateContent(name=name, language=language, components=components or []),
            )
        )

    # --- Media (§5.2) --------------------------------------------------------
    async def upload_attachment(
        self, data: bytes, *, mime_type: str, filename: str | None = None
    ) -> Attachment:
        raise ChannelNotSupported(f"{self.connector_type!r} cannot upload attachments")

    async def download_attachment(self, media_id: str) -> DownloadedAttachment:
        raise ChannelNotSupported(f"{self.connector_type!r} cannot download attachments")

    # --- Health (§5.2) -------------------------------------------------------
    async def health_signal(self) -> HealthSignal:
        raise ChannelNotSupported(f"{self.connector_type!r} reports no health signal")

    async def close(self) -> None:  # noqa: B027 - optional: not every adapter holds a transport
        """Release transport resources. Safe to call more than once."""


_ADAPTERS: dict[str, Callable[..., ChannelAdapter]] = {}


def register_adapter(connector_type: str, factory: Callable[..., ChannelAdapter]) -> None:
    """Register an adapter factory under its connector type (Doc 07 §5.4)."""
    _ADAPTERS[connector_type] = factory


def available_adapters() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))


def get_adapter(connector_type: str, **kwargs: Any) -> ChannelAdapter:
    """Resolve a connector type to an adapter, or fail loudly if none is registered.

    Mirrors the storage registry: an unregistered channel is a configuration error surfaced at the
    call site, never a silent degradation.
    """
    factory = _ADAPTERS.get(connector_type)
    if factory is None:
        raise ChannelError(
            f"channel connector {connector_type!r} is not registered; "
            f"available: {available_adapters()}"
        )
    return factory(**kwargs)
