"""Structured logging.

Emits structured (JSON) logs to stdout with a per-request correlation id, per the
logging strategy in Doc 08 §19 and the observability requirements in Doc 06 §13.3.
Secrets/PII must never be logged (Doc 09 §35) — do not pass sensitive values as
log fields.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Correlation id for the in-flight request; set by RequestIDMiddleware and read by
# the formatter so every log line for a request can be tied together (Doc 06 §13.3).
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Standard LogRecord attributes we do not want to duplicate into the JSON payload.
_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}

REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set_cookie",
    "password",
    "passwd",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
    "token_encryption_key",
    "signature",
    "phone",
    "phone_e164",
    "wa_id",
    "email",
    "full_name",
    "first_name",
    "last_name",
    "profile_name",
    "recipient",
    "body",
    "content",
    "payload",
}
_SENSITIVE_SUFFIXES = (
    "_password",
    "_secret",
    "_token",
    "_api_key",
    "_signature",
    "_phone",
    "_email",
    "_payload",
    "_body",
    "_content",
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|access[_-]?token|refresh[_-]?token|api[_-]?key|"
    r"authorization|cookie|signature)\b(\s*[:=]\s*)([^\s,;&]+)"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_LIVE_API_KEY = re.compile(r"\bsk_live_[A-Za-z0-9_-]+\b")
_EMAIL = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.I)
_E164 = re.compile(r"(?<!\w)\+[1-9]\d{7,14}(?!\d)")


def redact_text(value: str) -> str:
    """Remove common credential and PII shapes from an otherwise useful log string."""
    value = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", value)
    for pattern in (_BEARER, _JWT, _LIVE_API_KEY, _EMAIL, _E164):
        value = pattern.sub(REDACTED, value)
    return value


def redact_value(key: str, value: Any) -> Any:
    """Recursively redact structured log data, treating field names as the primary signal."""
    normalized = key.lower().replace("-", "_")
    if normalized in _SENSITIVE_KEYS or normalized.endswith(_SENSITIVE_SUFFIXES):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(child): redact_value(str(child), item) for child, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(key, item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        request_id = request_id_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        # Merge any structured ``extra={...}`` fields passed to the logger.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = redact_value(key, value)
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human-friendly formatter for local development."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = redact_text(super().format(record))
        request_id = request_id_ctx.get()
        return f"{base} [request_id={request_id}]" if request_id else base


def configure_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    """Configure the root logger. Idempotent — safe to call at startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_output else TextFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Route uvicorn's own output through the handler configured above, so the process emits one
    # log format on one stream.
    #
    # The parent ``uvicorn`` logger is the load-bearing entry. Uvicorn's dictConfig gives it a
    # plain stderr handler *and* ``propagate = False``; clearing only ``uvicorn.access`` leaves
    # that parent to catch each access record, render it in uvicorn's human format, and stop
    # propagation before it ever reaches the JSON handler here. The visible result with
    # ``LOG_JSON=true`` is that every request line — the bulk of log volume — arrives at the
    # collector as unparseable text on stderr, carrying no ``request_id`` to correlate with.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # RequestIDMiddleware emits the canonical access event while the correlation context is still
    # bound. Uvicorn logs only after the ASGI call returns, when that context has been reset.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
