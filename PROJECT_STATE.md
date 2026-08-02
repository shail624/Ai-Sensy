# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (CORE-02 starting baseline `16bd1c6d309d945ad367ba6c73477a87b61ade74`; resolve the milestone commit from Git) |
| Current milestone | `CORE-02 — Vi domain foundation — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0032_vi_domain_foundation` (32 linear revisions) |
| OpenAPI path count | `182` (OpenAPI `3.1.0`) |
| Backend test count | `936` pytest tests passed |
| Frontend test count | `636` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, and performance gates passed |
| Last completed milestone | `CORE-02 — Vi domain foundation` |
| Next milestone | `CORE-03 — Reactivation pipeline` (requires owner approval) |
| Current worktree status | `CLEAN at milestone handoff after the CORE-02 commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T11:53:32+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at CORE-02 start:
  `16bd1c6d309d945ad367ba6c73477a87b61ade74`.
- Contract: `frontend/openapi.json` contains 182 paths and the generated TypeScript contract/drift
  checks pass.
- Tests: pytest passed 936 tests; Vitest passed 636 tests.
- Migration lineage: `0001` through `0032` is present without a gap or downgrade; SQLite
  upgrade/downgrade/re-upgrade and deployed MySQL upgrade both passed.
- CORE-02 added the ten approved tenant-scoped Vi domain records, transition/approval rules,
  repositories/services, permission-scoped APIs, audit, Customer Timeline, durable business facts,
  optimistic concurrency, and idempotency. No operational UI was added.
- Canonical pre-merge and release profiles passed, including Ruff, strict mypy across 252 files,
  OpenAPI drift, TypeScript, ESLint, production build, Bandit, dependency audits, Trivy source/image
  scans, SBOMs, Compose/image contracts, and the isolated deployed stack. Playwright passed and the
  authenticated read canary recorded p95 16.5 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
