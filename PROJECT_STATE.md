# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (GOV-02 starting baseline `0ea14d682bba3f89b4c3ef71e872bccf145d1b3a`) |
| Current milestone | `GOV-02 — Premium AiSensy-Parity Product Goal Lock — APPROVED AND COMPLETE` |
| Current phase | `Phase 0 — Governance, scope, and premium product-goal lock — COMPLETE` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0031_automation_trigger_receipts` (31 linear revisions) |
| OpenAPI path count | `153` (OpenAPI `3.1.0`) |
| Backend test count | `932` pytest tests collected |
| Frontend test count | `628` Vitest tests enumerated |
| Validation status | `PASS` — GOV-02 documentation/governance checks passed; prior application-pipeline evidence is preserved and was not rerun |
| Last completed milestone | `GOV-02 — Premium AiSensy-Parity Product Goal Lock — APPROVED` |
| Next milestone | `CORE-01 — Navigation, scope, and permitted UI-reference lock` (requires owner approval) |
| Current worktree status | `CLEAN at milestone handoff — only the committed GOV-02 documentation set is delivered; ignored local reference/evidence files are not repository changes` |
| Last update timestamp | `2026-08-02T03:40:02+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at GOV-02 start:
  `0ea14d682bba3f89b4c3ef71e872bccf145d1b3a`.
- Contract: `frontend/openapi.json` contains 153 paths and the backend drift check passes.
- Tests: pytest collection reports 932 tests; Vitest enumeration reports 628 tests.
- Migration lineage: `0001` through `0031` is present without a gap or downgrade.
- GOV-02 changed documentation and governance only. Markdown, link, scope/exclusion, reference-ignore,
  migration/OpenAPI invariance, and changed-file-boundary checks passed. Backend/frontend runtime
  suites were not rerun; their last successful evidence remains preserved in `CHANGELOG.md`,
  `IMPLEMENTATION_TRACKER.md`, and `VALIDATION_RESULTS.md`.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
