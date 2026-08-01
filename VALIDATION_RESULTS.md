# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence; it must
> be refreshed after every milestone. Baseline: `a8479e7`, milestone `PAR-AUTO-03`, with a
> documentation-only `GOV-01` worktree in progress.

Last synchronized: `2026-08-02T02:51:14+05:30`.

## Backend

| Validation item | Status | Latest evidence |
|---|---|---|
| Pytest | PASS | 932 tests passed at the last completed milestone; 932 collected again on 2026-08-02. |
| Migration validation | PASS | Linear revisions `0001`–`0031`; MySQL upgrade and migration gate passed for the last completed milestone. |
| Ruff | PASS | Rerun on 2026-08-02; repository static gate and governance-script lint passed. |
| Mypy | PASS | Rerun on 2026-08-02; strict mypy clean across 247 backend source files. |
| Python compile | PASS | `scripts/update_governance.py` compiled on 2026-08-02; backend image boot/import contract remains passed from the last completed milestone. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | Frontend and Playwright TypeScript checks rerun and passed on 2026-08-02. |
| ESLint | PASS | Frontend ESLint rerun and passed on 2026-08-02. |
| Vitest | PASS | 628 tests passed at the last completed milestone; 628 enumerated again on 2026-08-02. |
| Playwright | PASS | Isolated production journey reported 1 passed / 0 failed at the last completed milestone. |
| Production build | PASS | TypeScript and Vite production build passed at the last completed milestone. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | OpenAPI 3.1.0 contains 153 paths; `export_openapi.py --check` passed on 2026-08-02. |
| Generated TypeScript contracts | PASS | Generated schema is tracked and the last completed milestone passed contract generation/drift validation. |

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
