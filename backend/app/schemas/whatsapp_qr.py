"""QR-07 — WhatsApp Scan/Connect API contracts.

Provider-neutral on the wire: every field is the platform's own vocabulary
(:mod:`app.channels.session`, :mod:`app.channels.runtime`), never a raw WAHA status string beyond
one informational, non-authoritative echo. No WAHA credential, API key, HMAC secret or QR byte is
ever represented in a JSON model — the QR image is served as a separate binary response, never
embedded here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WhatsAppQrStatus(BaseModel):
    """Current WhatsApp QR connection status for the caller's organization.

    ``configured=False`` covers every reason the screen has nothing to operate on — WAHA
    unconfigured, the organization not assigned, feature flags disabled — collapsed into one
    honest "not available" signal rather than distinguishing operator-irrelevant deployment detail.
    """

    configured: bool = Field(
        description="Whether a WhatsApp QR connection is available to configure/operate."
    )
    session_public_id: str | None = Field(
        default=None, description="Durable session identifier once a connection has been started."
    )
    row_version: int | None = Field(default=None, description="Optimistic-concurrency version.")

    session_state: str | None = Field(
        default=None, description="Provider-neutral session lifecycle (SessionState)."
    )
    pairing_state: str | None = Field(
        default=None,
        description=(
            "Provider-neutral pairing lifecycle (PairingState), or null when the provider's "
            "current status cannot determine it (e.g. mid-transition)."
        ),
    )
    provider_status: str | None = Field(
        default=None,
        description="Informational only: the raw provider status last observed. Not authoritative.",
    )

    connected: bool = Field(description="Whether this WhatsApp session can carry traffic now.")
    requires_reauthentication: bool = Field(
        description="Whether only a fresh scan can resolve the current state."
    )
    healthy: bool = Field(description="Session-level health — never server-only reachability.")
    health_detail: str = Field(description="Human-readable, secret-free health explanation.")

    can_reconnect: bool = Field(description="Whether a reconnect action is currently safe.")
    reconnect_blocked_reason: str | None = Field(
        default=None,
        description="Why reconnect is unavailable right now, when can_reconnect is false.",
    )

    identity_masked: str | None = Field(
        default=None, description="Paired account identity with digits partly masked."
    )
    push_name: str | None = Field(default=None, description="Paired account display name.")

    qr_available: bool = Field(
        description="Whether GET /whatsapp/qr will currently return an image."
    )

    provider_session_missing: bool = Field(
        default=False,
        description=(
            "Whether WhatsApp is reachable but holds no session for this connection. Distinct "
            "from an outage: the provider answered. The connection must be paired again; nothing "
            "is recreated automatically."
        ),
    )

    updated_at: datetime | None = Field(
        default=None, description="When this status was last reconciled against the provider."
    )


class WhatsAppQrLogoutRequest(BaseModel):
    """Explicit confirmation required before an irreversible logout."""

    confirm: bool = Field(
        description="Must be true. Logout invalidates WhatsApp credentials and requires a new scan."
    )
