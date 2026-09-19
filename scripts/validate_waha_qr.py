"""Validate WAHA QR image negotiation against the exact certified runtime.

QR-09-D7 existed because hermetic tests returned PNG regardless of the request's ``Accept``
header.  The certified WAHA 2026.7.2 server is content-negotiated: asking its QR route for JSON
returns JSON even when ``?format=image`` is present.  This gate starts an isolated digest-pinned
container, proves that provider contract, then exercises the repository's real ``WahaClient``.

QR bytes are held only in memory long enough to validate the PNG signature.  They are never
printed, logged, written, audited, or exposed as an artifact.  The temporary container has no
volume and is removed after the gate; the deployment's persistent session volume is untouched.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.fspath(ROOT / "backend"))

from app.channels.waha import WahaCredentials  # noqa: E402
from app.channels.waha.client import WahaClient  # noqa: E402

CERTIFIED_IMAGE = (
    "devlikeapro/waha@"
    "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
)
CERTIFIED_IMAGE_ID = "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
API_KEY = "qr09e-runtime-synthetic-key"
SESSION_NAME = "qr09e-runtime"
LABEL_KEY = "com.aisensy.validation"
LABEL_VALUE = "qr09e-waha-qr"
PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")


class ValidationError(RuntimeError):
    """The certified runtime did not satisfy the governed QR contract."""


def _run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ValidationError(f"command failed ({result.returncode}): {argv[0]}: {detail}")
    return result


def _docker() -> str:
    override = os.environ.get("WA_QUALITY_DOCKER")
    resolved = shutil.which(override or "docker")
    if resolved is None:
        raise ValidationError("Docker was not found")
    return resolved


def _request(
    url: str,
    *,
    method: str = "GET",
    accept: str | None = "application/json",
    payload: dict[str, Any] | None = None,
    read_body: bool = True,
) -> tuple[int, str, bytes]:
    headers = {"X-Api-Key": API_KEY}
    if accept is not None:
        headers["Accept"] = accept
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - loopback only
            content_type = response.headers.get_content_type()
            body = response.read() if read_body else b""
            return response.status, content_type, body
    except urllib.error.HTTPError as exc:
        content_type = exc.headers.get_content_type()
        exc.close()
        return exc.code, content_type, b""


def _json(url: str, **kwargs: Any) -> tuple[int, dict[str, Any]]:
    status, content_type, body = _request(url, **kwargs)
    if "json" not in content_type:
        raise ValidationError(f"expected JSON from provider API, received {content_type!r}")
    try:
        decoded = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("provider returned malformed JSON") from exc
    if not isinstance(decoded, dict):
        raise ValidationError("provider returned an unexpected JSON shape")
    return status, decoded


def _wait_ping(base_url: str, *, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/ping", timeout=3) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    raise ValidationError("certified WAHA container did not become responsive")


def _wait_for_qr(base_url: str, *, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last = "missing"
    while time.monotonic() < deadline:
        status, session = _json(f"{base_url}/api/sessions/{SESSION_NAME}")
        if status == 200:
            last = str(session.get("status"))
            if last == "SCAN_QR_CODE":
                return
        time.sleep(1)
    raise ValidationError(f"provider session did not reach QR state (last={last})")


async def _exercise_repository_client(base_url: str) -> int:
    credentials = WahaCredentials(base_url=base_url, api_key=API_KEY, session=SESSION_NAME)
    client = WahaClient(credentials)
    try:
        challenge = await client.qr_challenge(SESSION_NAME)
        if challenge.mimetype != "image/png":
            raise ValidationError(f"WahaClient returned {challenge.mimetype!r}, not image/png")
        if not challenge.data.startswith(PNG_SIGNATURE):
            raise ValidationError("WahaClient response is not a PNG")
        return challenge.size_bytes
    finally:
        await client.close()


def _published_base_url(docker: str, container: str) -> str:
    result = _run([docker, "port", container, "3000/tcp"])
    binding = result.stdout.strip().splitlines()[0]
    host, port = binding.rsplit(":", 1)
    if host != "127.0.0.1":
        raise ValidationError(f"temporary provider is not loopback-only: {binding!r}")
    return f"http://127.0.0.1:{int(port)}"


def main() -> int:
    docker = _docker()
    container = f"wa_waha_qr_gate_{os.getpid()}"
    started = False
    try:
        _run(
            [
                docker,
                "run",
                "-d",
                "--name",
                container,
                "--label",
                f"{LABEL_KEY}={LABEL_VALUE}",
                "-e",
                "WHATSAPP_DEFAULT_ENGINE=NOWEB",
                "-e",
                f"WAHA_API_KEY={API_KEY}",
                "-e",
                f"WHATSAPP_API_KEY={API_KEY}",
                "-p",
                "127.0.0.1::3000",
                CERTIFIED_IMAGE,
            ]
        )
        started = True
        base_url = _published_base_url(docker, container)
        _wait_ping(base_url)

        inspection = json.loads(_run([docker, "inspect", container]).stdout)[0]
        if inspection.get("Image") != CERTIFIED_IMAGE_ID:
            raise ValidationError("temporary provider did not run the certified image digest")
        if any(mount.get("Destination") == "/app/.sessions" for mount in inspection.get("Mounts", [])):
            raise ValidationError("isolated QR gate unexpectedly mounted persistent session state")

        status, version = _json(f"{base_url}/api/server/version")
        identity = (version.get("version"), version.get("engine"), version.get("tier"))
        if status != 200 or identity != ("2026.7.2", "NOWEB", "CORE"):
            raise ValidationError(f"provider identity drifted: status={status}, identity={identity!r}")

        status, _ = _json(
            f"{base_url}/api/sessions",
            method="POST",
            payload={
                "name": SESSION_NAME,
                "start": True,
                "config": {
                    "noweb": {
                        "markOnline": True,
                        "store": {"enabled": True, "fullSync": True},
                    }
                },
            },
        )
        if status != 201:
            raise ValidationError(f"provider session creation returned HTTP {status}")
        _wait_for_qr(base_url)

        json_status, json_type, _ = _request(
            f"{base_url}/api/{SESSION_NAME}/auth/qr?format=image",
            accept="application/json",
            read_body=False,
        )
        if (json_status, json_type) != (200, "application/json"):
            raise ValidationError(
                "certified JSON negotiation baseline drifted: "
                f"status={json_status}, content_type={json_type!r}"
            )

        size = asyncio.run(_exercise_repository_client(base_url))
        status, sessions_type, sessions_body = _request(f"{base_url}/api/sessions")
        if status != 200 or "json" not in sessions_type:
            raise ValidationError("provider session inventory is unavailable")
        try:
            sessions = json.loads(sessions_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("provider session inventory is malformed") from exc
        if not isinstance(sessions, list):
            raise ValidationError("provider session inventory has an unexpected shape")
        if len(sessions) != 1:
            raise ValidationError("QR retrieval created a duplicate provider session")

        print("WAHA QR content-negotiation runtime gate passed")
        print("  image: certified sha256:33ecd1b7...f2d75e")
        print("  provider: 2026.7.2 / NOWEB / CORE")
        print("  JSON Accept: HTTP 200 application/json (baseline reproduced)")
        print(f"  image Accept: HTTP 200 image/png ({size} bytes, body withheld)")
        print("  authentication: provider API key sent; value never logged")
        print("  session count: exactly one; no duplicate created")
        print("  QR: held in memory only; not displayed, persisted, logged, or scanned")
        return 0
    finally:
        if started:
            inspect = _run([docker, "inspect", container], check=False)
            if inspect.returncode == 0:
                info = json.loads(inspect.stdout)[0]
                labels = info.get("Config", {}).get("Labels", {}) or {}
                if labels.get(LABEL_KEY) == LABEL_VALUE:
                    _run([docker, "rm", "-f", container], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
