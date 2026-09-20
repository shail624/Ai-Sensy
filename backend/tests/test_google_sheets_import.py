"""Google Sheet contact import (scope §21, "Integrations — Limited").

The sheet is fetched and handed to the existing import pipeline as a stored CSV upload, so these
tests cover the part that is new: the service-account exchange, the shape of what comes back from
Google, and the error messages an operator reads when Google says no. The mapping, dedup, audit and
per-row error report are the import pipeline's own and are already covered by its tests — that
reuse is the design, not an omission.

A fake transport is used rather than mocking the module out, so the real request building, real
RS256 signing and real error mapping all execute. Only the network is replaced.
"""

from __future__ import annotations

import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from app.integrations.google_sheets import (
    GoogleSheetsClient,
    GoogleSheetsError,
    GoogleSheetsNotConfigured,
    ServiceAccount,
)

PASSWORD = "Sup3r-Secret-Pass1"
STAGE_URL = "/api/v1/contacts/import/google-sheet"


@pytest.fixture(scope="module")
def service_account_json() -> str:
    """A real RSA key, so the module's real RS256 signing runs rather than being stubbed."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return json.dumps({"client_email": "vi-sheets@vi-project.iam.gserviceaccount.com",
                       "private_key": pem, "type": "service_account"})


def transport_for(
    *, values: object = None, sheet_status: int = 200, token_status: int = 200
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            if token_status != 200:
                return httpx.Response(token_status, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "ya29.fake", "expires_in": 3600})
        if sheet_status != 200:
            return httpx.Response(sheet_status, json={"error": {"message": "nope"}})
        return httpx.Response(200, json={"values": values if values is not None else []})

    return httpx.MockTransport(handler)


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- The reader ---------------------------------------------------------------------------------
async def test_a_tab_is_returned_as_rows_of_strings(monkeypatch, service_account_json) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(
        transport=transport_for(values=[["Phone", "Name"], ["9876543210", "Asha"]])
    )

    rows = await client.fetch_rows("sheet-id", "Leads")

    assert rows == [["Phone", "Name"], ["9876543210", "Asha"]]


async def test_short_rows_are_padded_to_the_widest(monkeypatch, service_account_json) -> None:
    """Google omits trailing empty cells entirely instead of sending blanks.

    Left ragged, a CSV row that happened to end early would have fewer columns than its header, and
    every field mapped to the right of the gap would silently read from the wrong column.
    """
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(
        transport=transport_for(values=[["Phone", "Name", "Status"], ["9876543210"]])
    )

    rows = await client.fetch_rows("sheet-id", "Leads")

    assert rows == [["Phone", "Name", "Status"], ["9876543210", "", ""]]


async def test_export_creates_a_new_tab_and_writes_raw_rows(
    monkeypatch, service_account_json
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    seen: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, str(request.url), body))
        if request.method == "GET":
            return httpx.Response(200, json={"sheets": []})
        return httpx.Response(200, json={})

    sheets = GoogleSheetsClient(transport=httpx.MockTransport(handler))
    await sheets.ensure_export_tab("sheet-id", "Contacts 2026")
    await sheets.write_rows("sheet-id", "Contacts 2026", 1, [["name"], ["=unsafe"]])

    assert seen[0][0] == "GET"
    assert seen[1][0] == "POST" and seen[1][2] == {
        "requests": [{"addSheet": {"properties": {"title": "Contacts 2026"}}}]
    }
    assert seen[2][0] == "PUT"
    assert "valueInputOption=RAW" in seen[2][1]
    assert seen[2][2] == {"majorDimension": "ROWS", "values": [["name"], ["=unsafe"]]}


async def test_a_sheet_not_shared_with_the_robot_names_the_address_to_share_with(
    monkeypatch, service_account_json
) -> None:
    """The one error an operator will actually hit, so the message has to be the fix."""
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(transport=transport_for(sheet_status=403))

    with pytest.raises(GoogleSheetsError) as raised:
        await client.fetch_rows("sheet-id", "Leads")

    assert "vi-sheets@vi-project.iam.gserviceaccount.com" in str(raised.value)
    assert "Share" in str(raised.value)


async def test_an_unknown_sheet_says_where_the_id_comes_from(
    monkeypatch, service_account_json
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(transport=transport_for(sheet_status=404))

    with pytest.raises(GoogleSheetsError) as raised:
        await client.fetch_rows("wrong-id", "Leads")

    assert "/d/" in str(raised.value)


async def test_a_wrong_tab_name_says_so(monkeypatch, service_account_json) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(transport=transport_for(sheet_status=400))

    with pytest.raises(GoogleSheetsError) as raised:
        await client.fetch_rows("sheet-id", "Leeds")

    assert "Leeds" in str(raised.value)


async def test_rejected_credentials_do_not_echo_the_key(
    monkeypatch, service_account_json
) -> None:
    """A credential failure must never quote the credential into a log or an API response."""
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    client = GoogleSheetsClient(transport=transport_for(token_status=400))

    with pytest.raises(GoogleSheetsError) as raised:
        await client.fetch_rows("sheet-id", "Leads")

    assert "PRIVATE KEY" not in str(raised.value)
    assert "Sheets API" in str(raised.value)


async def test_an_unconfigured_integration_is_off_not_broken(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", "")

    with pytest.raises(GoogleSheetsNotConfigured) as raised:
        ServiceAccount.from_settings()

    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in str(raised.value)


async def test_a_malformed_key_does_not_quote_itself_back(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", "-----BEGIN PRIVATE KEY-----xyz")

    with pytest.raises(GoogleSheetsError) as raised:
        ServiceAccount.from_settings()

    assert "xyz" not in str(raised.value)
    assert "valid JSON" in str(raised.value)


# --- The endpoint -------------------------------------------------------------------------------
async def test_staging_a_tab_returns_an_upload_the_import_flow_accepts(
    client, make_user, monkeypatch, service_account_json
) -> None:
    """The whole point: a sheet becomes an ordinary upload, not a parallel import path."""
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    from app.services import google_sheet_import_service as module

    original = module.GoogleSheetsClient
    monkeypatch.setattr(
        module,
        "GoogleSheetsClient",
        lambda **kwargs: original(
            transport=transport_for(values=[["Phone", "Name"], ["+919876543210", "Asha"]])
        ),
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "ops@vi.co")

    staged = await client.post(
        STAGE_URL, headers=headers, json={"spreadsheet_id": "sheet-id", "tab": "Leads"}
    )

    assert staged.status_code == 200
    body = staged.json()
    assert body["rows"] == 2 and body["columns"] == 2

    # The staged upload is readable by the existing inspect endpoint, unchanged.
    inspected = await client.post(
        "/api/v1/contacts/import/inspect",
        headers=headers,
        json={"upload_id": body["upload_id"], "format": "csv"},
    )
    assert inspected.status_code == 200
    assert inspected.json()["headers"] == ["Phone", "Name"]


async def test_multiple_tabs_with_the_same_header_become_one_staged_upload(
    client, make_user, monkeypatch, service_account_json
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    from app.services import google_sheet_import_service as module

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        name = request.url.path.rsplit("/", 1)[-1]
        person = "Asha" if name == "Leads" else "Ravi"
        return httpx.Response(200, json={"values": [["Phone", "Name"], ["+919876543210", person]]})

    original = module.GoogleSheetsClient
    monkeypatch.setattr(
        module,
        "GoogleSheetsClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler)),
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "ops@vi.co")

    staged = await client.post(
        STAGE_URL,
        headers=headers,
        json={"spreadsheet_id": "sheet-id", "tabs": ["Leads", "Renewals"]},
    )

    assert staged.status_code == 200, staged.text
    assert staged.json()["tabs"] == ["Leads", "Renewals"]
    assert staged.json()["rows"] == 3
    inspected = await client.post(
        "/api/v1/contacts/import/inspect",
        headers=headers,
        json={"upload_id": staged.json()["upload_id"], "format": "csv"},
    )
    assert inspected.json()["headers"] == ["Phone", "Name"]
    assert inspected.json()["estimated_rows"] == 2


async def test_multiple_tabs_must_share_the_same_header(
    client, make_user, monkeypatch, service_account_json
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    from app.services import google_sheet_import_service as module

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        name = request.url.path.rsplit("/", 1)[-1]
        header = ["Phone", "Name"] if name == "Leads" else ["Mobile", "Customer"]
        return httpx.Response(200, json={"values": [header, ["+919876543210", "Asha"]]})

    original = module.GoogleSheetsClient
    monkeypatch.setattr(
        module,
        "GoogleSheetsClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler)),
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)
    refused = await client.post(
        STAGE_URL,
        headers=await _headers(client, "ops@vi.co"),
        json={"spreadsheet_id": "sheet-id", "tabs": ["Leads", "Renewals"]},
    )
    assert refused.status_code == 422
    assert "same header row" in refused.text


async def test_an_empty_tab_is_refused_rather_than_staged(
    client, make_user, monkeypatch, service_account_json
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    from app.services import google_sheet_import_service as module

    original = module.GoogleSheetsClient
    monkeypatch.setattr(
        module, "GoogleSheetsClient", lambda **kwargs: original(transport=transport_for(values=[]))
    )
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)

    refused = await client.post(
        STAGE_URL,
        headers=await _headers(client, "ops@vi.co"),
        json={"spreadsheet_id": "sheet-id", "tab": "Leads"},
    )

    assert refused.status_code == 422
    assert "no rows" in refused.text


async def test_staging_requires_the_import_permission(client, make_user) -> None:
    await make_user(email="nobody@vi.co", password=PASSWORD)

    denied = await client.post(
        STAGE_URL,
        headers=await _headers(client, "nobody@vi.co"),
        json={"spreadsheet_id": "sheet-id", "tab": "Leads"},
    )

    assert denied.status_code == 403


# --- Regressions found by reading the shipped diff back ------------------------------------------
def recording_transport(seen: list[str], *, body: object = None, raw: str | None = None):
    """A transport that remembers the sheet URL it was asked for."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        seen.append(str(request.url))
        if raw is not None:
            return httpx.Response(200, text=raw, headers={"Content-Type": "text/html"})
        return httpx.Response(200, json={"values": body if body is not None else [["a"]]})

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    ("tab", "encoded"),
    [
        ("Leads", "Leads"),
        ("My Tab", "My%20Tab"),
        # An ordinary name on a telecom sheet, and the one that used to address a different
        # endpoint entirely: the slash survived into the URL as a path separator.
        ("Prepaid/Postpaid", "Prepaid%2FPostpaid"),
        # These two used to raise httpx.InvalidURL -- not a GoogleSheetsError, so it escaped this
        # module's error mapping and reached the operator as a 500.
        ("Churn?90d", "Churn%3F90d"),
        ("Notes#1", "Notes%231"),
    ],
)
async def test_a_tab_name_is_one_encoded_url_segment(
    monkeypatch, service_account_json, tab, encoded
) -> None:
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    seen: list[str] = []

    rows = await GoogleSheetsClient(transport=recording_transport(seen)).fetch_rows("sheet-id", tab)

    assert rows == [["a"]]
    assert seen == [f"https://sheets.googleapis.com/v4/spreadsheets/sheet-id/values/{encoded}"]


async def test_a_reply_that_is_not_json_is_an_operator_message_not_a_traceback(
    monkeypatch, service_account_json
) -> None:
    """A proxy or captive portal answers 200 with HTML, and json() raises a decode error."""
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    seen: list[str] = []
    client = GoogleSheetsClient(transport=recording_transport(seen, raw="<html>blocked</html>"))

    with pytest.raises(GoogleSheetsError) as raised:
        await client.fetch_rows("sheet-id", "Leads")

    assert "proxy" in str(raised.value)


async def test_an_unconfigured_key_is_an_instruction_not_a_server_error(
    client, make_user, monkeypatch
) -> None:
    """The path every new installation takes first.

    The service built its client above the try block, so the "here is how to configure it" message
    was raised past its own handler and arrived as a 500 with nothing for the operator to act on.
    """
    monkeypatch.setattr(settings, "google_service_account_json", "")
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)

    refused = await client.post(
        STAGE_URL,
        headers=await _headers(client, "ops@vi.co"),
        json={"spreadsheet_id": "sheet-id", "tab": "Leads"},
    )

    assert refused.status_code == 422
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in refused.text


async def test_a_mangled_sheet_id_names_the_field_rather_than_asking_google(
    client, make_user, monkeypatch, service_account_json
) -> None:
    """A half-pasted URL is a clipboard problem, and saying so beats relaying Google's 404."""
    monkeypatch.setattr(settings, "google_service_account_json", service_account_json)
    await make_user(email="ops@vi.co", password=PASSWORD, is_superuser=True)

    refused = await client.post(
        STAGE_URL,
        headers=await _headers(client, "ops@vi.co"),
        json={"spreadsheet_id": "spreadsheets/d/1lLjGMP1rQQ", "tab": "Leads"},
    )

    assert refused.status_code == 422
    assert "spreadsheet_id" in refused.text
