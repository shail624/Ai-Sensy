#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

source = Path('builder/.github/m13-02-gate-diagnostic.sh').read_text(encoding='utf-8')
old = 'run_stage APPLY_VERIFIED_FIXES python builder/.github/m13-02-fixes.py "$source_dir" || exit 0'
new = '''run_stage APPLY_VERIFIED_FIXES python builder/.github/m13-02-fixes.py "$source_dir" || exit 0
run_stage APPLY_VERIFIED_FIXES_2 python builder/.github/m13-02-fixes-2.py "$source_dir" || exit 0'''
if source.count(old) != 1:
    raise SystemExit('verified diagnostic fix marker changed')
Path('/tmp/m13-02-gate-diagnostic.sh').write_text(source.replace(old, new, 1), encoding='utf-8')
PY

bash /tmp/m13-02-gate-diagnostic.sh "$@"
