#!/usr/bin/env bash
# Start the application processes the browser gates need, without Docker.
#
# `local_services.sh` brings up the data stores; this brings up what runs on top of them — the API,
# a Celery worker, and the built frontend behind the same-origin proxy the SPA expects. The
# `deployed` quality profile does all of this in containers, which is the right thing in CI and an
# obstacle anywhere Docker is not available: without it nothing under `e2e/tests/` can run at all,
# and an accessibility gate nobody can run is a gate that stops being true.
#
# Idempotent: each process starts only if nothing already answers for it.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${LOCAL_STACK_LOGS:-/tmp/wa-local-stack}"
mkdir -p "$LOGS"

export DB_HOST="${DB_HOST:-127.0.0.1}"
export DB_USER="${DB_USER:-root}"
export DB_PASSWORD="${DB_PASSWORD:-root}"
export DB_NAME="${DB_NAME:-wa_platform}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export SECRET_KEY="${SECRET_KEY:-local-development-key-not-for-production-32}"

# Sign-in is limited to 10 attempts per 5 minutes per caller, which is right in production and
# wrong for a gate runner: every browser test signs in, so one `playwright test` spends half the
# budget and a second run inside the window gets 429 on login. The tests then fail on a blank page
# and read as broken screens — which is exactly how this was first seen.
#
# `backend/tests/conftest.py` switches the same limiter off for the same reason. This is a local
# development stack (`ENVIRONMENT=development`); production keeps the default, which is on. Export
# RATE_LIMIT_ENABLED=true before running this to exercise the limiter deliberately.
export RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-false}"

answers() { curl -sf -o /dev/null --max-time 3 "$1" 2>/dev/null; }

# Every long-lived process is started in its own session with stdio fully detached.
#
# `( cmd & )` is not enough: the subshell stays as the parent and waits, so this script's stdout is
# still held open by a server that will not exit for hours. Run from a terminal that looks like a
# hang; run from a CI step or an agent it *is* one. `setsid` plus a closed stdin and a redirected
# stdout is what actually lets the launcher return.
start() {  # start <log-basename> <working-dir> <command...>
  local log="$LOGS/$1"; local dir="$2"; shift 2
  setsid --fork env -C "$dir" "$@" >"$log" 2>&1 </dev/null &
  disown 2>/dev/null || true
}

wait_for() {  # wait_for <seconds> <test-command...>
  local limit="$1"; shift
  for _ in $(seq 1 "$limit"); do "$@" && return 0; sleep 1; done
  return 1
}

if ! answers http://127.0.0.1:8000/health; then
  start api.log "$ROOT/backend" .venv/bin/python -m uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 --log-level warning
  wait_for 60 answers http://127.0.0.1:8000/health
fi
answers http://127.0.0.1:8000/health \
  && echo "api:     up (:8000)" \
  || { echo "api:     FAILED — see $LOGS/api.log"; exit 1; }

# The worker is what makes an import, an export or a campaign dispatch finish. Without one the
# owner journey reaches "Start import" and waits there until it times out, which reads as a broken
# import rather than as a missing process.
worker_ready() { grep -q "ready\." "$LOGS/worker.log" 2>/dev/null; }
if ! pgrep -f "celery -A app.queue.celery_app" >/dev/null 2>&1; then
  : >"$LOGS/worker.log"
  start worker.log "$ROOT/backend" .venv/bin/celery -A app.queue.celery_app.celery_app worker \
    --loglevel=info --concurrency=2
  wait_for 60 worker_ready
fi
pgrep -f "celery -A app.queue.celery_app" >/dev/null 2>&1 \
  && echo "worker:  up" \
  || echo "worker:  FAILED — see $LOGS/worker.log"

# The *built* bundle, not the dev server: the artefact that ships is the one worth checking, and
# `vite preview` carries the same /api proxy so the SPA stays same-origin (Doc 04 §2).
if ! answers http://127.0.0.1:4173/; then
  echo "web:     building…"
  ( cd "$ROOT/frontend" && npm run build ) >"$LOGS/build.log" 2>&1 \
    || { echo "web:     BUILD FAILED — see $LOGS/build.log"; exit 1; }
  start preview.log "$ROOT/frontend" npx vite preview --host 127.0.0.1 --port 4173
  wait_for 60 answers http://127.0.0.1:4173/
fi
answers http://127.0.0.1:4173/ \
  && echo "web:     up (:4173, production build)" \
  || { echo "web:     FAILED — see $LOGS/preview.log"; exit 1; }
answers http://127.0.0.1:4173/api/v1/openapi.json \
  && echo "proxy:   /api reaches the API" \
  || echo "proxy:   FAILED — the SPA will not be able to sign in"

cat <<'NEXT'

Create an owner once (the address must be one the login form accepts — a .local TLD is refused):
  cd backend && OWNER_PASSWORD='<password>' \
    .venv/bin/python -m app.cli create-owner --email owner@example.com --name Owner

Then run the browser gates:
  cd e2e && E2E_BASE_URL=http://127.0.0.1:4173 \
    E2E_OWNER_EMAIL=owner@example.com E2E_OWNER_PASSWORD='<password>' \
    E2E_ARTIFACTS_DIR=/tmp/wa-artifacts \
    npx playwright test

Add E2E_CHROMIUM_PATH=/path/to/chromium when a browser is already provisioned for a different
Playwright version, so the run uses it instead of downloading a second copy.
NEXT
