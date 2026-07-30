# Implementation Tracker (canonical)

> Single source of truth for project state. Every new session must read this first.
> Update it after each verified milestone. Keep it short: state, not narrative.

_Last updated: 2026-07-30 · verified from Git, frozen designs, generated contracts, and executable
quality gates._

## Current state

- **Branch:** `feature/module6-queue-engine`
- **Release baseline:** `v1.0.0-rc1`; FR-CON-04 stable baseline
  `baseline/fr-con-04-release-ready` at `b565d0f`
- **Migration head:** `0028_contact_documents` (28 linear revisions, base `0001`)
- **OpenAPI:** 3.1.0 · 141 paths · `frontend/openapi.json` verified against the live app
- **Backend:** 912 tests passed · Ruff clean · raw strict mypy clean across
  232 source files (down from 251 findings; exact checker mypy 2.3.0)
- **Frontend:** 621 tests passed · TypeScript clean · ESLint clean · production build passed
- **Docker:** development and production Compose models parse cleanly; production images build;
  the backend image boots with the 141-path/23-task contract; frontend nginx validates. The isolated
  automated gate validates migrations, owner bootstrap, API/worker/queue health, browser smoke,
  read performance, and project-scoped cleanup.
- **Current phase:** UX convergence — original AiSensy-inspired engagement experience
- **Security automation:** Bandit clean; backend production dependency audit clean; tracked-source
  and built-application-image Trivy HIGH/CRITICAL scans clean; CycloneDX SBOMs generated; release
  profiles are provider-neutral
- **Deployed gate:** Playwright owner login → queued CSV import → persisted contact search/profile
  passed across nginx/SPA/API/MySQL/Redis/Celery; current standard-read evidence is p95 22.7 ms / 30
  samples (<300 ms target)
- **Observability gate:** canonical correlated HTTP events and defensive formatter redaction are
  covered in isolation and in the real stack; Redis loss makes readiness return 503; the mounted
  digest-pinned nginx configuration is syntax-checked
- **Current milestone:** Phase 1 follow-up and chat acquisition utility — **RELEASE READY**

## Completed deliverables

| Area | Delivered |
|---|---|
| Foundation | Identity, authentication, RBAC, audit, settings, API keys, migrations `0001`–`0004` |
| CRM + queue | Contacts, tags, segments, attributes, import/export/bulk, queue/storage, migrations `0005`–`0013` |
| WhatsApp core | Channel abstraction, WABAs/numbers, webhooks, conversations, messages, media, migrations `0014`–`0016` |
| Templates + campaigns | Template registry, adaptive rate gate, campaign audience/dispatch/lifecycle/scheduling/cost, migrations `0017`–`0022` |
| Inbox + work | Shared inbox, notes, quick replies, conversation tags, reactions, task/activity engine, migrations `0023`–`0026` |
| Analytics | Rollups, queries, report exports, migration `0027` |
| Governed customer documents | Contact-linked document records, immutable versions, verification/rejection, expiry, archive, audit/history, signed previews, and migration `0028` |
| Frontend | Auth shell, dashboard, contacts/profile, inbox, campaigns, templates, media, channels, segments, pipelines, tasks, analytics, operations, admin, settings |
| Phase 1 product experience | Business-first responsive shell; command palette/search; premium dashboard and sign-in; customer 360; saved-view/bulk inbox; approval-ready campaign journey; Operations/Admin centers; honest Automation/Reactivation foundations |
| Phase 2 customer engagement | Server-synchronized inbox custom views/pins; customer/notes/AI thread context; governed Broadcast Center; template favorites; segment recents; factual engagement funnel; export navigation; human-controlled AI integration seams |
| Phase 3 reactivation + automation | Ten-route Reactivation workspace; ten-stage pipeline blueprint; 12-tab Customer 360; document boundary; analytics-backed reports; separate Scan Studio boundary; accessible non-executing automation canvas; document-summary AI seam |
| Phase 4A governed documents | Tenant-scoped document workflow shared by Customer 360 and Reactivation; media reuse; least-privilege RBAC; optimistic concurrency; immutable version and decision evidence |
| Compact engagement shell | Six-item task rail by default, permission-aware advanced navigation, original teal engagement palette, and preserved responsive/keyboard navigation |
| Guided campaign journey | Scroll-free progress rail; clear six-step hierarchy; audience/delivery choice cards; customer message preview; compact review/actions; optional AI assistance collapsed by default |
| Live Chat simplicity | Requests/Active/My chats triage over existing filters; advanced controls on demand; compact conversation rows; customer context, notes, labels and AI assistance one click away |
| Audience and retargeting presets | Four marketer-friendly quick-start templates over verified segment facts; preset-shaped saved segments surface as one-click campaign audiences; existing duplicate journey remains the follow-up path; campaign-specific event cohorts remain contract-gated rather than inferred from partial recipient pages |
| Campaign follow-up journey | Completed campaigns expose a clear Create follow-up action; the original definition opens as a fresh editable draft and still passes through the existing audience, schedule, approval and dispatch path |
| Chat link and QR | Every real WhatsApp number can generate a private browser-only `wa.me` link, optional prefilled message and downloadable QR; no tracking, shortening, external QR service, API or schema was introduced |
| Deployment | Ten-service production topology, nginx edge, runbook, container execution fixes and artifact routing |
| Post-RC1 CRM | Premium responsive contacts UI, bulk actions, CSV import, add-selection-to-campaign, and Excel import inspection/wizard support |
| Module 11 hardening | Raw strict mypy clean; provider-neutral static/pre-merge/release/deployed gates; SAST, dependency/source/image scans and SBOMs; isolated ten-service Playwright CSV-import journey; bounded read-latency canary; correlated/redacted runtime logging and dependency-readiness proof |

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

No repository implementation remains in Phase 4A. The active AiSensy-inspired parity roadmap is
recorded in Design Document 20, with the five-phase execution sequence in Design Document 21;
The remaining five-phase roadmap deliverables and all additive product domains remain separately
governed milestones rather than simulated UI. The remaining Phase 4 contract backlog is recorded
in Design Documents 18 and 19 and requires separately approved milestones.
Payments, catalogs, carts, checkout, orders, refunds and commerce journeys are explicitly excluded
from the product roadmap and must not be introduced as placeholders or future milestones.
Target-environment work still needs monitoring and commissioning evidence: log shipping,
metrics/dashboards, alert firing and dead-man validation, and external synthetic checks. Full
capacity certification remains a separate Performance Lab task. The AI assistant module remains
intentionally deferred beyond RC1.

## Release blockers

- Full load/stress/spike/soak and 1M-contact capacity evidence requires the isolated Performance Lab.
- Metrics/dashboard/alerting/log-shipping and external synthetic-monitor evidence remain target-
  environment deployment work; repository tests cannot prove receiver delivery or dead-man alerts.
- TLS/host hardening, UAT, verified restore, rollback rehearsal, and production approval are
  environment commissioning evidence and cannot be truthfully closed by repository tests.

## Known technical debt

- The production frontend build warns about a 707 kB main chunk. Analytics, Reactivation,
  Automation, and Scan Studio are route-split; further route-level splitting remains a performance
  improvement.
- Frontend tests emit React Router v7 future-flag and Node localStorage experimental warnings.
- The production dependency audit reports two moderate React Router advisories. Their fixed line is
  React Router 7.18+, so remediation requires an explicit routing upgrade rather than a silent patch.
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
- Run `python scripts/quality_gate.py static`, `pre-merge`, `release`, or `deployed` from the repository root
  using the backend virtual-environment Python. Generated security/SBOM evidence is ignored under
  `.quality-artifacts/`; Docker scanner cache is ignored under `.quality-cache/`.
- `alembic check` requires live MySQL; migration integrity is covered by `tests/test_migrations.py`.
- Regenerate the contract with `python scripts/export_openapi.py` from `backend/`, then
  `npm run gen:api` from `frontend/`. Use `python scripts/export_openapi.py --check` as the drift gate.
- Docker Desktop must be running before the production image-build and image-smoke gates execute.
