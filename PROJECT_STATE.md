# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (CORE-04 starting baseline `320b0bd211cddcd77c56208ba5238e8a14b4e116`; resolve the milestone commit from Git) |
| Current milestone | `CORE-04 — KYC operations — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0033_kyc_operations` (33 linear revisions) |
| OpenAPI path count | `188` (OpenAPI `3.1.0`) |
| Backend test count | `940` pytest tests passed |
| Frontend test count | `646` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, and performance gates passed |
| Last completed milestone | `CORE-04 — KYC operations` |
| Next milestone | `CORE-05 — SIM fulfilment` (requires owner approval) |
| Current worktree status | `MILESTONE CHANGES VALIDATED; clean state required after the CORE-04 commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T14:44:11+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at CORE-04 start:
  `320b0bd211cddcd77c56208ba5238e8a14b4e116`.
- Contract: `frontend/openapi.json` contains 188 paths and the generated TypeScript contract/drift
  checks pass.
- Tests: pytest passed 940 tests; Vitest passed 646 tests.
- Migration lineage: `0001` through `0033` is present without a gap or downgrade; SQLite
  upgrade/downgrade/re-upgrade and deployed MySQL upgrade both passed.
- CORE-04 connects a persisted KYC queue and case workspace to the existing Vi, Reactivation,
  Document Center, Task, Customer 360, RBAC, Audit, Timeline, and SLA authorities. Verification,
  protected Aadhaar/PAN references, appointments, separated decisions, structured rejection,
  immutable evidence, and approved Reactivation handoff are complete without storing identity
  numbers or rebuilding a completed module.
- Canonical pre-merge and release profiles passed, including Ruff, strict mypy across 252 files,
  OpenAPI drift, TypeScript, ESLint, production build, Bandit, dependency audits, Trivy source/image
  scans, SBOMs, Compose/image contracts, and the isolated deployed stack. Playwright passed 1/1 and
  the authenticated read canary recorded p95 12.551 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
