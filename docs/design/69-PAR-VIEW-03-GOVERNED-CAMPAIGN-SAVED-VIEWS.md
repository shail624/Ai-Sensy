# PAR-VIEW-03 — Governed Campaign Saved Views

**Status:** Repository implemented  
**Synchronized:** 2026-08-26T01:34:51+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

Campaign operators can save the current URL-backed search, lifecycle-status and sort definition
privately or, with explicit permission, publish it to their organization. A saved view reopens the
same reproducible list state at page one without carrying local pagination or changing any campaign.

## Shared governance authority

- Campaigns extends the same `WorkspaceViewService`, repository and physical table already serving
  Contacts and Reactivation; no parallel saved-filter store exists.
- `campaigns:views_manage` governs organization-shared creation and deletion. Every
  `campaigns:read` user may create/delete personal views.
- Tenant, workspace and private-user predicates are applied to list and identity reads. A foreign
  tenant, another user's private UUID or another workspace's UUID fails closed.
- Private and shared scopes remain independently capped at 25. Names remain case-insensitively
  unique within their scope under an organization row lock.
- Create/delete actions commit with `campaign_view.created` / `campaign_view.deleted` immutable
  Audit evidence.

## Portable filter contract

- Stored fields: trimmed name search, one validated campaign lifecycle status and one supported
  list sort.
- Excluded field: local page number. Applying a view intentionally returns to the first page.
- Campaign recipient cursor/status, dispatch, schedule, retry, export and lifecycle state are never
  stored. Saved views define presentation only.
- Invalid status/sort values fail request validation; extra transient input is discarded rather than
  persisted.

## UI

- Private and team definitions appear as compact lock/team chips below the existing Campaign list
  toolbar.
- `Save / manage` opens a responsive sheet with plain-language visibility, manager-only team
  publishing, personal/team grouping, mutation errors and explicit deletion confirmation.
- Applying a chip writes through the existing search-parameter authority and preserves all list,
  row-action, empty, error and pagination behavior.

## Persistence and API

- Migration `0059_campaign_workspace_views` advances one linear head to **60 revisions**, expands
  the existing workspace check to `campaigns` and adds `campaigns:views_manage` without modifying
  existing view rows.
- `GET/POST /api/v1/campaigns/views` and
  `DELETE /api/v1/campaigns/views/{view_id}` advance OpenAPI from 229 to **231 paths**; exported JSON
  and generated TypeScript agree.

## Validation

- Campaign/Contacts/Reactivation saved-view API regression: **16/16**.
- Migration upgrade/downgrade/re-upgrade: **5/5**.
- Focused Campaign UI: **54/54**.
- Complete backend: **1569 passed / 6 MySQL-only skipped / 0 failed in 395.87s**.
- Complete frontend: **45 files / 866 tests**.
- Static profile: **6/6**; strict mypy covers **320 source files**; OpenAPI drift, frontend lint,
  frontend/browser types and Vite **8.2.2** production build pass.
- Campaigns bundle: **120.31 kB / 30.52 kB gzip**.
- No new authenticated representative-data screenshot/device result is claimed; visual/WCAG/device
  review remains a host gate.

## Completion effect and remaining boundary

Campaigns advances **94% → 95%**, Saved Views **65% → 75%**, API **97% → 98%**, and the 31-row
product mean **75.6% → 76.0%**; median remains **86%**. KYC and Reports saved views and remaining
segment predicates stay pending. Campaign-to-case attribution, approved revenue/ROI facts,
production-scale query commissioning, authenticated WCAG/device review and target-host release
gates remain pending. No provider call, customer send, commit, push, release or deployment occurred.
