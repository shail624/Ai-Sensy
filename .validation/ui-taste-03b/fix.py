from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])

board = root / "ReactivationPipelineBoard.tsx"
text = board.read_text(encoding="utf-8")
for unused in ("  Clock3,\n", "  FileCheck2,\n"):
    text = text.replace(unused, "")
board.write_text(text, encoding="utf-8")

apply_script = root / "apply_ui_taste_03b.py"
text = apply_script.read_text(encoding="utf-8")
old = '''changed = set(
    subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines()
)
require(changed == expected, f"unexpected implementation boundary: {sorted(changed ^ expected)}")
'''
new = '''changed = set(
    subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines()
)
changed.update(
    subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], text=True
    ).splitlines()
)
require(changed == expected, f"unexpected implementation boundary: {sorted(changed ^ expected)}")
'''
if old not in text:
    raise SystemExit("implementation boundary patch target missing")
apply_script.write_text(text.replace(old, new, 1), encoding="utf-8")
