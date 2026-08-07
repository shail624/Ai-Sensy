"""WAHA QR provider adapter package (ADR-0021 Class B) — QR-01 foundation, QR-02 lifecycle, QR-03 pairing.

Importing this package registers the ``waha`` adapter factory, following the same self-registration
pattern as the Meta package so wiring a provider in is an import rather than an edit to the engine
(Doc 07 §5.4).

Registration here is **inert by design**:

* no network call happens at import or registration — the factory only constructs an object;
* no API key is required to import, register or construct the adapter;
* importing or registering the adapter still creates no session and pairs nothing — QR-03's pairing
  methods are capability-gated and must be called explicitly with a session name;
* no session can be stopped, restarted or logged out at any point — that is QR-06;
* nothing is added to :class:`~app.channels.runtime_registry.ProviderRuntimeRegistry`, so there is
  no live WAHA runtime and no supervisor can start one;
* every organization-facing QR feature flag stays off by default
  (:class:`~app.channels.flags.OmnichannelFeatureFlag`).

Registering the adapter makes it *resolvable*; it does not make it *enabled*. A deployment with no
``WAHA_BASE_URL``/``WAHA_API_KEY`` boots normally and the adapter simply raises
:class:`~app.channels.errors.ChannelConfigError` if anything ever asks it to talk to a server.

Unlike ``app.channels.meta``, this package installs **no** retry error map: QR-01 has no queued
provider work to classify. That arrives with the send/ingestion paths (QR-04/QR-05).
"""

from __future__ import annotations

from app.channels.base import register_adapter
from app.channels.capabilities import CONNECTOR_WAHA
from app.channels.waha.adapter import (
    PROHIBITED_CAPABILITIES,
    WahaChannelAdapter,
    WahaEngineNotApproved,
    _factory,
)
from app.channels.waha.client import (
    WahaClient,
    WahaCredentials,
    WahaServerHealth,
    WahaServerInfo,
    redact_headers,
)
from app.channels.waha.delivery import (
    ACK_TO_STATUS,
    WahaAck,
    WahaSendIndeterminate,
    extract_sent_id,
    map_ack,
)
from app.channels.waha.lifecycle import (
    WahaSessionSnapshot,
    WahaSessionStatus,
    map_session_status,
    parse_session_status,
    validate_session_name,
)
from app.channels.waha.pairing import (
    CERTIFIED_NOWEB_STORE,
    WahaQrChallenge,
    build_session_config,
)
from app.channels.waha.recovery import (
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    WAHA_RUNTIME_CAPABILITIES,
    ReconnectDecision,
    RuntimeLease,
    StaleRuntimeLease,
    assert_lease_current,
    backoff_delay,
    plan_reconnect,
    project_health,
    register_waha_runtime,
    waha_channel_metadata,
    waha_runtime_metadata,
)
from app.channels.waha.webhook import (
    MAX_BODY_BYTES,
    SIGNATURE_HEADER,
    WahaBodyTooLarge,
    canonical_message_id,
    event_identity,
    parse_events,
    verify_signature,
)

register_adapter(CONNECTOR_WAHA, _factory)

__all__ = [
    "ACK_TO_STATUS",
    "CERTIFIED_NOWEB_STORE",
    "DEFAULT_MAX_RECONNECT_ATTEMPTS",
    "MAX_BODY_BYTES",
    "WAHA_RUNTIME_CAPABILITIES",
    "ReconnectDecision",
    "RuntimeLease",
    "StaleRuntimeLease",
    "assert_lease_current",
    "backoff_delay",
    "plan_reconnect",
    "project_health",
    "register_waha_runtime",
    "waha_channel_metadata",
    "waha_runtime_metadata",
    "WahaAck",
    "WahaSendIndeterminate",
    "extract_sent_id",
    "map_ack",
    "PROHIBITED_CAPABILITIES",
    "SIGNATURE_HEADER",
    "WahaBodyTooLarge",
    "canonical_message_id",
    "event_identity",
    "parse_events",
    "verify_signature",
    "WahaChannelAdapter",
    "WahaClient",
    "WahaCredentials",
    "WahaEngineNotApproved",
    "WahaQrChallenge",
    "WahaServerHealth",
    "WahaServerInfo",
    "WahaSessionSnapshot",
    "WahaSessionStatus",
    "build_session_config",
    "map_session_status",
    "parse_session_status",
    "redact_headers",
    "validate_session_name",
]
