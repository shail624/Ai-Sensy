# PAR-VIEW-02 — Governed Contacts Saved Views

**Status:** Repository implemented  
**Synchronized:** 2026-08-24T19:38:20+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

Contacts operators can save the current server-evaluated search, tag and enum custom-attribute
filters privately or, with explicit permission, publish them to their organization. A saved view
reopens the same portable audience definition without carrying a stale cursor or changing any
contact.

## Shared authority

- Contacts and Reactivation use one `WorkspaceViewService`, repository and tenant-scoped table.
  The original `reactivation_views` physical name remains only as an additive-upgrade compatibility
  anchor; `workspace` is now part of every lookup, count, uniqueness scope and index.
- Every `contacts:read` user can create/delete their private definitions.
- `contacts:views_manage` governs organization-shared creation and deletion; managers receive it in
  the preset catalog while private access remains available to readers.
- Readers see every Contacts team definition in their tenant plus only their own private rows.
  Cross-workspace, cross-user-private and cross-tenant identifiers fail closed.
- Private and shared scopes each cap at 25. Names are case-insensitively unique within the correct
  workspace/scope under an organization row lock.
- Create/delete commits atomically with `contact_view.created` / `contact_view.deleted` Audit rows.

## Portable filter contract

- Stored fields: trimmed search query, tag UUID, and at most 25 validated enum custom-attribute
  key/value selections.
- Excluded field: cursor. Applying a view calls the existing filter authority, which intentionally
  drops the current cursor and returns to the first server page.
- The contact-search endpoint, segment-rule compiler, bulk actions and export audience remain the
  existing authorities; saved views store definitions only.

## UI

- The existing Contacts search/filter/mobile-sheet surface remains unchanged.
- A lock/team chip strip applies definitions in one click.
- `Save / manage` opens the same responsive sheet pattern as Reactivation with plain-language
  visibility, permission-truthful team publishing, grouped private/team definitions, API errors and
  explicit deletion confirmation.
- Empty, loading and saved-view API-error states do not block the Contacts table or bulk actions.

## Persistence and API

- Migration `0058_contacts_workspace_views` advances one linear head to **59 revisions**, adds the
  workspace discriminator/check/index scopes and `contacts:views_manage`, and preserves every
  existing Reactivation row as workspace `reactivation`.
- `GET/POST /api/v1/contacts/views` and `DELETE /api/v1/contacts/views/{view_id}` advance OpenAPI
  from 227 to **229 paths**; exported JSON and generated TypeScript agree.

## Validation

- Focused saved-view/API/Reactivation/migration backend: **16/16**.
- Focused Contacts/Reactivation UI: **19/19**.
- Complete frontend: **44 files / 863 tests**; lint, typecheck and Vite **8.2.2** build pass.
- Strict mypy passes across **319 source files**; changed-file Ruff and OpenAPI drift pass.
- Complete backend: **1564 passed / 6 MySQL-only skipped / 0 failed in 506.04s**.
- In-app local visual QA was attempted but local-page access was denied; authenticated
  representative-data browser/WCAG/device review remains a host gate and is not reported as PASS.

## Completion effect and remaining boundary

Contacts advances **95% → 98%**, Saved Views **55% → 65%**, API **96% → 97%**, and the 31-row
product mean **75.2% → 75.6%**; median remains **86%**. Campaigns, KYC and Reports still require
their server-saved-view integrations. Campaign-to-case attribution, approved revenue/ROI facts,
production-scale query commissioning, authenticated WCAG/device review and target-host release
gates remain pending. No provider call, customer send, commit, push, release or deployment occurred.
