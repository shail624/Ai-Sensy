# Self-Hosted WhatsApp Business Platform

Internal enterprise platform for the **Vi Reactivation Team** — built on the Official
Meta WhatsApp Cloud API (Channel 1) and a vendor-neutral Support Connector (Channel 2).
Single-tenant, self-hosted, not SaaS.

> **Architecture is frozen.** The authoritative specification is in [`docs/design/`](docs/design)
> (Docs 01–12). Start with [`12-ENTERPRISE-GOVERNANCE.md`](docs/design/12-ENTERPRISE-GOVERNANCE.md).
> Implementation follows those documents exactly, module by module.

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

`v1.0.0-rc1` contains the complete backend through Analytics & Reporting, the production
deployment topology, and the frontend application across the principal product areas. FR-CON-04
Excel import inspection is preserved at `baseline/fr-con-04-release-ready`. Current unreleased work
is Module 11 hardening: strict backend typing, security/release automation, and the isolated
deployed-stack E2E/performance canary plus defensive observability contracts are complete;
environment monitoring and commissioning evidence are next.

See `IMPLEMENTATION_TRACKER.md` for the verified current state and `CHANGELOG.md` for delivered
changes. The frozen design documents remain the authority for product behavior and contracts.
