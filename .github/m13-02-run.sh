#!/usr/bin/env bash
set -euo pipefail

python builder/.github/m13-02-build.py work
python builder/.github/m13-02-fixes.py work

python -m pip install --upgrade pip
python -m pip install -e './work/backend[dev]'

cd work/backend
ruff format \
  app/identity \
  app/models/contact_identity.py \
  app/models/__init__.py \
  app/models/contact_event.py \
  app/repositories/contact_identity.py \
  app/services/identity_resolution_service.py \
  app/services/audit_service.py \
  app/schemas/contact_identity.py \
  app/api/v1/endpoints/contact_identity.py \
  app/api/v1/router.py \
  alembic/versions/0036_customer_identity_resolution.py \
  tests/test_identity_resolution.py

ENVIRONMENT=test \
DATABASE_URL=sqlite+aiosqlite:// \
SECRET_KEY=test-secret-key-not-for-production-use-only \
python - <<'PY'
import json
from pathlib import Path
from app.main import create_app

schema = create_app().openapi()
Path('../frontend/openapi.json').write_text(
    json.dumps(schema, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
print(f"OPENAPI_PATHS={len(schema['paths'])}")
PY

cd ../frontend
npm ci
npm run gen:api

cd ../backend
ruff format --check app tests alembic/versions/0036_customer_identity_resolution.py
ruff check app tests alembic/versions/0036_customer_identity_resolution.py
mypy app
pytest \
  tests/test_identity_resolution.py \
  tests/test_api_contacts.py \
  tests/test_contact_events.py \
  tests/test_audit.py \
  tests/test_channel_foundation.py

rm -f /tmp/m13-02-identity.db
ENVIRONMENT=test \
DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db \
SECRET_KEY=test-secret-key-not-for-production-use-only \
alembic upgrade head
ENVIRONMENT=test \
DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db \
SECRET_KEY=test-secret-key-not-for-production-use-only \
alembic downgrade 0035_notification_center
ENVIRONMENT=test \
DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db \
SECRET_KEY=test-secret-key-not-for-production-use-only \
alembic upgrade head
python - <<'PY'
import sqlite3

connection = sqlite3.connect('/tmp/m13-02-identity.db')
tables = {
    row[0]
    for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
}
expected = {
    'contact_identities',
    'identity_conflicts',
    'identity_merge_recommendations',
}
if not expected <= tables:
    raise SystemExit(f'missing identity tables: {sorted(expected - tables)}')
print('MIGRATION_TABLES_PASS')
PY

pytest
pip-audit
bandit -q -r app

cd ../frontend
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm test
npm run build

cd ..
git diff --check
test -z "$(git diff --name-only -- \
  backend/app/channels/foundation.py \
  backend/app/channels/registry.py \
  backend/app/channels/validation.py \
  backend/app/channels/flags.py \
  backend/app/channels/dependencies.py \
  backend/app/api/deps.py \
  backend/tests/test_channel_foundation.py)"
test -z "$(git diff --name-only -- backend/app/channels/meta frontend/src/features frontend/src/pages)"
python - <<'PY'
import subprocess

expected = {
    'backend/alembic/versions/0036_customer_identity_resolution.py',
    'backend/app/api/v1/endpoints/contact_identity.py',
    'backend/app/api/v1/router.py',
    'backend/app/identity/__init__.py',
    'backend/app/identity/domain.py',
    'backend/app/identity/flags.py',
    'backend/app/models/__init__.py',
    'backend/app/models/contact_event.py',
    'backend/app/models/contact_identity.py',
    'backend/app/repositories/contact_identity.py',
    'backend/app/schemas/contact_identity.py',
    'backend/app/services/audit_service.py',
    'backend/app/services/identity_resolution_service.py',
    'backend/tests/test_identity_resolution.py',
    'frontend/openapi.json',
    'frontend/src/lib/api/schema.d.ts',
}
tracked = set(subprocess.check_output(['git', 'diff', '--name-only'], text=True).splitlines())
untracked = set(
    subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard'], text=True
    ).splitlines()
)
actual = tracked | untracked
if actual != expected:
    raise SystemExit(
        f'M13-02 boundary mismatch: expected={sorted(expected)} actual={sorted(actual)}'
    )
print('M13_02_BOUNDARY_PASS')
PY

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add \
  backend/alembic/versions/0036_customer_identity_resolution.py \
  backend/app/api/v1/endpoints/contact_identity.py \
  backend/app/api/v1/router.py \
  backend/app/identity \
  backend/app/models/__init__.py \
  backend/app/models/contact_event.py \
  backend/app/models/contact_identity.py \
  backend/app/repositories/contact_identity.py \
  backend/app/schemas/contact_identity.py \
  backend/app/services/audit_service.py \
  backend/app/services/identity_resolution_service.py \
  backend/tests/test_identity_resolution.py \
  frontend/openapi.json \
  frontend/src/lib/api/schema.d.ts
git commit -m 'feat(identity): add customer identity resolution'
git push origin HEAD:work/m13-02-customer-identity-resolution
