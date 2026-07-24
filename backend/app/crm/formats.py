"""Import/export file formats (FR-CON-04 ``.xlsx`` import; FR-CON-15 CSV/Excel/JSON export).

Pure helpers, no DB and no I/O — the format layer only. Everything about *what* a contact row
contains stays in :mod:`app.crm.csv_io` (``EXPORT_COLUMNS``, the CSV renderers, ``map_and_validate``);
this module only adds the other two encodings and the dispatch, so a row means the same thing in
every format and CSV behaviour is reused rather than reimplemented.

Reading an ``.xlsx`` yields the same ``list[dict[str, str]]`` shape as :func:`csv_io.read_csv`, so
the import pipeline's mapping, validation and error report work on it unchanged.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class FileInspection:
    """What the import wizard needs before it can offer a column mapping (Doc 05 B3.3 step 2).

    Deliberately *not* the file's data: inspection reads the header row, one sample row and
    whatever the container can cheaply tell us about its size. Nothing is imported, nothing is
    written, and no job is created.
    """

    headers: list[str]
    sample_row: list[str]
    sheet_name: str | None
    estimated_rows: int | None
    errors: list[dict[str, str]]


def _header_errors(headers: list[str]) -> list[dict[str, str]]:
    """Problems worth showing the operator before they map anything."""
    errors: list[dict[str, str]] = []
    if not headers:
        errors.append(
            {"field": "headers", "code": "missing", "message": "The file has no header row."}
        )
        return errors
    if any(name == "" for name in headers):
        errors.append(
            {
                "field": "headers",
                "code": "blank",
                "message": "One or more columns have no name and cannot be mapped.",
            }
        )
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in headers:
        if not name:
            continue
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    if duplicates:
        errors.append(
            {
                "field": "headers",
                "code": "duplicate",
                "message": f"Repeated column names: {', '.join(duplicates)}.",
            }
        )
    return errors


def inspect_xlsx(data: bytes) -> FileInspection:
    """Header, one sample row and a row estimate from the first worksheet.

    Uses the same read-only streaming load as :func:`read_xlsx` and the same cell rendering, so the
    headers shown here are by construction the headers the importer will see. It stops after the
    sample row rather than materialising the sheet.

    ``max_row`` comes from the sheet's stored dimension, which a generator may omit or overstate —
    hence *estimated*; the import itself always reports the true count.
    """
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)
        try:
            raw_header = next(rows)
        except StopIteration:
            return FileInspection([], [], sheet.title, None, _header_errors([]))
        headers = [_cell(name) for name in raw_header]
        sample: list[str] = []
        for row in rows:
            if all(cell is None for cell in row):
                continue  # trailing blank rows are an artefact of the file, not data
            sample = [_cell(value) for value in row][: len(headers)]
            break
        total = sheet.max_row
        estimated = max(total - 1, 0) if isinstance(total, int) else None
        return FileInspection(headers, sample, sheet.title, estimated, _header_errors(headers))
    finally:
        workbook.close()


def inspect_csv(data: bytes) -> FileInspection:
    """The same shape for CSV, decoded exactly as the importer decodes it."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    try:
        headers = [str(name).strip() for name in next(reader)]
    except StopIteration:
        return FileInspection([], [], None, None, _header_errors([]))
    sample: list[str] = []
    count = 0
    for row in reader:
        if not any(str(cell).strip() for cell in row):
            continue
        count += 1
        if not sample:
            sample = [str(cell).strip() for cell in row][: len(headers)]
    return FileInspection(headers, sample, None, count, _header_errors(headers))


def inspect(data: bytes, file_format: str) -> FileInspection:
    """Dispatch on the declared format; the caller has already checked it is supported."""
    return inspect_xlsx(data) if file_format == "xlsx" else inspect_csv(data)


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
