"""WAHA QR/multi-device adapter — QR-01 foundation.

A second *implementation* of the ``whatsapp`` channel family behind the existing
:class:`~app.channels.base.ChannelAdapter` seam (ADR-0020 invariant 1: "One existing channel seam").
No parallel adapter hierarchy, no provider-specific CRM service family, and nothing in core business
logic branches on ``connector_type``.

## What QR-01 actually implements

Exactly one thing: an authenticated **server** probe (version/engine banner and health), plus the
deterministic error mapping around it. That is the whole milestone.

## Why the capability set is (almost) empty

Capabilities are what the CRM *offers*. Declaring one advertises a working feature, so a capability
this adapter cannot execute would surface an action that fails at the provider — exactly the failure
mode the capability gate exists to prevent (Doc 07 §5.2).

The QR-00 certification spike proved the *provider* supports far more than this adapter does. That
distinction is the point: a provider endpoint existing is not the same as this adapter being able to
use it, and it is certainly not the same as a paired WhatsApp account working. Only ``HEALTH`` is
both implemented here and evidenced end-to-end, so only ``HEALTH`` is declared.

| Capability | Declared | Why |
|---|---|---|
| ``HEALTH`` | **yes** | :meth:`health_signal` is implemented and proven against the certified build. |
| ``QR_AUTH`` | no | Provider supports it (real QR observed in QR-00), but this adapter has no pairing method — QR-03. Declaring it would let the CRM offer a "Connect" action that cannot run. |
| ``SESSION_STREAM`` | no | Webhook ingestion is QR-04. |
| ``SESSION_RECONNECT`` / ``SESSION_LOGOUT`` | no | Session runtime is QR-06. |
| ``HISTORY_SYNC`` | no | QR-06; cursor stability also unproven (selection record: PENDING). |
| ``TEXT`` / ``MEDIA`` / ``MEDIA_UPLOAD`` / ``MEDIA_DOWNLOAD`` | no | Send path is QR-05 and none is proven with a paired account. |
| ``INTERACTIVE`` / ``REACTION`` / ``LOCATION`` / ``CONTACT`` | no | Neither implemented nor evidenced. |
| ``BULK`` / ``CAMPAIGNS`` / ``TEMPLATE`` | **never** | Permanently prohibited — see below. |

## Permanently prohibited capabilities

``BULK``, ``CAMPAIGNS`` and ``TEMPLATE`` are not "not yet"; they are **forbidden for this provider
forever**. ADR-0020 §5 keeps templates, campaigns and broadcasts as Meta capabilities; ADR-0021
states Class B "does not permit QR campaigns, broadcasts, bulk automation"; and the owner's Class B
approval excludes them explicitly. :data:`PROHIBITED_CAPABILITIES` records this and is enforced by a
test that no future milestone may quietly relax.

## Server health is not session health

:meth:`health_signal` and :meth:`status` report on the **WAHA server**, never on a WhatsApp account.
A perfectly healthy WAHA server with zero paired sessions cannot send or receive anything, so
:meth:`status` returns ``connected=False``: at QR-01 no WhatsApp session exists, can exist, or is
claimed to exist.
"""

from __future__ import annotations

from typing import Any, Final

from app.channels.base import ChannelAdapter
from app.channels.capabilities import CONNECTOR_WAHA, Capability, ChannelType
from app.channels.errors import ChannelConfigError, ChannelNotSupported
from app.channels.models import ChannelStatus, HealthSignal, OutboundMessage, SendResult
from app.channels.waha.client import WahaClient, WahaCredentials, WahaServerInfo
from app.core.config import settings

#: Capabilities this provider may never declare, at any milestone (ADR-0020 §5; ADR-0021; owner
#: Class B approval). Enforced by test, not convention.
PROHIBITED_CAPABILITIES: Final[frozenset[Capability]] = frozenset(
    {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
)


class WahaEngineNotApproved(ChannelConfigError):
    """The server runs an engine this deployment has not certified.

    Fails **closed**: engine payload shapes differ between WAHA engines, so an adapter written and
    certified against NOWEB must not silently interpret another engine's output.
    """


class WahaChannelAdapter(ChannelAdapter):
    """WAHA QR provider adapter (ADR-0021 Class B). QR-01: server probe only."""

    channel_type = ChannelType.WHATSAPP
    connector_type = CONNECTOR_WAHA
    #: Only what this adapter can actually do today. See the module docstring for the full rationale.
    capabilities = frozenset({Capability.HEALTH})

    def __init__(
        self,
        credentials: WahaCredentials | None = None,
        *,
        client: WahaClient | None = None,
    ) -> None:
        # Constructing an adapter must stay free of I/O: registration builds one eagerly in some
        # call paths, and a constructor that dialled the provider would make import order a
        # network dependency.
        self._client = client or WahaClient(credentials)

    @property
    def client(self) -> WahaClient:
        return self._client

    @property
    def configured(self) -> bool:
        """Whether a WAHA server has been configured for this deployment at all."""
        return self._client.credentials.configured

    # --- Version / engine safety --------------------------------------------
    @staticmethod
    def _assert_engine_approved(info: WahaServerInfo) -> None:
        approved = settings.waha_approved_engine
        if info.engine.upper() != approved.upper():
            raise WahaEngineNotApproved(
                f"WAHA server reports engine {info.engine!r}, but only {approved!r} is approved "
                "for this deployment. Payload shapes differ between engines; refusing to proceed.",
                detail=f"engine={info.engine}",
            )

    @staticmethod
    def version_drift(info: WahaServerInfo) -> str | None:
        """Human-readable drift note when the server is not the certified build, else ``None``.

        Reported, never auto-corrected: this repository pins an immutable image and does not
        upgrade providers on its own. Drift is a signal for an operator, not a trigger.
        """
        certified = settings.waha_certified_version
        if certified and info.version != certified:
            return f"version drift: server {info.version}, certified {certified}"
        return None

    async def server_info(self) -> WahaServerInfo:
        """Authenticated build banner, with the engine guard applied.

        The single place the engine is validated, so no caller can obtain a
        :class:`WahaServerInfo` for an unapproved engine.
        """
        info = await self._client.server_version()
        self._assert_engine_approved(info)
        return info

    # --- Session / auth ------------------------------------------------------
    async def authenticate(self) -> ChannelStatus:
        """Prove the **server** API key works. Does not create, resume or check a WhatsApp session.

        ``connected=False`` is deliberate and honest: authenticating to WAHA says nothing about a
        WhatsApp account, and at QR-01 no session exists. Reporting ``True`` here would let a caller
        conclude the channel can message.
        """
        info = await self.server_info()
        drift = self.version_drift(info)
        detail = f"WAHA server authenticated (version {info.version}, engine {info.engine})"
        if drift:
            detail = f"{detail}; {drift}"
        return ChannelStatus(
            connected=False,
            identity=None,
            detail=f"{detail}. No WhatsApp session — QR pairing is not implemented (QR-02+).",
        )

    async def status(self) -> ChannelStatus:
        """Server reachability/auth only — there is no session state to report at QR-01."""
        return await self.authenticate()

    # --- Health --------------------------------------------------------------
    async def health_signal(self) -> HealthSignal:
        """WAHA **server** health (``GET /health``) — storage headroom and dependencies.

        Never a WhatsApp session signal. ``healthy=True`` means the provider process is serving
        requests; it does not imply any account is paired or able to send.
        """
        self.require(Capability.HEALTH)
        health = await self._client.server_health()
        detail = f"WAHA server status={health.status} (server health only, not session health)"
        if health.detail:
            detail = f"{detail}; {health.detail}"
        return HealthSignal(healthy=health.healthy, detail=detail)

    # --- Outbound (not implemented at QR-01) --------------------------------
    async def _dispatch(self, message: OutboundMessage) -> SendResult:
        """Unreachable: :meth:`ChannelAdapter.send` gates on a capability this adapter withholds.

        Implemented anyway as defence in depth — if a future change ever declared a send
        capability without writing a send path, this fails loudly instead of silently doing
        nothing.
        """
        raise ChannelNotSupported(
            f"{self.connector_type!r} cannot send messages: the outbound path is not implemented "
            "at QR-01 (QR-05)."
        )

    async def close(self) -> None:
        await self._client.close()


def _factory(**kwargs: Any) -> WahaChannelAdapter:
    """Adapter factory used by the registry.

    Performs **no** network call and requires **no** API key: constructing an adapter for an
    unconfigured deployment is legal and inert, which is what lets the provider be registered
    statically while remaining disabled by default.
    """
    return WahaChannelAdapter(**kwargs)
