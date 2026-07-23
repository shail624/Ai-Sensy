"""CSV parsing, column mapping and per-row validation (FR-CON-03/05, Doc 04 §14.1).

Pure helpers — no DB, no I/O — so the import task can validate a whole file cheaply before
touching the database. A bad row never aborts the import: it is collected with its row number
and reason and rendered into the downloadable error report (FR-CON-05) while the rest proceeds.

Row validation **reuses the CRM's own rules** (`validate_e164`, the opt-in enum) rather than
restating them, so an imported contact is exactly as valid as one created through the API.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.models.contact import OPT_IN_STATUSES
from app.schemas.contact import validate_e164

#: Mapping targets that land on a contact column; anything else must be ``attr.<key>``.
CONTACT_FIELDS = (
    "phone_e164",
    "full_name",
    "first_name",
    "last_name",
    "email",
    "locale",
    "country_code",
    "opt_in_status",
)
ATTR_PREFIX = "attr."


@dataclass(slots=True)
class RowError:
    row_number: int
    error: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedRow:
    row_number: int
    fields: dict[str, Any]
    attributes: dict[str, Any]


@dataclass(slots=True)
class ParseResult:
    rows: list[ParsedRow]
    errors: list[RowError]

    @property
    def total(self) -> int:
        return len(self.rows) + len(self.errors)


def read_csv(data: bytes) -> list[dict[str, str]]:
    """Decode and parse CSV bytes into dict rows (BOM-tolerant)."""
    text = data.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def _validate_row(fields: dict[str, Any]) -> str | None:
    phone = fields.get("phone_e164")
    if not phone:
        return "phone_e164 is required"
    try:
        fields["phone_e164"] = validate_e164(phone)
    except ValueError as exc:
        return str(exc)
    status = fields.get("opt_in_status")
    if status and status not in OPT_IN_STATUSES:
        return f"opt_in_status must be one of {list(OPT_IN_STATUSES)}"
    return None


def map_and_validate(raw_rows: list[dict[str, str]], mapping: dict[str, str]) -> ParseResult:
    """Apply ``mapping`` (source column → target) and validate each row.

    Targets are contact fields or ``attr.<key>`` for custom attributes. Row numbering starts at
    2 because row 1 is the header — the numbers in the error report match what the operator
    sees in their spreadsheet.
    """
    rows: list[ParsedRow] = []
    errors: list[RowError] = []
    for index, raw in enumerate(raw_rows, start=2):
        fields: dict[str, Any] = {}
        attributes: dict[str, Any] = {}
        bad_target: str | None = None
        for column, target in mapping.items():
            value = (raw.get(column) or "").strip()
            if not value:
                continue
            if target.startswith(ATTR_PREFIX):
                attributes[target[len(ATTR_PREFIX) :]] = value
            elif target in CONTACT_FIELDS:
                fields[target] = value
            else:
                bad_target = target
                break
        if bad_target is not None:
            errors.append(RowError(index, f"unknown mapping target {bad_target!r}", raw))
            continue
        problem = _validate_row(fields)
        if problem:
            errors.append(RowError(index, problem, raw))
        else:
            rows.append(ParsedRow(index, fields, attributes))
    return ParseResult(rows=rows, errors=errors)


def error_report_csv(errors: list[RowError]) -> bytes:
    """Render rejected rows as a downloadable CSV report (FR-CON-05)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row_number", "error", "data"])
    for item in errors:
        writer.writerow([item.row_number, item.error, str(item.raw)])
    return buffer.getvalue().encode("utf-8")


def bulk_error_report_csv(errors: list[dict[str, Any]]) -> bytes:
    """Render per-item bulk failures as a downloadable report (Doc 04 §29 ``error_report_url``).

    Distinct from :func:`error_report_csv`: a bulk item is identified by its contact id, not by a
    spreadsheet row number.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["contact_id", "code", "message"])
    for item in errors:
        writer.writerow([item.get("id") or "", item.get("code", ""), item.get("message", "")])
    return buffer.getvalue().encode("utf-8")


#: Columns of the duplicate-scan report (FR-CON-06 ``mode=report``).
DEDUP_REPORT_COLUMNS = ("key", "value", "duplicate_count", "primary_id", "duplicate_ids")


def dedup_report_header() -> bytes:
    """Header of the dedup report, written once before streaming groups."""
    buffer = io.StringIO()
    csv.writer(buffer).writerow(DEDUP_REPORT_COLUMNS)
    return buffer.getvalue().encode("utf-8")


def dedup_report_rows(groups: list[dict[str, Any]]) -> bytes:
    """Render one batch of duplicate groups — called per batch so a large scan streams."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=DEDUP_REPORT_COLUMNS, extrasaction="ignore")
    for group in groups:
        writer.writerow(group)
    return buffer.getvalue().encode("utf-8")


#: Columns written by a contact export, in order (FR-CON-15).
EXPORT_COLUMNS = (
    "phone_e164",
    "wa_id",
    "full_name",
    "first_name",
    "last_name",
    "email",
    "locale",
    "country_code",
    "opt_in_status",
    "source",
    "tags",
    "created_at",
)


#: Characters a spreadsheet treats as the start of a formula (CWE-1236 / OWASP CSV injection).
#: Contact names, emails and tags are attacker-supplied — a WhatsApp profile name or an imported
#: row can carry any of these — so a value beginning with one must not be handed to Excel raw.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


#: A value that is unambiguously a number or phone number — ``+919990000001``, ``-42``,
#: ``(020) 7946-0000``. These begin with ``+``/``-`` but cannot carry a DDE payload, and
#: prefixing them would corrupt every exported phone number and break re-import.
_NUMERIC_LIKE = re.compile(r"^[+-]?[\d\s().\-]+$")


def neutralize_formula(value: Any) -> Any:
    """Prefix a leading formula trigger with ``'`` so spreadsheets read the cell as text.

    Applied to every exported cell, not only contact fields: an analytics dimension label (a
    campaign name, an agent name) is just as user-supplied. Non-strings pass through untouched.

    ``=`` and ``@`` are always neutralised. ``+``/``-`` are neutralised only when the value is not
    numeric-like, so ``+919990000001`` exports unchanged while the classic DDE payload
    ``+cmd|' /C calc'!A0`` does not (CWE-1236).
    """
    if not isinstance(value, str) or not value.startswith(_FORMULA_PREFIXES):
        return value
    if value[0] in "+-" and _NUMERIC_LIKE.match(value):
        return value
    return f"'{value}"


def export_header(columns: Sequence[str] = EXPORT_COLUMNS) -> bytes:
    """The CSV header row, written once before streaming batches."""
    buffer = io.StringIO()
    csv.writer(buffer).writerow(columns)
    return buffer.getvalue().encode("utf-8")


def export_rows(
    rows: list[dict[str, Any]], columns: Sequence[str] = EXPORT_COLUMNS
) -> bytes:
    """Render one batch of rows — called repeatedly so a large export never materialises at once.

    ``columns`` defaults to the contact export shape; other entities (analytics reports) pass their
    own, which is what keeps one writer serving every export (Doc 15 §19).
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    for row in rows:
        writer.writerow({key: neutralize_formula(value) for key, value in row.items()})
    return buffer.getvalue().encode("utf-8")
