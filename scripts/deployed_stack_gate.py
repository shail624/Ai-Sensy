"""Run browser and latency checks against an isolated production-Compose stack."""

from __future__ import annotations

import argparse
import base64
import os
import secrets
import shutil
import socket
import subprocess
import sys

try:  # Package import in tests; direct import when executed from the repository root.
    from scripts.performance_canary import run_canary
    from scripts.quality_gate import ARTIFACTS, ROOT, resolve_docker
except ModuleNotFoundError:  # pragma: no cover - exercised by the deployed command
    from performance_canary import run_canary
    from quality_gate import ARTIFACTS, ROOT, resolve_docker

PRODUCTION_COMPOSE = ROOT / "docker-compose.production.yml"


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def isolated_project_name() -> str:
    return f"wa-e2e-{os.getpid()}-{secrets.token_hex(3)}"


def stack_environment(image_tag: str, http_port: int) -> tuple[dict[str, str], str, str]:
    env = os.environ.copy()
    owner_email = "release-gate@example.com"
    owner_password = f"E2e-{secrets.token_urlsafe(18)}-9"
    env.update(
        {
            "IMAGE_TAG": image_tag,
            "HTTP_PORT": str(http_port),
            "SECRET_KEY": secrets.token_urlsafe(48),
            "TOKEN_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "MYSQL_ROOT_PASSWORD": secrets.token_urlsafe(24),
            "DB_NAME": "wa_e2e",
            "DB_USER": "wa_e2e",
            "DB_PASSWORD": secrets.token_urlsafe(24),
            "REDIS_PASSWORD": secrets.token_urlsafe(24),
            "META_APP_SECRET": secrets.token_urlsafe(24),
            "META_WEBHOOK_VERIFY_TOKEN": secrets.token_urlsafe(24),
            "API_WORKERS": "1",
            "WORKER_REALTIME_CONCURRENCY": "1",
            "WORKER_BULK_CONCURRENCY": "1",
            "WORKER_JOBS_CONCURRENCY": "1",
            "OWNER_EMAIL": owner_email,
            "OWNER_PASSWORD": owner_password,
        }
    )
    return env, owner_email, owner_password


def compose_command(docker: str, project: str, *arguments: str) -> tuple[str, ...]:
    if not project.startswith("wa-e2e-"):
        raise ValueError("refusing to address a non-isolated Compose project")
    return (
        docker,
        "compose",
        "--project-name",
        project,
        "--file",
        os.fspath(PRODUCTION_COMPOSE),
        *arguments,
    )


def _run(command: tuple[str, ...], *, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def _capture(command: tuple[str, ...], *, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def clear_previous_evidence() -> None:
    for path in (
        ARTIFACTS / "deployed-compose.log",
        ARTIFACTS / "deployed-compose-ps.txt",
        ARTIFACTS / "performance-canary.json",
        ARTIFACTS / "playwright-junit.xml",
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(ARTIFACTS / "playwright-results", ignore_errors=True)


def run_gate(*, app_image_tag: str, runner_image: str) -> int:
    docker = resolve_docker()
    project = isolated_project_name()
    port = available_port()
    env, owner_email, owner_password = stack_environment(app_image_tag, port)
    ARTIFACTS.mkdir(exist_ok=True)
    clear_previous_evidence()
    passed = False
    result = 1
    try:
        _run(
            compose_command(
                docker,
                project,
                "up",
                "--detach",
                "--wait",
                "--wait-timeout",
                "300",
                "--no-build",
            ),
            env=env,
        )
        _run(
            compose_command(
                docker,
                project,
                "run",
                "--rm",
                "-T",
                "--env",
                "OWNER_EMAIL",
                "--env",
                "OWNER_PASSWORD",
                "api",
                "python",
                "-m",
                "app.cli",
                "create-owner",
                "--name",
                "Release Gate Owner",
            ),
            env=env,
        )
        browser_env = env | {
            "E2E_BASE_URL": "http://nginx",
            "E2E_OWNER_EMAIL": owner_email,
            "E2E_OWNER_PASSWORD": owner_password,
            "E2E_RUN_ID": project.removeprefix("wa-e2e-"),
        }
        _run(
            (
                docker,
                "run",
                "--rm",
                "--init",
                "--ipc=host",
                "--network",
                f"{project}_default",
                "--env",
                "E2E_BASE_URL",
                "--env",
                "E2E_OWNER_EMAIL",
                "--env",
                "E2E_OWNER_PASSWORD",
                "--env",
                "E2E_RUN_ID",
                "--volume",
                f"{ARTIFACTS.resolve()}:/artifacts",
                runner_image,
            ),
            env=browser_env,
        )
        passed = (
            run_canary(
                base_url=f"http://127.0.0.1:{port}",
                email=owner_email,
                password=owner_password,
                samples=30,
                warmup=5,
                threshold_ms=300.0,
                output=ARTIFACTS / "performance-canary.json",
            )
            == 0
        )
        result = 0 if passed else 1
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"deployed-stack gate failed: {exc}", file=sys.stderr)
    finally:
        (ARTIFACTS / "deployed-compose-ps.txt").write_text(
            _capture(compose_command(docker, project, "ps", "--all"), env=env),
            encoding="utf-8",
        )
        if not passed:
            (ARTIFACTS / "deployed-compose.log").write_text(
                _capture(
                    compose_command(docker, project, "logs", "--no-color", "--timestamps"),
                    env=env,
                ),
                encoding="utf-8",
            )
        cleanup = subprocess.run(
            compose_command(
                docker,
                project,
                "down",
                "--volumes",
                "--remove-orphans",
                "--timeout",
                "10",
            ),
            cwd=ROOT,
            env=env,
            check=False,
        )
        if cleanup.returncode:
            print(f"isolated Compose cleanup failed for {project}", file=sys.stderr)
            result = 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-image-tag", required=True)
    parser.add_argument("--runner-image", required=True)
    args = parser.parse_args()
    return run_gate(app_image_tag=args.app_image_tag, runner_image=args.runner_image)


if __name__ == "__main__":
    raise SystemExit(main())
