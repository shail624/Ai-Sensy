# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (CORE-01 starting baseline `6d8d6719a0da7a3fa4f987503984ad36f6e6dd97`) |
| Current milestone | `CORE-01 — Navigation, scope, and permitted UI-reference lock — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0031_automation_trigger_receipts` (31 linear revisions) |
| OpenAPI path count | `153` (OpenAPI `3.1.0`) |
| Backend test count | `932` pytest tests collected |
| Frontend test count | `636` Vitest tests passed |
| Validation status | `PASS` — all daemon-independent CORE-01 application gates passed; Docker-backed release/deployed evidence is `PENDING – Host Machine Validation` |
| Last completed milestone | `CORE-01 — Navigation, scope, and permitted UI-reference lock` |
| Next milestone | `CORE-02 — Vi domain foundation` (requires owner approval) |
| Current worktree status | `CLEAN at milestone handoff — committed CORE-01 source, tests, ADR/design, and governance only; ignored local reference/evidence files are not repository changes` |
| Last update timestamp | `2026-08-02T04:23:52+05:30` (Asia/Calcutta) |

## Snapshot evidence

- GitHub baseline at CORE-01 start:
  `6d8d6719a0da7a3fa4f987503984ad36f6e6dd97`.
- Contract: `frontend/openapi.json` contains 153 paths and the backend drift check passes.
- Tests: pytest passed 932 tests; Vitest passed 636 tests.
- Migration lineage: `0001` through `0031` is present without a gap or downgrade.
- CORE-01 finalized the shared shell, navigation scope guard, permission-aware actions, maturity
  labels, responsive active states, and accessible overlays. OpenAPI and migrations are unchanged.
- Ruff, strict mypy, OpenAPI drift, frontend/browser TypeScript, ESLint, 932 pytest tests, 636
  Vitest tests, generated contracts, production build, Bandit, and dependency audits passed.
  Docker-backed Trivy/release/deployed validation is host-pending because Docker Desktop was not
  running; the last successful deployed-stack evidence is preserved in `VALIDATION_RESULTS.md`.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
