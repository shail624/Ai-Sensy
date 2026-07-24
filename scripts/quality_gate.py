"""Provider-neutral quality gates for local development and automation.

The Design Book defines *what* blocks promotion but deliberately does not pick a CI
vendor.  This runner is that stable repository interface: any CI system can invoke the
same profiles developers run locally.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
E2E = ROOT / "e2e"
ARTIFACTS = ROOT / ".quality-artifacts"
CACHE = ROOT / ".quality-cache"
PYTEST_BASETEMP = BACKEND / f".pytest-run-quality-{os.getpid()}"

# Multi-platform manifest digest for the official 0.72.0 image.  A digest is used
# deliberately: a mutable scanner tag must never sit inside a supply-chain gate.
TRIVY_IMAGE = (
    "aquasec/trivy:0.72.0@"
    "sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
)


class GateConfigurationError(RuntimeError):
    """The workstation cannot execute the selected profile."""


@dataclass(frozen=True, slots=True)
class Step:
    name: str
    argv: tuple[str, ...]
    cwd: Path = ROOT
    env: dict[str, str] = field(default_factory=dict)


def _first_executable(candidates: Iterable[str | Path], *, label: str) -> str:
    for candidate in candidates:
        value = os.fspath(candidate)
        if Path(value).is_file():
            return str(Path(value).resolve())
        resolved = shutil.which(value)
        if resolved:
            return resolved
    raise GateConfigurationError(f"{label} was not found; install it or set its override variable")


def resolve_python() -> str:
    override = os.environ.get("WA_QUALITY_PYTHON")
    candidates: list[str | Path] = []
    if override:
        candidates.append(override)
    candidates.extend(
        (
            BACKEND / ".venv" / "Scripts" / "python.exe",
            BACKEND / ".venv" / "bin" / "python",
            sys.executable,
        )
    )
    return _first_executable(candidates, label="backend Python")


def resolve_npm() -> str:
    override = os.environ.get("WA_QUALITY_NPM")
    candidates = [override] if override else []
    # Python cannot launch a PowerShell .ps1 shim directly on Windows. npm.cmd is
    # therefore preferred while `npm` remains the portable POSIX fallback.
    candidates.extend(("npm.cmd", "npm"))
    return _first_executable(candidates, label="npm")


def resolve_docker() -> str:
    override = os.environ.get("WA_QUALITY_DOCKER")
    return _first_executable(([override] if override else []) + ["docker"], label="Docker")


def _base_steps(python: str, npm: str) -> list[Step]:
    return [
        Step(
            "backend lint",
            (python, "-m", "ruff", "check", "app", "tests", "scripts", "../scripts"),
            BACKEND,
        ),
        Step("backend strict types", (python, "-m", "mypy", "app"), BACKEND),
        Step(
            "OpenAPI drift",
            (python, "scripts/export_openapi.py", "--check"),
            BACKEND,
        ),
        Step("frontend lint", (npm, "run", "lint"), FRONTEND),
        Step("frontend types", (npm, "run", "typecheck"), FRONTEND),
        Step("browser test types", (npm, "run", "typecheck"), E2E),
    ]


def _test_steps(python: str, npm: str) -> list[Step]:
    return [
        Step(
            "backend tests",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--basetemp={PYTEST_BASETEMP.name}",
            ),
            BACKEND,
        ),
        Step("frontend tests", (npm, "test"), FRONTEND),
        Step("frontend production build", (npm, "run", "build"), FRONTEND),
    ]


def _security_steps(python: str, npm: str, docker: str) -> list[Step]:
    ARTIFACTS.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    return [
        Step(
            "backend SAST",
            (
                python,
                "-m",
                "bandit",
                "-r",
                "app",
                "-ll",
                "-ii",
                "-f",
                "json",
                "-o",
                os.fspath(ARTIFACTS / "bandit.json"),
            ),
            BACKEND,
        ),
        Step(
            "backend dependency audit",
            (
                python,
                "-m",
                "pip_audit",
                "--strict",
                "--progress-spinner",
                "off",
                "--format",
                "cyclonedx-json",
                "--output",
                os.fspath(ARTIFACTS / "backend-sbom.cdx.json"),
                ".",
            ),
            BACKEND,
        ),
        Step(
            "frontend production dependency audit",
            (npm, "audit", "--omit=dev", "--audit-level=high"),
            FRONTEND,
        ),
        Step(
            "browser test dependency audit",
            (npm, "audit", "--audit-level=high"),
            E2E,
        ),
        Step(
            "tracked-source vulnerability, secret, and IaC scan",
            (python, os.fspath(ROOT / "scripts" / "trivy_scan.py"), "source"),
            ROOT,
            {"WA_QUALITY_DOCKER": docker},
        ),
    ]


def _release_steps(python: str, docker: str) -> list[Step]:
    tag = os.environ.get("WA_QUALITY_IMAGE_TAG", "quality-gate")
    # Compose parses required runtime variables even for a build-only command. Use
    # conspicuous non-secret sentinels so the release gate never needs or reads a
    # developer's real .env.production file.
    compose_env = {
        name: f"quality-gate-{name.lower().replace('_', '-')}"
        for name in (
            "SECRET_KEY",
            "TOKEN_ENCRYPTION_KEY",
            "MYSQL_ROOT_PASSWORD",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_PASSWORD",
            "META_APP_SECRET",
            "META_WEBHOOK_VERIFY_TOKEN",
        )
    }
    compose_env["IMAGE_TAG"] = tag
    compose = (docker, "compose", "-f", "docker-compose.production.yml")
    return [
        Step(
            "development Compose model",
            (docker, "compose", "-f", "docker-compose.yml", "config", "--quiet"),
        ),
        Step(
            "production release contract",
            (python, os.fspath(ROOT / "scripts" / "release_contract.py")),
            env=compose_env,
        ),
        Step("production image build", (*compose, "build", "--pull"), env=compose_env),
        Step(
            "backend image contract",
            (python, os.fspath(ROOT / "scripts" / "image_contract.py"), f"wa-platform/backend:{tag}", "backend"),
        ),
        Step(
            "frontend image contract",
            (python, os.fspath(ROOT / "scripts" / "image_contract.py"), f"wa-platform/frontend:{tag}", "frontend"),
        ),
        Step(
            "production image vulnerability scan and SBOM",
            (
                python,
                os.fspath(ROOT / "scripts" / "trivy_scan.py"),
                "images",
                f"wa-platform/backend:{tag}",
                f"wa-platform/frontend:{tag}",
            ),
            env={"WA_QUALITY_DOCKER": docker},
        ),
    ]


def _deployed_steps(python: str, docker: str) -> list[Step]:
    tag = os.environ.get("WA_QUALITY_IMAGE_TAG", "quality-gate")
    runner_image = f"wa-platform/e2e:{tag}"
    return [
        Step(
            "browser runner build",
            (docker, "build", "--pull", "--tag", runner_image, os.fspath(E2E)),
        ),
        Step(
            "isolated deployed-stack browser and performance gate",
            (
                python,
                os.fspath(ROOT / "scripts" / "deployed_stack_gate.py"),
                "--app-image-tag",
                tag,
                "--runner-image",
                runner_image,
            ),
        ),
    ]


def build_steps(profile: str) -> list[Step]:
    python = resolve_python()
    npm = resolve_npm()
    steps = _base_steps(python, npm)
    if profile in {"pre-merge", "release", "deployed"}:
        steps.extend(_test_steps(python, npm))
        steps.extend(_security_steps(python, npm, resolve_docker()))
    if profile in {"release", "deployed"}:
        steps.extend(_release_steps(python, resolve_docker()))
    if profile == "deployed":
        steps.extend(_deployed_steps(python, resolve_docker()))
    return steps


def run_steps(steps: Sequence[Step]) -> int:
    started = time.monotonic()
    completed: list[tuple[str, float]] = []
    for index, step in enumerate(steps, start=1):
        print(f"\n[{index}/{len(steps)}] {step.name}", flush=True)
        step_started = time.monotonic()
        env = os.environ.copy()
        env.update(step.env)
        result = subprocess.run(step.argv, cwd=step.cwd, env=env, check=False)
        elapsed = time.monotonic() - step_started
        if result.returncode:
            print(f"\nFAILED: {step.name} ({elapsed:.1f}s)", file=sys.stderr)
            return result.returncode
        completed.append((step.name, elapsed))

    print("\nQuality gate passed:")
    for name, elapsed in completed:
        print(f"  {name}: {elapsed:.1f}s")
    print(f"Total: {time.monotonic() - started:.1f}s")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        choices=("static", "pre-merge", "release", "deployed"),
        help=(
            "static is offline; pre-merge adds tests/source security; release adds images; "
            "deployed adds an isolated real-stack gate"
        ),
    )
    parser.add_argument("--list", action="store_true", help="print the selected steps without running them")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        steps = build_steps(args.profile)
    except GateConfigurationError as exc:
        print(f"quality gate configuration error: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for step in steps:
            print(step.name)
        return 0
    try:
        return run_steps(steps)
    finally:
        # Scanner snapshots contain source and should not survive a run. Individual
        # scan tools own their temporary paths; this removes only abandoned copies.
        for path in CACHE.glob("source-*") if CACHE.exists() else ():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        if PYTEST_BASETEMP.parent == BACKEND and PYTEST_BASETEMP.is_dir():
            shutil.rmtree(PYTEST_BASETEMP, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
