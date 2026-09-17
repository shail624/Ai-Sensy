# Self-Hosted WhatsApp Business Platform

## UI-REF-03 — manual contact creation (2026-09-13)

Added permission-gated Add Contact and a responsive Create Contact form using the existing
POST /api/v1/contacts endpoint. Name, international mobile number and source are supported;
consent remains unknown. Pending submission is guarded; server errors remain visible and
successful creation refreshes contact search without changing active filters.

PASS: 48 files / 887 frontend tests (8.22s), ESLint, TypeScript and production build.
PASS: local preview created one explicitly named test contact in the isolated preview database;
desktop/mobile form screenshots saved under output/previews/ui-ref-03-create-contact-*.png.
No production data, backend contracts, migrations, GitHub or deployment changed.

Still pending: reference-equivalent DOB/tag entry, country picker, Contacts/Segments secondary
navigation, full action/filter menus and cumulative production acceptance. No completion
percentage increase or claim of full AiSensy parity. See design document 74.

Internal enterprise platform for the **Vi Reactivation Team** — built on the Official
Meta WhatsApp Cloud API (Channel 1) and a vendor-neutral Support Connector (Channel 2).
Single-tenant, self-hosted, not SaaS.

Latest UI checkpoint: **UI-REF-02 — Live Chat shell alignment**. Reference-order views/search,
empty desktop columns and mobile filters verified; frontend **883/883**, types/build/lint pass.
Full feature/visual parity remains pending. [Evidence and limitations](docs/design/73-UI-REF-02-LIVE-CHAT-SHELL.md).

Previous local UI update: **UI-REF-01 — screenshot-aligned navigation**. Compact labelled rail,
persistent Manage and real settings deep links implemented; frontend **882/882**, types/lint/build
and bounded desktop/mobile preview pass. Full AiSensy screen/feature parity and production
readiness are **not** certified. See [the comparison and gaps](docs/design/72-UI-REF-01-SCREENSHOT-ALIGNED-NAVIGATION.md).

The permanent product target is an original, premium enterprise experience for the Vi Reactivation
Team, with approved workflow depth, usability, reliability, and visual quality comparable to or
better than AiSensy. AiSensy is a private benchmark—not an implementation source—and this
repository must use original code, identity, components, and assets with real backend-owned state.

> **Architecture is frozen.** The authoritative specification is in [`docs/design/`](docs/design)
> (Docs 01–12). Start with [`12-ENTERPRISE-GOVERNANCE.md`](docs/design/12-ENTERPRISE-GOVERNANCE.md).
> Implementation follows those documents exactly, module by module.

Current product and quality authority: [`VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`](VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md),
[`REPOSITORY_RULES.md`](REPOSITORY_RULES.md),
[`ADR-0012`](docs/adr/0012-premium-aisensy-parity-product-goal.md), and the
[`Premium Product Experience Standard`](docs/design/25-PREMIUM-PRODUCT-EXPERIENCE-STANDARD.md).
These are additive governance decisions; they do not replace frozen architecture or historical
delivery evidence.

## Repository layout

```
.
├── backend/          FastAPI backend (Python 3.13, SQLAlchemy 2, Celery, Alembic)
│   ├── app/          application package (core / db / api …)
│   ├── alembic/      database migrations
│   ├── tests/        unit / integration / API tests
│   └── Dockerfile    multi-stage production image (+ docker-entrypoint.sh)
├── frontend/         React + TypeScript + Vite + Tailwind SPA
│   ├── src/          application source
│   └── Dockerfile    multi-stage production image (+ nginx.conf for the SPA)
├── deploy/
│   ├── DEPLOYMENT.md production runbook — build, migrate, start, scale, back up, roll back
│   └── nginx/        edge reverse-proxy configuration
├── docs/             frozen architecture documents (01–12) + research
├── docker-compose.yml             local MySQL + Redis for development
├── docker-compose.production.yml  full production topology (10 services)
└── CHANGELOG.md
```

`e2e/` contains the pinned Playwright Chromium journey; root `scripts/` contains the
provider-neutral quality, security, image, and deployed-stack gates.

## Prerequisites

- Python 3.13+ (3.14 also works for local tests), Node.js 20+, and Docker (for MySQL/Redis).

## Local development

1. **Start infrastructure** (MySQL + Redis):
   ```
   cp .env.example .env
   docker compose up -d
   ```
2. **Backend**:
   ```
   cd backend
   cp .env.example .env
   python -m venv .venv && .venv/Scripts/activate   # (Windows) or: source .venv/bin/activate
   pip install -e ".[dev]"
   uvicorn app.main:app --reload
   ```
   API docs at http://localhost:8000/docs · liveness at http://localhost:8000/health
3. **Frontend**:
   ```
   cd frontend
   npm install
   npm run dev
   ```
   App at http://localhost:5173
4. **Browser-test tooling** (required by the repository quality gate):
   ```
   cd e2e
   npm ci
   ```

## Tests

- Backend (hermetic; SQLite, no external services): `cd backend && pytest`
- Backend lint and type gate: `cd backend && ruff check app tests scripts && mypy app`
- Frontend: `cd frontend && npm test`

### Running the live-MySQL tests

`backend/tests/test_migrations_mysql.py` proves the migration chain against a *real* MySQL 8 rather
than SQLite, and skips cleanly when no server answers. Docker is the convenience, not the
requirement — any MySQL 8 works, including one installed directly:

```bash
apt-get install -y mysql-server                 # or: docker compose up -d
mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'root'"
./scripts/local_services.sh                     # starts MySQL + Redis if they are not already up
cd backend && DB_HOST=127.0.0.1 MYSQL_ROOT_PASSWORD=root pytest
```

With a server reachable the full backend suite runs with **zero skips**. Without one it still
passes; the skipped tests simply do not run, which is why they are easy to leave unproven — and
why `scripts/local_services.sh` exists. A machine that restarted turns a zero-skip run back into
six skips with no failure to notice, so the script is idempotent and safe to run before every
suite.

### Sweeping the read surface against a real database

The hermetic suite runs on SQLite, so a query that is only wrong for MySQL passes every test and
fails the first time an operator opens the page. `scripts/live_api_read_sweep.py` closes that gap by
asking a running server for every read the contract declares:

```bash
python scripts/live_api_read_sweep.py --base-url http://127.0.0.1:8000 \
    --email <owner> --password <password> --output output/evidence/live-api-read-sweep.json
```

It fails only on a 5xx or a transport error, and reports separately any path it could not exercise
because the contract does not enumerate that parameter's accepted values.

The provider-neutral Module 11 gate is the automation entry point for local and CI execution:

```bash
python scripts/quality_gate.py static       # offline lint, types, and contract drift
python scripts/quality_gate.py pre-merge    # full tests/build plus source security gates
python scripts/quality_gate.py release      # production images, smoke, scans, and SBOMs
python scripts/quality_gate.py deployed     # release + isolated real-stack browser/perf gate
```

Run it with the backend virtual environment's Python. The heavier profiles require current
advisory-network access; `release` and `deployed` also require Docker. The deployed profile uses a
unique Compose project with disposable volumes, never a developer or production database.
Machine-readable evidence is written to the ignored `.quality-artifacts/` directory.

## Production deployment

```bash
cp .env.production.example .env.production      # fill every REQUIRED value
docker compose -f docker-compose.production.yml --env-file .env.production up migrate
docker compose -f docker-compose.production.yml --env-file .env.production up -d
```

Full procedure — build, schema, first owner, scaling, TLS, backup, rollback and troubleshooting —
is in [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md).

## Implementation status

`v1.0.0-rc1` contains the production deployment topology and the implemented frontend/backend
workflows across the principal product areas. PAR-AUTO-22 remains the last complete `release`
quality profile at **23/23**: 1521 backend tests with zero skips, 832 frontend tests, and security/
dependency/image/SBOM/runtime gates. The current source tree passes **1,733 backend tests with zero
skips** — VAL-01 stood up a real MySQL 8 and cleared the six live-migration tests that every prior
run reported as skipped — plus 971 frontend tests across 57 files, the synchronized 247-path
contract, production build, and a live read sweep of 210 requests over 73 contract-declared GET
paths against MySQL with no 5xx. Read latency at 200,000 campaign recipients is in FIX-01: the
ordinary reads are all under 32ms, and three aggregate reads (`/scan/reachability` filtered by
verdict, `/scan/reachability/counts`, `/templates/usage`) sit at 267–347ms, at or over the 300ms
budget and recorded rather than hidden. Its Docker/security release rerun is pending. The prior cumulative `deployed` proof remains preserved
at **25/25**, including its disposable ten-service browser/performance/failure exercise.
This certifies the repository and local production topology; it does not mean the entire approved
feature roadmap is complete or that a target host has been commissioned. The canonical
31-module table currently averages **82.4%** unweighted (recalculated median **88%**), with exact remaining work
tracked in `MODULE_STATUS.md` and `ROADMAP.md`. FR-CON-04 Excel import inspection is preserved at
`baseline/fr-con-04-release-ready`.

See `IMPLEMENTATION_TRACKER.md` for the verified current state and `CHANGELOG.md` for delivered
changes. The frozen design documents remain the authority for product behavior and contracts.
