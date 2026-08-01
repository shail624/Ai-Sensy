# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence; it must
> be refreshed after every milestone. GitHub baseline: `298a3b7`; milestone `GOV-01` is complete,
> and the current repository validation pipeline completed successfully.

Last synchronized: `2026-08-02T03:03:58+05:30`.

## Backend

| Validation item | Status | Latest evidence |
|---|---|---|
| Pytest | PASS | Current pipeline passed 932 backend tests on 2026-08-02. |
| Migration validation | PASS | Current pipeline preserved the linear `0001`–`0031` migration lineage and head. |
| Ruff | PASS | Current repository validation pipeline passed Ruff on 2026-08-02. |
| Mypy | PASS | Current pipeline passed strict mypy across 247 backend source files. |
| Python compile | PASS | Current pipeline passed the applicable Python compile/import validation. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | Current pipeline passed frontend and Playwright TypeScript checks on 2026-08-02. |
| ESLint | PASS | Current pipeline passed frontend ESLint on 2026-08-02. |
| Vitest | PASS | Current pipeline passed 628 frontend tests on 2026-08-02. |
| Playwright | PASS | Isolated production journey reported 1 passed / 0 failed at the last completed milestone. |
| Production build | PASS | Current pipeline passed the TypeScript and Vite production build. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | Current pipeline passed drift validation; OpenAPI 3.1.0 contains 153 paths. |
| Generated TypeScript contracts | PASS | Current pipeline passed generated TypeScript contract validation. |

## Infrastructure

| Validation item | Status | Latest evidence |
|---|---|---|
| Docker | PASS | Development/production Compose contracts, production images, and isolated deployed stack passed at the last completed milestone. |
| Celery | PASS | Worker booted with the unchanged 24 registered tasks; real queued workflows passed. |
| Redis | PASS | Queue/readiness behavior passed, including the expected 503 readiness response during simulated Redis loss. |
| Target production commissioning | PENDING – Host Machine Validation | TLS/host hardening, UAT, restore/rollback rehearsal, receiver delivery, and production approval require the target host. |

## Accessibility

| Validation item | Status | Latest evidence |
|---|---|---|
| Existing responsive/keyboard baseline | PASS | Prior live desktop/mobile audits verified headings, labelled controls, focus behavior, and responsive routes. |
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
| Production frontend bundle | PENDING – Host Machine Validation | The main chunk warning was approximately 707 kB; further route splitting remains a performance task. |
| React Router advisories | PENDING – Host Machine Validation | Two moderate advisories require an explicit React Router 7.18+ upgrade milestone, not a silent dependency change. |
| Contact-scoped conversation history | PENDING – Host Machine Validation | `ConversationHistorySection.tsx` still exposes the known unavailable/TODO boundary. |
| Final domain workflows | PENDING – Host Machine Validation | Reactivation, KYC, SIM, Activation, Notification Center, approvals, Google Sheets, and Download Center remain incomplete as detailed in `MODULE_STATUS.md`. |

## Milestone closeout rule

A new result replaces prior evidence only after the exact command has completed. A failure remains
`FAIL` until rerun successfully. Environment-dependent checks stay
`PENDING – Host Machine Validation`; they must never be relabelled `PASS` from repository-only
inference.
