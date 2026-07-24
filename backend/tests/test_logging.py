"""Observability contracts: structured correlation and defensive log redaction."""

from __future__ import annotations

import json
import logging

from app.core.logging import REDACTED, JsonFormatter, TextFormatter, request_id_ctx


def _record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, message, (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_redacts_structured_secrets_and_pii() -> None:
    record = _record(
        "login owner@example.com +14155550123 password=hunter2 Bearer abc.def.ghi",
        access_token="eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature",
        payload={"email": "customer@example.com", "safe_count": 3},
        error="recipient +442071838750 rejected",
        job_id="job-123",
    )
    token = request_id_ctx.set("request-safe-123")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)

    assert payload["request_id"] == "request-safe-123"
    assert payload["access_token"] == REDACTED
    assert payload["payload"] == REDACTED
    assert payload["job_id"] == "job-123"
    assert "owner@example.com" not in payload["message"]
    assert "+14155550123" not in payload["message"]
    assert "hunter2" not in payload["message"]
    assert "+442071838750" not in payload["error"]


def test_text_formatter_applies_the_same_redaction_boundary() -> None:
    rendered = TextFormatter().format(
        _record("authorization=super-secret owner@example.com +14155550123")
    )
    assert rendered.count(REDACTED) == 3
    assert "super-secret" not in rendered
    assert "owner@example.com" not in rendered
