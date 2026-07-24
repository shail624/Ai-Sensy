"""Typed helpers for SQLAlchemy DML execution results."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import CursorResult, Result


def affected_rows(result: Result[Any]) -> int:
    """Return a DML statement's row count after narrowing its async result."""
    if not isinstance(result, CursorResult):
        raise RuntimeError("DML execution did not return a cursor result")
    return result.rowcount or 0
