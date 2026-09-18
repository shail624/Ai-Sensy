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


def test_no_log_call_passes_a_key_that_logging_reserves() -> None:
    """`extra={"created": ...}` does not log a field — it raises.

    `logging.makeRecord` refuses any key that would overwrite a `LogRecord` attribute, and it
    raises *before* any formatter runs, so redaction and JSON encoding cannot save it. The failure
    is invisible until the level is low enough for the line to execute: campaign dispatch carried
    `extra={"created": len(created)}` and never failed a test, because the suite does not run at
    INFO — it failed the moment a worker started with `--loglevel=info`, which is every worker.

    Swept across the whole package rather than fixed in one place: one word in a dictionary is an
    easy mistake to repeat, and the cost of repeating it is a task that dies at the log line.
    """
    import ast
    import pathlib

    probe = logging.LogRecord("n", logging.INFO, "p", 1, "m", None, None)
    reserved = set(vars(probe)) | {"message", "asctime"}
    root = pathlib.Path(__file__).resolve().parent.parent / "app"

    collisions = [
        f"{path.relative_to(root.parent)}:{key.lineno} extra={{{key.value!r}: ...}}"
        for path in sorted(root.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "extra" and isinstance(keyword.value, ast.Dict)
        for key in keyword.value.keys
        if isinstance(key, ast.Constant) and key.value in reserved
    ]

    assert collisions == [], "these log calls raise KeyError instead of logging:\n" + "\n".join(
        collisions
    )


def test_the_campaign_batch_log_line_survives_an_info_level_logger(caplog) -> None:
    """The line that actually broke, at the level that broke it."""
    from app.services import campaign_batch_service

    with caplog.at_level(logging.INFO, logger=campaign_batch_service.logger.name):
        campaign_batch_service.logger.info(
            "campaign_batches_planned",
            extra={"campaign": 1, "batches_created": 2, "outstanding": 3},
        )

    assert [r.message for r in caplog.records] == ["campaign_batches_planned"]
    assert caplog.records[0].batches_created == 2
