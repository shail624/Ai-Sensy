# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (CORE-07 starting baseline `4881a1d93580dfe48932a9f6e615b276629f4114`; resolve the milestone commit from Git) |
| Current milestone | `CORE-07 — Customer 360 domain convergence — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0034_reactivation_crm` (34 linear revisions) |
| OpenAPI path count | `189` (OpenAPI `3.1.0`) |
| Backend test count | `945` pytest tests passed |
| Frontend test count | `651` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, responsive browser, and performance gates passed |
| Last completed milestone | `CORE-07 — Customer 360 domain convergence` |
| Next milestone | `CORE-08 — General approval engine` (requires owner approval) |
| Current worktree status | `MILESTONE CHANGES VALIDATED; clean state required after the CORE-07 commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T17:34:14+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at the CORE-07 start:
  `4881a1d93580dfe48932a9f6e615b276629f4114`.
- Contract: `frontend/openapi.json` contains 189 paths and the generated TypeScript contract/drift
  checks pass.
- Tests: pytest passed 945 tests; Vitest passed 651 tests.
- Migration lineage: `0001` through `0034` is present without a gap or downgrade; SQLite
  upgrade/downgrade/re-upgrade and deployed MySQL upgrade both passed.
- CORE-07 composes existing Contact, Inbox, Reactivation, Task, Document, KYC/SIM/Activation,
  Campaign, Audit and Customer Timeline sources inside one permission-aware Customer 360 workspace.
  Exact Contact filters extend existing APIs; no duplicate model, migration, endpoint family,
  synthetic metric, fake data, or rebuilt module was introduced.
- Canonical static/application/security/release steps and the corrected isolated deployed step pass,
  including Ruff, strict mypy across 253 files, OpenAPI drift, TypeScript, ESLint, production build,
  945 pytest and 651 Vitest tests, Bandit, dependency audits, Trivy source/image scans, SBOMs,
  Compose/image contracts, the 189-path/25-task backend image, and MySQL/Redis/Celery. Playwright
  passed 1/1 in 11.1 seconds and the authenticated read canary recorded p95 10.4 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
