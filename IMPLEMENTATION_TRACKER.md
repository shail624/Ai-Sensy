# Implementation Tracker (canonical)

> Single source of truth for project state. Every new session must read this first.
> Update it after each verified milestone. Keep it short: state, not narrative.

_Last updated: 2026-07-25 · verified from Git, frozen designs, generated contracts, and executable
quality gates._

## Current state

- **Branch:** `feature/module6-queue-engine`
- **Release baseline:** `v1.0.0-rc1`; FR-CON-04 stable baseline
  `baseline/fr-con-04-release-ready` at `b565d0f`
- **Migration head:** `0027_analytics` (27 linear revisions, base `0001`)
- **OpenAPI:** 3.1.0 · 133 paths · `frontend/openapi.json` verified against the live app
- **Backend:** 883 tests passed · Ruff clean · raw strict mypy clean across
  227 source files (down from 251 findings; exact checker mypy 2.3.0)
- **Frontend:** 581 tests passed · TypeScript clean · ESLint clean · production build passed
- **Docker:** development and production Compose models parse cleanly; production images build;
  the backend image boots with the 133-path contract; frontend nginx validates. The full production
  stack was first built and executed on 2026-07-23.
- **Current phase:** Module 11 — Hardening & Deployment (M-F Enterprise)
- **Current milestone:** backend strict typing completion — **RELEASE READY**

## Completed deliverables

| Area | Delivered |
|---|---|
| Foundation | Identity, authentication, RBAC, audit, settings, API keys, migrations `0001`–`0004` |
| CRM + queue | Contacts, tags, segments, attributes, import/export/bulk, queue/storage, migrations `0005`–`0013` |
| WhatsApp core | Channel abstraction, WABAs/numbers, webhooks, conversations, messages, media, migrations `0014`–`0016` |
| Templates + campaigns | Template registry, adaptive rate gate, campaign audience/dispatch/lifecycle/scheduling/cost, migrations `0017`–`0022` |
| Inbox + work | Shared inbox, notes, quick replies, conversation tags, reactions, task/activity engine, migrations `0023`–`0026` |
| Analytics | Rollups, queries, report exports, migration `0027` |
| Frontend | Auth shell, dashboard, contacts/profile, inbox, campaigns, templates, media, channels, segments, pipelines, tasks, analytics, operations, admin, settings |
| Deployment | Ten-service production topology, nginx edge, runbook, container execution fixes and artifact routing |
| Post-RC1 CRM | Premium responsive contacts UI, bulk actions, CSV import, add-selection-to-campaign, and Excel import inspection/wizard support |
| Module 11 hardening | Raw strict mypy clean; typed Celery/async, SQLAlchemy, repository/service, JSON, callback, and iterator seams; ADR-0004 transition retired |

## FR-CON-04 release-ready scope

- Permission-gated, tenant-scoped `POST /api/v1/contacts/import/inspect`.
- Non-mutating `.xlsx` header/sample/sheet/row-estimate inspection using the same openpyxl parser
  and cell rendering as the worker import path.
- Synchronous workbook work moved off the async request loop and bounded to 25 MB for inspection.
- Import wizard accepts CSV up to 100 MB and `.xlsx` up to 25 MB for inline inspection; the existing
  async import request contract, mapping, deduplication, routing, and job behavior are preserved.
- ADR-0002 accepted; API/UI design docs, OpenAPI JSON, generated TypeScript types, backend tests,
  frontend tests, and changelog updated.

## Remaining deliverables

No implementation remains in the backend strict-typing milestone. After final release evidence,
Module 11 continues with repository-level automation of the broader CI/E2E/performance/security
gates defined by Docs 8 and 10. The AI assistant module remains intentionally deferred beyond RC1
and is not inferred as the next task.

## Known technical debt

- The production frontend build warns about a 567 kB main chunk; analytics is already lazy-loaded,
  but further route-level splitting remains a performance improvement.
- Frontend tests emit React Router v7 future-flag and Node localStorage experimental warnings.
- `ConversationHistorySection.tsx` retains a contact-scoped conversation API TODO.
- The branch name predates the RC1 and frontend work now accumulated on it.

## Permanent invariants (never violate)

Repository → Service → API layering · all sends through `SendService` · provider payloads stay in
the Meta adapter · Retry Engine is the single authority on classify/backoff · Rate Gate never opens
(fail-safe pacing) · persist-first webhooks · campaign status controls dispatch · frozen modules
are not redesigned · unbuilt surfaces stay absent rather than stubbed · partitioned tables carry no
FKs · frontend API types are generated only, never hand-written.

## Notes for the next session

- Run backend commands from `backend/` via `.venv/Scripts/python.exe` so pytest loads `pyproject.toml`.
- Run the blocking backend type gate directly with `mypy app`; no debt baseline or global error-code
  suppression remains.
- `alembic check` requires live MySQL; migration integrity is covered by `tests/test_migrations.py`.
- Regenerate the contract with `python scripts/export_openapi.py` from `backend/`, then
  `npm run gen:api` from `frontend/`. Use `python scripts/export_openapi.py --check` as the drift gate.
- Docker Desktop must be running before the production image-build and image-smoke gates execute.
