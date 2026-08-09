# Deployment Guide — Self-Hosted WhatsApp Business Platform

Covers building, migrating, starting, verifying, upgrading and rolling back the production stack.

> **These manifests were first executed and validated on 2026-07-23.** That run exposed and fixed
> worker event-loop reuse, storage registration, nginx re-resolution, and duplicate probe-header
> defects; the evidence is recorded in `CHANGELOG.md`. Every new release must still run §2–§8 on a
> staging host and confirm each check before production traffic is moved. §14 lists what to watch
> for.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Docker Engine ≥ 24 + Compose v2 | `docker compose version` must report v2.x |
| 4 vCPU / 8 GB RAM minimum | MySQL and three worker pools share the host |
| 20 GB disk, growing | `mysql-data` and `media-data` grow with message and export volume |
| Meta Cloud API app | App secret + webhook verify token, phone number registered |
| TLS certificate | Terminate at the edge (§6) or at a load balancer in front of it |
| Outbound HTTPS to `graph.facebook.com` | Required for sending; the platform never accepts inbound from Meta except via the webhook |

Architecture: **nginx** (edge) → **frontend** (static SPA) and **api** (FastAPI); **three worker
pools** and **one beat** consume from **redis**; **mysql** holds all durable state.

---

## 2. Configure

```bash
cp .env.production.example .env.production
```

Fill every value marked REQUIRED. Compose declares them as `${VAR:?}`, so a missing one aborts
`up` naming the variable rather than starting a half-configured stack.

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"                        # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"                        # REDIS_PASSWORD
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"  # TOKEN_ENCRYPTION_KEY
```

`TOKEN_ENCRYPTION_KEY` encrypts WhatsApp access tokens at rest and is **required in production** —
the application deliberately refuses to derive it from `SECRET_KEY` there. Omitting it does not
degrade gracefully: registering a WABA fails and stored tokens cannot be decrypted, so the platform
authenticates and serves the UI while being unable to send a single message. Rotating it does not
re-encrypt existing rows; the stored tokens become unreadable and must be re-entered.

`REDIS_PASSWORD` must stay URL-safe (letters, digits, `-`, `_`). It is interpolated into
`REDIS_URL` as `redis://:<password>@redis:6379/0`, so an `@`, `/` or `:` inside it silently
corrupts the connection string. `token_urlsafe` already produces a safe alphabet.

**Never commit `.env.production`.** Prefer your orchestrator's secret store, injected as
environment variables.

---

## 3. Build

```bash
docker compose -f docker-compose.production.yml --env-file .env.production build
```

The frontend build runs `tsc --noEmit && vite build`, so a type error fails the image rather than
shipping. The backend installs from `pyproject.toml` — the canonical dependency list — so the image
cannot drift from the application's real requirements.

Each image builds from its own directory (`./backend`, `./frontend`) and each carries its own
`.dockerignore`. Docker reads only the ignore file at the **root of the build context**, so the
repository-root `.dockerignore` does not apply to either build — `backend/.dockerignore` keeps the
host `.venv` and any local `.env` out of the image, and `frontend/.dockerignore` keeps
`node_modules/` out of the upload. Both images are self-contained: the entrypoint and the SPA's
nginx config are baked in, not bind-mounted, so `docker run wa-platform/backend:<tag> worker` works
on its own.

Source maps are built but never served: `vite.config.ts` uses `sourcemap: "hidden"` and the SPA's
nginx returns 404 for `*.map`. To symbolicate a production stack trace, pull the maps out of the
image (`docker run --rm --entrypoint sh wa-platform/frontend:<tag> -c 'cat /usr/share/nginx/html/assets/<name>.map'`)
or upload them to your error tracker at release time.

---

## 4. Migrate

Schema changes are a **separate one-shot service**, not a step inside the API container. `api`,
the workers and `beat` all wait on `service_completed_successfully`, so no replica can serve an
older schema.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up migrate
```

Expect `alembic upgrade head` to finish at **`0027_analytics`** and the container to exit 0.
Re-running is a no-op.

Verify:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production \
  run --rm migrate alembic current
```

The entrypoint recognises four roles (`api`, `worker`, `beat`, `migrate`) and executes anything
else verbatim, so one-off commands like this need no `--entrypoint` override. The dependency waits
still run first, which is what a command touching the database wants.

---

## 5. Initial setup (first deploy only)

Create the first organization and owner. Permissions are seeded idempotently by
`sync_system_roles` on migrate, so this only creates the human account:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production \
  run --rm api python -m app.cli create-owner
```

Then clear `OWNER_*` from `.env.production`.

---

## 6. Start

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d
```

Service roles:

| Service | Role | Scaling |
|---|---|---|
| `mysql`, `redis` | State and broker | Single instance |
| `migrate` | One-shot schema | Exits 0 |
| `api` | FastAPI behind uvicorn | Scale freely |
| `worker-realtime` | control, priority sends, webhooks | Scale for responsiveness |
| `worker-bulk` | campaign fan-out, retries | **Scale for throughput** |
| `worker-jobs` | imports, exports, media, analytics rollups, cleanup | Scale for batch load |
| `beat` | Periodic scheduler | **Exactly one — never scale** |
| `frontend` | Static SPA | Scale freely |
| `nginx` | Edge proxy | Scale freely |

### Workers

Queues are split by pool (Doc 06 §2.3) so a bulk campaign cannot starve control traffic:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production \
  up -d --scale worker-bulk=3
```

### Beat

Beat is a ticker, not a worker. **Two instances fire every schedule twice.** The tasks are
idempotent so a duplicate is survivable, but it doubles work for nothing.

Four schedules ship in code (`app/queue/celery_app.py`), all UTC:

| Entry | Cadence |
|---|---|
| `campaign-scheduler-tick` | every minute |
| `analytics-rollup-incremental` | every 15 minutes |
| `analytics-rollup-nightly` | 02:15 UTC |
| `analytics-rollup-prune` | 03:00 UTC |

```bash
docker compose -f docker-compose.production.yml logs beat | head -40   # confirm all four
```

### nginx / TLS

The shipped config listens on plain HTTP and expects TLS to terminate in front of it. To terminate
at this proxy instead, mount your certificates and add to the `server` block in
`deploy/nginx/nginx.conf`:

```nginx
listen 443 ssl http2;
ssl_certificate     /etc/nginx/certs/fullchain.pem;
ssl_certificate_key /etc/nginx/certs/privkey.pem;
ssl_protocols       TLSv1.2 TLSv1.3;
```

…then uncomment the `Strict-Transport-Security` header (it is deliberately off until TLS exists —
sending HSTS over plain HTTP locks clients out of a site that cannot serve HTTPS) and add a
`:80 → :443` redirect server.

### Client IP — read this before putting a load balancer in front

The proxy sends `X-Forwarded-For: $remote_addr`, **replacing** any value the client supplied rather
than appending to it. That is deliberate. uvicorn runs with `--forwarded-allow-ips '*'` and derives
`request.client` from this header, and the auth rate limiter (10 attempts / 5 min) buckets on
`request.client`. If the header were appended to, a client could send its own `X-Forwarded-For` and
change it on every request — each login attempt would land in a fresh bucket and brute-force
protection would be worth nothing.

This is correct as long as **nginx is the outermost hop**. If you put an ALB, Cloudflare or another
proxy in front, `$remote_addr` becomes that proxy's address and every user collapses into one
rate-limit bucket. In that case restore the real client address at this proxy instead:

```nginx
# in the http block — one line per trusted proxy range
set_real_ip_from  10.0.0.0/8;      # your load balancer's CIDR, never 0.0.0.0/0
real_ip_header    X-Forwarded-For;
real_ip_recursive on;
```

`$remote_addr` is then the true client, and the existing `proxy_set_header X-Forwarded-For
$remote_addr;` keeps forwarding exactly one trustworthy value. Never widen `set_real_ip_from` to
`0.0.0.0/0` — that trusts the header from anyone and reopens the spoofing hole.

---

## 7. Health verification

```bash
curl -fsS  http://<host>/health          # liveness  → {"status":"ok",...}
curl -fsSi http://<host>/ready           # readiness → database, redis, storage all "up"
docker compose -f docker-compose.production.yml ps      # every service healthy
```

`/ready` returns **503** with a per-dependency breakdown if any dependency is down — that is the
signal to health-gate on.

Worker fleet and queue depth (needs an authenticated operator token):

```bash
curl -fsS -H "Authorization: Bearer $TOKEN" http://<host>/api/v1/queues
```

---

## 8. Smoke verification

Run after every deploy:

1. **Sign in** through the SPA at `http://<host>/`.
2. **Import one controlled CSV contact** through Contacts → Import and confirm the worker completes it.
3. **Confirm the webhook**: send a WhatsApp message to the registered number; it appears in Inbox.
4. **Reply** from the Inbox inside the 24-hour window.
5. **Analytics freshness**: `GET /api/v1/analytics/freshness` — lag under 15 minutes once one
   incremental rollup has run. If empty, Beat is not running (§6).
6. **Export a report**: Analytics → Export → CSV; poll until a download link appears.
7. **Open the CSV in Excel** and confirm a contact name beginning `=` is prefixed with `'`
   (formula-injection neutralisation) while phone numbers keep their leading `+`.
8. **Executive gating**: a user without `analytics:executive` gets 403 on `/api/v1/analytics/costs`.

Before promotion, `python scripts/quality_gate.py deployed` automates the safe repository subset of
this verification against a uniquely named, disposable production-Compose stack. It logs in through
the real SPA, imports and finds a contact through the jobs worker, and enforces the standard-read
p95 budget. It does not replace the registered-number, Meta sandbox, analytics, or RBAC checks above.

Backfill so the dashboard is not empty on day one:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production \
  run --rm api celery -A app.queue.celery_app.celery_app call \
    app.analytics.tasks.rollup_backfill \
    --args='["2026-01-01T00:00:00","2026-07-23T00:00:00"]'
```

---

## 9. Upgrade

Migrations are **expand-only** — additive, never destructive in the same release — so the old code
keeps running against the new schema during a rolling deploy.

```bash
git pull && export IMAGE_TAG=$(git rev-parse --short HEAD)
docker compose -f docker-compose.production.yml --env-file .env.production build
docker compose -f docker-compose.production.yml --env-file .env.production up migrate   # exits 0
docker compose -f docker-compose.production.yml --env-file .env.production up -d
```

Pin `IMAGE_TAG` per release so §10 is a tag change rather than a rebuild.

---

## 10. Rollback

**Application rollback** (schema unchanged, the common case):

```bash
IMAGE_TAG=<previous-tag> docker compose -f docker-compose.production.yml \
  --env-file .env.production up -d
```

Because migrations are expand-only, the previous release runs against the newer schema unchanged.

**Schema rollback** — only if a migration is itself the fault. Every revision has a tested
`downgrade`, but a downgrade that drops a column **destroys the data in it**:

```bash
docker compose -f docker-compose.production.yml run --rm migrate \
  sh -c "alembic downgrade <previous_revision>"
```

Take a backup first (§11) and prefer rolling the application back and fixing forward.

---

## 11. Backup

| What | Why | How |
|---|---|---|
| `mysql-data` | All durable state | `mysqldump --single-transaction --routines` nightly, off-host |
| `media-data` | Inbound media + export artifacts; **not reconstructable** | Volume snapshot or object-store sync |
| `redis-data` | In-flight queue only; rebuildable | Optional — a loss costs queued work, not records |
| `waha-sessions` | WhatsApp session credentials (QR profile only); **not reconstructable without a human re-scanning a QR code** | Volume snapshot alongside `mysql-data`. See §15. |
| `.env.production` | Secrets | Secret store, not a backup tarball. Losing `SECRET_KEY` signs every user out; losing `REDIS_PASSWORD` means the stack cannot reach its own broker until you reset it on both sides. |

```bash
docker compose -f docker-compose.production.yml exec mysql \
  mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines \
  "$DB_NAME" | gzip > backup-$(date -u +%Y%m%dT%H%M%SZ).sql.gz
```

Restore into a **scratch instance** and run `alembic current` before trusting any backup.
Analytics rollups are derived and need no backup — they rebuild from source via
`rollup_backfill`.

---

## 12. Observability

What the platform exposes today, and where to attach a monitor. **No new endpoint was added for
this** — the API contract is frozen — so everything below is either already served or is a
sidecar you run alongside the stack.

| Signal | Where | Use it for |
|---|---|---|
| Liveness | `GET /health` (unauthenticated) | Restart policy. Cheap; touches no dependency. |
| Readiness | `GET /ready` (unauthenticated) | Load-balancer gating. 503 + per-dependency breakdown for database, Redis, storage. |
| Queue depth & worker fleet | `GET /api/v1/queues` (operator token) | Backlog and dead workers. The primary saturation signal. |
| Analytics freshness | `GET /api/v1/analytics/freshness` (token) | Whether Beat and the rollup pool are alive. Lag > 15 min means one of them is not. |
| Structured logs | stdout, JSON; every HTTP access event has `request_id` | Correlation. Request-scoped application events inherit the id and the edge logs it as `rid=`. |
| Celery task events | Redis broker | Per-task timing and failures — `task_send_sent_event` and `worker_send_task_events` are already enabled. |
| Container health | `docker compose ps` | Per-service healthchecks: API via `/health`, workers via `celery inspect ping`, Beat via its schedule file. |

**Alert on these four**, in priority order:

1. `/ready` returning 503 on any API container.
2. Queue depth on `sends.bulk` or `webhooks.process` climbing monotonically for > 15 min.
3. Analytics freshness lag > 30 min (Beat has stopped ticking).
4. Any container in a restart loop — most often `beat` (§14).

### Metrics and tracing

There is no `/metrics` endpoint and no tracer wired in. Adding either means changing the API
surface or the middleware stack, which is out of scope here. The two low-friction paths, both
purely additive at the deployment layer:

- **Celery metrics** — run Flower or `celery-exporter` as an extra service against the same broker.
  Task events are already being emitted, so this needs no application change:

  ```yaml
  # docker-compose.override.yml
  services:
    flower:
      image: mher/flower:2.0
      command: ["celery", "--broker=redis://:${REDIS_PASSWORD}@redis:6379/0", "flower"]
      expose: ["5555"]     # never publish this port — it has no authentication of its own
      depends_on: { redis: { condition: service_healthy } }
  ```

- **HTTP metrics and traces** — `prometheus-fastapi-instrumentator` or the OpenTelemetry FastAPI
  instrumentation both attach in `create_app()` (`backend/app/main.py`) in a few lines. That is an
  application change and belongs in a normal reviewed commit, not in a deployment step.

Until then, the edge access log carries `rt=` (request time) and `urt=` (upstream time) per
request, which is enough to find a slow endpoint without any instrumentation.

---

## 13. Capacity, limits and logs

### Log rotation

Every service declares the `json-file` driver capped at `10m × 5` files (≈50 MB per container,
≈500 MB for the stack). Docker's default is **unbounded**, and an unbounded log on the same disk as
`mysql-data` eventually takes the database down. If you ship logs to an aggregator, point the
driver at it instead — do not simply remove the cap.

Application logs are JSON on stdout. Every canonical `http_request` event has a `request_id`, and
request-scoped application events inherit it (`app/core/logging.py`). Lifecycle events outside a
request do not invent one. The edge access log carries the same id as `rid=`, so an nginx line joins
to the API lines it produced:

```bash
docker compose -f docker-compose.production.yml logs api | grep '"request_id":"<id>"'
```

### Resource limits

None are set, deliberately — a wrong memory ceiling shows up as an OOM-killed worker mid-campaign,
which is worse than no ceiling. Set them once you have measured your own load, in an override file:

```yaml
# docker-compose.override.yml
services:
  worker-bulk:
    deploy:
      resources:
        limits:   { cpus: "2.0", memory: 1500M }
        reservations: { memory: 512M }
```

Two numbers to keep consistent when you scale:

- **Database connections.** Each API container opens up to `DB_POOL_SIZE + DB_MAX_OVERFLOW` (10+10)
  connections *per uvicorn worker process*, and each Celery worker up to the same per concurrency
  slot. `MYSQL_MAX_CONNECTIONS` (default 300) must stay above the fleet total, or new containers
  fail to connect while existing ones look healthy.
- **Send throughput** is paced by the rate gate, not by worker count. Adding `worker-bulk` replicas
  past the number's messages-per-second ceiling buys queue depth, not delivery speed.

---

## 14. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `exec /usr/local/bin/docker-entrypoint.sh: no such file or directory` | The script was checked out with CRLF endings. `.gitattributes` pins `*.sh` to LF — re-clone or run `git add --renormalize .` |
| Image build fails at `pip install .` with a missing `README.md` | `backend/README.md` was deleted; `pyproject.toml` declares it as the project readme |
| Frontend image build fails at `COPY nginx.conf` | `frontend/nginx.conf` moved out of the build context — it must sit beside `frontend/Dockerfile` |
| Backend image is multi-GB / builds slowly | `backend/.dockerignore` missing, so the host `.venv` is being uploaded into the context |
| Stack never starts, `redis` unhealthy with `NOAUTH` | `REDIS_PASSWORD` set for the app but not for the healthcheck, or vice versa — both read the same variable, so check `--env-file` is actually being passed |
| `beat` restarts in a loop, nothing periodic runs | `/var/run/celery` not writable by the non-root `app` user. The image creates and chowns it; a volume created against an older image keeps the old root ownership — `docker volume rm wa-platform_beat-data` and recreate |
| Exports and media fail although `/ready` says storage is up | Same cause on `media-data`: the readiness probe is read-only, so it cannot see an unwritable directory. Recreate the volume as above |
| `GET /api/v1/queues` returns 500 | Redis is unreachable. The endpoint surfaces the broker error rather than degrading to 503, so a 500 here means "check Redis", not "the API is broken". `/ready` is the authoritative dependency signal — it reports `redis: down` correctly. Changing the status code would alter the API contract, so it is left as-is. |
| Access log lines are plain text, not JSON | An older build. `configure_logging` must neutralise the parent `uvicorn` logger, not just `uvicorn.access` — the parent holds a stderr handler with `propagate = False` and would otherwise swallow every request line before it reaches the JSON handler. The two lines uvicorn emits *before* application startup stay plain; that is unavoidable and harmless. |
| API access events are duplicated | An older build. The application middleware owns the correlated `http_request` event; `uvicorn.access` is disabled after logging configuration. |
| `/ready` 503, storage down | `media-data` not mounted in that role, or path not writable |
| Dashboard empty, freshness lag climbing | Beat not running, or `worker-jobs` not consuming `analytics.rollup` |
| Webhooks rejected | `META_APP_SECRET` mismatch — signature verification fails closed |
| Sends accepted then never delivered | `worker-bulk` down, or the rate gate pacing (check `/api/v1/queues`) |
| Export stuck "preparing" | `worker-jobs` down, or storage unwritable; check the `export_failed` log line |
| 413 on upload | Larger than `client_max_body_size` (25 MB) in `deploy/nginx/nginx.conf` |
| Login brute-force protection appears ineffective | A proxy in front of nginx — every client shares one bucket. Configure `set_real_ip_from` (§6) |
| Browser console: blocked script/style by CSP | A third-party origin was introduced. Widen the specific directive in `deploy/nginx/nginx.conf`; never fall back to `unsafe-inline` for `script-src` |
| WhatsApp QR screen says the session must be paired again after a restart | The `waha-sessions` volume is missing or was pruned. See §15 |

---

## 15. WhatsApp QR provider (WAHA) — optional

The QR/WhatsApp channel (ADR-0021 Class B) is **opt-in and off by default**. With
`WAHA_BASE_URL` unset the backend registers no provider runtime and the QR screen reports
`configured=false` to every caller, so a deployment that has not adopted it runs exactly the stack
it ran before.

### Topology

| Property | Value | Why |
|---|---|---|
| Image | `devlikeapro/waha@sha256:33ecd1b7…` | **Digest-pinned, never a tag.** The provider certification evidence is for one immutable build; a floating tag can be repointed upstream and would silently invalidate it. |
| Engine | `NOWEB` | The only engine the adapter is certified against. It fails closed (`WahaEngineNotApproved`) on anything else. |
| Network | Compose network only — **no published port** | WAHA's API is a WhatsApp bridge. Only the backend reaches it, at `http://waha:3000`. Nginx does not proxy it and nothing routes to it from outside. Local development binds `127.0.0.1` only. |
| Session state | `waha-sessions` → `/app/.sessions` | `noweb/waha.sqlite3` (session registry) plus `noweb/<session>/` (per-session store). |

Enable it explicitly:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production --profile waha up -d
```

Required in `.env.production` when the profile is enabled: `WAHA_API_KEY`,
`WAHA_BASE_URL=http://waha:3000`, `WAHA_SESSION_NAME`, `WAHA_WEBHOOK_HMAC_SECRET` and
`WAHA_ORGANIZATION_ID`. The HMAC secret signs inbound deliveries and is verified over the raw body
before anything is parsed; leaving it empty rejects **every** delivery rather than accepting
unsigned ones.

Generate `WAHA_WEBHOOK_HMAC_SECRET` as a dedicated high-entropy value. It is not Meta's webhook
verification token, Meta's app secret, the WAHA API key, or WhatsApp session material, and none of
those values may be reused for it. Inject the same dedicated value into the backend and WAHA
containers through the deployment secret store; never place it in a Compose command, log, ticket,
screenshot, or tracked file.

### Signed webhook delivery

Production Compose configures one **global** WAHA webhook sender:

- callback: `http://api:8000/api/v1/webhooks/waha` on the private Compose network;
- events: `message`, `message.any`, and `message.ack` only;
- authentication: `X-Webhook-Hmac`, SHA-512 over the exact raw JSON body;
- retries: 15 attempts, constant two-second delay, on every delivery error.

Global configuration is intentional. The deployment owns one governed receiver, the signing key
stays in container environment rather than being persisted in a session config, and a Compose
restart reapplies the configuration before restored sessions start. Do not also add `config.webhooks`
to session creation: WAHA combines global and per-session webhooks, which would duplicate every
delivery. The certified 2026.7.2 sender has no configured request timeout; the bounded retry count
limits retry quantity but cannot bound one hung HTTP request. Keep the callback private, local and
responsive, and alert on WAHA webhook-send failures.

Local development uses `http://host.docker.internal:8000/api/v1/webhooks/waha`; the Compose
`host-gateway` mapping provides that internal route on Linux and Docker Desktop supplies it on its
supported hosts. The provider port remains loopback-only. Start the backend with the same
`WAHA_WEBHOOK_HMAC_SECRET` as the root Compose environment before exercising the webhook path.

Changing the WAHA HMAC secret requires a coordinated restart: update the backend and WAHA secret
values together, restart the API/worker roles and WAHA service, then validate a signed controlled
delivery. A mismatch fails closed with HTTP 403 and is retried by WAHA. It never authorizes falling
back to unsigned delivery.

### Why the session volume is not optional

WAHA holds the WhatsApp credentials obtained when a human scanned the QR code. They live only in
`/app/.sessions`. Without the volume, any container restart brings the provider back holding no
session at all: it answers normally, but reports `404 Session not found` for a connection the
platform still records as paired. The QR screen then shows **"WhatsApp is reachable but no longer
has this connection's session"** and requires a fresh scan — recoverable, but it means an outage of
the WhatsApp channel until someone is physically present with the phone.

Treat `waha-sessions` as stateful data: snapshot it with `mysql-data`, and never prune it to
reclaim disk.

### Operator procedures

| Situation | What the screen says | Action |
|---|---|---|
| Provider container down | Provider unavailable; reconnect blocked | Restore the container. Durable pairing truth is preserved — do **not** re-scan. |
| Provider up, session gone | "reachable but no longer has this connection's session" | Re-pair: open **Channels → WhatsApp (QR)**, start the connection, scan the QR with the linked handset. |
| Session paused/degraded, still paired | Reconnect available | Use **Reconnect**. No new QR is required. |
| Deliberate disconnect | — | Use **Log out** (requires explicit confirmation). This invalidates the WhatsApp credentials and a new scan is required afterwards. |

Nothing re-creates a session automatically, and no code path deletes one: re-establishing a
session is always an explicit operator action, so an outage can never silently unlink an account.

### Disable / roll back

Stop the provider and clear `WAHA_BASE_URL`; the backend returns to `configured=false` and the rest
of the platform is unaffected. Meta-based messaging is entirely independent and keeps running.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production stop waha
```

Leave the `waha-sessions` volume in place unless you intend to force a re-scan — removing it
discards the WhatsApp credentials.
