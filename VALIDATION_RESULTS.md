# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence; it must
> be refreshed after every milestone. CORE-04 starting GitHub baseline: `320b0bd`; the milestone
> delivers governed KYC operations by extending existing Vi, Document, Task, Reactivation, Customer
> 360, Audit, Timeline, RBAC, and SLA authorities. The canonical deployed-stack gate passed.

Last synchronized: `2026-08-02T14:44:11+05:30`.

## CORE-04 KYC operations

| Validation item | Status | Latest evidence |
|---|---|---|
| Creation prerequisites and governed checks | PASS | Eligible document-ready Reactivation cases create one tenant-scoped KYC case idempotently; holder, Delhi-presence and active-number checks plus invalid/stale commands pass service/API tests. |
| Protected document checklist | PASS | Aadhaar/PAN checklist entries reference verified same-tenant/same-contact Document Center records; protected-access denial passes and no schema/API/UI/audit field stores identity numbers. |
| Appointment lifecycle | PASS | Creation reuses idempotent TaskService; reschedule, completion and cancellation reuse existing Task commands, immutable events, audit and Customer Timeline evidence. |
| Reviewer/manager authority separation | PASS | Requester cannot review; manager must differ from requester and approved reviewer; structured rejection/information reasons, approval prerequisites and immutable decision history pass. |
| Reactivation handoff | PASS | Only valid manager approval advances the existing case through `kyc_pending` to `verification` using the CORE-02 transition authority, optimistic concurrency and immutable stage/audit/Timeline evidence. |
| RBAC and tenant isolation | PASS | KYC/document/task read-write-decide-approve permissions and cross-tenant denial pass focused service/API tests; UI exposes permission-aware read-only/denied states. |
| Customer 360 and shared reuse | PASS | Existing Reactivation drawer, protected DocumentWorkspace, Task lifecycle, Customer 360 section, Contacts/User directory, Audit, Timeline, RBAC, SLA and design-system states are extended; no parallel authority exists. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover factual queue/detail, checklist/actions, loading, empty, error, read-only, accessible labels/tabs/drawer, desktop table and mobile-card transformation, and no mock fallback. |
| Authenticated representative-data browser review | PENDING – Host Machine Validation | The local protected route and anonymous redirect were verified; a target-host account with representative KYC/protected-document data and final desktop/tablet/mobile browser matrix is required for authenticated visual/WCAG sign-off. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for density, filters, forms, action placement and layered workspaces; no proprietary code, asset, branding, exact styling, wording or reference file is shipped. |
| Focused and full tests | PASS | 24 focused backend and 33 focused cross-feature frontend tests pass; canonical suites pass 940/940 pytest and 646/646 Vitest. |
| Migration and API boundary | PASS | One additive head `0033_kyc_operations` fills verified reference/Task/reason constraints; OpenAPI advances only from 184 to 188 paths (+4) and generated TypeScript drift is clean. |
| Milestone boundary | PASS | No SIM fulfilment, Activation Queue, fake operational data, plaintext identity number, duplicate document/task/approval/timeline system, or completed-module rebuild was introduced. |

## CORE-03 Reactivation pipeline

| Validation item | Status | Latest evidence |
|---|---|---|
| Persisted pipeline and factual counts | PASS | Tenant-scoped joined projection returns all fifteen approved stage counts and bounded cards from real cases, contacts, owners, eligibility, tasks, documents, SLA, reservation, family, and conversion facts; no fixture fallback exists. |
| Governed transitions and concurrency | PASS | All permitted/rejected lifecycle moves pass exact matrix tests; drag, keyboard, and drawer actions use the CORE-02 transition service, server-published targets, idempotency, and `row_version`; stale writes return conflict. |
| RBAC and tenant isolation | PASS | Read/write/transition actions are permission-aware; cross-tenant pipeline, note, case, owner, task, and document access fails closed in service/API tests. |
| Assignment and immutable evidence | PASS | Assignment/number edits reuse the versioned CORE-02 update authority; transitions and notes retain immutable stage/audit/Customer Timeline evidence. |
| Shared module reuse | PASS | Existing Contacts/User directory, Customer 360, Tasks/reminders, Documents, Audit, Timeline, SLA, Modal, router, and design system are extended in place; no completed module was rebuilt. |
| UI states and accessibility | PASS | Focused tests cover loading, empty, error, permission, responsive board/list, pointer/keyboard movement, drawer labelling/focus, and no-mock guarantees. Authenticated 1280×720, 768×1024, and 390×844 review found no page-level horizontal overflow. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for shell, filters, density, modal/drawer and responsive patterns; no proprietary code, asset, branding, exact styling, wording, or reference file is shipped. |
| Focused CORE-03 tests | PASS | 6 focused backend service/API tests and 9 focused Reactivation/foundation frontend tests pass; the full suites pass 938/938 and 641/641. |
| Migration/API boundary | PASS | Migration remains single head `0032`; verified projection/note gaps add only 2 paths, advancing OpenAPI from 182 to 184 with generated TypeScript drift clean. |
| Milestone boundary | PASS | No KYC operations workspace, SIM fulfilment UI, Activation Queue, migration, mock lead card, fake count, local-only workflow state, or duplicate authority was introduced. |

## CORE-02 Vi domain foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Domain records and constraints | PASS | All ten approved records are registered; tenant/contact/case uniqueness, fixed values, positive/ordered SLA constraints, serial uniqueness, and immutable histories are covered by model/migration tests. |
| Transition and prerequisite rules | PASS | Reactivation, KYC preparation/approval, SIM fulfilment, activation approval/completion, and SLA command tests passed; invalid/stale commands fail closed. |
| Idempotency and concurrency | PASS | Same-key/same-command replays return existing outcomes; mismatched reuse and stale row versions return conflict evidence in focused tests. |
| RBAC and tenant isolation | PASS | Fifteen additive permissions, role defaults, API denial, manager approval boundaries, public UUID scoping, and cross-tenant 404 behavior passed. |
| Audit, Timeline, and durable facts | PASS | Material commands atomically append audit rows, Customer Timeline projections, and existing-ledger business events without introducing a parallel authority. |
| Milestone boundary | PASS | No Reactivation Kanban, KYC workspace, SIM fulfilment UI, Activation Queue, fake data, placeholder workflow, duplicate CRM pipeline, document store, timeline, or event bus was added. |
| Focused CORE-02 tests | PASS | 6 focused service/API/migration tests passed, including migration upgrade/downgrade/re-upgrade. |
| Deployed domain foundation | PASS | MySQL applied `0032`; API, Redis, Celery workers/beat, frontend, and nginx reached healthy state in the isolated ten-service stack. |

## CORE-01 navigation and product shell

| Validation item | Status | Latest evidence |
|---|---|---|
| Permitted navigation catalogue | PASS | Six-item task rail, grouped More surface, shared create actions, honest maturity labels, and permanent scope guard passed focused and full-suite tests. |
| RBAC and excluded concepts | PASS | Permission-filtered navigation/create/search tests passed; Ads, Payments, Billing, marketplace, SaaS/multi-project, and commerce destinations remain absent. |
| Keyboard and focus behavior | PASS | Menus, command palette, and mobile drawer expose state, close on Escape where applicable, trap dialog focus, and restore invoking focus. |
| Responsive active states | PASS | Compact/expanded rail, secondary routes, and primary mobile-overflow routes passed focused tests; mobile targets are at least 44px. |
| Reference and originality review | PASS | Six paired full/viewport workflows were inventoried; authenticated 1280×720 shell, More, and command palette were compared without importing reference code or assets. |
| Authenticated browser smoke | PASS | Dashboard shell and factual downstream-error states rendered at 1280×720 with a 72px rail, 672px command palette, and no horizontal overflow. |
| Focused frontend tests | PASS | 30/30 navigation/foundation tests passed after the final responsive active-state correction. |
| Source/migration/API boundary | PASS | Product scope sources, all 31 migrations, OpenAPI JSON, and generated TypeScript contract are unchanged from the CORE-01 baseline. |

## GOV-02 documentation and governance

| Validation item | Status | Latest evidence |
|---|---|---|
| Required governance files | PASS | All ten required root documents, ADR-0012, and Design Document 25 are present and non-empty. |
| Markdown structure and relative links | PASS | Heading/table structure and repository-relative Markdown links passed the GOV-02 static check. |
| Product-goal and priority consistency | PASS | Scope, rules, roadmap, tracker, ADR, and experience standard agree on the permanent target and ordered priorities. |
| Reference boundary and originality | PASS | Approved/conditional/prohibited categories, local-only ignore policy, fourteen-step review, and no-copy boundary are recorded consistently. |
| Exclusions | PASS | Ads, payments, billing/subscriptions, marketplace, reseller/multi-project, public signup, and commerce remain excluded. |
| No-placeholder and premium screen gate | PASS | Real-state rule, shared-component standard, continuous-quality boundary, and twenty-point Definition of Done are locked. |
| Changed-file boundary | PASS | GOV-02 changes only Markdown governance, ADR, and design files; no source, test, API, migration, configuration, or runtime file changed. |
| Reference library isolation | PASS | `.reference/` is locally ignored and no capture/archive file is tracked or staged. |
| Migration invariance | PASS | Migration head remains `0031_automation_trigger_receipts` with 31 linear revisions. |
| OpenAPI invariance | PASS | `frontend/openapi.json` remains OpenAPI 3.1.0 with 153 paths and is unchanged from the starting Git baseline. |

## Backend

| Validation item | Status | Latest evidence |
|---|---|---|
| Pytest | PASS | Canonical deployed validation passed 940/940 backend tests in 394.35 seconds. |
| Migration validation | PASS | Single head `0033_kyc_operations`; 33 linear revisions; SQLite upgrade/downgrade/re-upgrade and deployed MySQL upgrade passed. Generic SQLite `alembic check` remains non-authoritative because of pre-existing repository-wide reflection noise. |
| Ruff | PASS | Canonical deployed profile passed Ruff across application, tests, scripts, and root tools. |
| Mypy | PASS | Canonical deployed profile passed strict mypy across 252 backend source files. |
| Python compile | PASS | `compileall` passed for backend application/scripts and root scripts. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | Frontend and Playwright TypeScript checks passed in the canonical deployed profile with regenerated contracts. |
| ESLint | PASS | Frontend ESLint passed in the canonical deployed profile. |
| Vitest | PASS | Full suite passed 646/646 tests across 30 files. |
| Playwright | PASS | Isolated production owner journey passed 1/1 against the final CORE-04 images in 8.635 seconds. |
| Production build | PASS | TypeScript and Vite production build passed after final CORE-04 source and generated-contract changes. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | Live generation and drift validation passed; OpenAPI 3.1.0 advanced from 184 to 188 paths (+4) without removing a path. |
| Generated TypeScript contracts | PASS | `npm run gen:api` regenerated the typed KYC operations/checklist/appointment contracts; frontend typecheck and drift checks passed. |

## Infrastructure

| Validation item | Status | Latest evidence |
|---|---|---|
| Docker | PASS | Development/production Compose models, ten-service release contract, production builds, backend/frontend image contracts, Trivy source/image scans, SBOMs, and isolated deployment passed. |
| Celery | PASS | Realtime, bulk, and jobs workers plus beat reached healthy state; the backend image retained 24 registered tasks and queued journey evidence passed. |
| Redis | PASS | Isolated Redis reached healthy state and supported the deployed queue/readiness journey. |
| Target production commissioning | PENDING – Host Machine Validation | TLS/host hardening, UAT, restore/rollback rehearsal, receiver delivery, and production approval require the target host. |

## Accessibility

| Validation item | Status | Latest evidence |
|---|---|---|
| Existing responsive/keyboard baseline | PASS | CORE-01/03 evidence remains green; CORE-04 focused tests verify labelled tabs/actions, accessible drawer/state boundaries, dense desktop table, mobile cards, responsive transformations, and permission-aware read-only behavior. |
| Full final-scope WCAG regression | PENDING – Host Machine Validation | Must be repeated on every completed final-scope route with real domain data and the target browser/device matrix. |

## Performance

| Validation item | Status | Latest evidence |
|---|---|---|
| Standard-read canary | PASS | p95 12.551 ms across 30 authenticated reads, below the 300 ms budget. |
| Full load/stress/spike/soak and 1M-contact certification | PENDING – Host Machine Validation | Requires the isolated Performance Lab and production-like capacity. |

## Known limitations

| Validation item | Status | Current limitation |
|---|---|---|
| Target observability receivers | PENDING – Host Machine Validation | Log shipping, dashboards, alert firing/dead-man delivery, and external synthetic checks need deployed receivers. |
| Production frontend bundle | PENDING – Host Machine Validation | The main chunk warning is 719.05 kB; further route splitting remains a performance task. |
| Docker-backed source scan | PASS | Trivy vulnerability, secret, and IaC scan passed; production backend/frontend image vulnerability scans and CycloneDX SBOM generation also passed. |
| React Router advisories | PENDING – Host Machine Validation | Two moderate advisories require an explicit React Router 7.18+ upgrade milestone, not a silent dependency change. |
| Contact-scoped conversation history | PENDING – Host Machine Validation | `ConversationHistorySection.tsx` still exposes the known unavailable/TODO boundary. |
| Final domain workflows | PENDING – Host Machine Validation | CORE-04 supplies governed KYC operations over the existing authorities; SIM/Activation operational UIs plus Notification Center, generalized approvals, Google Sheets, and Download Center remain later milestones. |

## Milestone closeout rule

A new result replaces prior evidence only after the exact command has completed. A failure remains
`FAIL` until rerun successfully. Environment-dependent checks stay
`PENDING – Host Machine Validation`; they must never be relabelled `PASS` from repository-only
inference.
