"""WAHA QR/multi-device adapter — QR-01 foundation.

A second *implementation* of the ``whatsapp`` channel family behind the existing
:class:`~app.channels.base.ChannelAdapter` seam (ADR-0020 invariant 1: "One existing channel seam").
No parallel adapter hierarchy, no provider-specific CRM service family, and nothing in core business
logic branches on ``connector_type``.

## What this adapter actually implements

QR-01: an authenticated **server** probe (version/engine banner and health), plus the deterministic
error mapping around it.

QR-02: reading a **named session's** lifecycle status and translating it into the platform's own
vocabulary (:mod:`app.channels.waha.lifecycle`).

QR-03: **QR pairing** — creating a session with the certified store configuration and fetching the
transient QR challenge a handset scans (:mod:`app.channels.waha.pairing`). This is the milestone
that earns ``QR_AUTH``.

QR-04: **inbound stream** — raw-body HMAC verification and normalization of provider deliveries into
canonical :class:`InboundEvent` values for the existing ``webhook_events`` ingest authority
(:mod:`app.channels.waha.webhook`). This is the milestone that earns ``SESSION_STREAM``.

The asymmetry is deliberate: QR-03 can bring a session **up** but has no way to stop, restart or log
one out. Teardown is QR-06, so nothing here can destroy a working pairing. Likewise QR-04 *receives*
events but sends nothing and applies no delivery state — that is QR-05.

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
| ``QR_AUTH`` | **yes** | QR-03. :meth:`begin_pairing`/:meth:`pairing_challenge`/:meth:`pairing_state` are implemented, and physical-phone certification paired a real handset through this exact provider path. |
| ``SESSION_STREAM`` | **yes** | QR-04. Raw-body sha512 HMAC verification and event normalization into the existing ``webhook_events`` ingest authority. |
| ``SESSION_RECONNECT`` / ``SESSION_LOGOUT`` | no | Session runtime is QR-06. QR-03 can bring a session **up**; it deliberately cannot stop, restart or log one out. |
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

:meth:`health_signal`, :meth:`authenticate` and :meth:`status` report on the **WAHA server**, never
on a WhatsApp account. A perfectly healthy WAHA server with zero paired sessions cannot send or
receive anything, so those three always return ``connected=False``.

:meth:`session_status` is the only method that may report ``connected=True``, and only for a
session the caller named that the provider reports as ``WORKING``. The distinction is the point:
"the server answers" and "this account can message" are different facts, and QR-02 keeps them on
separate methods so no caller can conflate them.
"""

from __future__ import annotations

from typing import Any, Final

from app.channels.base import ChannelAdapter
from app.channels.capabilities import CONNECTOR_WAHA, Capability, ChannelType
from app.channels.errors import ChannelConfigError, ChannelNotSupported
from app.channels.models import (
    ChannelStatus,
    HealthSignal,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    SendResult,
)
from app.channels.runtime import PairingState
from app.channels.waha.client import WahaClient, WahaCredentials, WahaServerInfo
from app.channels.waha.lifecycle import WahaSessionSnapshot
from app.channels.waha.pairing import WahaQrChallenge
from app.channels.waha.webhook import parse_events, to_inbound_message, verify_signature
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
    capabilities = frozenset(
        {Capability.HEALTH, Capability.QR_AUTH, Capability.SESSION_STREAM}
    )

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
            detail=f"{detail}. No WhatsApp session — QR pairing is not implemented (QR-03).",
        )

    async def status(self) -> ChannelStatus:
        """Server reachability/auth only.

        Unchanged by QR-02 on purpose: this adapter owns no session name, so it cannot know *which*
        session a generic ``status()`` should describe. Session lifecycle is read explicitly through
        :meth:`session_snapshot`, which requires the caller to name the session it means.
        """
        return await self.authenticate()

    # --- Session lifecycle (QR-02) -------------------------------------------
    @staticmethod
    def _assert_session_engine(snapshot: WahaSessionSnapshot) -> None:
        """Apply the engine guard to a session payload.

        An adapter certified against NOWEB must not interpret — or pair against — another engine's
        session. Sessions whose payload omits the engine are not rejected: the guard reports on what
        the provider stated, and inventing a violation from silence would break valid deployments.
        """
        if snapshot.engine is None:
            return
        approved = settings.waha_approved_engine
        if snapshot.engine.upper() != approved.upper():
            raise WahaEngineNotApproved(
                f"WAHA session reports engine {snapshot.engine!r}, but only {approved!r} is "
                "approved for this deployment.",
                detail=f"engine={snapshot.engine}",
            )

    async def session_snapshot(self, name: str) -> WahaSessionSnapshot:
        """Read one session's lifecycle status and map it to provider-neutral state."""
        snapshot = await self._client.session_status(name)
        self._assert_session_engine(snapshot)
        return snapshot

    async def session_status(self, name: str) -> ChannelStatus:
        """Provider-neutral :class:`ChannelStatus` for one named session.

        ``connected`` is true only for a ``WORKING`` session — never for a merely reachable server.
        """
        snapshot = await self.session_snapshot(name)
        pairing = snapshot.pairing_state
        detail = (
            f"WAHA session {snapshot.name!r}: provider status={snapshot.status.value}, "
            f"session_state={snapshot.session_state.value}, "
            f"pairing_state={pairing.value if pairing else 'indeterminate'}"
        )
        return ChannelStatus(
            connected=snapshot.connected,
            identity=snapshot.identity,
            detail=detail,
        )

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

    # --- Pairing (QR-03) -----------------------------------------------------
    async def begin_pairing(self, name: str) -> WahaSessionSnapshot:
        """Create and start a session so it can present a QR, then report its mapped state.

        Capability-gated on :attr:`Capability.QR_AUTH`. The engine guard applies, so a session
        created on an unapproved engine is rejected rather than paired against.

        Deliberately **not** idempotent-by-guessing: if the provider says a session of this name
        already exists, that error surfaces. Silently reusing or recreating it could tear down a
        working pairing, and this milestone owns no teardown.
        """
        self.require(Capability.QR_AUTH)
        snapshot = await self._client.create_session(name)
        self._assert_session_engine(snapshot)
        return snapshot

    async def pairing_challenge(self, name: str) -> WahaQrChallenge:
        """Fetch the transient QR challenge for a session that is awaiting a scan.

        The result is never logged or persisted — see :class:`WahaQrChallenge`. A session that is
        not awaiting a scan raises rather than returning a stale or placeholder image.
        """
        self.require(Capability.QR_AUTH)
        return await self._client.qr_challenge(name)

    async def pairing_state(self, name: str) -> PairingState | None:
        """Provider-neutral pairing state, or ``None`` when the provider status cannot determine it.

        ``None`` is a real answer, not a failure. Certification proved ``STARTING`` occurs both for
        a fresh session heading toward a QR and for an already-paired session restarting toward
        ``WORKING``; ``STOPPED`` and ``FAILED`` are similarly undetermined. Callers must leave
        durable pairing truth untouched when this returns ``None`` — inferring "unpaired" here would
        discard a real pairing on a transient restart.
        """
        self.require(Capability.QR_AUTH)
        snapshot = await self.session_snapshot(name)
        return snapshot.pairing_state

    # --- Inbound stream (QR-04) ----------------------------------------------
    def verify_webhook_signature(self, body: bytes, signature: str | None) -> bool:
        """Raw-body sha512 HMAC check, run **before** anything parses the delivery.

        The raw bytes are what the provider signed, so they are verified as received — any
        re-serialisation would change them. An unconfigured secret rejects rather than accepts.
        """
        return verify_signature(
            body,
            signature,
            settings.waha_webhook_hmac_secret,
        )

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundEvent]:
        """Verified delivery → canonical events, deduped on a session+type-scoped identity.

        ``envelope.id`` alone is not unique: certification proved one provider message is delivered
        as both ``message`` and ``message.any`` sharing it. See :mod:`app.channels.waha.webhook`.
        """
        self.require(Capability.SESSION_STREAM)
        return parse_events(payload)

    def to_inbound_message(self, payload: dict[str, Any]) -> InboundMessage:
        """A ``MESSAGES`` event's payload → the message it represents (text at QR-04)."""
        self.require(Capability.SESSION_STREAM)
        return to_inbound_message(payload)

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
