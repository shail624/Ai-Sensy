"""Focused tests for the strict-mypy debt ratchet."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts import check_mypy


def test_parse_mypy_output_normalizes_windows_and_linux_paths() -> None:
    output = "\n".join(
        (
            r"app\services\example.py:10: error: First issue  [arg-type]",
            "/workspace/project/backend/app/services/example.py:11: error: Again  [arg-type]",
            r"C:\workspace\backend\app\models\item.py:12:3: error: Bare generic  [type-arg]",
            "Found 3 errors in 2 files (checked 226 source files)",
        )
    )

    assert check_mypy.parse_mypy_output(output) == {
        "app/models/item.py": {"type-arg": 1},
        "app/services/example.py": {"arg-type": 2},
    }


def test_parse_mypy_output_refuses_uncoded_error_lines() -> None:
    with pytest.raises(check_mypy.RatchetError, match="without parseable error codes"):
        check_mypy.parse_mypy_output("app/service.py:4: error: missing code")


def test_compare_counts_fails_only_new_or_increased_pairs() -> None:
    baseline = {
        "app/a.py": {"arg-type": 2, "type-arg": 1},
        "app/removed.py": {"attr-defined": 1},
    }
    current = {
        "app/a.py": {"arg-type": 3, "new-code": 1},
    }

    increases, decreases = check_mypy.compare_counts(baseline, current)

    assert increases == [
        ("app/a.py", "arg-type", 2, 3),
        ("app/a.py", "new-code", 0, 1),
    ]
    assert decreases == [
        ("app/a.py", "type-arg", 1, 0),
        ("app/removed.py", "attr-defined", 1, 0),
    ]


def test_baseline_round_trip_is_canonical_and_records_mypy_version(tmp_path: Path) -> None:
    target = tmp_path / "mypy-baseline.json"
    counts = {
        r"app\z.py": {"type-arg": 2, "arg-type": 1},
        "app/a.py": {"no-any-return": 3},
    }

    check_mypy.write_baseline(counts, mypy_version="2.3.0", path=target)

    document = json.loads(target.read_text(encoding="utf-8"))
    assert document == {
        "format_version": 1,
        "mypy_version": "2.3.0",
        "errors": {
            "app/a.py": {"no-any-return": 3},
            "app/z.py": {"arg-type": 1, "type-arg": 2},
        },
    }
    assert check_mypy.load_baseline(target) == check_mypy.Baseline(
        mypy_version="2.3.0",
        errors=document["errors"],
    )


def test_main_requires_explicit_write_for_a_missing_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "mypy-baseline.json"
    monkeypatch.setattr(check_mypy, "BASELINE_PATH", target)
    monkeypatch.setattr(check_mypy, "installed_mypy_version", lambda: "2.3.0")
    monkeypatch.setattr(
        check_mypy,
        "run_mypy",
        lambda: {"app/service.py": {"arg-type": 1}},
    )

    assert check_mypy.main([]) == 2
    assert not target.exists()
    assert "baseline is missing" in capsys.readouterr().err

    assert check_mypy.main(["--write-baseline"]) == 0
    assert target.exists()
    assert check_mypy.load_baseline(target).errors == {
        "app/service.py": {"arg-type": 1}
    }


def test_main_rejects_mypy_version_drift_before_running_checker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "mypy-baseline.json"
    check_mypy.write_baseline(
        {"app/service.py": {"arg-type": 1}},
        mypy_version="1.19.0",
        path=target,
    )
    checker_ran = False

    def unexpected_run() -> check_mypy.Counts:
        nonlocal checker_ran
        checker_ran = True
        return {}

    monkeypatch.setattr(check_mypy, "BASELINE_PATH", target)
    monkeypatch.setattr(check_mypy, "installed_mypy_version", lambda: "2.3.0")
    monkeypatch.setattr(check_mypy, "run_mypy", unexpected_run)

    assert check_mypy.main([]) == 2
    assert checker_ran is False
    assert "baseline uses 1.19.0, installed version is 2.3.0" in capsys.readouterr().err


def test_main_requires_refresh_for_decreases_and_refuses_increases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "mypy-baseline.json"
    check_mypy.write_baseline(
        {"app/service.py": {"arg-type": 2}},
        mypy_version="2.3.0",
        path=target,
    )
    monkeypatch.setattr(check_mypy, "BASELINE_PATH", target)
    monkeypatch.setattr(check_mypy, "installed_mypy_version", lambda: "2.3.0")
    monkeypatch.setattr(
        check_mypy,
        "run_mypy",
        lambda: {"app/service.py": {"arg-type": 1}},
    )

    assert check_mypy.main([]) == 1
    assert "STALE: findings decreased by 1" in capsys.readouterr().err

    assert check_mypy.main(["--write-baseline"]) == 0
    assert check_mypy.load_baseline(target).errors == {
        "app/service.py": {"arg-type": 1}
    }
    capsys.readouterr()

    monkeypatch.setattr(
        check_mypy,
        "run_mypy",
        lambda: {"app/service.py": {"arg-type": 3}},
    )
    assert check_mypy.main([]) == 1
    assert "app/service.py [arg-type]: 1 -> 3" in capsys.readouterr().err

    assert check_mypy.main(["--write-baseline"]) == 1
    assert "same-version baseline write cannot increase allowances" in capsys.readouterr().err
    assert check_mypy.load_baseline(target).errors == {
        "app/service.py": {"arg-type": 1}
    }


def test_checker_upgrade_requires_separate_explicit_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "mypy-baseline.json"
    check_mypy.write_baseline(
        {"app/old.py": {"arg-type": 1}},
        mypy_version="1.19.0",
        path=target,
    )
    monkeypatch.setattr(check_mypy, "BASELINE_PATH", target)
    monkeypatch.setattr(check_mypy, "installed_mypy_version", lambda: "2.3.0")
    monkeypatch.setattr(
        check_mypy,
        "run_mypy",
        lambda: {"app/new.py": {"attr-defined": 2}},
    )

    assert check_mypy.main(["--write-baseline"]) == 2
    assert "requires --allow-version-change" in capsys.readouterr().err
    assert check_mypy.load_baseline(target).mypy_version == "1.19.0"

    assert check_mypy.main(["--write-baseline", "--allow-version-change"]) == 0
    updated = check_mypy.load_baseline(target)
    assert updated.mypy_version == "2.3.0"
    assert updated.errors == {"app/new.py": {"attr-defined": 2}}
