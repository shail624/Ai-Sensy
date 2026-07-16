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
│   └── tests/        unit / integration / API tests
├── frontend/         React + TypeScript + Vite + Tailwind SPA
│   └── src/          application source
├── docs/             frozen architecture documents (01–12) + research
├── docker-compose.yml  local MySQL + Redis for development
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
- Frontend: `cd frontend && npm test`

## Implementation status

Module 1 (Foundation + Authentication + RBAC) is being built step by step per the
frozen documents. See `CHANGELOG.md` and Doc 12 §56 (module manifest) for scope.
