"""Execute the contract's read surface against a running API, on its real database.

The pytest suite runs on SQLite. MySQL 8 disagrees with SQLite in ways that only appear when a
statement actually executes: ``ONLY_FULL_GROUP_BY`` is on by default in MySQL and absent in SQLite,
the date/time and JSON function sets differ, and ``FILTER (WHERE ...)`` has no MySQL equivalent. A
query that is wrong for MySQL therefore passes every hermetic test and fails the first time a real
operator opens the page. This sweep is the gate that closes that gap: it asks a running server,
backed by the database it will actually use, for every read the contract declares.

Two rules keep it bounded and meaningful:

- **Only parameterless paths.** A path with ``{id}`` needs a row that exists, which is the pytest
  suite's job; inventing ids here would test the 404 handler, not the query.
- **Only operator reads.** ``/webhooks/`` is excluded: its GET is the provider's own verification
  handshake, not a read of the operator's data, and it answers 503 until that provider is
  configured. Sweeping it would report an unconfigured optional integration as a broken query.
- **Every declared choice, once.** For each enum-valued query parameter the endpoint declares, the
  path is requested once per enum value with the other parameters left at their defaults. That
  exercises each documented branch -- a granularity that only breaks on ``month``, say -- without
  the combinatorial explosion of crossing every parameter with every other.

Each request is also timed, and the evidence records the slowest paths. A query that costs what
the *account* weighs rather than what the *page* weighs is invisible on an empty database and easy
to write by accident (PERF-01 was exactly that), so the sweep is the natural place to notice it:
run it against an account with real volume and the offenders sort themselves to the top.

Only a 5xx or a transport error fails the gate. A 400, 403, 404 or 422 means the endpoint ran and
answered; refusing an unbounded date range is correct behaviour, not a defect. Endpoints that
declare a date ``preset`` are given one, so the aggregate query underneath really executes rather
than being turned away at validation.

A path whose required query parameters are free-form -- a ``dimension`` string, a ``metrics``
array -- cannot be called from the contract alone, because the contract does not enumerate the
values those accept. Such a path is reported under ``not_exercised`` rather than counted as
answered: its 422 proves validation works, not that the query underneath is sound, and reporting
it as a pass would be the exact false comfort this gate exists to remove.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

#: Supplied to any endpoint that declares it, so date-bounded aggregates execute instead of being
#: refused at validation. Overridden per-request when ``preset`` is the enum being swept.
DEFAULT_PRESET = "last_30d"

#: Provider callback namespace. Its GET is Meta's verification handshake, which answers 503 until
#: that optional provider is configured -- an unconfigured integration, never a broken read.
EXCLUDED_PREFIX = "/api/v1/webhooks/"


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "mfa_code": None},
    )
    response.raise_for_status()
    payload: Any = response.json()
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str):
        raise RuntimeError("login response did not contain an access token")
    return token


def _enum_values(schema: dict[str, Any]) -> list[Any]:
    """The choices a parameter declares, looking through the ``anyOf`` that optionality adds."""
    if isinstance(schema.get("enum"), list):
        return [value for value in schema["enum"] if value is not None]
    for branch in schema.get("anyOf", ()):
        if isinstance(branch, dict) and isinstance(branch.get("enum"), list):
            return [value for value in branch["enum"] if value is not None]
    return []


def plan_requests(spec: dict[str, Any]) -> tuple[list[tuple[str, dict[str, str]]], list[str]]:
    """One request per parameterless GET, plus one per declared enum choice on it.

    Returns the planned requests and, separately, the paths that cannot be exercised from the
    contract alone because they require a parameter whose accepted values it does not enumerate.
    """
    planned: list[tuple[str, dict[str, str]]] = []
    not_exercised: list[str] = []
    for path, operations in sorted(spec.get("paths", {}).items()):
        operation = operations.get("get")
        if operation is None or "{" in path or path.startswith(EXCLUDED_PREFIX):
            continue
        parameters = [p for p in operation.get("parameters", ()) if p.get("in") == "query"]
        names = {p.get("name") for p in parameters}
        if any(
            p.get("required") and not _enum_values(p.get("schema", {}))
            for p in parameters
        ):
            not_exercised.append(path)
            continue
        base: dict[str, str] = {"preset": DEFAULT_PRESET} if "preset" in names else {}
        planned.append((path, dict(base)))
        for parameter in parameters:
            name = parameter.get("name")
            for value in _enum_values(parameter.get("schema", {})):
                planned.append((path, {**base, str(name): str(value)}))
    return planned, not_exercised


def run_sweep(*, base_url: str, email: str, password: str, spec_path: Path, output: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    planned, not_exercised = plan_requests(spec)

    failures: list[dict[str, Any]] = []
    statuses: dict[int, int] = {}
    slowest: dict[str, float] = {}
    with httpx.Client(base_url=base_url, timeout=60.0, trust_env=False) as client:
        headers = {"Authorization": f"Bearer {login(client, email, password)}"}
        for path, params in planned:
            url = f"{path}?{urlencode(params)}" if params else path
            started = time.perf_counter()
            try:
                response = client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                failures.append({"path": path, "params": params, "error": repr(exc)[:400]})
                continue
            elapsed_ms = (time.perf_counter() - started) * 1_000
            slowest[path] = max(slowest.get(path, 0.0), elapsed_ms)
            statuses[response.status_code] = statuses.get(response.status_code, 0) + 1
            if response.status_code >= 500:
                failures.append(
                    {
                        "path": path,
                        "params": params,
                        "status": response.status_code,
                        "body": response.text[:400],
                    }
                )

    paths_swept = len({path for path, _ in planned})
    evidence = {
        "spec": str(spec_path),
        "paths_swept": paths_swept,
        "requests_issued": len(planned),
        "status_counts": {str(code): count for code, count in sorted(statuses.items())},
        "not_exercised": not_exercised,
        # Worst observed time per path, slowest first. Not a budget -- one warm request on one
        # container is not a performance test -- but a cheap way to see which reads grow with the
        # data rather than with the page.
        "slowest_ms": {
            path: round(ms, 1)
            for path, ms in sorted(slowest.items(), key=lambda item: -item[1])[:10]
        },
        "failures": failures,
        "passed": not failures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    print(
        f"live API read sweep: {len(planned)} requests across {paths_swept} parameterless GET paths"
    )
    for failure in failures:
        print(f"  FAIL {failure['path']} {failure.get('status', failure.get('error'))}")
    print(f"  {len(planned) - len(failures)} answered, {len(failures)} returned 5xx or raised")
    for path in not_exercised:
        print(f"  NOT EXERCISED {path} (requires a parameter the contract does not enumerate)")
    for path, ms in sorted(slowest.items(), key=lambda item: -item[1])[:3]:
        print(f"  slowest: {ms:7.1f} ms  {path}")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "frontend" / "openapi.json",
        help="The canonical exported contract; the sweep covers exactly what it declares.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return run_sweep(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        spec_path=args.spec,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
