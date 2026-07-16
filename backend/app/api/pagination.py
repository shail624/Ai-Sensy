"""Cursor (keyset) pagination helpers (Doc 04 §3, §6)."""

from __future__ import annotations

import base64
import json
from datetime import datetime

from pydantic import BaseModel

from app.core.exceptions import BadRequestError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class Page(BaseModel):
    """The ``page`` object of a collection envelope (Doc 04 §3)."""

    limit: int
    has_more: bool
    next_cursor: str | None = None
    prev_cursor: str | None = None
    total: int | None = None


def clamp_limit(raw: str | None) -> int:
    try:
        value = int(raw) if raw is not None else DEFAULT_LIMIT
    except ValueError as exc:
        raise BadRequestError("Invalid 'limit' parameter.") from exc
    return max(1, min(value, MAX_LIMIT))


def encode_cursor(created_at: datetime, entity_id: int) -> str:
    raw = json.dumps({"created_at": created_at.isoformat(), "id": entity_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        return datetime.fromisoformat(data["created_at"]), int(data["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise BadRequestError("Invalid pagination cursor.") from exc
