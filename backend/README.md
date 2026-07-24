# Backend — Self-Hosted WhatsApp Business Platform

FastAPI application for the **Vi Reactivation Team** platform: the HTTP API, the Celery queue
engine, and the Alembic schema. Python 3.13+, SQLAlchemy 2 (async), MySQL 8, Redis 7.

> This file is not decoration. `pyproject.toml` declares `readme = "README.md"`, so the packaging
> build reads it — without this file `pip install .` fails, and with it the production image build.

## Layout

```
backend/
├── app/
│   ├── main.py          FastAPI factory: logging, middleware, error handlers, routers
│   ├── cli.py           operational CLI (`python -m app.cli create-owner`)
│   ├── core/            config, logging, middleware, security, redis, rate limiting
│   ├── api/             health probes + versioned API surface (/api/v1)
│   ├── db/              async engine, session factory, mixins
│   ├── models/          SQLAlchemy models
│   ├── repositories/    data access (the only layer that touches the session directly)
│   ├── services/        business logic and transaction boundaries
│   ├── schemas/         Pydantic request/response models
│   ├── queue/           Celery app, queue registry, retry engine, heartbeats
│   ├── channels/        provider adapters (Meta Cloud API)
│   ├── analytics/       rollup tasks
│   ├── crm/             contact import/export and campaign tasks
│   ├── rbac/            permission catalog and role seeding
│   └── storage/         pluggable object storage (local volume / S3-compatible)
├── alembic/             migrations (linear, expand-only)
├── tests/               hermetic suite — SQLite, no external services required
├── docker-entrypoint.sh container entrypoint: api | worker | beat | migrate
└── Dockerfile           multi-stage production image
```

## Local development

```bash
cp .env.example .env
python -m venv .venv && .venv/Scripts/activate   # Windows; or: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Requires MySQL and Redis — start them from the repository root with `docker compose up -d`.

API docs at http://localhost:8000/docs · liveness at http://localhost:8000/health

## Checks

```bash
pytest                          # hermetic suite (SQLite; no MySQL or Redis needed)
ruff check app tests scripts    # lint
mypy app                        # strict type gate
```

## Operational entry points

| Command | Purpose |
|---|---|
| `alembic upgrade head` | Apply migrations. Idempotent; run to completion before serving. |
| `python -m app.cli create-owner` | Create the first organization and Owner user (first deploy only). |
| `python -m scripts.export_openapi` | Regenerate `frontend/openapi.json` from the live app. |

The container image wraps the first two through `docker-entrypoint.sh`, which selects a role
(`api`, `worker`, `beat`, `migrate`) from its first argument. See
[`deploy/DEPLOYMENT.md`](../deploy/DEPLOYMENT.md) for the production procedure.
