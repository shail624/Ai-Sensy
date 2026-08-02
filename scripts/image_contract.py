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
        code = (
            "from app.main import app; "
            "from app.queue.celery_app import celery_app; "
            "celery_app.loader.import_default_modules(); "
            "assert len(app.openapi()['paths']) == 184; "
            "assert len([name for name in celery_app.tasks if name.startswith('app.')]) == 24; "
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
