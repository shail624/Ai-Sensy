"""Meta Cloud API transport (Doc 01 CMP-01 — official API, direct to Meta, no reseller).

Deliberately dumb: it authenticates, calls the Graph API, and turns every failure into a
channel-neutral exception. It holds **no business logic and no domain knowledge** — payload shapes
belong to the adapter, retry/backoff to the queue engine (Doc 06 §6), and pacing to the rate gate
(§5). Keeping the transport this thin is what lets it be tested without a network and reused by the
adapter, media, template and webhook code that lands in later steps.

Secrets: the token comes from the environment (Doc 01 §5.4) and is sent as a bearer header. It is
never logged, never placed in a URL, and never included in an exception message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.channels.errors import ChannelAuthError, ChannelConfigError, ChannelTransportError
from app.channels.meta.errors import MetaApiError
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MetaCredentials:
    """What the client needs to talk to Meta.

    Passed in explicitly (rather than read from settings inside the client) so that when
    ``whatsapp_business_accounts`` exists, a per-WABA token loads from the database and reaches the
    client the same way — no change here.
    """

    access_token: str
    phone_number_id: str = ""
    waba_id: str = ""
    api_version: str = ""
    base_url: str = ""
    #: Inbound-only secrets (Doc 04 §23). App-level rather than per-WABA — one Meta app receives
    #: every WABA's webhooks — so unlike ``access_token`` they come from the environment and an
    #: adapter built with no credentials at all can still verify a delivery.
    app_secret: str = ""
    verify_token: str = ""

    @classmethod
    def from_settings(cls) -> MetaCredentials:
        """Process-wide defaults from the environment."""
        return cls(
            access_token=settings.meta_access_token,
            phone_number_id=settings.meta_phone_number_id,
            waba_id=settings.meta_waba_id,
            api_version=settings.meta_api_version,
            base_url=settings.meta_api_base_url,
            app_secret=settings.meta_app_secret,
            verify_token=settings.meta_webhook_verify_token,
        )

    @property
    def version(self) -> str:
        return self.api_version or settings.meta_api_version

    @property
    def root(self) -> str:
        return (self.base_url or settings.meta_api_base_url).rstrip("/")

    def require_token(self) -> None:
        if not self.access_token:
            raise ChannelConfigError(
                "Meta access token is not configured; set META_ACCESS_TOKEN."
            )

    def require_phone_number(self) -> str:
        if not self.phone_number_id:
            raise ChannelConfigError(
                "Meta phone number id is not configured; set META_PHONE_NUMBER_ID."
            )
        return self.phone_number_id


class MetaCloudClient:
    """Thin async Graph API client.

    ``http`` is injectable so tests drive it with an ``httpx.MockTransport`` and never touch the
    network (Doc 10 §8).
    """

    def __init__(
        self,
        credentials: MetaCredentials | None = None,
        *,
        http: httpx.AsyncClient | None = None,
        timeout: float | None = None,
    ) -> None:
        self.credentials = credentials or MetaCredentials.from_settings()
        self._timeout = timeout if timeout is not None else settings.meta_timeout_seconds
        self._http = http
        self._owns_http = http is None

    # --- Transport -----------------------------------------------------------
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self._http

    def _headers(self) -> dict[str, str]:
        self.credentials.require_token()
        return {"Authorization": f"Bearer {self.credentials.access_token}"}

    def url(self, path: str) -> str:
        """Absolute Graph URL for a version-relative ``path`` (e.g. ``"123/messages"``)."""
        return f"{self.credentials.root}/{self.credentials.version}/{path.lstrip('/')}"

    async def _send(self, request: httpx.Request) -> httpx.Response:
        try:
            return await self._client().send(request)
        except httpx.TimeoutException as exc:
            # Network-shaped → transient; the queue engine decides the backoff (Doc 06 §6.2).
            raise ChannelTransportError(f"Meta request timed out: {request.url.path}") from exc
        except httpx.HTTPError as exc:
            raise ChannelTransportError(f"Meta request failed: {request.url.path}") from exc

    def _build(self, method: str, url: str, **kwargs: Any) -> httpx.Request:
        return self._client().build_request(
            method, url, headers=self._headers(), timeout=self._timeout, **kwargs
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the Graph API and return the decoded object, or raise a channel error."""
        request = self._build(
            method, self.url(path), json=json, params=params, files=files, data=data
        )
        response = await self._send(request)
        return self._decode(response)

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("POST", path, json=json, files=files, data=data)

    async def download(self, url: str) -> httpx.Response:
        """Fetch a binary from a Meta-issued URL (media download is a two-step flow).

        The URL is Meta's own and still requires the bearer token, so it goes through this client
        rather than a bare ``httpx`` call.
        """
        response = await self._send(self._build("GET", url))
        if response.status_code >= 400:
            self._raise(response)
        return response

    # --- Error translation ---------------------------------------------------
    def _decode(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            self._raise(response)
        if not response.content:
            return {}
        try:
            body = response.json()
        except ValueError as exc:
            raise MetaApiError(
                "Meta returned a non-JSON response",
                http_status=response.status_code,
            ) from exc
        return body if isinstance(body, dict) else {"data": body}

    def _raise(self, response: httpx.Response) -> None:
        """Translate a Graph error envelope into the channel's own exception type."""
        payload: dict[str, Any] = {}
        try:
            decoded = response.json()
            if isinstance(decoded, dict):
                payload = decoded.get("error") or {}
        except ValueError:
            payload = {}

        message = payload.get("message") or f"Meta returned HTTP {response.status_code}"
        code = payload.get("code")
        logger.warning(
            "meta_api_error",
            extra={
                "status": response.status_code,
                "code": code,
                "subcode": payload.get("error_subcode"),
                "fbtrace_id": payload.get("fbtrace_id"),
            },
        )
        if response.status_code in (401, 403):
            raise ChannelAuthError(message, detail=payload.get("type"))
        raise MetaApiError(
            message,
            code=code,
            subcode=payload.get("error_subcode"),
            http_status=response.status_code,
            fbtrace_id=payload.get("fbtrace_id"),
            error_type=payload.get("type"),
        )

    async def close(self) -> None:
        """Close the transport if this client created it."""
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None
