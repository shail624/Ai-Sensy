# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (owner-corrected CORE-05 starting baseline `3457938e8c29768167653040ee93a22caa11eedc`; resolve the milestone commit from Git) |
| Current milestone | `CORE-05 — Lightweight Reactivation CRM — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0034_reactivation_crm` (34 linear revisions) |
| OpenAPI path count | `189` (OpenAPI `3.1.0`) |
| Backend test count | `943` pytest tests passed |
| Frontend test count | `646` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, and performance gates passed |
| Last completed milestone | `CORE-05 — Lightweight Reactivation CRM` |
| Next milestone | `CORE-07 — Customer 360 domain convergence` (requires owner approval; no standalone SIM/Activation workspace is planned) |
| Current worktree status | `MILESTONE CHANGES VALIDATED; clean state required after the CORE-05 commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T16:18:34+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at the corrected CORE-05 start:
  `3457938e8c29768167653040ee93a22caa11eedc`.
- Contract: `frontend/openapi.json` contains 189 paths and the generated TypeScript contract/drift
  checks pass.
- Tests: pytest passed 943 tests; Vitest passed 646 tests.
- Migration lineage: `0001` through `0034` is present without a gap or downgrade; SQLite
  upgrade/downgrade/re-upgrade and deployed MySQL upgrade both passed.
- CORE-05 makes the existing Reactivation case the lightweight CRM authority: nine statuses, six
  labels, Task-backed Follow-up/Release dates, due views/actions, assignment, notes, immutable
  history, Audit and Customer Timeline. KYC/SIM/Activation foundations remain preserved; no
  parallel reminder/notification authority or standalone heavy operational workspace was added.
- Canonical pre-merge and deployed profiles passed, including Ruff, strict mypy across 253 files,
  OpenAPI drift, TypeScript, ESLint, production build, Bandit, dependency audits, Trivy source/image
  scans, SBOMs, Compose/image contracts, the 189-path/25-task backend image, and the isolated
  deployed stack. Playwright passed 1/1 in 11.338 seconds and the authenticated read canary recorded
  p95 17.761 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
