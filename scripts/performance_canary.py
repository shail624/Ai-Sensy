"""Bounded deployed-stack API latency canary for the frozen standard-read target."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import httpx


def percentile(values: list[float], fraction: float) -> float:
    """Return the nearest-rank percentile, which keeps the blocking rule auditable."""
    if not values:
        raise ValueError("at least one observation is required")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "mfa_code": None},
    )
    response.raise_for_status()
    payload: Any = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise RuntimeError("login response did not contain an access token")
    return payload["access_token"]


def run_canary(
    *,
    base_url: str,
    email: str,
    password: str,
    samples: int,
    warmup: int,
    threshold_ms: float,
    output: Path,
) -> int:
    timings: list[float] = []
    with httpx.Client(base_url=base_url, timeout=10.0, trust_env=False) as client:
        for path in ("/health", "/ready"):
            response = client.get(path)
            response.raise_for_status()
        token = login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        for index in range(warmup + samples):
            started = time.perf_counter()
            response = client.get("/api/v1/contacts", headers=headers)
            elapsed_ms = (time.perf_counter() - started) * 1_000
            response.raise_for_status()
            if index >= warmup:
                timings.append(elapsed_ms)

    p95_ms = percentile(timings, 0.95)
    evidence = {
        "endpoint": "GET /api/v1/contacts",
        "samples": samples,
        "warmup": warmup,
        "threshold_p95_ms": threshold_ms,
        "observed_p50_ms": round(percentile(timings, 0.50), 3),
        "observed_p95_ms": round(p95_ms, 3),
        "observed_max_ms": round(max(timings), 3),
        "passed": p95_ms < threshold_ms,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        f"performance canary: p95={p95_ms:.1f}ms across {samples} reads "
        f"(budget < {threshold_ms:.1f}ms)"
    )
    return 0 if p95_ms < threshold_ms else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--threshold-ms", type=float, default=300.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 20 or args.warmup < 1:
        parser.error("the canary requires at least 20 samples and one warmup request")
    return run_canary(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        samples=args.samples,
        warmup=args.warmup,
        threshold_ms=args.threshold_ms,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
