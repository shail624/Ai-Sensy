# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence; it must
> be refreshed after every milestone. CORE-01 starting GitHub baseline: `6d8d671`; the milestone
> changes the shared frontend shell only. All daemon-independent checks passed. Docker-backed
> release, deployed, and Trivy source-scan evidence is host-pending because Docker Desktop was not
> running; prior successful deployed evidence is retained where applicable.

Last synchronized: `2026-08-02T04:23:52+05:30`.

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
| Pytest | PASS | CORE-01 validation passed 932 backend tests in 242.20 seconds. |
| Migration validation | PASS | Alembic reports the single head `0031_automation_trigger_receipts`; 31 linear revision files are unchanged. |
| Ruff | PASS | Canonical static and pre-merge profiles passed Ruff. |
| Mypy | PASS | Canonical static and pre-merge profiles passed strict mypy across 247 backend source files. |
| Python compile | PASS | `compileall` passed for backend application/scripts and root scripts. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | CORE-01 canonical static gate passed frontend and Playwright TypeScript checks. |
| ESLint | PASS | CORE-01 canonical static gate passed frontend ESLint. |
| Vitest | PASS | Full suite passed 636/636 tests across 28 files. |
| Playwright | PENDING – Host Machine Validation | Prior isolated production journey remains successful, but CORE-01 deployed browser rerun requires the unavailable Docker daemon; focused authenticated in-app browser smoke passed. |
| Production build | PASS | TypeScript and Vite production build passed after final source changes. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | Drift validation passed; OpenAPI 3.1.0 remains at 153 paths. |
| Generated TypeScript contracts | PASS | `npm run gen:api` completed and produced no contract diff; frontend typecheck passed. |

## Infrastructure

| Validation item | Status | Latest evidence |
|---|---|---|
| Docker | PENDING – Host Machine Validation | Compose service parsing succeeded, but CORE-01 Trivy/release/deployed reruns could not connect to `dockerDesktopLinuxEngine`; prior production-image/deployed evidence remains preserved. |
| Celery | PASS | Worker booted with the unchanged 24 registered tasks; real queued workflows passed. |
| Redis | PASS | Queue/readiness behavior passed, including the expected 503 readiness response during simulated Redis loss. |
| Target production commissioning | PENDING – Host Machine Validation | TLS/host hardening, UAT, restore/rollback rehearsal, receiver delivery, and production approval require the target host. |

## Accessibility

| Validation item | Status | Latest evidence |
|---|---|---|
| Existing responsive/keyboard baseline | PASS | CORE-01 focused tests and authenticated desktop browser review verified labelled controls, active state, focus management, 44px mobile targets, and overflow behavior. |
| Full final-scope WCAG regression | PENDING – Host Machine Validation | Must be repeated on every completed final-scope route with real domain data and the target browser/device matrix. |

## Performance

| Validation item | Status | Latest evidence |
|---|---|---|
| Standard-read canary | PASS | p95 19.002 ms across 30 authenticated reads, below the 300 ms budget. |
| Full load/stress/spike/soak and 1M-contact certification | PENDING – Host Machine Validation | Requires the isolated Performance Lab and production-like capacity. |

## Known limitations

| Validation item | Status | Current limitation |
|---|---|---|
| Target observability receivers | PENDING – Host Machine Validation | Log shipping, dashboards, alert firing/dead-man delivery, and external synthetic checks need deployed receivers. |
| Production frontend bundle | PENDING – Host Machine Validation | The main chunk warning is 713.18 kB; further route splitting remains a performance task. |
| Docker-backed source scan | PENDING – Host Machine Validation | The final pre-merge Trivy step requires a running Docker Desktop daemon; Ruff, mypy, OpenAPI, tests, build, Bandit, and dependency audits completed first and passed. |
| React Router advisories | PENDING – Host Machine Validation | Two moderate advisories require an explicit React Router 7.18+ upgrade milestone, not a silent dependency change. |
| Contact-scoped conversation history | PENDING – Host Machine Validation | `ConversationHistorySection.tsx` still exposes the known unavailable/TODO boundary. |
| Final domain workflows | PENDING – Host Machine Validation | Reactivation, KYC, SIM, Activation, Notification Center, approvals, Google Sheets, and Download Center remain incomplete as detailed in `MODULE_STATUS.md`. |

## Milestone closeout rule

A new result replaces prior evidence only after the exact command has completed. A failure remains
`FAIL` until rerun successfully. Environment-dependent checks stay
`PENDING – Host Machine Validation`; they must never be relabelled `PASS` from repository-only
inference.
