from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
runner = root / "run_ui_taste_03b.sh"
text = runner.read_text(encoding="utf-8")
old = '''mapfile -t actual_files < <(git diff --name-only | sort)
mapfile -t expected_sorted < <(printf '%s\\n' "${expected_files[@]}" | sort)
test "${#actual_files[@]}" -eq 19
diff -u <(printf '%s\\n' "${expected_sorted[@]}") <(printf '%s\\n' "${actual_files[@]}")
'''
new = '''mapfile -t actual_files < <(
  { git diff --name-only; git ls-files --others --exclude-standard; } | sort -u
)
mapfile -t expected_sorted < <(printf '%s\\n' "${expected_files[@]}" | sort)
test "${#actual_files[@]}" -eq 19
diff -u <(printf '%s\\n' "${expected_sorted[@]}") <(printf '%s\\n' "${actual_files[@]}")
'''
if old not in text:
    raise SystemExit("final boundary patch target missing")
runner.write_text(text.replace(old, new, 1), encoding="utf-8")
