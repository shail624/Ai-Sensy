# PAR-VIEW-01 — Governed Reactivation Saved Views

**Status:** Repository implemented  
**Synchronized:** 2026-08-24T18:55:01+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

Reactivation operators can persist the existing search, owner, status, label, reminder and reminder-
date filters as reusable personal views. Authorized managers can publish the same portable view to
the whole tenant. A saved definition also restores board or list mode, but deliberately never stores
page position.

## Authority and safety

- `reactivation_views` is the saved-definition authority. It contains no Reactivation case data and
  does not duplicate case, Task, reminder, KYC, SIM, Activation, Audit or Timeline authorities.
- Every `reactivation:read` user may create and delete their own private views. New
  `reactivation:views_manage` governs shared create/delete; managers receive it in the shipped role
  preset while owner/admin retain their existing full-control behavior.
- Readers list every team view plus only their own private views. Another user's private UUID and
  every foreign-tenant UUID return not found.
- Private and shared scopes are independently capped at 25. Shared names are tenant-unique and
  private names are owner-unique, case-insensitively. The organization row lock serializes limit and
  name checks.
- The API validates stage, label, owner UUID, reminder bucket/date, search length, visibility and
  display mode. Database checks independently constrain visibility/display; indexed tenant/scope
  reads avoid an unbounded cross-tenant scan.
- Create/delete mutations commit atomically with immutable `reactivation_view.created` and
  `reactivation_view.deleted` Audit evidence.

## UI

- The existing factual work views, filter bar, URL state, board/list controls, case drawer and
  pagination remain unchanged.
- Compact chips distinguish personal views with a lock and team views with a people marker.
- `Save / manage` opens an accessible responsive sheet with plain-language `Only me`/`Whole team`
  choices, permission-truthful publishing, grouped definitions, errors and an explicit deletion
  confirmation that states no cases will be changed.
- Applying a view replaces stale filters and pagination with the stored portable definition.

## Persistence and API

- Migration `0057_reactivation_saved_views` adds the table, indexes, checks and permission while
  preserving one linear **58-revision** head.
- `GET/POST /api/v1/reactivation/views` and
  `DELETE /api/v1/reactivation/views/{view_id}` advance OpenAPI from 225 to **227 paths**; exported
  JSON and generated TypeScript agree.

## Validation

- Focused Reactivation view/migration/Vi API: **13/13 backend**.
- Focused Reactivation UI: **12/12**.
- Complete backend: **1559 passed / 6 MySQL-only skipped / 0 failed in 459.36s**.
- Complete frontend: **43 files / 860 tests**; lint, typecheck and Vite **8.2.2** build pass.
- Strict mypy passes across **317 source files**; changed-file Ruff lint/format and OpenAPI drift pass.
- Reactivation chunk: **89.27 kB / 20.09 kB gzip**.

## Completion effect and remaining boundary

Reactivation advances **94% → 96%**, Saved Views **42% → 55%**, API **95% → 96%**, and the
31-row product mean **74.7% → 75.2%**; median remains **86%**. Contacts, Campaigns, KYC and Reports
still require their own server-saved-view integrations. Campaign-to-case attribution, approved
revenue/ROI facts, production-scale query commissioning, authenticated WCAG/device review and
target-host release gates remain pending. No provider call, customer send, commit, push, release or
deployment occurred.
