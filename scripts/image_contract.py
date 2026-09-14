"""Validate a built application image without starting external dependencies."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

try:  # Package import in tests; direct import when executed as scripts/image_contract.py.
    from scripts.quality_gate import ROOT, resolve_docker
except ModuleNotFoundError:  # pragma: no cover - exercised by the release command
    from quality_gate import ROOT, resolve_docker


EXPECTED_APPLICATION_TASKS = frozenset(
    {
        "app.analytics.tasks.rollup_backfill",
        "app.analytics.tasks.dispatch_report_schedules",
        "app.analytics.tasks.rollup_incremental",
        "app.analytics.tasks.rollup_nightly",
        "app.analytics.tasks.rollup_prune",
        "app.analytics.tasks.run_report_export",
        "app.automation.tasks.consume_automation_trigger_receipt",
        "app.automation.tasks.dispatch_automation_trigger_receipts",
        "app.automation.tasks.dispatch_scheduled_automations",
        "app.automation.tasks.execute_automation_test_run",
        "app.channels.tasks.download_inbound_media",
        "app.channels.tasks.ingest_webhook_events",
        "app.channels.tasks.process_inbound_message",
        "app.channels.tasks.process_webhook_event",
        "app.channels.tasks.run_template_sync",
        "app.channels.tasks.run_waba_sync",
        "app.channels.tasks.send_message",
        "app.crm.campaign_tasks.dispatch_campaign",
        "app.crm.campaign_tasks.dispatch_campaign_batch",
        "app.crm.campaign_tasks.retry_campaign_recipient",
        "app.crm.campaign_tasks.scan_campaign_retries",
        "app.crm.campaign_tasks.scheduler_tick",
        "app.crm.campaign_tasks.send_campaign_recipient",
        "app.crm.reactivation_tasks.dispatch_due_reminders",
        "app.crm.tasks.auto_resolve_inactive_conversations",
        "app.crm.tasks.run_contact_bulk_delete",
        "app.crm.tasks.run_contact_bulk_update",
        "app.crm.tasks.run_contact_deduplicate",
        "app.crm.tasks.run_contact_export",
        "app.crm.tasks.run_contact_import",
        "app.crm.tasks.run_conversation_transcript_export",
        "app.crm.tasks.run_campaign_results_export",
    }
)


def canonical_openapi_path_count() -> int:
    """Return the API surface certified by the checked frontend contract artifact."""
    payload = json.loads((ROOT / "frontend" / "openapi.json").read_text(encoding="utf-8"))
    paths = payload.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("frontend/openapi.json has no paths object")
    return len(paths)


def inspect_image(docker: str, image: str) -> dict[str, Any]:
    result = subprocess.run(
        (docker, "image", "inspect", image),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"could not inspect {image}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise RuntimeError(f"unexpected inspect response for {image}")
    return payload[0]


def validate_metadata(metadata: dict[str, Any]) -> list[str]:
    config = metadata.get("Config")
    if not isinstance(config, dict):
        return ["image metadata has no Config object"]
    problems: list[str] = []
    user = str(config.get("User", "")).strip().lower()
    if user in {"", "0", "root", "0:0", "root:root"}:
        problems.append("runtime user is root or unspecified")
    healthcheck = config.get("Healthcheck")
    if not isinstance(healthcheck, dict) or not healthcheck.get("Test"):
        problems.append("image has no healthcheck")
    return problems


def smoke_command(docker: str, image: str, kind: str) -> tuple[str, ...]:
    prefix = (docker, "run", "--rm", "--network", "none")
    if kind == "backend":
        expected_paths = canonical_openapi_path_count()
        expected_tasks = repr(sorted(EXPECTED_APPLICATION_TASKS))
        code = (
            "from app.main import app; "
            "from app.queue.celery_app import celery_app; "
            "celery_app.loader.import_default_modules(); "
            f"assert len(app.openapi()['paths']) == {expected_paths}; "
            f"expected_tasks = set({expected_tasks}); "
            "registered_tasks = {name for name in celery_app.tasks if name.startswith('app.')}; "
            "assert registered_tasks == expected_tasks, "
            "{'missing': sorted(expected_tasks - registered_tasks), "
            "'unexpected': sorted(registered_tasks - expected_tasks)}; "
            "print('backend image contract passed')"
        )
        return (*prefix, "--entrypoint", "python", image, "-c", code)
    return (*prefix, image, "nginx", "-t")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("kind", choices=("backend", "frontend"))
    args = parser.parse_args()
    docker = resolve_docker()
    try:
        problems = validate_metadata(inspect_image(docker, args.image))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"image contract could not be inspected: {exc}", file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(f"image contract failed: {problem}", file=sys.stderr)
        return 1
    return subprocess.run(
        smoke_command(docker, args.image, args.kind), cwd=ROOT, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
