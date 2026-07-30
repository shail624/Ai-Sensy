"""Hermetic tests for the provider-neutral Module 11 quality tooling."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import (  # noqa: E402
    deployed_stack_gate,
    image_contract,
    performance_canary,
    quality_gate,
    release_contract,
    trivy_scan,
)


def _service(
    *, image: str = "example/service:1@sha256:abc", healthcheck: bool = True
) -> dict[str, object]:
    value: dict[str, object] = {
        "image": image,
        "restart": "unless-stopped",
        "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "5"}},
    }
    if healthcheck:
        value["healthcheck"] = {"test": ["CMD", "true"]}
    return value


def _valid_model() -> dict[str, object]:
    services = {name: _service() for name in release_contract.EXPECTED_SERVICES}
    services["migrate"] = _service(healthcheck=False)
    services["migrate"]["restart"] = "no"
    services["frontend"] = _service(healthcheck=False)
    services["nginx"]["ports"] = [{"target": 80, "published": "18080"}]
    for name in ("api", "worker-realtime", "worker-bulk", "worker-jobs", "beat"):
        services[name]["depends_on"] = {
            "migrate": {"condition": "service_completed_successfully"}
        }
    services["nginx"]["depends_on"] = {
        "api": {"condition": "service_healthy"},
        "frontend": {"condition": "service_healthy"},
    }
    return {"services": services}


def _valid_compose_text() -> str:
    required = "\n".join(f"{name}: ${{{name}:?required}}" for name in release_contract.REQUIRED_SECRETS)
    return f"image: app:${{IMAGE_TAG:?required}}\n{required}"


def test_release_contract_accepts_expected_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, encoding=None: (
            "FROM example@sha256:abc AS runtime\nUSER nginx\nHEALTHCHECK x"
            if "frontend" in self.parts
            else "FROM example@sha256:abc AS runtime\nUSER app\nHEALTHCHECK x"
        ),
    )
    assert (
        release_contract.validate_contract(
            _valid_model(), _valid_compose_text(), "IMAGE_TAG=1.0.0-rc1"
        )
        == []
    )


def test_release_contract_rejects_latest_and_extra_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, encoding=None: (
            "FROM example@sha256:abc AS runtime\nUSER nginx\nHEALTHCHECK x"
            if "frontend" in self.parts
            else "FROM example@sha256:abc AS runtime\nUSER app\nHEALTHCHECK x"
        ),
    )
    model = _valid_model()
    services = model["services"]
    assert isinstance(services, dict)
    services["api"]["image"] = "example/api:latest"
    services["api"]["ports"] = [{"target": 8000, "published": "8000"}]
    problems = release_contract.validate_contract(model, _valid_compose_text(), "IMAGE_TAG=latest")
    assert any("only nginx" in problem for problem in problems)
    assert any("mutable latest" in problem for problem in problems)
    assert any("non-latest" in problem for problem in problems)


def test_release_contract_rejects_unpinned_application_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, encoding=None: (
            "FROM nginx:alpine AS runtime\nUSER nginx\nHEALTHCHECK x"
            if "frontend" in self.parts
            else "FROM python:alpine AS runtime\nUSER app\nHEALTHCHECK x"
        ),
    )

    problems = release_contract.validate_contract(
        _valid_model(), _valid_compose_text(), "IMAGE_TAG=1.0.0-rc1"
    )

    assert problems.count("backend Dockerfile has an unpinned base stage") == 1
    assert problems.count("frontend Dockerfile has an unpinned base stage") == 1


def test_release_contract_rejects_unpinned_external_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, encoding=None: (
            "FROM example@sha256:abc AS runtime\nUSER nginx\nHEALTHCHECK x"
            if "frontend" in self.parts
            else "FROM example@sha256:abc AS runtime\nUSER app\nHEALTHCHECK x"
        ),
    )
    model = _valid_model()
    services = model["services"]
    assert isinstance(services, dict)
    services["mysql"]["image"] = "mysql:8.0"

    problems = release_contract.validate_contract(
        model, _valid_compose_text(), "IMAGE_TAG=1.0.0-rc1"
    )

    assert "mysql external image is not pinned by digest" in problems


def test_image_contract_rejects_root_or_missing_healthcheck() -> None:
    assert image_contract.validate_metadata({"Config": {"User": "root"}}) == [
        "runtime user is root or unspecified",
        "image has no healthcheck",
    ]


def test_backend_image_smoke_imports_the_worker_task_modules() -> None:
    command = image_contract.smoke_command("docker", "app:test", "backend")
    code = command[-1]
    assert "loader.import_default_modules()" in code
    assert "len(app.openapi()['paths']) == 141" in code
    assert "startswith('app.')" in code


def test_quality_runner_stops_at_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv, **kwargs):
        calls.append(tuple(argv))
        return subprocess.CompletedProcess(argv, 7 if len(calls) == 2 else 0)

    monkeypatch.setattr(quality_gate.subprocess, "run", fake_run)
    steps = [
        quality_gate.Step("one", ("tool", "one")),
        quality_gate.Step("two", ("tool", "two")),
        quality_gate.Step("three", ("tool", "three")),
    ]
    assert quality_gate.run_steps(steps) == 7
    assert calls == [("tool", "one"), ("tool", "two")]


def test_deployed_profile_is_cumulative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quality_gate, "resolve_python", lambda: "python")
    monkeypatch.setattr(quality_gate, "resolve_npm", lambda: "npm")
    monkeypatch.setattr(quality_gate, "resolve_docker", lambda: "docker")

    names = [step.name for step in quality_gate.build_steps("deployed")]

    assert names[0] == "backend lint"
    assert "backend tests" in names
    assert "tracked-source vulnerability, secret, and IaC scan" in names
    assert "production image vulnerability scan and SBOM" in names
    assert names[-2:] == [
        "browser runner build",
        "isolated deployed-stack browser and performance gate",
    ]


def test_source_snapshot_includes_only_git_reported_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("kept", encoding="utf-8")
    (source / ".env.production").write_text("not copied", encoding="utf-8")
    destination = tmp_path / "snapshot"
    destination.mkdir()
    monkeypatch.setattr(trivy_scan, "ROOT", source)
    monkeypatch.setattr(trivy_scan, "tracked_paths", lambda: [Path("tracked.txt")])

    trivy_scan.make_source_snapshot(destination)

    assert (destination / "tracked.txt").read_text(encoding="utf-8") == "kept"
    assert not (destination / ".env.production").exists()


def test_render_compose_does_not_echo_synthetic_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"services": {}}), stderr="")

    monkeypatch.setattr(release_contract.subprocess, "run", fake_run)
    model = release_contract.render_compose("docker", "SECRET_KEY: ${SECRET_KEY:?required}")
    assert model == {"services": {}}
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["SECRET_KEY"] == "quality-gate-secret-key"
    assert captured["capture_output"] is True


def test_edge_configuration_uses_the_rendered_pinned_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, ...]] = []

    def fake_run(argv, **kwargs):
        captured.append(tuple(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(release_contract.subprocess, "run", fake_run)
    model = _valid_model()

    assert release_contract.validate_edge_configuration("docker", model) is None
    assert captured[0][0:5] == ("docker", "run", "--rm", "--network", "none")
    assert captured[0][-2:] == ("example/service:1@sha256:abc", "-t")


def test_runtime_log_contract_requires_correlation_and_rejects_leaks() -> None:
    event = {
        "message": "http_request",
        "request_id": "request-123",
        "http_method": "GET",
        "http_path": "/health",
        "status_code": 200,
        "duration_ms": 1.2,
    }
    raw = f"api-1 | {json.dumps(event)}"
    edge = 'nginx-1 | 127.0.0.1 - - [date] "GET /health HTTP/1.1" 200 1 rid=request-123'

    evidence = deployed_stack_gate.validate_runtime_logs(
        raw, edge, forbidden_values=["safe-secret"]
    )

    assert evidence["http_request_events"] == 1
    assert evidence["shared_request_ids"] == 1
    with pytest.raises(RuntimeError, match="synthetic secret/PII"):
        deployed_stack_gate.validate_runtime_logs(
            raw + "\napi-1 | safe-secret", edge, forbidden_values=["safe-secret"]
        )
    with pytest.raises(RuntimeError, match="shared request id"):
        deployed_stack_gate.validate_runtime_logs(
            raw, edge.replace("request-123", "request-456"), forbidden_values=[]
        )


def test_performance_canary_uses_auditable_nearest_rank() -> None:
    assert performance_canary.percentile([30.0, 10.0, 20.0, 40.0], 0.50) == 20.0
    assert performance_canary.percentile([30.0, 10.0, 20.0, 40.0], 0.95) == 40.0


def test_deployed_compose_commands_are_scoped_to_generated_projects() -> None:
    command = deployed_stack_gate.compose_command("docker", "wa-e2e-123-abc", "down")
    assert command[2:4] == ("--project-name", "wa-e2e-123-abc")
    with pytest.raises(ValueError, match="non-isolated"):
        deployed_stack_gate.compose_command("docker", "wa-platform", "down")
