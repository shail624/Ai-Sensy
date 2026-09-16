"""Read a Google Sheet tab with a service account (scope §21, "Integrations — Limited").

Deliberately built on the two libraries already here -- PyJWT for the RS256 assertion and httpx for
the two HTTP calls -- rather than pulling in ``google-api-python-client``. The whole protocol is a
signed JWT exchanged for a bearer token and one ``GET``; a client library for that would be more
code to audit, not less, and every dependency on the ingest side of a customer-data path is one
more thing to keep patched.

**A service account, not an operator's Google login.** A personal account's password change, 2FA
enrolment or departure would silently stop every sync, and the failure would look like an empty
sheet rather than a broken credential. The service account also lets the sheet be shared read-only
with exactly one robot identity, which is auditable from the Google side.

The key never leaves this module's memory: it is not logged, not returned by any endpoint and not
written to the database. What *is* persisted is the sheet's content, as an ordinary contact import.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt

from app.core.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
#: Google rejects an assertion whose lifetime exceeds an hour; a short one limits replay value.
_ASSERTION_LIFETIME_SECONDS = 600


class GoogleSheetsError(Exception):
    """Anything that stopped the sheet being read, phrased for an operator.

    One exception type on purpose: from the caller's side "the credential is wrong", "the sheet is
    not shared with the robot" and "that tab does not exist" are the same kind of event -- the
    import cannot start and the operator must fix something in Google. What differs is the message,
    which is why it carries one written for a human rather than a status code.
    """


class GoogleSheetsNotConfigured(GoogleSheetsError):
    """No service account key is set, so the integration is off rather than broken."""


@dataclass(frozen=True, slots=True)
class ServiceAccount:
    client_email: str
    private_key: str

    @classmethod
    def from_settings(cls) -> ServiceAccount:
        raw = settings.google_service_account_json.strip()
        if not raw:
            raise GoogleSheetsNotConfigured(
                "No Google service account is configured. Set GOOGLE_SERVICE_ACCOUNT_JSON to the "
                "contents of the key file, then share the sheet with that account's email."
            )
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            # Deliberately does not echo the value: it contains a private key.
            raise GoogleSheetsError(
                "The configured Google service account is not valid JSON. Paste the key file's "
                "whole contents, including the surrounding braces."
            ) from exc
        if not isinstance(parsed, dict):
            raise GoogleSheetsError("The Google service account key must be a JSON object.")
        email, key = parsed.get("client_email"), parsed.get("private_key")
        if not isinstance(email, str) or not isinstance(key, str):
            raise GoogleSheetsError(
                "The Google service account key is missing 'client_email' or 'private_key'. "
                "Download a fresh JSON key from the service account's Keys tab."
            )
        return cls(client_email=email, private_key=key)


class GoogleSheetsClient:
    """Fetches one tab's cell values. Read-only by construction and by requested scope."""

    def __init__(
        self,
        *,
        account: ServiceAccount | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # `transport` exists so the tests exercise this module's real request building, signing and
        # error mapping against a fake network rather than mocking the module out entirely.
        self._account = account or ServiceAccount.from_settings()
        self._transport = transport

    def _assertion(self) -> str:
        now = int(time.time())
        try:
            return jwt.encode(
                {
                    "iss": self._account.client_email,
                    "scope": settings.google_sheets_scope,
                    "aud": TOKEN_URL,
                    "iat": now,
                    "exp": now + _ASSERTION_LIFETIME_SECONDS,
                },
                self._account.private_key,
                algorithm="RS256",
            )
        except Exception as exc:  # noqa: BLE001 - any signing failure is one operator message
            raise GoogleSheetsError(
                "The Google service account's private key could not be used to sign a request. "
                "The key file may be truncated; download a fresh one."
            ) from exc

    async def _token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": JWT_BEARER, "assertion": self._assertion()},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            raise GoogleSheetsError(
                "Google refused the service account's credentials. Check that the key is current "
                "and that the Sheets API is enabled for its project."
            )
        token = response.json().get("access_token")
        if not isinstance(token, str):
            raise GoogleSheetsError("Google's token response did not contain an access token.")
        return token

    async def fetch_rows(self, spreadsheet_id: str, tab: str) -> list[list[str]]:
        """Every populated row of one tab, as rows of strings.

        Google returns ragged rows -- trailing empty cells are omitted entirely rather than sent as
        blanks -- so rows are padded to the widest one. A CSV writer would otherwise produce short
        lines and the column an operator mapped would silently shift on rows that happened to end
        early.
        """
        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=settings.google_sheets_timeout_seconds,
            trust_env=False,
        ) as client:
            token = await self._token(client)
            response = await client.get(
                f"{SHEETS_BASE}/{spreadsheet_id}/values/{httpx.URL(path=tab).path.lstrip('/')}",
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code == 403:
            raise GoogleSheetsError(
                f"The sheet is not shared with {self._account.client_email}. Open the sheet, press "
                "Share, and give that address Viewer access."
            )
        if response.status_code == 404:
            raise GoogleSheetsError(
                "No sheet with that id was found. Copy the id out of the sheet's URL, between "
                "'/d/' and the next '/'."
            )
        if response.status_code == 400:
            raise GoogleSheetsError(
                f"Google rejected the request for tab {tab!r}. Check the tab name matches exactly, "
                "including spaces and capitals."
            )
        if response.status_code != 200:
            raise GoogleSheetsError(
                f"Google returned an unexpected {response.status_code} for that sheet."
            )

        values: Any = response.json().get("values", [])
        if not isinstance(values, list):
            raise GoogleSheetsError("Google's response did not contain a grid of values.")
        rows = [[str(cell) for cell in row] for row in values if isinstance(row, list)]
        width = max((len(row) for row in rows), default=0)
        return [row + [""] * (width - len(row)) for row in rows]
