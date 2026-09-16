"""Bring a Google Sheet tab into the existing contact import (scope §21).

This service does one thing: fetch a tab and hand it to the import pipeline as if an operator had
uploaded it. It deliberately does **not** parse, validate, deduplicate, audit or write contacts,
because :class:`~app.services.import_service.ImportService` already does all of that through the
CRM's own :class:`ContactService` -- which is what makes an imported contact indistinguishable from
one created through the API. A second import path would be a second set of rules to keep in step,
and the one that drifted would be the one nobody was watching.

So the sheet becomes a CSV, the CSV becomes an ordinary stored upload, and everything downstream --
column mapping, the dedup strategy, the per-row error report, job progress, the audit trail -- is
the machinery that already exists and is already tested.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.integrations.google_sheets import (
    GoogleSheetsClient,
    GoogleSheetsError,
    GoogleSheetsNotConfigured,
)
from app.models.media import MediaAsset
from app.models.user import User
from app.services.media_service import MediaService
from app.storage.validation import MEDIA_DOCUMENT

#: A sheet wider or longer than this is almost certainly the wrong tab rather than a real import,
#: and the contact importer's own limits would reject it later with a far less useful message.
MAX_ROWS = 50_000


@dataclass(slots=True)
class SheetImportSource:
    asset: MediaAsset
    row_count: int
    column_count: int


class GoogleSheetImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._media = MediaService(session)

    async def stage(
        self,
        *,
        organization_id: int,
        actor: User,
        spreadsheet_id: str,
        tab: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> SheetImportSource:
        """Fetch a tab and store it as an uploaded CSV, ready for the normal import flow.

        Returns the stored asset, whose public id is the ``upload_id`` the existing inspect and
        start endpoints take. Nothing about contacts happens here.
        """
        client = GoogleSheetsClient(transport=transport)
        try:
            rows = await client.fetch_rows(spreadsheet_id, tab)
        except GoogleSheetsNotConfigured as exc:
            raise ValidationError(
                str(exc),
                errors=[{"field": "spreadsheet_id", "code": "not_configured", "message": str(exc)}],
            ) from exc
        except GoogleSheetsError as exc:
            # The message is already written for an operator; passing it through beats replacing it
            # with a generic one that sends them to the logs.
            raise ValidationError(
                str(exc),
                errors=[{"field": "spreadsheet_id", "code": "unreadable", "message": str(exc)}],
            ) from exc

        if not rows:
            raise ValidationError(
                f"Tab {tab!r} has no rows.",
                errors=[{"field": "tab", "code": "empty", "message": "the tab contains no data"}],
            )
        if len(rows) > MAX_ROWS:
            raise ValidationError(
                f"Tab {tab!r} has {len(rows)} rows, more than the {MAX_ROWS} this import accepts.",
                errors=[{"field": "tab", "code": "too_large", "message": f"limit {MAX_ROWS} rows"}],
            )

        buffer = io.StringIO()
        # QUOTE_ALL because a sheet holds free text: an unquoted cell containing a comma would
        # otherwise split into two columns and shift every mapped field to its right.
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerows(rows)

        asset, _ = await self._media.upload(
            organization_id=organization_id,
            actor=actor,
            data=buffer.getvalue().encode("utf-8"),
            media_type=MEDIA_DOCUMENT,
            mime_type="text/csv",
            file_name=f"{tab}.csv",
        )
        return SheetImportSource(
            asset=asset, row_count=len(rows), column_count=len(rows[0]) if rows else 0
        )
