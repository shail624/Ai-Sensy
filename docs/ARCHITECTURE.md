# Architecture — Self-Hosted WhatsApp Business Platform

> Internal business platform built on the **Official Meta WhatsApp Cloud API**.
> Not a SaaS. Single-tenant, self-hosted, engineered for a 10-year lifespan.

---

## 1. Guiding principles

| Principle | How it is applied |
|-----------|-------------------|
| **Clean Architecture** | Strict layering: API → Service → Repository → Model. Dependencies point inward. |
| **SOLID** | Single-responsibility services; interfaces (protocols) for repositories; DI everywhere. |
| **Repository Pattern** | All persistence goes through repositories. Services never touch the ORM session directly for queries beyond the repo API. |
| **Dependency Injection** | FastAPI's dependency system wires sessions, repositories, services, and the current-user context. |
| **Async everywhere** | Async SQLAlchemy 2.0, async httpx, async endpoints. No blocking calls in the request path. |
| **Type-safe** | Pydantic v2 schemas at the edges; SQLAlchemy 2.0 typed `Mapped[]` models; mypy-friendly. |
| **Secure by default** | Argon2id password hashing, JWT access/refresh split, RBAC on every protected route, no secrets in code. |
| **Observable** | Redacted structured JSON logging, bounded request-id correlation across nginx/API, and dependency-aware health endpoints. |
| **Tested** | Unit tests for pure logic, integration tests for the full API against a real (SQLite) database. |

---

## 2. Layered design

```
┌──────────────────────────────────────────────────────────────┐
│  API layer  (app/api)                                          │
│  - FastAPI routers / endpoints                                 │
│  - Request/response validation via Pydantic schemas            │
│  - Auth & RBAC dependencies (app/api/deps.py)                  │
└───────────────▲──────────────────────────────────────────────┘
                │ calls
┌───────────────┴──────────────────────────────────────────────┐
│  Service layer  (app/services)                                 │
│  - Business logic & orchestration                              │
│  - Transaction boundaries                                      │
│  - Raises domain exceptions (app/core/exceptions.py)           │
└───────────────▲──────────────────────────────────────────────┘
                │ uses
┌───────────────┴──────────────────────────────────────────────┐
│  Repository layer  (app/repositories)                          │
│  - CRUD + query composition over SQLAlchemy models             │
│  - The ONLY place that builds ORM queries                      │
└───────────────▲──────────────────────────────────────────────┘
                │ maps
┌───────────────┴──────────────────────────────────────────────┐
│  Model layer  (app/models)                                     │
│  - SQLAlchemy 2.0 declarative models (Mapped[])                │
│  - Mixins: timestamps, soft-delete, UUID/int PK                │
└──────────────────────────────────────────────────────────────┘
```

Cross-cutting concerns live in `app/core` (config, security, logging, exceptions,
constants) and `app/db` (engine, session, declarative base, mixins).

---

## 3. Runtime topology (Docker Compose)

```
                         ┌───────────────┐
        Internet ───────▶│     nginx     │  (reverse proxy, TLS termination)
                         └──────┬────────┘
              ┌─────────────────┼──────────────────┐
              ▼                                     ▼
       ┌────────────┐                        ┌────────────┐
       │  frontend  │ (Module 2, React/Vite) │  backend   │ (FastAPI / uvicorn)
       └────────────┘                        └─────┬──────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    ▼                               ▼                        ▼
              ┌───────────┐                  ┌────────────┐           ┌────────────┐
              │   MySQL   │                  │   Redis    │           │   Celery   │
              │ (primary) │                  │ (broker +  │◀──────────│  worker    │
              └───────────┘                  │  cache)    │           │  + beat    │
                                             └────────────┘           └────────────┘
```

- **backend** — FastAPI app (this and later modules).
- **MySQL 8** — primary datastore.
- **Redis 7** — Celery broker/result backend + application cache + rate-limit store.
- **Celery worker / beat** — async jobs (campaign sending, retries, scheduled tasks) — wired from Module 6, container defined from Module 1.
- **nginx** — reverse proxy; single public entrypoint.

---

## 4. Technology choices & rationale

| Concern | Choice | Why |
|---------|--------|-----|
| Web framework | **FastAPI** | Async, type-driven, OpenAPI out of the box. |
| ORM | **SQLAlchemy 2.0 (async)** | Mature, typed `Mapped[]` API, portable across MySQL/SQLite. |
| Migrations | **Alembic** | First-class SQLAlchemy migrations, async env. |
| DB driver | **aiomysql** (MySQL) / **aiosqlite** (tests) | Async MySQL in production; SQLite keeps tests hermetic and fast. |
| Validation | **Pydantic v2 + pydantic-settings** | Fast, strict, env-driven settings. |
| Password hashing | **argon2-cffi (Argon2id)** | OWASP-recommended; avoids bcrypt's 72-byte limit and passlib version pitfalls. |
| Tokens | **PyJWT** | Standard, minimal, well-audited. |
| HTTP client | **httpx** (async) | For Meta Cloud API calls (from Module 4). |
| Background jobs | **Celery + Redis** | Battle-tested distributed task queue. |
| Tests | **pytest/Vitest + Playwright Chromium + httpx** | Hermetic logic/API coverage plus one focused real-stack browser journey and a deployed latency canary. |

> **Python version:** production images target **Python 3.13** on the digest-pinned
> `python:3.13.14-alpine3.24` base.
> The pinned dependencies also run on 3.14 so the suite can be executed on a
> developer machine that has a newer interpreter.

---

## 5. Security model (Module 1 scope)

- **Passwords:** Argon2id, per-password salt handled by the hasher. Never logged.
- **Access token (JWT):** short-lived (default 30 min), carries `sub` (user id),
  `type=access`, and a `jti`. Signed HS256 with `SECRET_KEY`.
- **Refresh token (JWT):** long-lived (default 14 days), `type=refresh`, rotated on use.
- **RBAC:** Users ⇄ Roles (many-to-many), Roles ⇄ Permissions (many-to-many).
  Permissions are strings like `users:read`, `roles:manage`. A `require_permissions(...)`
  dependency enforces them per route. A `superuser` bypass exists for the bootstrap admin.
- **No hard-coded secrets:** everything comes from environment / `.env`.

See [`docs/modules/01-authentication.md`](modules/01-authentication.md) for the full module spec.

---

## 6. Directory layout

The root `e2e/` package owns the pinned Playwright journey, while root `scripts/` owns the
provider-neutral quality, security, image, and deployed-stack orchestration.

```
Ai Sensy Project/
├── docker-compose.yml            # full stack
├── docker-compose.override.yml   # dev conveniences (hot reload, exposed ports)
├── .env.example                  # compose-level env template
├── backend/                      # FastAPI application (Module 1+)
│   ├── app/
│   │   ├── core/                 # config, security, logging, exceptions
│   │   ├── db/                   # engine, session, base, mixins
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── repositories/         # data-access layer
│   │   ├── services/             # business logic
│   │   ├── api/                  # routers, endpoints, deps
│   │   └── seeds/                # initial roles/permissions/admin
│   ├── alembic/                  # migrations
│   └── tests/                    # unit + integration
├── frontend/                     # React app (Module 2)
└── docs/                         # architecture, roadmap, per-module specs
```
