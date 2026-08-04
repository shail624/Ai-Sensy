#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

source = Path('builder/.github/m13-02-run.sh').read_text(encoding='utf-8')
old = 'ruff format --check app tests alembic/versions/0036_customer_identity_resolution.py'
new = '''ruff format --check \\
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
if source.count(old) != 1:
    raise SystemExit('verified Ruff format marker changed')
Path('/tmp/m13-02-run.sh').write_text(source.replace(old, new), encoding='utf-8')
PY

bash /tmp/m13-02-run.sh
