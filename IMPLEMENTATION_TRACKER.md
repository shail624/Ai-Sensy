# Implementation Tracker (canonical)

> Single source of truth for project state. Every new session must read this first.
> Update it after each verified milestone. Keep it short: state, not narrative.

_Last updated: 2026-07-25 · reconstructed from Git, frozen designs, generated contracts, and
executable quality gates._

## Current state

- **Branch:** `feature/module6-queue-engine`
- **Release baseline:** `v1.0.0-rc1`; current work is post-RC1 CRM/frontend hardening
- **Migration head:** `0027_analytics` (27 linear revisions, base `0001`)
- **OpenAPI:** 3.1.0 · 133 paths · `frontend/openapi.json` verified against the live app
- **Backend:** 878 tests passed · 18 focused import tests passed · Ruff clean
- **Frontend:** 581 tests passed · TypeScript clean · ESLint clean · production build passed
- **Docker:** development and production Compose models parse cleanly; production images build;
  the backend image boots with the 133-path contract; frontend nginx validates. The full production
  stack was first built and executed on 2026-07-23.
- **Current phase:** post-RC1 CRM/frontend completion and deployment hardening
- **Current milestone:** FR-CON-04 Excel contact import — **RELEASE READY**

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

No implementation remains in the current FR-CON-04 milestone. The next product milestone requires
owner prioritization; do not infer it from the historical branch name.

## Known technical debt

- Backend strict mypy is configured but has no clean baseline: 251 existing errors across 67 files.
  The FR-CON-04 service and schemas add no mypy errors. Establishing a ratcheted baseline is the
  recommended next engineering task.
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
- `alembic check` requires live MySQL; migration integrity is covered by `tests/test_migrations.py`.
- Regenerate the contract with `python scripts/export_openapi.py` from `backend/`, then
  `npm run gen:api` from `frontend/`. Use `python scripts/export_openapi.py --check` as the drift gate.
- Docker Desktop must be running before the production image-build and image-smoke gates execute.
