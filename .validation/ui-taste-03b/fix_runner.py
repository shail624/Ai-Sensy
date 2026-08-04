from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
runner = root / "run_ui_taste_03b.sh"
lines = runner.read_text(encoding="utf-8").splitlines()
start = next(
    (index for index, line in enumerate(lines) if line.startswith("mapfile -t actual_files")),
    None,
)
if start is None or start + 3 >= len(lines):
    raise SystemExit("final boundary block missing")
lines[start : start + 4] = [
    "mapfile -t actual_files < <(",
    "  { git diff --name-only; git ls-files --others --exclude-standard; } | sort -u",
    ")",
    "mapfile -t expected_sorted < <(printf '%s\\n' \"${expected_files[@]}\" | sort)",
    'test "${#actual_files[@]}" -eq 19',
    "diff -u <(printf '%s\\n' \"${expected_sorted[@]}\") <(printf '%s\\n' \"${actual_files[@]}\")",
]
runner.write_text("\n".join(lines) + "\n", encoding="utf-8")
