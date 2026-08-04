#!/usr/bin/env bash
set +e

source_dir="${1:?source directory required}"
report="${2:?report path required}"
: > "$report"
printf 'BASELINE=%s\n' "$(git -C "$source_dir" rev-parse HEAD)" >> "$report"
printf 'RUN=%s\n' "${GITHUB_RUN_ID:-local}" >> "$report"

run_stage() {
  local name="$1"
  shift
  printf '\n=== %s ===\n' "$name" >> "$report"
  "$@" >> "$report" 2>&1
  local code=$?
  printf '\nEXIT=%s\n' "$code" >> "$report"
  if [ "$code" -ne 0 ]; then
    printf '\nFIRST_FAILURE=%s\n' "$name" >> "$report"
    return "$code"
  fi
  return 0
}

run_stage APPLY_SOURCE python builder/.github/m13-02-build.py "$source_dir" || exit 0
run_stage APPLY_VERIFIED_FIXES python builder/.github/m13-02-fixes.py "$source_dir" || exit 0
run_stage INSTALL_BACKEND python -m pip install -e "./$source_dir/backend[dev]" || exit 0

changed_python="app/identity app/models/contact_identity.py app/models/__init__.py app/models/contact_event.py app/repositories/contact_identity.py app/services/identity_resolution_service.py app/services/audit_service.py app/schemas/contact_identity.py app/api/v1/endpoints/contact_identity.py app/api/v1/router.py alembic/versions/0036_customer_identity_resolution.py tests/test_identity_resolution.py"
run_stage FORMAT bash -lc "cd '$source_dir/backend' && ruff format $changed_python" || exit 0

run_stage OPENAPI bash -lc "cd '$source_dir/backend' && ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:// SECRET_KEY=test-secret-key-not-for-production-use-only python -c 'import json; from pathlib import Path; from app.main import create_app; schema=create_app().openapi(); Path(\"../frontend/openapi.json\").write_text(json.dumps(schema, indent=2, sort_keys=True)+\"\\n\", encoding=\"utf-8\"); print(\"OPENAPI_PATHS=\", len(schema[\"paths\"]))'" || exit 0

run_stage NPM_CI bash -lc "cd '$source_dir/frontend' && npm ci" || exit 0
run_stage GENERATE_CLIENT bash -lc "cd '$source_dir/frontend' && npm run gen:api" || exit 0
run_stage RUFF_FORMAT_CHECK bash -lc "cd '$source_dir/backend' && ruff format --check $changed_python" || exit 0
run_stage RUFF_CHECK bash -lc "cd '$source_dir/backend' && ruff check app tests alembic/versions/0036_customer_identity_resolution.py" || exit 0
run_stage MYPY bash -lc "cd '$source_dir/backend' && mypy app" || exit 0
run_stage FOCUSED_TESTS bash -lc "cd '$source_dir/backend' && pytest tests/test_identity_resolution.py tests/test_api_contacts.py tests/test_contact_events.py tests/test_audit.py tests/test_channel_foundation.py" || exit 0

run_stage MIGRATION bash -lc "cd '$source_dir/backend' && rm -f /tmp/m13-02-identity.db && ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db SECRET_KEY=test-secret-key-not-for-production-use-only alembic upgrade head && ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db SECRET_KEY=test-secret-key-not-for-production-use-only alembic downgrade 0035_notification_center && ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:////tmp/m13-02-identity.db SECRET_KEY=test-secret-key-not-for-production-use-only alembic upgrade head" || exit 0

run_stage FULL_PYTEST bash -lc "cd '$source_dir/backend' && pytest" || exit 0
run_stage PIP_AUDIT bash -lc "cd '$source_dir/backend' && pip-audit" || exit 0
run_stage BANDIT bash -lc "cd '$source_dir/backend' && bandit -q -r app" || exit 0
run_stage NPM_PRODUCTION_AUDIT bash -lc "cd '$source_dir/frontend' && npm audit --omit=dev --audit-level=high" || exit 0
run_stage FRONTEND_LINT bash -lc "cd '$source_dir/frontend' && npm run lint" || exit 0
run_stage FRONTEND_TYPECHECK bash -lc "cd '$source_dir/frontend' && npm run typecheck" || exit 0
run_stage VITEST bash -lc "cd '$source_dir/frontend' && npm test" || exit 0
run_stage PRODUCTION_BUILD bash -lc "cd '$source_dir/frontend' && npm run build" || exit 0
run_stage DIFF_CHECK bash -lc "cd '$source_dir' && git diff --check" || exit 0

printf '\nALL_DIAGNOSTIC_GATES_PASS\n' >> "$report"
