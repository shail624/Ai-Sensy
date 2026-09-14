# PAR-VIEW-05 — Governed Report Saved Views

Status: `REPOSITORY IMPLEMENTED`  
Date: 2026-09-13  
Host Validated: `NO`  
Provider Validated: `NOT APPLICABLE`  
Production Ready: `NO`

## Outcome

Analytics readers can save the current report period, granularity and comparison as a personal
view. Users with `analytics:views_manage` can publish or delete team views. Reports reuse the one
tenant-scoped workspace-view authority already serving Reactivation, Contacts, Campaigns and KYC;
no parallel persistence model or browser-only substitute is introduced.

## Contract

- `GET /api/v1/analytics/views` returns all team views in the caller's organization plus only the
  caller's private views.
- `POST /api/v1/analytics/views` creates a case-insensitively unique private or team definition
  under the existing per-scope cap and organization lock.
- `DELETE /api/v1/analytics/views/{view_id}` deletes an authorized definition and records immutable
  Audit evidence.
- Every Analytics reader may govern personal views; `analytics:views_manage` is required for team
  publishing and team deletion.
- Workspace, organization and private-user boundaries fail closed. A UUID from another workspace,
  tenant or private owner is not exposed.

## Portable filter boundary

The stored definition contains only the existing server-evaluated report filters:

- one exact preset, or a complete custom `from`/`to` range;
- `day` or `week` granularity;
- optional previous-period comparison.

The active report tab, export format, schedule/progress state and other transient UI state are not
stored. Applying a view writes the validated filters through the existing Analytics URL contract,
so reload and shared-link behavior remain reproducible without creating a second query authority.

## User experience

The Analytics filter bar now includes private/team chips and a responsive `Save / manage` sheet.
The sheet explains visibility in plain language, hides unauthorized team publishing, groups private
and team definitions, surfaces API errors, and requires an explicit delete action. Desktop and
390-pixel mobile preview checks verified the saved team view and responsive sheet using an isolated
local database. The preview intentionally showed zero/unknown metrics because no representative
production rollup data was introduced.

## Persistence and Audit

Migration `0061_reports_workspace_views` expands the existing workspace discriminator to `reports`
and seeds `analytics:views_manage`, preserving one linear **62-revision** history. Create/delete
actions emit `report_view.created` and `report_view.deleted`. OpenAPI advances **233 → 235 paths**
and the generated TypeScript contract is synchronized.

## Validation

- Focused API/migration/OpenAPI/permission contracts: **12/12 PASS**.
- Focused Analytics UI: **41/41 PASS**.
- Complete backend: **1579 passed / 6 MySQL-only skipped / 0 failed in 413.35s**.
- Complete frontend: **47 files / 875 tests PASS**.
- Static gate: **6/6 PASS**; strict mypy covers **322 source files**.
- OpenAPI drift, frontend lint/types/browser-test types and Vite **8.2.2** production build: PASS.
- Authenticated local desktop/mobile preview: PASS for the bounded saved-view workflow; this is not
  representative-data WCAG, protected-media, production-scale or target-host acceptance.

## Completion accounting and remaining boundary

Executive Reports advances **75% → 80%** and Saved Views **85% → 95%**. The 31 canonical rows sum
to **2,388**, an unweighted mean of **77.0%**; median advances **86% → 88%**. The remaining `GROW-03` product
gap is the approved segment-predicate/saved-filter slice. Revenue/ROI and campaign attribution,
capacity/utilization truth, remaining artifact families, authenticated representative-data browser/
WCAG review, Docker/security release rerun, and target-host TLS/secrets/monitoring/restore/UAT remain
separate. No provider/customer call, send, commit, push, release or deployment occurred.
