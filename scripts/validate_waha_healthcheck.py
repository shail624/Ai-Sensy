"""Validate the certified WAHA image's healthcheck against a real container.

Compose syntax alone did not catch QR-09-D4: the committed probe named ``wget``, but the immutable
certified image does not contain that executable.  This release gate therefore starts the actual
digest-pinned service and verifies Docker health, the probe's positive and negative behavior, the
restart path, and the deployment invariants that make the provider safe to run.

The script never pairs a phone, reads session contents, deletes a container/volume, or changes the
provider's declared capabilities.  A service that was stopped before the gate is stopped again in
``finally``; its persistent session volume is always retained.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
PRODUCTION_COMPOSE = ROOT / "docker-compose.production.yml"
SERVICE = "waha"
CONTAINER_NAME = "wa_waha"
CERTIFIED_IMAGE = (
    "devlikeapro/waha@"
    "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
)
CERTIFIED_IMAGE_ID = "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
HEALTH_TEST = [
    "CMD",
    "curl",
    "--fail",
    "--silent",
    "--show-error",
    "--max-time",
    "5",
    "http://127.0.0.1:3000/ping",
]
PRODUCTION_SENTINELS = (
    "DB_NAME",
    "DB_PASSWORD",
    "DB_USER",
    "IMAGE_TAG",
    "META_APP_SECRET",
    "META_WEBHOOK_VERIFY_TOKEN",
    "MYSQL_ROOT_PASSWORD",
    "REDIS_PASSWORD",
    "SECRET_KEY",
    "TOKEN_ENCRYPTION_KEY",
    "WAHA_API_KEY",
)


class ValidationError(RuntimeError):
    """A required runtime or deployment invariant did not hold."""


def _run(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ValidationError(f"command failed ({result.returncode}): {argv[0]} {argv[1]}: {detail}")
    return result


def _docker() -> str:
    override = os.environ.get("WA_QUALITY_DOCKER")
    resolved = shutil.which(override or "docker")
    if resolved is None:
        raise ValidationError("Docker was not found")
    return resolved


def _compose(docker: str, *args: str) -> list[str]:
    return [docker, "compose", "-f", os.fspath(COMPOSE), "--profile", "waha", *args]


def _production_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in PRODUCTION_SENTINELS:
        if not env.get(name):
            env[name] = f"qr09b-validation-{name.lower().replace('_', '-')}"
    return env


def _compose_model(docker: str, path: Path, *, production: bool = False) -> dict[str, Any]:
    argv = [docker, "compose", "-f", os.fspath(path), "--profile", "waha", "config", "--format", "json"]
    result = _run(argv, env=_production_env() if production else None)
    return json.loads(result.stdout)


def _assert_compose_contract(model: dict[str, Any], *, production: bool) -> None:
    services = model.get("services", {})
    waha = services.get(SERVICE)
    if not isinstance(waha, dict):
        raise ValidationError("the waha profile did not resolve a waha service")
    if waha.get("image") != CERTIFIED_IMAGE:
        raise ValidationError(f"WAHA image drifted from the certified digest: {waha.get('image')!r}")
    if waha.get("restart") != "unless-stopped":
        raise ValidationError("WAHA restart policy drifted")
    if waha.get("healthcheck", {}).get("test") != HEALTH_TEST:
        raise ValidationError("resolved WAHA healthcheck differs from the runtime-tested probe")

    volumes = waha.get("volumes", [])
    expected_volume = any(
        item.get("source") == "waha-sessions" and item.get("target") == "/app/.sessions"
        for item in volumes
        if isinstance(item, dict)
    )
    if not expected_volume:
        raise ValidationError("waha-sessions:/app/.sessions is not present")

    ports = waha.get("ports", [])
    if production:
        if ports:
            raise ValidationError("production WAHA unexpectedly publishes a port")
    elif not any(
        item.get("host_ip") == "127.0.0.1"
        and int(item.get("target", 0)) == 3000
        and int(item.get("published", 0)) == 3000
        for item in ports
        if isinstance(item, dict)
    ):
        raise ValidationError("development WAHA is not published loopback-only on port 3000")

    dependants = [
        name
        for name, service in services.items()
        if isinstance(service, dict) and SERVICE in (service.get("depends_on") or {})
    ]
    if dependants:
        raise ValidationError(f"unexpected startup coupling to WAHA: {', '.join(sorted(dependants))}")


def _container_id(docker: str) -> str:
    return _run(_compose(docker, "ps", "-q", SERVICE), check=False).stdout.strip()


def _is_running(docker: str, container_id: str) -> bool:
    if not container_id:
        return False
    result = _run([docker, "inspect", "--format", "{{.State.Running}}", container_id], check=False)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _wait_healthy(docker: str, container_id: str, *, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    last = "missing"
    while time.monotonic() < deadline:
        result = _run(
            [docker, "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", container_id],
            check=False,
        )
        last = result.stdout.strip() or "missing"
        if result.returncode == 0 and last == "healthy":
            return
        if last == "unhealthy":
            break
        time.sleep(2)
    inspect = _run([docker, "inspect", container_id], check=False)
    raise ValidationError(f"WAHA did not become healthy (last={last}): {inspect.stdout[-2000:]}")


def _inspect(docker: str, container_id: str) -> dict[str, Any]:
    return json.loads(_run([docker, "inspect", container_id]).stdout)[0]


def _session_files(docker: str, container_id: str) -> set[str]:
    result = _run(
        [docker, "exec", container_id, "find", "/app/.sessions", "-maxdepth", "5", "-type", "f", "-print"],
        check=False,
    )
    if result.returncode:
        raise ValidationError(f"could not inventory the session volume: {result.stderr.strip()}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _assert_runtime_contract(docker: str, container_id: str) -> tuple[str, set[str]]:
    info = _inspect(docker, container_id)
    if info.get("Image") != CERTIFIED_IMAGE_ID:
        raise ValidationError(f"running image id is not the certified digest: {info.get('Image')!r}")
    if info.get("HostConfig", {}).get("RestartPolicy", {}).get("Name") != "unless-stopped":
        raise ValidationError("running restart policy is not unless-stopped")
    if info.get("Config", {}).get("Healthcheck", {}).get("Test") != HEALTH_TEST:
        raise ValidationError("running health command differs from the compose contract")

    mounts = info.get("Mounts", [])
    session_mount = next(
        (mount for mount in mounts if mount.get("Destination") == "/app/.sessions" and mount.get("Type") == "volume"),
        None,
    )
    if session_mount is None:
        raise ValidationError("running container has no persistent /app/.sessions volume")

    ports = info.get("NetworkSettings", {}).get("Ports", {}).get("3000/tcp", [])
    if not ports or any(binding.get("HostIp") != "127.0.0.1" for binding in ports):
        raise ValidationError("running development provider is not loopback-only")

    live = _run([docker, "exec", container_id, *HEALTH_TEST[1:]], check=False)
    if live.returncode:
        raise ValidationError(f"health command failed against the responsive provider: {live.stderr.strip()}")

    negative = HEALTH_TEST[1:].copy()
    negative[-1] = "http://127.0.0.1:1/ping"
    unavailable = _run([docker, "exec", container_id, *negative], check=False)
    if unavailable.returncode == 0:
        raise ValidationError("health command incorrectly succeeded against an unavailable endpoint")

    api_key = os.environ.get("WAHA_API_KEY", "waha-local-dev-key")
    request = urllib.request.Request(
        "http://127.0.0.1:3000/api/server/version",
        headers={"X-Api-Key": api_key},
    )
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - fixed loopback URL
        version = json.load(response)
    observed = (version.get("version"), version.get("engine"), version.get("tier"))
    if observed != ("2026.7.2", "NOWEB", "CORE"):
        raise ValidationError(f"provider identity drifted: {observed!r}")

    return str(session_mount.get("Name")), _session_files(docker, container_id)


def main() -> int:
    docker = _docker()
    development = _compose_model(docker, COMPOSE)
    production = _compose_model(docker, PRODUCTION_COMPOSE, production=True)
    _assert_compose_contract(development, production=False)
    _assert_compose_contract(production, production=True)

    previous_id = _container_id(docker)
    was_running = _is_running(docker, previous_id)
    started = False
    try:
        _run(_compose(docker, "up", "-d", SERVICE))
        started = True
        container_id = _container_id(docker)
        if not container_id:
            raise ValidationError("Compose did not create the WAHA container")
        _wait_healthy(docker, container_id)
        volume_name, files_before = _assert_runtime_contract(docker, container_id)

        _run(_compose(docker, "restart", SERVICE))
        container_id_after = _container_id(docker)
        _wait_healthy(docker, container_id_after)
        volume_after, files_after = _assert_runtime_contract(docker, container_id_after)
        if volume_after != volume_name:
            raise ValidationError("WAHA restart replaced the session volume")
        if not files_before.issubset(files_after):
            raise ValidationError("WAHA restart removed files from persistent session storage")

        print("WAHA runtime healthcheck gate passed")
        print("  image: certified sha256:33ecd1b7...f2d75e")
        print("  provider: 2026.7.2 / NOWEB / CORE")
        print("  positive probe: PASS (/ping, unauthenticated)")
        print("  negative probe: PASS (unavailable loopback endpoint returned non-zero)")
        print("  Docker healthy transition: PASS before and after restart")
        print("  development exposure: 127.0.0.1:3000 only")
        print("  production exposure: no published WAHA port")
        print(f"  session volume preserved: {volume_name}")
        print("  startup coupling: none added")
        return 0
    finally:
        if started and not was_running:
            _run(_compose(docker, "stop", SERVICE), check=False)


if __name__ == "__main__":
    raise SystemExit(main())
