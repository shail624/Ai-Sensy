"""Run the pinned Trivy scanner against tracked source or built images."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

try:  # Package import in tests; direct import when executed as scripts/trivy_scan.py.
    from scripts.quality_gate import ARTIFACTS, CACHE, ROOT, TRIVY_IMAGE, resolve_docker
except ModuleNotFoundError:  # pragma: no cover - exercised by the release command
    from quality_gate import ARTIFACTS, CACHE, ROOT, TRIVY_IMAGE, resolve_docker


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw))
        source = ROOT / relative
        if source.is_file() and not source.is_symlink():
            paths.append(relative)
    return paths


def make_source_snapshot(destination: Path) -> None:
    for relative in tracked_paths():
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _docker_mount(path: Path, destination: str, *, read_only: bool = False) -> str:
    suffix = ":ro" if read_only else ""
    return f"{path.resolve()}:{destination}{suffix}"


def scan_source(docker: str) -> int:
    ARTIFACTS.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="source-", dir=CACHE) as temporary:
        snapshot = Path(temporary)
        make_source_snapshot(snapshot)
        command = (
            docker,
            "run",
            "--rm",
            "--volume",
            _docker_mount(snapshot, "/workspace", read_only=True),
            "--volume",
            _docker_mount(CACHE, "/root/.cache/trivy"),
            "--volume",
            _docker_mount(ARTIFACTS, "/artifacts"),
            TRIVY_IMAGE,
            "fs",
            "--scanners",
            "vuln,misconfig,secret",
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
            "--format",
            "json",
            "--output",
            "/artifacts/trivy-source.json",
            "/workspace",
        )
        return subprocess.run(command, cwd=ROOT, check=False).returncode


def scan_images(docker: str, images: list[str]) -> int:
    ARTIFACTS.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    for image in images:
        safe_name = image.replace("/", "-").replace(":", "-")
        common = (
            docker,
            "run",
            "--rm",
            "--volume",
            "/var/run/docker.sock:/var/run/docker.sock",
            "--volume",
            _docker_mount(CACHE, "/root/.cache/trivy"),
            "--volume",
            _docker_mount(ARTIFACTS, "/artifacts"),
            TRIVY_IMAGE,
            "image",
        )
        vulnerability = (
            *common,
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
            "--format",
            "json",
            "--output",
            f"/artifacts/{safe_name}-vulnerabilities.json",
            image,
        )
        if subprocess.run(vulnerability, cwd=ROOT, check=False).returncode:
            return 1
        sbom = (
            *common,
            "--format",
            "cyclonedx",
            "--output",
            f"/artifacts/{safe_name}-sbom.cdx.json",
            image,
        )
        if subprocess.run(sbom, cwd=ROOT, check=False).returncode:
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("source")
    images_parser = subparsers.add_parser("images")
    images_parser.add_argument("images", nargs="+")
    args = parser.parse_args()
    docker = resolve_docker()
    if args.command == "source":
        return scan_source(docker)
    return scan_images(docker, args.images)


if __name__ == "__main__":
    raise SystemExit(main())
