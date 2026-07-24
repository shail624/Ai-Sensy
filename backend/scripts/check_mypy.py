"""Enforce a strict-mypy debt ratchet without weakening ``pyproject.toml``.

The checked-in baseline records allowances by normalized source path and mypy error code. The
normal check requires an exact match: increases are regressions, while decreases make the baseline
stale until it is explicitly lowered. The exact mypy version is part of the baseline so a checker
upgrade cannot silently reinterpret the debt.

Run from the ``backend`` directory::

    .venv/Scripts/python.exe scripts/check_mypy.py
    .venv/Scripts/python.exe scripts/check_mypy.py --write-baseline

Writing is always explicit. Review and commit ``mypy-baseline.json`` after establishing a baseline
or intentionally upgrading mypy; ordinary checks never modify it.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASELINE_PATH = BACKEND_DIR / "mypy-baseline.json"
FORMAT_VERSION = 1

Counts = dict[str, dict[str, int]]
Delta = tuple[str, str, int, int]

_ERROR_LINE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::\d+)?: error: .* \[(?P<code>[^\[\]]+)\]\s*$"
)


class RatchetError(RuntimeError):
    """The ratchet could not run or its baseline is invalid."""


@dataclass(frozen=True)
class Baseline:
    """Validated on-disk baseline."""

    mypy_version: str
    errors: Counts


def normalize_path(raw_path: str) -> str:
    """Return a stable ``app/...`` path for mypy output from Windows or Linux."""
    normalized = posixpath.normpath(raw_path.strip().replace("\\", "/"))
    backend = posixpath.normpath(str(BACKEND_DIR.resolve()).replace("\\", "/"))

    if normalized.casefold().startswith(f"{backend.casefold()}/"):
        normalized = normalized[len(backend) + 1 :]

    normalized = normalized.removeprefix("./")
    if normalized != "app" and not normalized.startswith("app/"):
        marker = normalized.casefold().rfind("/app/")
        if marker >= 0:
            normalized = normalized[marker + 1 :]
    return normalized


def _canonical_counts(counts: Mapping[str, Mapping[str, int]]) -> Counts:
    canonical: Counts = {}
    for raw_path, codes in counts.items():
        path = normalize_path(raw_path)
        target = canonical.setdefault(path, {})
        for code, count in codes.items():
            target[code] = target.get(code, 0) + count
    return {
        path: {code: canonical[path][code] for code in sorted(canonical[path])}
        for path in sorted(canonical)
    }


def parse_mypy_output(output: str) -> Counts:
    """Count coded mypy diagnostics, rejecting error lines that cannot be ratcheted."""
    counts: Counts = {}
    unparsed: list[str] = []
    for line in output.splitlines():
        if ": error:" not in line:
            continue
        match = _ERROR_LINE.match(line)
        if match is None:
            unparsed.append(line)
            continue
        path = normalize_path(match.group("path"))
        code = match.group("code").strip()
        by_code = counts.setdefault(path, {})
        by_code[code] = by_code.get(code, 0) + 1

    if unparsed:
        sample = "\n".join(f"  {line}" for line in unparsed[:3])
        raise RatchetError(
            "mypy emitted error diagnostics without parseable error codes; "
            f"the ratchet refuses to ignore them:\n{sample}"
        )
    return _canonical_counts(counts)


def installed_mypy_version() -> str:
    """Return the exact installed checker version used for this run."""
    try:
        return version("mypy")
    except PackageNotFoundError as exc:  # pragma: no cover - depends on developer environment
        raise RatchetError("mypy is not installed; install the backend dev dependencies") from exc


def run_mypy() -> Counts:
    """Run strict mypy using the repository configuration and return normalized counts."""
    command = [
        sys.executable,
        "-m",
        "mypy",
        "--config-file",
        str(BACKEND_DIR / "pyproject.toml"),
        "--show-error-codes",
        "--no-pretty",
        "--no-color-output",
        "--no-error-summary",
        "app",
    ]
    completed = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode not in {0, 1}:
        detail = completed.stdout.strip() or "no output"
        raise RatchetError(f"mypy failed to execute (exit {completed.returncode}):\n{detail}")

    counts = parse_mypy_output(completed.stdout)
    if completed.returncode == 1 and not counts:
        raise RatchetError(
            "mypy reported failure but emitted no coded diagnostics; refusing an empty comparison"
        )
    return counts


def _validate_counts(raw_errors: object, *, source: Path) -> Counts:
    if not isinstance(raw_errors, dict):
        raise RatchetError(f"invalid mypy baseline {source}: 'errors' must be an object")

    validated: Counts = {}
    for path, raw_codes in raw_errors.items():
        if not isinstance(path, str) or not path:
            raise RatchetError(f"invalid mypy baseline {source}: every path must be a string")
        if path != normalize_path(path):
            raise RatchetError(
                f"invalid mypy baseline {source}: path is not normalized: {path!r}"
            )
        if not isinstance(raw_codes, dict) or not raw_codes:
            raise RatchetError(
                f"invalid mypy baseline {source}: {path!r} must contain error-code counts"
            )
        codes: dict[str, int] = {}
        for code, count in raw_codes.items():
            if not isinstance(code, str) or not code:
                raise RatchetError(
                    f"invalid mypy baseline {source}: every error code must be a string"
                )
            if type(count) is not int or count <= 0:
                raise RatchetError(
                    f"invalid mypy baseline {source}: {path} [{code}] must be a positive integer"
                )
            codes[code] = count
        validated[path] = codes
    return _canonical_counts(validated)


def load_baseline(path: Path | None = None) -> Baseline:
    """Load and validate the checked-in JSON baseline."""
    path = path or BASELINE_PATH
    if not path.exists():
        raise RatchetError(
            f"mypy baseline is missing ({path}); establish it explicitly with --write-baseline"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RatchetError(f"cannot read mypy baseline {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise RatchetError(f"invalid mypy baseline {path}: root must be an object")
    if document.get("format_version") != FORMAT_VERSION:
        raise RatchetError(
            f"unsupported mypy baseline format in {path}: "
            f"expected {FORMAT_VERSION}, got {document.get('format_version')!r}"
        )
    mypy_version = document.get("mypy_version")
    if not isinstance(mypy_version, str) or not mypy_version:
        raise RatchetError(f"invalid mypy baseline {path}: 'mypy_version' must be a string")
    return Baseline(
        mypy_version=mypy_version,
        errors=_validate_counts(document.get("errors"), source=path),
    )


def write_baseline(
    counts: Mapping[str, Mapping[str, int]],
    *,
    mypy_version: str,
    path: Path | None = None,
) -> None:
    """Write a canonical baseline after the caller explicitly requested it."""
    path = path or BASELINE_PATH
    document = {
        "format_version": FORMAT_VERSION,
        "mypy_version": mypy_version,
        "errors": _canonical_counts(counts),
    }
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def compare_counts(
    baseline: Mapping[str, Mapping[str, int]],
    current: Mapping[str, Mapping[str, int]],
) -> tuple[list[Delta], list[Delta]]:
    """Return ``(increases, decreases)`` sorted by path and error code."""
    expected = _canonical_counts(baseline)
    actual = _canonical_counts(current)
    keys = sorted(
        {(path, code) for path, codes in expected.items() for code in codes}
        | {(path, code) for path, codes in actual.items() for code in codes}
    )
    increases: list[Delta] = []
    decreases: list[Delta] = []
    for path, code in keys:
        before = expected.get(path, {}).get(code, 0)
        after = actual.get(path, {}).get(code, 0)
        delta = (path, code, before, after)
        if after > before:
            increases.append(delta)
        elif after < before:
            decreases.append(delta)
    return increases, decreases


def _total(counts: Mapping[str, Mapping[str, int]]) -> int:
    return sum(sum(codes.values()) for codes in counts.values())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help=f"explicitly lower {BASELINE_PATH.name} to the current strict-mypy counts",
    )
    parser.add_argument(
        "--allow-version-change",
        action="store_true",
        help="allow --write-baseline to replace findings after a reviewed mypy upgrade",
    )
    args = parser.parse_args(argv)

    try:
        if args.allow_version_change and not args.write_baseline:
            raise RatchetError("--allow-version-change requires --write-baseline")

        current_version = installed_mypy_version()
        if args.write_baseline:
            current = run_mypy()
            if BASELINE_PATH.exists():
                baseline = load_baseline()
                if baseline.mypy_version != current_version:
                    if not args.allow_version_change:
                        raise RatchetError(
                            "writing a baseline for mypy "
                            f"{current_version} over {baseline.mypy_version} requires "
                            "--allow-version-change and review of the full baseline diff"
                        )
                else:
                    increases, _ = compare_counts(baseline.errors, current)
                    if increases:
                        print(
                            "mypy ratchet REFUSED: a same-version baseline write cannot "
                            "increase allowances",
                            file=sys.stderr,
                        )
                        for path, code, before, after in increases:
                            print(
                                f"  {path} [{code}]: {before} -> {after}",
                                file=sys.stderr,
                            )
                        return 1
            write_baseline(current, mypy_version=current_version)
            print(
                f"wrote {BASELINE_PATH} ({_total(current)} findings, mypy {current_version})"
            )
            return 0

        baseline = load_baseline()
        if baseline.mypy_version != current_version:
            raise RatchetError(
                "mypy version mismatch: baseline uses "
                f"{baseline.mypy_version}, installed version is {current_version}. "
                "Install the baseline version or review the checker upgrade and run "
                "--write-baseline --allow-version-change explicitly."
            )

        current = run_mypy()
        increases, decreases = compare_counts(baseline.errors, current)
        if increases:
            print(
                "mypy ratchet FAILED: new or increased findings "
                f"(current {_total(current)}; baseline {_total(baseline.errors)}; "
                f"mypy {current_version})",
                file=sys.stderr,
            )
            for path, code, before, after in increases:
                print(f"  {path} [{code}]: {before} -> {after}", file=sys.stderr)
            return 1

        if decreases:
            reduction = _total(baseline.errors) - _total(current)
            print(
                "mypy ratchet STALE: findings decreased by "
                f"{reduction} (current {_total(current)}; baseline "
                f"{_total(baseline.errors)}; mypy {current_version}); lower the checked-in "
                "baseline with --write-baseline",
                file=sys.stderr,
            )
            for path, code, before, after in decreases:
                print(f"  {path} [{code}]: {before} -> {after}", file=sys.stderr)
            return 1

        print(
            f"mypy ratchet passed ({_total(current)} findings; baseline "
            f"{_total(baseline.errors)}; mypy {current_version})"
        )
        return 0
    except RatchetError as exc:
        print(f"mypy ratchet ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
