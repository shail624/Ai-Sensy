# PAR-VIEW-04 — Governed KYC Saved Views

**Status:** Repository implemented  
**Synchronized:** 2026-08-26T02:16:27+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

KYC operators can save the current customer search and lifecycle-status queue definition privately
or, with explicit permission, publish it to their organization. Filters are URL-backed so reloads,
links and saved definitions reproduce the same server-evaluated queue without carrying local case
state or changing a KYC record.

## Shared governance authority

- KYC extends the same `WorkspaceViewService`, repository and physical table already serving
  Campaigns, Contacts and Reactivation; no parallel saved-filter store exists.
- `kyc:views_manage` governs organization-shared creation and deletion. Every `kyc:read` user may
  create/delete personal views.
- Tenant, workspace and private-user predicates are applied to list and identity reads. A foreign
  tenant, another user's private UUID or another workspace's UUID fails closed.
- Private and shared scopes remain independently capped at 25. Names remain case-insensitively
  unique within their scope under an organization row lock.
- Create/delete actions commit with `kyc_view.created` / `kyc_view.deleted` immutable Audit
  evidence.

## Portable filter contract

- Stored fields: trimmed customer search and one validated KYC lifecycle status.
- Excluded fields: the bounded 200-row fetch limit, selected case/drawer, evidence checklist,
  document references, appointments, SLA/detail state and reviewer/manager decisions.
- Applying a definition clears only the transient selected case and writes the portable filters to
  the URL; the existing tenant-scoped KYC query remains authoritative.
- Invalid status values fail request validation; extra transient input is discarded rather than
  persisted.

## UI

- Private and team definitions appear as compact lock/team chips above the existing KYC queue.
- `Save / manage` opens a responsive sheet with plain-language visibility, manager-only team
  publishing, personal/team grouping, mutation errors and explicit deletion confirmation.
- The existing search input and status tabs now use URL state while preserving refresh, metrics,
  list/mobile transformations, case drawer, empty/error/loading and permission-denied behavior.

## Persistence and API

- Migration `0060_kyc_workspace_views` advances one linear head to **61 revisions**, expands the
  existing workspace check to `kyc` and adds `kyc:views_manage` without modifying existing view
  rows.
- `GET/POST /api/v1/kyc/views` and `DELETE /api/v1/kyc/views/{view_id}` advance OpenAPI from 231 to
  **233 paths**; exported JSON and generated TypeScript agree.

## Validation

- Focused API/migration/OpenAPI/permission contracts: **12/12**.
- Focused KYC UI: **2 files / 8 tests**.
- Complete backend: **1574 passed / 6 MySQL-only skipped / 0 failed in
  450.05s**.
- Complete frontend: **46 files / 870 tests**.
- Static profile: **6/6**; strict mypy covers **321 source files**; OpenAPI drift, frontend lint,
  frontend/browser types and Vite **8.2.2** production build pass.
- Reactivation/KYC bundle: **94.77 kB / 21.45 kB gzip**.
- No authenticated representative-data screenshot/device result is claimed; visual/WCAG/device and
  production protected-media review remain host gates.

## Completion effect and remaining boundary

KYC advances **85% → 90%**, Saved Views **75% → 85%**, API **98% → 99%**, and the 31-row product
mean **76.0% → 76.5%**; median remains **86%**. Reports saved views and remaining segment
predicates stay pending. Server pagination/high-volume performance, protected-media commissioning,
authenticated WCAG/device review and target-host release gates remain pending. No provider call,
customer send, commit, push, release or deployment occurred.
