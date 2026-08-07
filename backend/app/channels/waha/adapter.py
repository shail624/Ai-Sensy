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

QR-05: **send and delivery state** — outbound text through the configured session, provider-id
capture, acknowledgement translation onto the platform's existing monotonic status vocabulary, and
the reconcile-before-resend primitive (:mod:`app.channels.waha.delivery`). This earns ``TEXT``.

QR-06: **recovery, health and teardown** — start/stop/logout behind a runtime lease, bounded
reconnect planning, and a session-scoped health projection
(:mod:`app.channels.waha.recovery`). This earns ``SESSION_RECONNECT`` and ``SESSION_LOGOUT``.

QR-06 is the first milestone that may take a session **down**, so its safety rules matter: a
reconnect is planned from the platform's own durable pairing record rather than the provider's
ambiguous ``STARTING``, an unreachable provider means "unknown" rather than "unpaired", and a logout
deliberately produces re-authentication-required truth that nothing here tries to auto-repair.

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
| ``SESSION_RECONNECT`` / ``SESSION_LOGOUT`` | **yes** | QR-06. Start/stop/logout are implemented behind a runtime lease, with bounded reconnect planning that never guesses from an ambiguous provider status. |
| ``HISTORY_SYNC`` | no | QR-06; cursor stability also unproven (selection record: PENDING). |
| ``TEXT`` | **yes** | QR-05. :meth:`_dispatch` sends text through the configured session, and certification proved an external cross-account delivery reaching ``READ``. |
| ``MEDIA`` / ``MEDIA_UPLOAD`` / ``MEDIA_DOWNLOAD`` | no | QR-05 sends text only; media transfer is a later milestone. |
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
from app.channels.errors import ChannelConfigError, ChannelNotSupported, ChannelTransportError
from app.channels.models import (
    ChannelStatus,
    HealthSignal,
    InboundEvent,
    InboundMessage,
    MessageType,
    OutboundMessage,
    SendResult,
    StatusUpdate,
    TextContent,
)
from app.channels.runtime import PairingState
from app.channels.waha.client import WahaClient, WahaCredentials, WahaServerInfo
from app.channels.waha.delivery import extract_sent_id, to_status_update
from app.channels.waha.lifecycle import WahaSessionSnapshot
from app.channels.waha.pairing import WahaQrChallenge
from app.channels.waha.recovery import (
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    ReconnectDecision,
    RuntimeLease,
    plan_reconnect,
    project_health,
)
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
        {
            Capability.HEALTH,
            Capability.QR_AUTH,
            Capability.SESSION_STREAM,
            Capability.TEXT,
            Capability.SESSION_RECONNECT,
            Capability.SESSION_LOGOUT,
        }
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

    def to_status_update(self, payload: dict[str, Any]) -> StatusUpdate:
        """A ``message.ack`` event's payload → the delivery-state change it represents.

        Returns the platform's own status vocabulary, so ``messages`` applies it through the
        existing monotonic :func:`~app.models.message.advances` guard. An uncertified
        acknowledgement raises rather than being guessed at — see :mod:`app.channels.waha.delivery`.
        """
        self.require(Capability.SESSION_STREAM)
        return to_status_update(payload)

    # --- Session recovery / teardown (QR-06) ---------------------------------
    async def session_health(self, name: str) -> HealthSignal:
        """Health of one **WhatsApp session** — not the server.

        A reachable server with no ``WORKING`` session reports unhealthy, and a session awaiting a
        scan reports re-authentication required, which outranks generic provider health. An
        unreachable provider is reported as unknown-and-unhealthy rather than optimistically fine.
        """
        self.require(Capability.HEALTH)
        try:
            snapshot = await self.session_snapshot(name)
        except ChannelTransportError:
            return project_health(None)
        return project_health(snapshot)

    async def plan_session_recovery(
        self,
        name: str,
        *,
        durable_pairing_state: PairingState,
        attempts: int = 0,
        max_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS,
    ) -> ReconnectDecision:
        """Decide what may safely be done for a session, without mutating anything.

        ``durable_pairing_state`` is the platform's own record, and it is authoritative here: the
        provider's ``STARTING`` cannot distinguish a fresh session from a paired one resuming, so a
        reconnect is never planned from provider status alone.
        """
        self.require(Capability.SESSION_RECONNECT)
        try:
            snapshot = await self.session_snapshot(name)
            status = snapshot.status
        except ChannelTransportError:
            # Unreachable is "unknown", never "unpaired" — durable truth must survive an outage.
            status = None
        return plan_reconnect(
            provider_status=status,
            durable_pairing_state=durable_pairing_state,
            attempts=attempts,
            max_attempts=max_attempts,
        )

    async def reconnect_session(self, name: str, *, lease: RuntimeLease | None = None) -> WahaSessionSnapshot:
        """Resume an existing session. Never creates one, never pairs, never fetches a QR.

        Idempotent against an already-working session: the provider is asked to start, and a session
        that is already ``WORKING`` simply stays that way.
        """
        self.require(Capability.SESSION_RECONNECT)
        self._require_lease(lease)
        snapshot = await self._client.start_session(name)
        self._assert_session_engine(snapshot)
        return snapshot

    async def stop_session(self, name: str, *, lease: RuntimeLease | None = None) -> WahaSessionSnapshot:
        """Halt a session while leaving its stored credentials intact.

        Non-destructive to pairing — see :meth:`logout_session` for the destructive counterpart.
        """
        self.require(Capability.SESSION_RECONNECT)
        self._require_lease(lease)
        snapshot = await self._client.stop_session(name)
        self._assert_session_engine(snapshot)
        return snapshot

    async def logout_session(self, name: str, *, lease: RuntimeLease | None = None) -> WahaSessionSnapshot:
        """Invalidate the session's WhatsApp credentials, requiring a fresh scan afterwards.

        The resulting re-authentication-required state is the **intended** outcome, not a fault to
        be auto-repaired: nothing in this adapter may respond to it by fetching a QR or re-pairing.
        """
        self.require(Capability.SESSION_LOGOUT)
        self._require_lease(lease)
        snapshot = await self._client.logout_session(name)
        self._assert_session_engine(snapshot)
        return snapshot

    @staticmethod
    def _require_lease(lease: RuntimeLease | None) -> None:
        """Lifecycle mutation requires a lease the caller has already validated as current.

        The durable check belongs to the existing session authority
        (:func:`~app.channels.waha.recovery.assert_lease_current` against
        ``SessionManager``/``ProviderRuntimeManager``); this only refuses an unowned mutation
        outright so no caller can skip that step by omission.
        """
        if lease is None:
            raise ChannelConfigError(
                "A session lifecycle mutation requires a runtime lease; refusing to act without "
                "proven ownership."
            )

    # --- Outbound (QR-05) ----------------------------------------------------
    async def _dispatch(self, message: OutboundMessage) -> SendResult:
        """Send one text through the configured session.

        Only text is implemented, so a non-text message is refused rather than silently degraded
        into one. A transport failure surfaces as :class:`WahaSendIndeterminate`, which is **not**
        retry-safe: reconcile with :meth:`reconcile_send` before considering any resend.
        """
        if message.type is not MessageType.TEXT:
            raise ChannelNotSupported(
                f"{self.connector_type!r} can send text only at QR-05; "
                f"{message.type.value!r} is not implemented."
            )
        content = message.content
        if not isinstance(content, TextContent):
            raise ChannelNotSupported("A text send requires TextContent.")

        body = await self._client.send_text(chat_id=message.to, text=content.body)
        provider_id = extract_sent_id(body)
        # `accepted` is false without an id: the provider answered, but nothing identifies the
        # message, so it can never be correlated to an acknowledgement or reconciled later.
        return SendResult(
            to=message.to,
            channel_message_id=provider_id,
            accepted=bool(provider_id),
            raw=body,
        )

    async def reconcile_send(self, *, to: str, canonical_id: str) -> bool:
        """Whether ``canonical_id`` exists at the provider — the reconcile-before-resend primitive.

        Endpoint-scoped by construction: the lookup runs inside the configured session's own chat,
        so it cannot confirm a message belonging to another endpoint and performs no global search.

        ``True`` means the message **is** present and must not be resent. ``False`` means this
        session's recent history does not contain it. A caller may only resend on ``False``; if the
        lookup itself fails, the error propagates and the outcome stays indeterminate rather than
        being downgraded to "absent".
        """
        self.require(Capability.TEXT)
        return await self._client.message_exists(chat_id=to, canonical_id=canonical_id)

    async def close(self) -> None:
        await self._client.close()


def _factory(**kwargs: Any) -> WahaChannelAdapter:
    """Adapter factory used by the registry.

    Performs **no** network call and requires **no** API key: constructing an adapter for an
    unconfigured deployment is legal and inert, which is what lets the provider be registered
    statically while remaining disabled by default.
    """
    return WahaChannelAdapter(**kwargs)
