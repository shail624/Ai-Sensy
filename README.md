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

## Tests

- Backend (hermetic; SQLite, no external services): `cd backend && pytest`
- Backend lint and type gate: `cd backend && ruff check app tests scripts && mypy app`
- Frontend: `cd frontend && npm test`

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
is Module 11 hardening: the backend now passes its unchanged strict-mypy policy directly.

See `IMPLEMENTATION_TRACKER.md` for the verified current state and `CHANGELOG.md` for delivered
changes. The frozen design documents remain the authority for product behavior and contracts.
