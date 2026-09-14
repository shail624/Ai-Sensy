"""Validate QR-09C's WAHA signed-webhook wiring against the certified image.

This gate does not create a WAHA session, request/display a QR code, pair a handset, or touch the
repository's persistent ``waha-sessions`` volume. It renders both Compose models with synthetic
credentials, then starts the exact certified image and an isolated private callback receiver. The
provider's own ``WebhookSender`` implementation generates the request and HMAC; the test never
manufactures a provider signature in repository code.

Because WAHA has no unpaired webhook-test API, invoking its shipped sender is the narrowest runtime
proof available before physical pairing. It proves image executability, private-network callback
reachability, raw-body SHA-512 signing, retry behavior, and restart-time environment persistence.
The already-governed backend tests separately prove rejection, ingest and dedupe semantics.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_COMPOSE = ROOT / "docker-compose.yml"
PRODUCTION_COMPOSE = ROOT / "docker-compose.production.yml"
CERTIFIED_IMAGE = (
    "devlikeapro/waha@"
    "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
)
CERTIFIED_IMAGE_ID = "sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e"
RECEIVER_IMAGE = (
    "python:3.13.14-alpine3.24@"
    "sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
)
CALLBACK_PATH = "/api/v1/webhooks/waha"
DEVELOPMENT_CALLBACK = f"http://host.docker.internal:8000{CALLBACK_PATH}"
PRODUCTION_CALLBACK = f"http://api:8000{CALLBACK_PATH}"
EVENTS = "message,message.any,message.ack"
RETRY_POLICY = "constant"
RETRY_DELAY_SECONDS = "2"
RETRY_ATTEMPTS = "15"

# Test-only sentinels. They never come from, replace, or inspect a deployment credential.
SYNTHETIC_HMAC = "qr09c-synthetic-waha-hmac-only"
SYNTHETIC_API_KEY = "qr09c-synthetic-waha-api-key"
SYNTHETIC_META_TOKEN = "qr09c-synthetic-meta-token-not-reused"

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
    "WAHA_WEBHOOK_HMAC_SECRET",
)

RECEIVER_PROGRAM = r"""
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {
    "attempts": 0,
    "valid_hmac": [],
    "algorithms": [],
    "request_ids": [],
    "body_hashes": [],
    "events": [],
    "paths": [],
    "user_agents": [],
}
SECRET = os.environ["PROBE_HMAC_SECRET"].encode()
STATE_PATH = "/tmp/qr09c-receiver-state.json"


def persist():
    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(STATE, handle, sort_keys=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        expected = hmac.new(SECRET, body, hashlib.sha512).hexdigest()
        STATE["attempts"] += 1
        STATE["valid_hmac"].append(
            hmac.compare_digest(expected, self.headers.get("X-Webhook-Hmac", ""))
        )
        STATE["algorithms"].append(self.headers.get("X-Webhook-Hmac-Algorithm"))
        STATE["request_ids"].append(self.headers.get("X-Webhook-Request-Id"))
        STATE["body_hashes"].append(hashlib.sha256(body).hexdigest())
        STATE["paths"].append(self.path)
        STATE["user_agents"].append(self.headers.get("User-Agent"))
        try:
            STATE["events"].append(json.loads(body).get("event"))
        except (ValueError, AttributeError):
            STATE["events"].append(None)
        persist()

        # One deterministic 503 proves the certified sender retries. Every later request succeeds.
        status = 503 if STATE["attempts"] == 1 else 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, _format, *args):
        return


persist()
ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
"""

SENDER_PROGRAM = r"""
const { WebhookSender } = require('/app/dist/core/integrations/webhooks/WebhookSender.js');
const logger = {
  child() { return this; },
  info() {}, debug() {}, warn() {}, error() {},
};
const sender = new WebhookSender(logger, {
  url: process.env.WHATSAPP_HOOK_URL,
  hmac: { key: process.env.WHATSAPP_HOOK_HMAC_KEY },
  retries: {
    policy: process.env.WHATSAPP_HOOK_RETRIES_POLICY,
    delaySeconds: Number(process.env.WHATSAPP_HOOK_RETRIES_DELAY_SECONDS),
    attempts: Number(process.env.WHATSAPP_HOOK_RETRIES_ATTEMPTS),
  },
});
sender.send({
  id: process.env.QR09C_EVENT_ID,
  timestamp: 1786233600000,
  event: process.env.QR09C_EVENT_NAME,
  session: 'qr09c-unpaired-runtime',
  payload: { fromMe: false, body: 'QR09C_RUNTIME_PROBE' },
  engine: 'NOWEB',
  environment: { version: '2026.7.2' },
});
setTimeout(() => process.exit(0), 7000);
"""


class ValidationError(RuntimeError):
    """A required runtime or deployment invariant did not hold."""


def _run(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: float | None = 30.0,
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
        timeout=timeout,
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


def _model_env(*, production: bool) -> dict[str, str]:
    env = os.environ.copy()
    env["WAHA_WEBHOOK_HMAC_SECRET"] = SYNTHETIC_HMAC
    env["WAHA_API_KEY"] = SYNTHETIC_API_KEY
    if production:
        for name in PRODUCTION_SENTINELS:
            if name == "WAHA_WEBHOOK_HMAC_SECRET":
                env[name] = SYNTHETIC_HMAC
            elif name == "WAHA_API_KEY":
                env[name] = SYNTHETIC_API_KEY
            elif name == "META_WEBHOOK_VERIFY_TOKEN":
                env[name] = SYNTHETIC_META_TOKEN
            elif not env.get(name):
                env[name] = f"qr09c-synthetic-{name.lower().replace('_', '-')}"
    return env


def _compose_model(docker: str, path: Path, *, production: bool) -> dict[str, Any]:
    result = _run(
        [
            docker,
            "compose",
            "-f",
            os.fspath(path),
            "--profile",
            "waha",
            "config",
            "--format",
            "json",
        ],
        env=_model_env(production=production),
    )
    model = json.loads(result.stdout)
    if not isinstance(model, dict):
        raise ValidationError("Compose returned a non-object model")
    return model


def _environment(service: dict[str, Any]) -> dict[str, str]:
    raw = service.get("environment")
    if not isinstance(raw, dict):
        raise ValidationError("WAHA has no rendered environment")
    return {str(key): str(value) for key, value in raw.items()}


def _assert_compose_model(model: dict[str, Any], *, production: bool) -> None:
    services = model.get("services")
    if not isinstance(services, dict) or not isinstance(services.get("waha"), dict):
        raise ValidationError("the waha profile did not resolve a WAHA service")
    waha = services["waha"]
    if waha.get("image") != CERTIFIED_IMAGE:
        raise ValidationError("WAHA image drifted from the certified digest")
    env = _environment(waha)
    expected = {
        "WHATSAPP_HOOK_URL": PRODUCTION_CALLBACK if production else DEVELOPMENT_CALLBACK,
        "WHATSAPP_HOOK_EVENTS": EVENTS,
        "WHATSAPP_HOOK_HMAC_KEY": SYNTHETIC_HMAC,
        "WHATSAPP_HOOK_RETRIES_POLICY": RETRY_POLICY,
        "WHATSAPP_HOOK_RETRIES_DELAY_SECONDS": RETRY_DELAY_SECONDS,
        "WHATSAPP_HOOK_RETRIES_ATTEMPTS": RETRY_ATTEMPTS,
    }
    for name, value in expected.items():
        if env.get(name) != value:
            raise ValidationError(f"rendered {name} does not match the governed webhook contract")
    if env["WHATSAPP_HOOK_HMAC_KEY"] == SYNTHETIC_META_TOKEN:
        raise ValidationError("WAHA HMAC reused the Meta verification-token sentinel")

    volumes = waha.get("volumes", [])
    if not any(
        isinstance(item, dict)
        and item.get("source") == "waha-sessions"
        and item.get("target") == "/app/.sessions"
        for item in volumes
    ):
        raise ValidationError("persistent WAHA session volume changed")

    ports = waha.get("ports", [])
    if production:
        if ports:
            raise ValidationError("production WAHA unexpectedly publishes a port")
        api = services.get("api")
        if not isinstance(api, dict):
            raise ValidationError("production model has no API service for the internal callback")
        if _environment(api).get("WAHA_WEBHOOK_HMAC_SECRET") != SYNTHETIC_HMAC:
            raise ValidationError("WAHA sender and backend verifier do not receive the same secret")
        waha_networks = set((waha.get("networks") or {}).keys())
        api_networks = set((api.get("networks") or {}).keys())
        if not (waha_networks & api_networks):
            raise ValidationError("WAHA and API do not share an internal Compose network")
    else:
        if not any(
            isinstance(item, dict)
            and item.get("host_ip") == "127.0.0.1"
            and int(item.get("target", 0)) == 3000
            for item in ports
        ):
            raise ValidationError("development WAHA is not loopback-only")
        extra_hosts = json.dumps(waha.get("extra_hosts", {}), sort_keys=True)
        if "host.docker.internal" not in extra_hosts or "host-gateway" not in extra_hosts:
            raise ValidationError("development callback has no host-gateway route")


def _wait_for_ping(docker: str, container: str, *, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _run(
            [
                docker,
                "exec",
                container,
                "curl",
                "--fail",
                "--silent",
                "--max-time",
                "3",
                "http://127.0.0.1:3000/ping",
            ],
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise ValidationError("certified WAHA container did not become responsive")


def _wait_receiver(docker: str, container: str, *, attempts: int, timeout: float = 15.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        result = _run(
            [
                docker,
                "exec",
                container,
                "python",
                "-c",
                "import pathlib; print(pathlib.Path('/tmp/qr09c-receiver-state.json').read_text())",
            ],
            check=False,
        )
        if result.returncode == 0:
            last = json.loads(result.stdout)
            if int(last.get("attempts", 0)) >= attempts:
                return last
        time.sleep(0.25)
    raise ValidationError(f"receiver observed {last.get('attempts', 0)} of {attempts} expected requests")


def _runtime_env() -> list[str]:
    return [
        "--env",
        "WHATSAPP_DEFAULT_ENGINE=NOWEB",
        "--env",
        f"WAHA_API_KEY={SYNTHETIC_API_KEY}",
        "--env",
        f"WHATSAPP_API_KEY={SYNTHETIC_API_KEY}",
        "--env",
        f"WHATSAPP_HOOK_URL={PRODUCTION_CALLBACK}",
        "--env",
        f"WHATSAPP_HOOK_EVENTS={EVENTS}",
        "--env",
        f"WHATSAPP_HOOK_HMAC_KEY={SYNTHETIC_HMAC}",
        "--env",
        f"WHATSAPP_HOOK_RETRIES_POLICY={RETRY_POLICY}",
        "--env",
        f"WHATSAPP_HOOK_RETRIES_DELAY_SECONDS={RETRY_DELAY_SECONDS}",
        "--env",
        f"WHATSAPP_HOOK_RETRIES_ATTEMPTS={RETRY_ATTEMPTS}",
    ]


def _assert_runtime_environment(docker: str, container: str) -> None:
    info = json.loads(_run([docker, "inspect", container]).stdout)[0]
    if info.get("Image") != CERTIFIED_IMAGE_ID:
        raise ValidationError("runtime image id is not the certified digest")
    env = dict(item.split("=", 1) for item in info.get("Config", {}).get("Env", []) if "=" in item)
    expected = {
        "WHATSAPP_HOOK_URL": PRODUCTION_CALLBACK,
        "WHATSAPP_HOOK_EVENTS": EVENTS,
        "WHATSAPP_HOOK_HMAC_KEY": SYNTHETIC_HMAC,
        "WHATSAPP_HOOK_RETRIES_POLICY": RETRY_POLICY,
        "WHATSAPP_HOOK_RETRIES_DELAY_SECONDS": RETRY_DELAY_SECONDS,
        "WHATSAPP_HOOK_RETRIES_ATTEMPTS": RETRY_ATTEMPTS,
    }
    if any(env.get(name) != value for name, value in expected.items()):
        raise ValidationError("runtime webhook environment drifted from the Compose contract")


def _provider_json(docker: str, container: str, path: str) -> Any:
    result = _run(
        [
            docker,
            "exec",
            container,
            "curl",
            "--fail",
            "--silent",
            "--max-time",
            "5",
            "--header",
            f"X-Api-Key: {SYNTHETIC_API_KEY}",
            f"http://127.0.0.1:3000{path}",
        ]
    )
    return json.loads(result.stdout)


def _send(docker: str, container: str, *, event_id: str, event_name: str) -> None:
    _run(
        [
            docker,
            "exec",
            "--env",
            f"QR09C_EVENT_ID={event_id}",
            "--env",
            f"QR09C_EVENT_NAME={event_name}",
            container,
            "node",
            "-e",
            SENDER_PROGRAM,
        ],
        timeout=15.0,
    )


def _assert_first_delivery(state: dict[str, Any]) -> None:
    if state.get("attempts") != 2:
        raise ValidationError("one controlled 503 did not produce exactly one retry")
    if state.get("valid_hmac") != [True, True]:
        raise ValidationError("certified sender did not produce valid raw-body SHA-512 HMACs")
    if state.get("algorithms") != ["sha512", "sha512"]:
        raise ValidationError("certified sender did not declare sha512")
    if state.get("paths") != [CALLBACK_PATH, CALLBACK_PATH]:
        raise ValidationError("provider did not reach the governed backend callback path")
    if state.get("events") != ["message", "message"]:
        raise ValidationError("provider retry changed the event body")
    if len(set(state.get("body_hashes", []))) != 1:
        raise ValidationError("provider retry changed the signed raw body")
    request_ids = state.get("request_ids", [])
    if len(request_ids) != 2 or not request_ids[0] or len(set(request_ids)) != 1:
        raise ValidationError("provider retry did not preserve its request identity")
    if state.get("user_agents") != ["WAHA/2026.7.2", "WAHA/2026.7.2"]:
        raise ValidationError("runtime sender identity drifted")


def _assert_after_restart(state: dict[str, Any]) -> None:
    if state.get("attempts") != 3:
        raise ValidationError("post-restart delivery did not reach the receiver")
    if state.get("valid_hmac") != [True, True, True]:
        raise ValidationError("post-restart delivery lost signed-webhook configuration")
    if state.get("events", [])[-1:] != ["message.ack"]:
        raise ValidationError("post-restart ACK delivery was not observed")
    request_ids = state.get("request_ids", [])
    if len(request_ids) != 3 or request_ids[2] == request_ids[0]:
        raise ValidationError("a new post-restart delivery did not get a new request identity")


def main() -> int:
    if SYNTHETIC_HMAC == SYNTHETIC_META_TOKEN:
        raise ValidationError("test sentinels must model separate WAHA and Meta credentials")
    docker = _docker()
    _assert_compose_model(
        _compose_model(docker, DEVELOPMENT_COMPOSE, production=False), production=False
    )
    _assert_compose_model(
        _compose_model(docker, PRODUCTION_COMPOSE, production=True), production=True
    )

    suffix = secrets.token_hex(4)
    prefix = f"qr09c-webhook-{suffix}"
    network = f"{prefix}-network"
    receiver = f"{prefix}-api"
    provider = f"{prefix}-waha"
    volume = f"{prefix}-sessions"
    created: list[tuple[str, str]] = []
    try:
        _run([docker, "network", "create", network])
        created.append(("network", network))
        _run([docker, "volume", "create", volume])
        created.append(("volume", volume))
        _run(
            [
                docker,
                "run",
                "--detach",
                "--name",
                receiver,
                "--network",
                network,
                "--network-alias",
                "api",
                "--env",
                f"PROBE_HMAC_SECRET={SYNTHETIC_HMAC}",
                "--entrypoint",
                "python",
                RECEIVER_IMAGE,
                "-c",
                RECEIVER_PROGRAM,
            ]
        )
        created.append(("container", receiver))
        _wait_receiver(docker, receiver, attempts=0)

        _run(
            [
                docker,
                "run",
                "--detach",
                "--name",
                provider,
                "--network",
                network,
                "--mount",
                f"type=volume,source={volume},target=/app/.sessions",
                *_runtime_env(),
                CERTIFIED_IMAGE,
            ],
            timeout=60.0,
        )
        created.append(("container", provider))
        _wait_for_ping(docker, provider)
        _assert_runtime_environment(docker, provider)

        version = _provider_json(docker, provider, "/api/server/version")
        observed = (version.get("version"), version.get("engine"), version.get("tier"))
        if observed != ("2026.7.2", "NOWEB", "CORE"):
            raise ValidationError(f"provider identity drifted: {observed!r}")
        if _provider_json(docker, provider, "/api/sessions") != []:
            raise ValidationError("runtime gate must never operate on a created or paired session")

        _send(docker, provider, event_id="qr09c-runtime-message", event_name="message")
        _assert_first_delivery(_wait_receiver(docker, receiver, attempts=2))

        _run([docker, "restart", provider], timeout=60.0)
        _wait_for_ping(docker, provider)
        _assert_runtime_environment(docker, provider)
        if _provider_json(docker, provider, "/api/sessions") != []:
            raise ValidationError("provider restart unexpectedly created a session")
        _send(docker, provider, event_id="qr09c-runtime-ack", event_name="message.ack")
        _assert_after_restart(_wait_receiver(docker, receiver, attempts=3))

        print("WAHA signed-webhook runtime gate passed")
        print("  image: certified sha256:33ecd1b7...f2d75e")
        print("  provider: 2026.7.2 / NOWEB / CORE")
        print("  callback: private api:8000 route reachable")
        print("  signature: provider-generated raw-body SHA-512 HMAC verified")
        print("  subscriptions: message, message.any, message.ack only")
        print("  retry: one 503 produced one byte-identical retry with stable request id")
        print("  restart: global config and signed ACK delivery preserved")
        print("  sessions/QR/phone: none created, displayed, scanned, or paired")
        return 0
    finally:
        # Delete only disposable resources this invocation named and created. Never touch a
        # repository, developer, production or anonymous session volume.
        for kind, name in reversed(created):
            if not name.startswith(prefix):
                raise ValidationError("refusing cleanup outside this gate's isolated prefix")
            if kind == "container":
                _run([docker, "rm", "--force", name], check=False)
            elif kind == "volume":
                _run([docker, "volume", "rm", name], check=False)
            elif kind == "network":
                _run([docker, "network", "rm", name], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
