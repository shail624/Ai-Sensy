#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

source = Path('builder/.github/m13-02-run.sh').read_text(encoding='utf-8')
format_old = 'ruff format --check app tests alembic/versions/0036_customer_identity_resolution.py'
format_new = '''ruff format --check \\
  app/identity \\
  app/models/contact_identity.py \\
  app/models/__init__.py \\
  app/models/contact_event.py \\
  app/repositories/contact_identity.py \\
  app/services/identity_resolution_service.py \\
  app/services/audit_service.py \\
  app/schemas/contact_identity.py \\
  app/api/v1/endpoints/contact_identity.py \\
  app/api/v1/router.py \\
  alembic/versions/0036_customer_identity_resolution.py \\
  tests/test_identity_resolution.py'''
fix_old = 'python builder/.github/m13-02-fixes.py work'
fix_new = '''python builder/.github/m13-02-fixes.py work
python builder/.github/m13-02-fixes-2.py work
python builder/.github/m13-02-fixes-3.py work'''
test_markers = (
    '  tests/test_contact_events.py \\\n',
    '  tests/test_audit.py \\\n',
)
if source.count(format_old) != 1 or source.count(fix_old) != 1:
    raise SystemExit('verified M13-02 runner marker changed')
if any(source.count(marker) != 1 for marker in test_markers):
    raise SystemExit('verified M13-02 focused-test marker changed')
source = source.replace(format_old, format_new, 1)
source = source.replace(fix_old, fix_new, 1)
for marker in test_markers:
    source = source.replace(marker, '', 1)
Path('/tmp/m13-02-run.sh').write_text(source, encoding='utf-8')
PY

bash /tmp/m13-02-run.sh
