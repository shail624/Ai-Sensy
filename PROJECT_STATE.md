# Project State

## MAINT-02 — typed campaign list filters (2026-09-13)

Latest milestone: MAINT-02. Branch: `claude/sweet-darwin-5i66uq`; approved starting
HEAD: `6d755f250eb3cd1b2e3126ba2ba26ff32f8516b2`. Delivery HEAD is this milestone's
single commit (resolve from Git). Repository version remains `1.0.0-rc1`.

PASS: the approved branch reproduced an empty query-parameter declaration in live OpenAPI,
despite frozen API design section 17 requiring campaign name/status filtering. No frozen
requirement calls for the undeclared shape. The route now declares optional typed q/status;
status validation derives from the existing campaign status tuple. The existing legacy
status-filter spelling remains accepted with its existing precedence, without adding it
to the public generated query shape.

PASS: regenerated OpenAPI and frontend types; the generated client sends filters and query
cache keys include them. Removed duplicate client-side search/status filtering. Existing
local sorting and paging remain; no server pagination, new tabs, campaign kinds, migrations,
execution, scheduling, audience or dispatch changes. Empty filtered results are distinguished
from an empty registry; filter controls remain mounted while results load.

PASS: full backend suite **962 passed**, no failures/skips (176.71s); focused new backend
contract/filter/status/tenant checks **14 passed**. Frontend campaign tests **48 passed**;
full frontend suite **657 passed / 33 files** (5.64s). TypeScript, production build,
ESLint, changed-backend Ruff, endpoint mypy and OpenAPI drift check passed.
Build bundle-size and runtime/tool deprecation warnings remain non-blocking.
Initial sandbox restrictions on dependency installation/bundler startup were resolved;
the completed runs above are the acceptance results.

OpenAPI remains **193 paths**, migration head remains **0035_notification_center**.
No source-of-truth document changed. Existing module completion estimates are not increased.
PENDING – Host Machine Validation: deployed MySQL/browser/E2E commissioning was not run;
this bounded contract milestone is not a new production-readiness certification.

Design note: `docs/design/MAINT-02-CAMPAIGN-LIST-FILTER-CONTRACT.md`.
Decision: `docs/adr/0020-maint-02-campaign-list-filter-contract.md`.
Scope limited to MAINT-02; other local work was excluded through an isolated worktree.
Next action after the single commit/push: STOP; no next milestone is authorized.

## Historical records below — retained, not current MAINT-02 evidence

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `feature/module6-queue-engine` |
| Current Git HEAD | `HEAD` (roadmap-correction starting baseline `32ecfeeb3a5d4cc68d1974024f85666beb122eca`; resolve the correction commit from Git) |
| Current milestone | `CORE-07 — Customer 360 domain convergence — COMPLETE` |
| Current phase | `Phase 1 — Core operations and real domain ownership — IN PROGRESS` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0034_reactivation_crm` (34 linear revisions) |
| OpenAPI path count | `189` (OpenAPI `3.1.0`) |
| Backend test count | `945` pytest tests passed |
| Frontend test count | `651` Vitest tests passed |
| Validation status | `PASS` — static, application, security, release-image, MySQL migration, Redis/Celery, Playwright, responsive browser, and performance gates passed |
| Last completed milestone | `CORE-07 — Customer 360 domain convergence` |
| Next milestone | `CORE-09 — Notification Center` (requires owner approval; **CORE-08 — Skipped: Not required by product owner.**) |
| Current worktree status | `GOVERNANCE CORRECTION REVIEWED; clean state required after the correction commit; local quality artifacts and permitted references remain ignored` |
| Last update timestamp | `2026-08-02T17:39:04+05:30` (Asia/Calcutta) |

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
- Owner decision: **CORE-08 — Skipped: Not required by product owner.**
  No Approval Center, generic framework, queue, escalation system, or new approval authority is
  planned. Existing KYC-specific approvals and authorization safeguards remain unchanged.
- Canonical static/application/security/release steps and the corrected isolated deployed step pass,
  including Ruff, strict mypy across 253 files, OpenAPI drift, TypeScript, ESLint, production build,
  945 pytest and 651 Vitest tests, Bandit, dependency audits, Trivy source/image scans, SBOMs,
  Compose/image contracts, the 189-path/25-task backend image, and MySQL/Redis/Celery. Playwright
  passed 1/1 in 11.1 seconds and the authenticated read canary recorded p95 10.4 ms across 30 reads.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, and test evidence; update this file after all
other edits so its worktree status is truthful. Do not claim a milestone complete while this file
describes an earlier HEAD or earlier milestone.
