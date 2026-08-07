"""Minimal typed async WAHA client (QR-01 server probe, QR-02 lifecycle read, QR-03 pairing).

Deliberately small, and grown one milestone at a time:

* QR-01 — two authenticated reads: the server version/engine banner and the server health probe.
* QR-02 — one more read: a single session's lifecycle status.
* QR-03 — creating a session with the certified configuration, and fetching its transient QR.

Start, stop, restart and logout (QR-06), webhook ingestion (QR-04), messaging (QR-05), media and
history are **not** implemented here and must not be reachable from this milestone. In particular
this client can bring a session up but still cannot tear a paired one down.

Everything the platform catches is a channel-neutral error from :mod:`app.channels.errors`, so no
WAHA exception type escapes the seam (Doc 07 §5.3). Deterministic mapping of every failure shape
observed against the real certified build is in :meth:`WahaClient._decode` / :meth:`_raise`.

**Secrets.** The API key is held in :class:`WahaCredentials`, sent only as the ``X-Api-Key``
request header, and never logged, never echoed into an exception message, and never included in a
``repr``. :func:`redact_headers` is the single place header redaction is defined and is applied to
anything diagnostic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import quote

import httpx

from app.channels.errors import (
    ChannelApiError,
    ChannelAuthError,
    ChannelConfigError,
    ChannelTransportError,
)
from app.channels.waha.delivery import WahaSendIndeterminate
from app.channels.waha.lifecycle import WahaSessionSnapshot, validate_session_name
from app.channels.waha.pairing import WahaQrChallenge, build_session_config
from app.channels.waha.webhook import canonical_message_id
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Header carrying the server API key. Never logged with its value.
API_KEY_HEADER: Final = "X-Api-Key"

#: Header names whose values must never appear in a log, error, trace or diagnostic payload.
SENSITIVE_HEADERS: Final[frozenset[str]] = frozenset({"x-api-key", "authorization", "cookie"})

_REDACTED: Final = "***redacted***"


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Copy of ``headers`` with every sensitive value replaced.

    The one definition of what "redacted" means for this adapter, so a future diagnostic surface
    cannot accidentally invent a laxer rule.
    """
    return {
        name: (_REDACTED if name.lower() in SENSITIVE_HEADERS else value)
        for name, value in headers.items()
    }


@dataclass(frozen=True, slots=True)
class WahaServerInfo:
    """The server's self-reported build banner (``GET /api/server/version``).

    Describes the **WAHA server**, not a WhatsApp account. A populated ``version``/``engine`` says
    nothing about whether any WhatsApp session exists.
    """

    version: str
    engine: str
    tier: str | None = None
    platform: str | None = None


@dataclass(frozen=True, slots=True)
class WahaServerHealth:
    """The server's own health probe (``GET /health``) — storage headroom and dependencies.

    Again server-scoped: ``healthy=True`` means the WAHA process is serving requests, **not** that a
    WhatsApp session is paired or able to message.
    """

    healthy: bool
    status: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class WahaCredentials:
    """Connection details for the self-hosted WAHA server.

    Passed in explicitly rather than read inside the client, mirroring
    :class:`~app.channels.meta.client.MetaCredentials`, so a per-connection credential loaded from
    ``channel_secrets`` reaches the client the same way in a later milestone with no change here.
    """

    base_url: str = ""
    api_key: str = ""
    #: The session this connection sends through. **This is the endpoint scope**: a message id may
    #: only ever be resolved within its own session, which is what prevents one endpoint from
    #: advancing another's message. Mirrors Meta's ``require_phone_number()``.
    session: str = ""

    @classmethod
    def from_settings(cls) -> WahaCredentials:
        """Process-wide defaults. All are empty unless explicitly configured."""
        return cls(
            base_url=settings.waha_base_url,
            api_key=settings.waha_api_key,
            session=settings.waha_session_name,
        )

    def __repr__(self) -> str:  # pragma: no cover - defensive; exercised via test_no_secret_in_repr
        """Never render the key, even in a traceback or debugger."""
        return (
            f"WahaCredentials(base_url={self.base_url!r}, session={self.session!r}, "
            f"api_key={_REDACTED!r})"
        )

    def require_session(self) -> str:
        """The session to act on, validated, or fail closed before any request is built.

        Sending or reconciling without an explicit session would leave the endpoint scope implicit,
        and an implicit scope is how one endpoint ends up resolving another's message.
        """
        if not self.session:
            raise ChannelConfigError(
                "WAHA session is not configured; set WAHA_SESSION_NAME. "
                "A send must name the endpoint it goes through."
            )
        return validate_session_name(self.session)

    @property
    def configured(self) -> bool:
        """Whether this deployment has been given a WAHA server at all."""
        return bool(self.base_url and self.api_key)

    @property
    def root(self) -> str:
        return self.base_url.rstrip("/")

    def require(self) -> None:
        """Fail closed before any socket is opened when the provider is not configured.

        Separate from an auth *rejection*: this never reaches the network, and the message names
        the environment variable to set without revealing anything secret.
        """
        if not self.base_url:
            raise ChannelConfigError(
                "WAHA base URL is not configured; set WAHA_BASE_URL. "
                "The WAHA provider is unconfigured and disabled by default."
            )
        if not self.api_key:
            raise ChannelConfigError(
                "WAHA API key is not configured; set WAHA_API_KEY. "
                "There is no default key — an unauthenticated WAHA server must never be used."
            )


class WahaClient:
    """Async HTTP client for the two authenticated reads QR-01 needs.

    ``http`` is injectable so tests drive it with an ``httpx.MockTransport`` and never touch the
    network — the same pattern :class:`~app.channels.meta.client.MetaCloudClient` uses.
    """

    def __init__(
        self,
        credentials: WahaCredentials | None = None,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float | None = None,
    ) -> None:
        self._credentials = credentials or WahaCredentials.from_settings()
        self._http = http
        self._timeout = timeout if timeout is not None else settings.waha_timeout_seconds

    @property
    def credentials(self) -> WahaCredentials:
        return self._credentials

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self._http

    def _headers(self) -> dict[str, str]:
        return {API_KEY_HEADER: self._credentials.api_key, "Accept": "application/json"}

    def url(self, path: str) -> str:
        return f"{self._credentials.root}/{path.lstrip('/')}"

    async def _get(self, path: str) -> dict[str, Any]:
        """Authenticated GET returning a decoded object, or a channel-neutral error."""
        self._credentials.require()
        request = httpx.Request("GET", self.url(path), headers=self._headers())
        try:
            # Timeout lives on the send call, not the request: httpx.Request carries no timeout.
            response = await self._client().send(request)
        except httpx.TimeoutException as exc:
            # Distinct from "unavailable": the server may be up but wedged. Both are transient to
            # the retry engine, but the operator-facing text must not conflate them.
            raise ChannelTransportError(
                f"WAHA request timed out after {self._timeout}s: {request.url.path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChannelTransportError(
                f"WAHA server is unavailable: {request.url.path}"
            ) from exc
        return self._decode(response)

    def _decode(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            self._raise(response)

        # An unexpected content type is treated as a provider fault rather than parsed
        # optimistically: the certified build answers every API route with JSON, so HTML here means
        # a proxy, login page or error surface is in front of the server (observed: the root path
        # returns `text/html` on 401).
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            raise ChannelApiError(
                "WAHA returned an unexpected content type "
                f"({content_type or 'none'}); expected JSON",
                http_status=response.status_code,
            )
        try:
            body = response.json()
        except ValueError as exc:
            # Body deliberately not included — it is provider output of unknown provenance.
            raise ChannelApiError(
                "WAHA returned a malformed (non-JSON) response",
                http_status=response.status_code,
            ) from exc
        if not isinstance(body, dict):
            raise ChannelApiError(
                "WAHA returned an unexpected JSON shape; expected an object",
                http_status=response.status_code,
            )
        return body

    def _raise(self, response: httpx.Response) -> None:
        """Deterministic mapping of every error shape observed on the certified build.

        ``401``/``403`` → :class:`ChannelAuthError` (bad or missing API key). ``5xx`` and everything
        else reached → :class:`ChannelApiError` carrying the status for the retry engine. The
        provider's message is *not* interpolated into the exception, because an error body is
        attacker-influencable and may echo request material.
        """
        status = response.status_code
        # Status only — no body, no headers. Redaction is structural, not best-effort.
        logger.warning("waha_api_error", extra={"status": status, "path": response.url.path})

        if status in (401, 403):
            raise ChannelAuthError(
                "WAHA rejected the configured API key "
                f"(HTTP {status}); check WAHA_API_KEY for this server.",
                detail=f"http_{status}",
            )
        if status >= 500:
            raise ChannelApiError(
                f"WAHA server error (HTTP {status})",
                code=status,
                http_status=status,
            )
        raise ChannelApiError(
            f"WAHA returned HTTP {status}",
            code=status,
            http_status=status,
        )

    # --- The two reads QR-01 needs ------------------------------------------
    async def server_version(self) -> WahaServerInfo:
        """``GET /api/server/version`` — the build banner used by the engine/version guard."""
        body = await self._get("/api/server/version")
        version = body.get("version")
        engine = body.get("engine")
        if not isinstance(version, str) or not isinstance(engine, str):
            raise ChannelApiError(
                "WAHA version response is missing 'version' or 'engine'",
            )
        tier = body.get("tier")
        platform = body.get("platform")
        return WahaServerInfo(
            version=version,
            engine=engine,
            tier=tier if isinstance(tier, str) else None,
            platform=platform if isinstance(platform, str) else None,
        )

    async def server_health(self) -> WahaServerHealth:
        """``GET /health`` — the server's own probe. Not a WhatsApp session check."""
        body = await self._get("/health")
        status = body.get("status")
        status_text = status if isinstance(status, str) else "unknown"
        failing = body.get("error")
        detail = None
        if isinstance(failing, dict) and failing:
            # Component *names* only; component payloads may contain paths and are not echoed.
            detail = "unhealthy components: " + ", ".join(sorted(failing))
        return WahaServerHealth(
            healthy=status_text == "ok", status=status_text, detail=detail
        )

    # --- Session lifecycle read (QR-02) -------------------------------------
    async def session_status(self, name: str) -> WahaSessionSnapshot:
        """``GET /api/sessions/{name}`` — one session's lifecycle status.

        A **read**. QR-02 deliberately adds no create/start/stop/restart/logout call: observing a
        session is what the platform needs to map provider status onto its own lifecycle, and
        mutating one belongs to the pairing and runtime milestones (QR-03/QR-06).
        """
        session = validate_session_name(name)
        body = await self._get(f"/api/sessions/{session}")
        return WahaSessionSnapshot.from_payload(body)

    # --- Pairing (QR-03) -----------------------------------------------------
    async def create_session(self, name: str) -> WahaSessionSnapshot:
        """``POST /api/sessions`` — create and start a session with the certified configuration.

        The only write QR-03 adds. Stop, restart and logout are QR-06 and are intentionally absent,
        so this client still cannot tear a paired session down.

        The store configuration comes from :func:`build_session_config` rather than being written
        inline: certification proved a snake_case ``full_sync`` is accepted and then silently
        ignored, which would leave a session that looks healthy with no history.
        """
        session = validate_session_name(name)
        payload = {"name": session, "start": True, "config": build_session_config()}
        body = await self._post("/api/sessions", payload)
        return WahaSessionSnapshot.from_payload(body)

    async def qr_challenge(self, name: str) -> WahaQrChallenge:
        """``GET /api/{session}/auth/qr`` — the transient QR image for a session awaiting a scan.

        Returns raw image bytes, so it bypasses :meth:`_decode` (which requires JSON). The provider
        answers ``422`` when the session is not awaiting a scan — already paired, still booting or
        failed — and that is surfaced as a normal :class:`ChannelApiError` rather than being
        smoothed over, because "no QR right now" is a real state the caller must handle.

        The result is never logged or persisted; see :class:`WahaQrChallenge`.
        """
        session = validate_session_name(name)
        content, content_type = await self._get_bytes(f"/api/{session}/auth/qr?format=image")
        return WahaQrChallenge(session=session, mimetype=content_type, data=content)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Authenticated JSON POST returning a decoded object, or a channel-neutral error."""
        self._credentials.require()
        request = httpx.Request(
            "POST",
            self.url(path),
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
        )
        try:
            response = await self._client().send(request)
        except httpx.TimeoutException as exc:
            raise ChannelTransportError(
                f"WAHA request timed out after {self._timeout}s: {request.url.path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChannelTransportError(f"WAHA server is unavailable: {request.url.path}") from exc
        return self._decode(response)

    async def _get_bytes(self, path: str) -> tuple[bytes, str]:
        """Authenticated GET returning raw bytes and content type, for non-JSON provider media."""
        self._credentials.require()
        request = httpx.Request("GET", self.url(path), headers=self._headers())
        try:
            response = await self._client().send(request)
        except httpx.TimeoutException as exc:
            raise ChannelTransportError(
                f"WAHA request timed out after {self._timeout}s: {request.url.path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChannelTransportError(f"WAHA server is unavailable: {request.url.path}") from exc
        if response.status_code >= 400:
            self._raise(response)
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            raise ChannelApiError(
                f"WAHA returned an unexpected QR content type ({content_type or 'none'})",
                http_status=response.status_code,
            )
        return response.content, content_type

    # --- Send / reconcile (QR-05) --------------------------------------------
    async def send_text(self, *, chat_id: str, text: str) -> dict[str, Any]:
        """``POST /api/sendText`` through the configured session.

        A transport failure here is **ambiguous**, not a clean failure: the request may have reached
        WhatsApp before the connection broke. It is raised as :class:`WahaSendIndeterminate` so no
        caller can treat it as retry-safe.
        """
        session = self._credentials.require_session()
        payload = {"session": session, "chatId": chat_id, "text": text}
        try:
            return await self._post("/api/sendText", payload)
        except ChannelTransportError as exc:
            raise WahaSendIndeterminate(
                "WAHA send outcome is unknown: the transport failed after the request was issued. "
                "Reconcile before any resend — the message may already have been delivered."
            ) from exc

    async def message_exists(self, *, chat_id: str, canonical_id: str) -> bool:
        """Whether ``canonical_id`` is present in this session's copy of ``chat_id``.

        The reconcile-before-resend primitive, and deliberately **endpoint-scoped**: the lookup runs
        inside one session's own chat, so it can never confirm or advance a message belonging to a
        different endpoint. There is no global provider-message search.
        """
        session = self._credentials.require_session()
        path = (
            f"/api/{session}/chats/{quote(chat_id, safe='')}/messages"
            "?limit=50&downloadMedia=false"
        )
        body = await self._get_list(path)
        for entry in body:
            if not isinstance(entry, dict):
                continue
            if canonical_message_id(entry.get("id")) == canonical_id:
                return True
        return False

    async def _get_list(self, path: str) -> list[Any]:
        """Authenticated GET returning a JSON array (the chat-messages shape)."""
        self._credentials.require()
        request = httpx.Request("GET", self.url(path), headers=self._headers())
        try:
            response = await self._client().send(request)
        except httpx.TimeoutException as exc:
            raise ChannelTransportError(
                f"WAHA request timed out after {self._timeout}s: {request.url.path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChannelTransportError(f"WAHA server is unavailable: {request.url.path}") from exc
        if response.status_code >= 400:
            self._raise(response)
        try:
            body = response.json()
        except ValueError as exc:
            raise ChannelApiError("WAHA returned a malformed (non-JSON) response") from exc
        if not isinstance(body, list):
            raise ChannelApiError("WAHA returned an unexpected JSON shape; expected an array")
        return body

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
