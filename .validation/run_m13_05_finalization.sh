#!/usr/bin/env bash
set -euo pipefail

BASELINE=5d7ea154588418410611de4f568e978c2e3caba9
WORK_BRANCH=work/m13-05-provider-runtime-foundation

cat .validation/m13-05-overlay/part* > /tmp/m13-05-overlay.b64
cp .validation/m13-05-fix.b64 /tmp/m13-05-fix.b64
cp .validation/finalize_m13_05.py /tmp/finalize_m13_05.py

git checkout --force "$BASELINE"
git switch -C "$WORK_BRANCH"
base64 --decode /tmp/m13-05-overlay.b64 > /tmp/m13-05-overlay.tar.gz
tar -xzf /tmp/m13-05-overlay.tar.gz
base64 --decode /tmp/m13-05-fix.b64 > /tmp/m13-05-fix.tar.gz
tar -xzf /tmp/m13-05-fix.tar.gz
python /tmp/finalize_m13_05.py apply-fixes
git diff --check

python - <<'PY'
import subprocess
expected = {
    'backend/alembic/versions/0039_qr_pairing_provider_runtime_foundation.py',
    'backend/app/channels/capabilities.py',
    'backend/app/channels/dependencies.py',
    'backend/app/channels/flags.py',
    'backend/app/channels/runtime.py',
    'backend/app/channels/runtime_registry.py',
    'backend/app/models/channel_session.py',
    'backend/app/rbac/catalog.py',
    'backend/app/repositories/channel_session.py',
    'backend/app/services/audit_service.py',
    'backend/app/services/pairing_manager.py',
    'backend/app/services/provider_runtime_manager.py',
    'backend/app/services/session_manager.py',
    'backend/tests/test_channel_foundation.py',
    'backend/tests/test_migrations.py',
    'backend/tests/test_provider_runtime.py',
}
modified = set(subprocess.check_output(['git', 'diff', '--name-only', '5d7ea154588418410611de4f568e978c2e3caba9']).decode().splitlines())
untracked = set(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard']).decode().splitlines())
actual = modified | untracked
assert actual == expected, f'unexpected implementation boundary: {sorted(actual ^ expected)}'
assert not any(path.startswith('backend/app/api/') for path in actual)
assert not any(path.startswith('frontend/') for path in actual)
print('Implementation files:', len(actual))
PY

python -m pip install -e './backend[dev]'
(cd frontend && npm ci)
(cd e2e && npm ci)

(cd backend && python -m ruff check app tests scripts ../scripts)
(cd backend && python -m mypy app)

(cd backend && python - <<'PY'
import json
from pathlib import Path
from app.main import create_app
committed = json.loads(Path('../frontend/openapi.json').read_text(encoding='utf-8'))
generated = create_app().openapi()
assert committed == generated
assert len(generated['paths']) == 200
encoded = json.dumps(generated)
for forbidden in ('pairing_state', 'pairing_reason_code', 'runtime_capabilities_json', 'qr_payload', 'channel_sessions'):
    assert forbidden not in encoded
print('OpenAPI semantic equality: PASS')
print('OpenAPI paths:', len(generated['paths']))
print('Documented pre-existing issue: byte-order-only exporter mismatch on untouched baseline')
PY
)
(cd frontend && npm run gen:api)
git diff --exit-code -- frontend/src/lib/api/schema.d.ts frontend/openapi.json

(cd frontend && npm run lint && npm run typecheck)
(cd e2e && npm run typecheck)

(cd backend && python -m pytest -q tests/test_channel_foundation.py tests/test_session_manager.py tests/test_provider_runtime.py tests/test_migrations.py | tee /tmp/focused-tests.log)
FOCUSED_TESTS=$(grep -oE '[0-9]+ passed' /tmp/focused-tests.log | tail -1 | awk '{print $1}')
test -n "$FOCUSED_TESTS"
export FOCUSED_TESTS

(cd backend && python -m pytest -q -p no:cacheprovider --basetemp=.pytest-run-m13-05 | tee /tmp/backend-tests.log)
BACKEND_TESTS=$(grep -oE '[0-9]+ passed' /tmp/backend-tests.log | tail -1 | awk '{print $1}')
test -n "$BACKEND_TESTS"
export BACKEND_TESTS

(cd frontend && npm test)
(cd frontend && npm run build)

mkdir -p .quality-artifacts .quality-cache
(cd backend && python -m bandit -r app -ll -ii -f json -o ../.quality-artifacts/bandit.json)
(cd backend && python -m pip_audit --strict --progress-spinner off --format cyclonedx-json --output ../.quality-artifacts/backend-sbom.cdx.json .)
(cd frontend && npm audit --omit=dev --audit-level=high)
(cd e2e && npm audit --audit-level=high)
WA_QUALITY_DOCKER=docker python scripts/trivy_scan.py source

(cd backend && python -m pytest -q tests/test_migrations.py tests/test_provider_runtime.py)
(cd backend && python - <<'PY'
from alembic.config import Config
from alembic.script import ScriptDirectory
cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)
assert script.get_current_head() == '0039_qr_pairing_provider_runtime_foundation'
print('Migration head:', script.get_current_head())
PY
)

python - <<'PY'
from pathlib import Path
import gzip
for path in sorted(Path('frontend/dist/assets').glob('*')):
    if path.is_file() and path.suffix in {'.js', '.css'}:
        raw = path.stat().st_size
        gz = len(gzip.compress(path.read_bytes()))
        print(f'{path.name}: {raw / 1000:.2f} kB / {gz / 1000:.2f} kB gzip')
PY

export VALIDATION_RUN_ID="${GITHUB_RUN_ID}"
export M13_TIMESTAMP='2026-08-04T22:45:00+05:30'
python /tmp/finalize_m13_05.py update-governance
git diff --check

python - <<'PY'
import subprocess
expected = {
    'CHANGELOG.md', 'IMPLEMENTATION_TRACKER.md', 'MODULE_STATUS.md', 'PROJECT_STATE.md', 'ROADMAP.md', 'VALIDATION_RESULTS.md',
    'backend/alembic/versions/0039_qr_pairing_provider_runtime_foundation.py',
    'backend/app/channels/capabilities.py', 'backend/app/channels/dependencies.py', 'backend/app/channels/flags.py',
    'backend/app/channels/runtime.py', 'backend/app/channels/runtime_registry.py',
    'backend/app/models/channel_session.py', 'backend/app/rbac/catalog.py',
    'backend/app/repositories/channel_session.py', 'backend/app/services/audit_service.py',
    'backend/app/services/pairing_manager.py', 'backend/app/services/provider_runtime_manager.py',
    'backend/app/services/session_manager.py', 'backend/tests/test_channel_foundation.py',
    'backend/tests/test_migrations.py', 'backend/tests/test_provider_runtime.py',
}
modified = set(subprocess.check_output(['git', 'diff', '--name-only', '5d7ea154588418410611de4f568e978c2e3caba9']).decode().splitlines())
untracked = set(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard']).decode().splitlines())
actual = modified | untracked
assert actual == expected, f'unexpected final boundary: {sorted(actual ^ expected)}'
assert not any(path.startswith('backend/app/api/') for path in actual)
assert not any(path.startswith('frontend/') for path in actual)
print('Final files:', len(actual))
PY

grep -q 'M13-06 is not started' IMPLEMENTATION_TRACKER.md
grep -q 'Stop after M13-05' PROJECT_STATE.md
grep -q '0039_qr_pairing_provider_runtime_foundation' VALIDATION_RESULTS.md

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add CHANGELOG.md IMPLEMENTATION_TRACKER.md MODULE_STATUS.md PROJECT_STATE.md ROADMAP.md VALIDATION_RESULTS.md backend

git commit -m 'feat(channels): add provider runtime foundation'
test "$(git rev-list --count "$BASELINE"..HEAD)" = '1'
git push --force-with-lease origin HEAD:"$WORK_BRANCH"

echo "PRODUCT_COMMIT=$(git rev-parse HEAD)"
git show --stat --oneline --decorate --no-renames HEAD
git status --short
