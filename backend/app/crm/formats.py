"""Import/export file formats (FR-CON-04 ``.xlsx`` import; FR-CON-15 CSV/Excel/JSON export).

Pure helpers, no DB and no I/O — the format layer only. Everything about *what* a contact row
contains stays in :mod:`app.crm.csv_io` (``EXPORT_COLUMNS``, the CSV renderers, ``map_and_validate``);
this module only adds the other two encodings and the dispatch, so a row means the same thing in
every format and CSV behaviour is reused rather than reimplemented.

Reading an ``.xlsx`` yields the same ``list[dict[str, str]]`` shape as :func:`csv_io.read_csv`, so
the import pipeline's mapping, validation and error report work on it unchanged.
"""

from __future__ import annotations

import io
import json
from collections.abc import Sequence
from typing import Any, Protocol

from openpyxl import Workbook, load_workbook

from app.crm.csv_io import (
    EXPORT_COLUMNS,
    export_header,
    export_rows,
    neutralize_formula,
)

#: Formats an import may be uploaded in (FR-CON-03/04).
IMPORT_FORMATS = ("csv", "xlsx")
#: Formats an export may be generated in (FR-CON-15).
EXPORT_FORMATS = ("csv", "xlsx", "json")

CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
}


def _cell(value: Any) -> str:
    """Render a spreadsheet cell as the trimmed text the CSV path would have produced."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        # openpyxl types bare numbers as float; "+14155550001" must not become "1.4155550001e+10".
        return str(int(value))
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value).strip()


def read_xlsx(data: bytes) -> list[dict[str, str]]:
    """Parse the first worksheet into header-keyed rows (FR-CON-04).

    Read-only mode streams the sheet rather than building a full object graph. Row 1 is the
    header, matching the CSV contract, so the operator's column mapping is identical either way.
    """
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)
        try:
            raw_header = next(rows)
        except StopIteration:
            return []
        header = [_cell(name) for name in raw_header]
        parsed: list[dict[str, str]] = []
        for row in rows:
            if all(cell is None for cell in row):
                continue  # trailing blank rows are an artefact of the file, not data
            parsed.append(
                {
                    name: _cell(value)
                    for name, value in zip(header, row, strict=False)
                    if name
                }
            )
        return parsed
    finally:
        workbook.close()


class ExportWriter(Protocol):
    """Accumulates rendered batches and returns the finished artifact."""

    def add(self, rows: list[dict[str, Any]]) -> None: ...

    def finish(self) -> bytes: ...


class CsvExportWriter:
    """CSV export — delegates to the existing renderers so contact output is unchanged."""

    def __init__(self, columns: Sequence[str] = EXPORT_COLUMNS) -> None:
        self._columns = tuple(columns)
        self._chunks: list[bytes] = [export_header(self._columns)]

    def add(self, rows: list[dict[str, Any]]) -> None:
        self._chunks.append(export_rows(rows, self._columns))

    def finish(self) -> bytes:
        return b"".join(self._chunks)


class XlsxExportWriter:
    """Excel export (FR-CON-15). Write-only mode appends rows without holding a cell graph."""

    def __init__(self, columns: Sequence[str] = EXPORT_COLUMNS) -> None:
        self._columns = tuple(columns)
        self._workbook = Workbook(write_only=True)
        self._sheet = self._workbook.create_sheet("export")
        self._sheet.append(list(self._columns))

    def add(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            # Excel evaluates formulas, so the same neutralisation the CSV path applies is
            # applied here (CWE-1236).
            self._sheet.append(
                [neutralize_formula(row.get(column)) for column in self._columns]
            )

    def finish(self) -> bytes:
        buffer = io.BytesIO()
        self._workbook.save(buffer)
        return buffer.getvalue()


class JsonExportWriter:
    """JSON export (FR-CON-15) — one array of row objects, keyed by the export columns."""

    def __init__(self, columns: Sequence[str] = EXPORT_COLUMNS) -> None:
        self._columns = tuple(columns)
        self._rows: list[dict[str, Any]] = []

    def add(self, rows: list[dict[str, Any]]) -> None:
        # JSON is not evaluated by a spreadsheet, so values are written as-is.
        self._rows.extend(
            {column: row.get(column) for column in self._columns} for row in rows
        )

    def finish(self) -> bytes:
        return json.dumps(self._rows, ensure_ascii=False, default=str).encode("utf-8")


_WRITERS: dict[str, type] = {
    "csv": CsvExportWriter,
    "xlsx": XlsxExportWriter,
    "json": JsonExportWriter,
}


def export_writer(
    file_format: str, columns: Sequence[str] = EXPORT_COLUMNS
) -> ExportWriter:
    """The writer for a validated export format (the service rejects unknown ones with 422)."""
    return _WRITERS[file_format](columns)
