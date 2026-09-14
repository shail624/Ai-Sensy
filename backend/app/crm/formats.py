"""Import/export file formats (FR-CON-04 ``.xlsx`` import; CSV/Excel/JSON/PDF export).

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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, time
from typing import Any, Protocol

from openpyxl import Workbook, load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.crm.csv_io import (
    EXPORT_COLUMNS,
    export_header,
    export_rows,
    neutralize_formula,
)

#: Formats an import may be uploaded in (FR-CON-03/04).
IMPORT_FORMATS = ("csv", "xlsx")
#: Formats an export may be generated in (FR-CON-15).
EXPORT_FORMATS = ("csv", "xlsx", "json", "pdf")

CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "pdf": "application/pdf",
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
    if isinstance(value, date | time):
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


class PdfExportWriter:
    """Compact, paginated analytics table rendered with PDF's built-in Helvetica family.

    PDF is intentionally report-only at the service boundary. Analytics period labels, metric
    names and numeric values are compatible with the built-in font, so the production image needs
    no external font asset and the artifact remains deterministic and portable.
    """

    _PAGE_SIZE = landscape(A4)
    _MARGIN = 34.0
    _TITLE_Y = _PAGE_SIZE[1] - 42.0
    _TABLE_TOP = _PAGE_SIZE[1] - 76.0
    _ROW_HEIGHT = 18.0
    _FOOTER_Y = 22.0
    _BODY_FONT_SIZE = 7.0
    _HEADER_FONT_SIZE = 7.0

    def __init__(
        self,
        columns: Sequence[str] = EXPORT_COLUMNS,
        *,
        title: str = "Analytics report",
    ) -> None:
        self._columns = tuple(columns)
        self._title = title
        self._buffer = io.BytesIO()
        self._canvas = canvas.Canvas(
            self._buffer,
            pagesize=self._PAGE_SIZE,
            pageCompression=1,
            invariant=1,
        )
        self._canvas.setTitle(title)
        self._page_number = 0
        self._row_on_page = 0
        self._has_rows = False
        self._finished = False
        self._widths = self._column_widths()
        self._begin_page()

    @staticmethod
    def _label(column: str) -> str:
        if column.endswith("_micros"):
            base = column.removesuffix("_micros").replace("_", " ").title()
            return f"{base} (micros)"
        return column.replace("_", " ").title()

    @staticmethod
    def _value(value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:,.2f}".rstrip("0").rstrip(".")
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _column_widths(self) -> tuple[float, ...]:
        available = self._PAGE_SIZE[0] - (2 * self._MARGIN)
        weights = [max(9, min(24, len(self._label(column)))) for column in self._columns]
        if self._columns and self._columns[0] == "period":
            weights[0] = max(weights[0], 15)
        total = sum(weights) or 1
        return tuple(available * weight / total for weight in weights)

    @property
    def _rows_per_page(self) -> int:
        available = self._TABLE_TOP - self._FOOTER_Y - self._ROW_HEIGHT
        return max(1, int(available // self._ROW_HEIGHT) - 1)

    @staticmethod
    def _fit(text: str, width: float, font: str, size: float) -> str:
        clean = text.encode("latin-1", errors="replace").decode("latin-1")
        available = max(1.0, width - 8.0)
        if stringWidth(clean, font, size) <= available:
            return clean
        suffix = "..."
        while clean and stringWidth(clean + suffix, font, size) > available:
            clean = clean[:-1]
        return clean + suffix if clean else suffix

    def _begin_page(self) -> None:
        self._page_number += 1
        self._row_on_page = 0
        pdf = self._canvas
        page_width, _ = self._PAGE_SIZE

        pdf.setFillColor(colors.HexColor("#182230"))
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(self._MARGIN, self._TITLE_Y, self._fit(self._title, 560, "Helvetica-Bold", 15))
        pdf.setFillColor(colors.HexColor("#667085"))
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(page_width - self._MARGIN, self._TITLE_Y + 1, f"Page {self._page_number}")

        x = self._MARGIN
        header_bottom = self._TABLE_TOP - self._ROW_HEIGHT
        pdf.setFillColor(colors.HexColor("#EEF2F6"))
        pdf.rect(
            self._MARGIN,
            header_bottom,
            page_width - (2 * self._MARGIN),
            self._ROW_HEIGHT,
            stroke=0,
            fill=1,
        )
        pdf.setStrokeColor(colors.HexColor("#D0D5DD"))
        pdf.setLineWidth(0.5)
        for column, width in zip(self._columns, self._widths, strict=True):
            pdf.setFillColor(colors.HexColor("#344054"))
            pdf.setFont("Helvetica-Bold", self._HEADER_FONT_SIZE)
            pdf.drawString(
                x + 4,
                header_bottom + 5.5,
                self._fit(self._label(column), width, "Helvetica-Bold", self._HEADER_FONT_SIZE),
            )
            pdf.line(x, header_bottom, x, self._TABLE_TOP)
            x += width
        pdf.line(x, header_bottom, x, self._TABLE_TOP)
        pdf.line(self._MARGIN, self._TABLE_TOP, x, self._TABLE_TOP)
        pdf.line(self._MARGIN, header_bottom, x, header_bottom)

        pdf.setFillColor(colors.HexColor("#667085"))
        pdf.setFont("Helvetica", 7)
        pdf.drawString(self._MARGIN, self._FOOTER_Y, "Generated by the Vi Reactivation Operations Platform")

    def _draw_row(self, row: dict[str, Any]) -> None:
        if self._row_on_page >= self._rows_per_page:
            self._canvas.showPage()
            self._begin_page()

        row_top = self._TABLE_TOP - self._ROW_HEIGHT * (self._row_on_page + 1)
        row_bottom = row_top - self._ROW_HEIGHT
        if self._row_on_page % 2:
            self._canvas.setFillColor(colors.HexColor("#F9FAFB"))
            self._canvas.rect(
                self._MARGIN,
                row_bottom,
                self._PAGE_SIZE[0] - (2 * self._MARGIN),
                self._ROW_HEIGHT,
                stroke=0,
                fill=1,
            )

        x = self._MARGIN
        self._canvas.setStrokeColor(colors.HexColor("#E4E7EC"))
        self._canvas.setFillColor(colors.HexColor("#344054"))
        self._canvas.setFont("Helvetica", self._BODY_FONT_SIZE)
        for column, width in zip(self._columns, self._widths, strict=True):
            text = self._fit(
                self._value(row.get(column)), width, "Helvetica", self._BODY_FONT_SIZE
            )
            self._canvas.drawString(x + 4, row_bottom + 5.5, text)
            self._canvas.line(x, row_bottom, x, row_top)
            x += width
        self._canvas.line(x, row_bottom, x, row_top)
        self._canvas.line(self._MARGIN, row_bottom, x, row_bottom)
        self._row_on_page += 1

    def add(self, rows: list[dict[str, Any]]) -> None:
        if self._finished:
            raise RuntimeError("Cannot add rows after the PDF is finished.")
        for row in rows:
            self._has_rows = True
            self._draw_row(row)

    def finish(self) -> bytes:
        if self._finished:
            return self._buffer.getvalue()
        if not self._has_rows:
            self._canvas.setFillColor(colors.HexColor("#667085"))
            self._canvas.setFont("Helvetica", 9)
            self._canvas.drawString(
                self._MARGIN + 4,
                self._TABLE_TOP - (2 * self._ROW_HEIGHT) + 5.5,
                "No data matched the selected report range.",
            )
        self._canvas.save()
        self._finished = True
        return self._buffer.getvalue()


_WRITERS: dict[str, Callable[[Sequence[str]], ExportWriter]] = {
    "csv": CsvExportWriter,
    "xlsx": XlsxExportWriter,
    "json": JsonExportWriter,
}


def export_writer(
    file_format: str,
    columns: Sequence[str] = EXPORT_COLUMNS,
    *,
    title: str | None = None,
) -> ExportWriter:
    """The writer for a validated export format (the service rejects unknown ones with 422)."""
    if file_format == "pdf":
        return PdfExportWriter(columns, title=title or "Analytics report")
    return _WRITERS[file_format](columns)
