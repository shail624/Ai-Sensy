# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (synchronization base `f882c99c35d3b4addf20acc6edc551043e591380`) |
| Current milestone | `GOV-01 — Permanent governance baseline — APPROVED AND COMPLETE` |
| Current phase | `Phase 0 — Governance and scope lock — COMPLETE` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0031_automation_trigger_receipts` (31 linear revisions) |
| OpenAPI path count | `153` (OpenAPI `3.1.0`) |
| Backend test count | `932` pytest tests collected |
| Frontend test count | `628` Vitest tests enumerated |
| Validation status | `PASS` — current repository validation pipeline completed successfully; target-host commissioning remains pending |
| Last completed milestone | `GOV-01 — Permanent governance baseline — APPROVED` |
| Next milestone | `CORE-01 — Navigation, scope, and permitted UI-reference lock` (requires owner approval) |
| Current worktree status | `DIRTY — untracked scripts/update_governance.py is not part of GitHub` |
| Last update timestamp | `2026-08-02T03:11:48+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub governance baseline before this synchronization commit:
  `f882c99c35d3b4addf20acc6edc551043e591380`.
- Contract: `frontend/openapi.json` contains 153 paths and the backend drift check passes.
- Tests: pytest collection reports 932 tests; Vitest enumeration reports 628 tests.
- Migration lineage: `0001` through `0031` is present without a gap or downgrade.
- The current repository validation pipeline completed successfully. Earlier release/deployed
  evidence remains preserved in `CHANGELOG.md` and `IMPLEMENTATION_TRACKER.md`.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
