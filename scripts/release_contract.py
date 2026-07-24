"""Validate the production Compose model against release invariants."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

try:  # Package import in tests; direct import when executed as scripts/release_contract.py.
    from scripts.quality_gate import ROOT, resolve_docker
except ModuleNotFoundError:  # pragma: no cover - exercised by the release command
    from quality_gate import ROOT, resolve_docker

PRODUCTION_COMPOSE = ROOT / "docker-compose.production.yml"
PRODUCTION_ENV_EXAMPLE = ROOT / ".env.production.example"
EXPECTED_SERVICES = {
    "mysql",
    "redis",
    "migrate",
    "api",
    "worker-realtime",
    "worker-bulk",
    "worker-jobs",
    "beat",
    "frontend",
    "nginx",
}
HEALTHCHECKED_SERVICES = EXPECTED_SERVICES - {"migrate", "frontend"}
REQUIRED_SECRETS = {
    "SECRET_KEY",
    "TOKEN_ENCRYPTION_KEY",
    "MYSQL_ROOT_PASSWORD",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_PASSWORD",
    "META_APP_SECRET",
    "META_WEBHOOK_VERIFY_TOKEN",
}


def required_variables(compose_text: str) -> set[str]:
    return set(re.findall(r"\$\{([A-Z][A-Z0-9_]*):\?", compose_text))


def synthetic_environment(compose_text: str) -> dict[str, str]:
    env = os.environ.copy()
    for name in required_variables(compose_text):
        env[name] = f"quality-gate-{name.lower().replace('_', '-')}"
    env["IMAGE_TAG"] = os.environ.get("IMAGE_TAG", "quality-gate")
    env["HTTP_PORT"] = "18080"
    return env


def render_compose(docker: str, compose_text: str) -> dict[str, Any]:
    result = subprocess.run(
        (
            docker,
            "compose",
            "-f",
            os.fspath(PRODUCTION_COMPOSE),
            "config",
            "--format",
            "json",
        ),
        cwd=ROOT,
        env=synthetic_environment(compose_text),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Docker Compose could not render the production model")
    model = json.loads(result.stdout)
    if not isinstance(model, dict):
        raise RuntimeError("Docker Compose returned a non-object model")
    return model


def _image_uses_latest(image: object) -> bool:
    return isinstance(image, str) and (image == "latest" or image.endswith(":latest"))


def validate_contract(
    model: dict[str, Any], compose_text: str, env_example_text: str
) -> list[str]:
    problems: list[str] = []
    required = required_variables(compose_text)
    missing_secrets = sorted(REQUIRED_SECRETS - required)
    if missing_secrets:
        problems.append("production Compose does not fail closed for: " + ", ".join(missing_secrets))
    if "${IMAGE_TAG:?" not in compose_text:
        problems.append("IMAGE_TAG must be required; a mutable image default is not release-safe")

    example_tag = next(
        (
            line.partition("=")[2].strip()
            for line in env_example_text.splitlines()
            if line.startswith("IMAGE_TAG=")
        ),
        "",
    )
    if not example_tag or example_tag == "latest":
        problems.append(".env.production.example must demonstrate a non-latest release tag")

    services = model.get("services")
    if not isinstance(services, dict):
        return [*problems, "rendered Compose model has no services object"]
    service_names = set(services)
    if service_names != EXPECTED_SERVICES:
        missing = sorted(EXPECTED_SERVICES - service_names)
        extra = sorted(service_names - EXPECTED_SERVICES)
        problems.append(f"production service inventory changed (missing={missing}, extra={extra})")

    published = {name for name, service in services.items() if service.get("ports")}
    if published != {"nginx"}:
        problems.append(f"only nginx may publish host ports; found {sorted(published)}")

    for name, service in services.items():
        if _image_uses_latest(service.get("image")):
            problems.append(f"{name} resolves to a mutable latest image")
        logging = service.get("logging")
        options = logging.get("options", {}) if isinstance(logging, dict) else {}
        if options.get("max-size") != "10m" or str(options.get("max-file")) != "5":
            problems.append(f"{name} does not retain the bounded 10m x 5 log policy")
        if name != "migrate" and service.get("restart") != "unless-stopped":
            problems.append(f"{name} must restart unless stopped")
        if name in HEALTHCHECKED_SERVICES and "healthcheck" not in service:
            problems.append(f"{name} has no Compose healthcheck")

    for name in ("api", "worker-realtime", "worker-bulk", "worker-jobs", "beat"):
        depends_on = services.get(name, {}).get("depends_on", {})
        migrate = depends_on.get("migrate", {}) if isinstance(depends_on, dict) else {}
        if migrate.get("condition") != "service_completed_successfully":
            problems.append(f"{name} does not wait for a successful migration")

    nginx_dependencies = services.get("nginx", {}).get("depends_on", {})
    for name in ("api", "frontend"):
        dependency = nginx_dependencies.get(name, {}) if isinstance(nginx_dependencies, dict) else {}
        if dependency.get("condition") != "service_healthy":
            problems.append(f"nginx does not health-gate {name}")

    dockerfiles = {
        "backend": (ROOT / "backend" / "Dockerfile", "USER app"),
        "frontend": (ROOT / "frontend" / "Dockerfile", "USER nginx"),
    }
    for name, (path, user_line) in dockerfiles.items():
        text = path.read_text(encoding="utf-8")
        from_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip().upper().startswith("FROM ")
        ]
        if not from_lines or any("@sha256:" not in line.split()[1] for line in from_lines):
            problems.append(f"{name} Dockerfile has an unpinned base stage")
        if user_line not in text:
            problems.append(f"{name} image no longer declares its non-root runtime user")
        if "HEALTHCHECK " not in text:
            problems.append(f"{name} image no longer declares a healthcheck")
    return problems


def main() -> int:
    compose_text = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
    env_example_text = PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")
    try:
        model = render_compose(resolve_docker(), compose_text)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"release contract could not be rendered: {exc}", file=sys.stderr)
        return 2
    problems = validate_contract(model, compose_text, env_example_text)
    if problems:
        print("release contract failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"release contract passed: {len(EXPECTED_SERVICES)} services, edge-only publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
