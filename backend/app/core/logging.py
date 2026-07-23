"""Structured logging.

Emits structured (JSON) logs to stdout with a per-request correlation id, per the
logging strategy in Doc 08 §19 and the observability requirements in Doc 06 §13.3.
Secrets/PII must never be logged (Doc 09 §35) — do not pass sensitive values as
log fields.
"""

from __future__ import annotations

import json
import logging
import sys
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


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Merge any structured ``extra={...}`` fields passed to the logger.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human-friendly formatter for local development."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
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


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
