"""Custom-attribute typing rules (Doc 03 §6.3, FR-CON-11).

Pure helpers for the typed EAV model: which value column backs each ``data_type``, how to
coerce/validate an incoming value, and how to read a stored value back out. No DB access.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

TYPE_STRING = "string"
TYPE_NUMBER = "number"
TYPE_DATETIME = "datetime"
TYPE_BOOLEAN = "boolean"
TYPE_ENUM = "enum"
DATA_TYPES = (TYPE_STRING, TYPE_NUMBER, TYPE_DATETIME, TYPE_BOOLEAN, TYPE_ENUM)

#: data_type → the ``contact_attribute_values`` column holding it (Doc 03 §6.3).
VALUE_COLUMN: dict[str, str] = {
    TYPE_STRING: "value_string",
    TYPE_ENUM: "value_string",
    TYPE_NUMBER: "value_number",
    TYPE_DATETIME: "value_datetime",
    TYPE_BOOLEAN: "value_boolean",
}

MAX_STRING_LENGTH = 1024


class AttributeValueError(ValueError):
    """Raised when a value does not satisfy its attribute's declared type."""


def coerce_value(data_type: str, value: Any, enum_values: list[str] | None = None) -> Any:
    """Validate/convert ``value`` for ``data_type``. Raises :class:`AttributeValueError`."""
    if value is None:
        return None
    if data_type == TYPE_STRING:
        if not isinstance(value, str):
            raise AttributeValueError("expected a string")
        if len(value) > MAX_STRING_LENGTH:
            raise AttributeValueError(f"exceeds {MAX_STRING_LENGTH} characters")
        return value
    if data_type == TYPE_ENUM:
        if not isinstance(value, str):
            raise AttributeValueError("expected a string")
        allowed = enum_values or []
        if value not in allowed:
            raise AttributeValueError(f"must be one of {allowed}")
        return value
    if data_type == TYPE_NUMBER:
        if isinstance(value, bool) or not isinstance(value, int | float | str | Decimal):
            raise AttributeValueError("expected a number")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise AttributeValueError("expected a number") from exc
    if data_type == TYPE_DATETIME:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        if not isinstance(value, str):
            raise AttributeValueError("expected an ISO-8601 datetime")
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as exc:
            raise AttributeValueError("expected an ISO-8601 datetime") from exc
    if data_type == TYPE_BOOLEAN:
        if not isinstance(value, bool):
            raise AttributeValueError("expected a boolean")
        return value
    raise AttributeValueError(f"unknown data_type {data_type!r}")


def read_value(data_type: str, row: Any) -> Any:
    """Read the stored value back as a JSON-friendly Python value."""
    if data_type == TYPE_NUMBER:
        return float(row.value_number) if row.value_number is not None else None
    if data_type == TYPE_DATETIME:
        return row.value_datetime
    if data_type == TYPE_BOOLEAN:
        return row.value_boolean
    return row.value_string
