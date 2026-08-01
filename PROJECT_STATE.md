# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. The recorded Git HEAD is the HEAD on which the current uncommitted
> milestone is based.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `a8479e76b5a64df112c5d1db702214e89417e5ec` |
| Current milestone | `GOV-01 — Permanent governance baseline` |
| Current phase | `Phase 0 — Governance and scope lock` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0031_automation_trigger_receipts` (31 linear revisions) |
| OpenAPI path count | `153` (OpenAPI `3.1.0`) |
| Backend test count | `932` pytest tests collected |
| Frontend test count | `628` Vitest tests enumerated |
| Validation status | `PASS` for the repository baseline; target-host commissioning remains pending |
| Last completed milestone | `PAR-AUTO-03 — Durable business-event trigger receipts` |
| Next milestone | `CORE-01 — Navigation, scope, and permitted UI-reference lock` (requires owner approval) |
| Current worktree status | `DIRTY — 8 changed path(s)` |
| Last update timestamp | `2026-08-02T02:51:14+05:30` (Asia/Calcutta) |

## Snapshot evidence

- Git baseline: `git describe --tags --always` returned
  `baseline/fr-con-04-release-ready-24-ga8479e7` before governance edits.
- Contract: `frontend/openapi.json` contains 153 paths and the backend drift check passes.
- Tests: pytest collection reports 932 tests; Vitest enumeration reports 628 tests.
- Migration lineage: `0001` through `0031` is present without a gap or downgrade.
- The last completed milestone's full release/deployed evidence is preserved in `CHANGELOG.md` and
  `IMPLEMENTATION_TRACKER.md`.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
