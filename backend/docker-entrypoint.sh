#!/bin/sh
# Backend container entrypoint (api / worker / beat / migrate).
#
# One script, four roles, chosen by the first argument. It exists to do the two things a container
# cannot express declaratively: wait for the stateful dependencies to accept connections, and keep
# schema migration a *single* one-shot step rather than a race between replicas.
#
#   api      — uvicorn
#   worker   — celery worker; pass queues via WORKER_QUEUES, concurrency via WORKER_CONCURRENCY
#   beat     — celery beat (run exactly one replica)
#   migrate  — alembic upgrade head, then exit 0
#
# Anything else is executed verbatim, so one-off operational commands need no --entrypoint:
#
#   docker compose run --rm api python -m app.cli create-owner
#   docker compose run --rm migrate alembic current
#
set -eu

ROLE="${1:-api}"

log() { printf '%s entrypoint[%s]: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ROLE" "$*" >&2; }

# Wait for a TCP endpoint. Compose healthchecks already gate startup, but a dependency can also
# restart mid-life; failing fast with a clear message beats a stack trace from the driver.
wait_for() {
    host="$1"; port="$2"; name="$3"
    attempts="${WAIT_ATTEMPTS:-60}"
    i=1
    while [ "$i" -le "$attempts" ]; do
        if python -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0 if s.connect_ex((\"$host\", $port))==0 else 1)"; then
            log "$name reachable at $host:$port"
            return 0
        fi
        log "waiting for $name at $host:$port ($i/$attempts)"
        i=$((i + 1))
        sleep 2
    done
    log "ERROR: $name never became reachable at $host:$port"
    return 1
}

if [ -n "${DB_HOST:-}" ]; then
    wait_for "$DB_HOST" "${DB_PORT:-3306}" "database"
fi
if [ -n "${REDIS_HOST:-}" ]; then
    wait_for "$REDIS_HOST" "${REDIS_PORT:-6379}" "redis"
fi

case "$ROLE" in
    migrate)
        # Idempotent: a second run against an up-to-date database is a no-op. Run this to
        # completion before api/worker/beat start, so no replica serves an older schema.
        log "applying migrations"
        exec alembic upgrade head
        ;;
    api)
        log "starting uvicorn on :${PORT:-8000} with ${API_WORKERS:-2} workers"
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "${PORT:-8000}" \
            --workers "${API_WORKERS:-2}" \
            --proxy-headers \
            --forwarded-allow-ips '*' \
            --no-server-header
        ;;
    worker)
        # Queues are explicit per service so a slow bulk send can never starve control traffic
        # (Doc 06 §2.3 pools). `-Ofair` stops a worker prefetching work it cannot start yet.
        log "starting celery worker on queues: ${WORKER_QUEUES:?WORKER_QUEUES is required}"
        exec celery -A app.queue.celery_app.celery_app worker \
            --queues "$WORKER_QUEUES" \
            --concurrency "${WORKER_CONCURRENCY:-4}" \
            --hostname "${WORKER_NAME:-worker}@%h" \
            --loglevel "${LOG_LEVEL:-INFO}" \
            -Ofair
        ;;
    beat)
        # Exactly one replica: Beat is a ticker, and two would fire every slot twice.
        # The schedule file lives on a volume so a restart does not re-fire a slot it already sent.
        log "starting celery beat (single replica)"
        exec celery -A app.queue.celery_app.celery_app beat \
            --loglevel "${LOG_LEVEL:-INFO}" \
            --schedule "${BEAT_SCHEDULE_FILE:-/var/run/celery/celerybeat-schedule}"
        ;;
    *)
        # Not a role — run it as a command. This is what makes `docker compose run --rm api
        # python -m app.cli create-owner` work: with an ENTRYPOINT baked into the image, the
        # arguments land here rather than being executed directly, and rejecting them would
        # force every operational one-liner to pass --entrypoint. The dependency waits above
        # have already run, which is exactly what a CLI command touching the database wants.
        log "no such role; executing as a command: $*"
        exec "$@"
        ;;
esac
