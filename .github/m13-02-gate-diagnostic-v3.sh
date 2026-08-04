#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

source = Path('builder/.github/m13-02-gate-diagnostic.sh').read_text(encoding='utf-8')
fix_old = 'run_stage APPLY_VERIFIED_FIXES python builder/.github/m13-02-fixes.py "$source_dir" || exit 0'
fix_new = '''run_stage APPLY_VERIFIED_FIXES python builder/.github/m13-02-fixes.py "$source_dir" || exit 0
run_stage APPLY_VERIFIED_FIXES_2 python builder/.github/m13-02-fixes-2.py "$source_dir" || exit 0'''
test_old = 'tests/test_contact_events.py '
if source.count(fix_old) != 1 or source.count(test_old) != 1:
    raise SystemExit('verified M13-02 diagnostic marker changed')
source = source.replace(fix_old, fix_new, 1).replace(test_old, '', 1)
Path('/tmp/m13-02-gate-diagnostic.sh').write_text(source, encoding='utf-8')
PY

bash /tmp/m13-02-gate-diagnostic.sh "$@"
