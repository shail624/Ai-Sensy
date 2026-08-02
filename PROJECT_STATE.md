# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (CORE-03 starting baseline `c1cb133e76716803a0ed65b73a7789daea389ceb`; resolve the milestone commit from Git) |
| Current milestone | `CORE-03 — Reactivation pipeline — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0032_vi_domain_foundation` (32 linear revisions) |
| OpenAPI path count | `184` (OpenAPI `3.1.0`) |
| Backend test count | `938` pytest tests passed |
| Frontend test count | `641` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, and performance gates passed |
| Last completed milestone | `CORE-03 — Reactivation pipeline` |
| Next milestone | `CORE-04 — KYC operations` (requires owner approval) |
| Current worktree status | `CLEAN at milestone handoff after the CORE-03 commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T13:20:26+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at CORE-03 start:
  `c1cb133e76716803a0ed65b73a7789daea389ceb`.
- Contract: `frontend/openapi.json` contains 184 paths and the generated TypeScript contract/drift
  checks pass.
- Tests: pytest passed 938 tests; Vitest passed 641 tests.
- Migration lineage: `0001` through `0032` is present without a gap or downgrade; SQLite
  upgrade/downgrade/re-upgrade and deployed MySQL upgrade both passed.
- CORE-03 connects the existing Reactivation route to persisted CORE-02 cases, counts, transitions,
  assignment, eligibility/rejection, tasks/reminders, documents, notes, reservation/family facts,
  conversion, SLA, immutable history, audit, and Customer Timeline evidence. No completed module
  or parallel domain authority was rebuilt.
- Canonical pre-merge and release profiles passed, including Ruff, strict mypy across 252 files,
  OpenAPI drift, TypeScript, ESLint, production build, Bandit, dependency audits, Trivy source/image
  scans, SBOMs, Compose/image contracts, and the isolated deployed stack. Playwright passed 1/1 and
  the authenticated read canary recorded p95 8.547 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
