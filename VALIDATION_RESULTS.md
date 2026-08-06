# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence and
> separates repository-verifiable engineering gates from target-host visual/commissioning evidence.

Last synchronized: `2026-08-07T02:00:00+05:30`.


## Alembic version-table MySQL fix — support long revision ids

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified failure reproduced | PASS | `alembic upgrade head` against a real MySQL 8 database (`docker compose up -d`) failed with `sqlalchemy.exc.DataError: (pymysql.err.DataError) (1406, "Data too long for column 'version_num' at row 1")` while transitioning `0035_notification_center → 0036_customer_identity_resolution`. `SHOW CREATE TABLE alembic_version` confirmed `version_num varchar(32)`; the failing revision id is 33 characters. |
| Revision graph integrity | PASS | Single head unchanged: `ScriptDirectory.get_heads() == ["0041_channel_sync_control_plane"]`. Linear chain confirmed: no revision has a tuple `down_revision` (no merges). Base unchanged: `get_bases() == ["0001_identity_and_audit"]`. Revision count: 42 (was 41) — exactly one insertion, no renumbering. |
| No revision renamed/shortened/squashed/reordered | PASS | `0036_customer_identity_resolution` through `0041_channel_sync_control_plane` keep their exact existing `revision` strings and DDL bodies; only `0036`'s `down_revision` pointer (a graph-linkage field, not an identity) was retargeted to the new `0035a_widen_version_table`. |
| Fresh MySQL 8: base → head | PASS | Automated (throwaway per-test database) and manual (real `docker compose` instance, real `alembic upgrade head` CLI invocation) — both succeed; `SELECT version_num FROM alembic_version` returns `0041_channel_sync_control_plane`; `SHOW CREATE TABLE alembic_version` shows `varchar(255)`. |
| MySQL stamped at 0035 → head | PASS | Automated: `alembic upgrade 0035_notification_center` then `alembic upgrade head` against a throwaway MySQL database — the exact historically-failing transition — succeeds. |
| `create-owner` after upgrade | PASS | Automated (`bootstrap_owner` against a throwaway MySQL database) and manual (`python -m app.cli create-owner` against a real, freshly migrated `docker compose` database) — both succeed; re-running is idempotent (`Owner already exists ... no changes`), matching the documented contract. |
| Regression coverage | PASS | `test_migrations.py`: 3 new hermetic (SQLite) tests — single head, linear chain, revision-id length margin. `test_migrations_mysql.py`: new file, 3 tests against real throwaway MySQL databases (fresh base→head, 0035→head, create-owner-after-upgrade); `pytestmark = skipif(not reachable)` — confirmed skipping cleanly (not failing) when no MySQL server is running. |
| Ruff | PASS | `ruff check app tests scripts` clean. |
| Strict mypy | PASS | `mypy app` — "Success: no issues found in 287 source files" (migrations/tests are outside the strict-typed `app` package, matching existing repository convention). |
| Full backend test suite | PASS | 991 passed (985 before this remediation; +6 — the new regression tests, with MySQL reachable so all three live tests genuinely ran, not skipped). |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` — "openapi.json is up to date"; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` — all 6 steps pass (backend lint, backend strict types, OpenAPI drift, frontend lint, frontend types, browser test types), confirming no frontend file was touched. |
| Application/domain unchanged | PASS | No endpoint, model, schema, RBAC definition, ADR, provider/Meta/WAHA code, or frontend file appears in the diff — `git status --porcelain` shows exactly 2 modified files (`0036_customer_identity_resolution.py`, `test_migrations.py`) and 2 new files (`0035a_widen_version_table.py`, `test_migrations_mysql.py`). |
| Remaining scope | Honestly recorded | This fix repairs the MySQL schema/auth blocker only. A real, populated `/chat-history` UI preview remains blocked by the separate, pre-existing absence of an approved development fixture mechanism for conversation/message data (requires live Meta WhatsApp Business API credentials to register a phone number and create genuine conversations, which this environment correctly does not have). No Host Validated or Production Ready claim is made. |


## Chat History pagination/polling/accessibility hardening (audit findings D1–D8)

| Validation item | Status | Latest evidence |
|---|---|---|
| D1 — dead Previous control | PASS | The backend never returns `prev_cursor` (confirmed: only the schema default, no endpoint sets it); the bidirectional `Pagination` control was replaced with a forward-only `Next` plus a `Back to newest` reset shown only once a later page has loaded. A dedicated regression proves Next loads the next cursor, Back to newest appears only after paging forward, activating it reloads the initial 25-row page (`limit` stays 25 throughout), and the control then disappears again. |
| D2 — inherited 10s polling on a read-only view | PASS | `useConversation`/`useMessages` (`features/inbox/api.ts`) gained an optional trailing `refetchInterval` parameter defaulting to the existing `POLL_INTERVAL_MS`; Chat History passes `false` for both. Three regressions inspect the real registered `QueryCache` entries: Chat History's detail/messages queries carry `refetchInterval: false`; a probe calling the hooks with no override (the exact call shape Live Chat's `ConversationThread` and Customer 360's `ConversationHistorySection` already use) still gets `POLL_INTERVAL_MS`; loading an older message page does not reactivate polling. |
| Live Chat polling preserved | PASS | `inbox.test.tsx` (26 tests, unchanged) and `customer-profile` (13 tests, unchanged) pass without modification — no existing consumer's call site or behaviour changed. |
| D3 — responsive focus | PASS | Reuses the existing `useMediaQuery` utility (`lib/useMediaQuery.ts`) with a `(max-width: 1023.98px)` query matching the route's own `lg` split. Selecting a conversation below `lg` moves focus to the "Back to conversation history" button; returning to the list restores focus to the row that was open; neither happens at or above `lg`. Three regressions cover narrow-select, narrow-return and desktop-no-op. |
| D4 — contact filter in active-filter detection | PASS | `hasActiveFilter` now includes `filters.contact`; a `contact`-filtered empty result renders "No conversations match" with a working Clear filters action instead of the global empty state. |
| D6 — status badge tone | PASS | Changed to `status === "open" ? "success" : "neutral"`, matching `ConversationList.tsx`'s existing Live Chat convention exactly. A regression renders one conversation per status and asserts the rendered tone class for all four. |
| D7 — message list accessible name | PASS | `aria-label="Message history"` added to the message `<ul>`. |
| D8 — heading semantics | PASS | Page title is now an `<h1>`; the selected thread's contact name is now an `<h2>` (matching `ConversationThread.tsx`'s own heading level for the identical field); no duplicate heading level is introduced. |
| No detail/message request before selection | PASS | New regression asserts neither `/conversations/{id}` nor `/conversations/{id}/messages` is ever called while `selectedId` is null. |
| Frontend lint | PASS | `eslint .` clean. |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Chat History tests | PASS | 34 tests in `chat-history.test.tsx` (22 existing + 12 new for D1–D8 and the strengthened gaps), all passing. |
| Relevant consumer tests | PASS | `inbox.test.tsx` (26), `customer-profile` (13), `components/layout` (21) — all unchanged and passing. |
| Full frontend suite | PASS | 37 files / 766 tests passed (754 before this hardening pass). |
| Production build | PASS | Main chunk `207.50/57.27 kB gzip` against `207.50/57.23 kB gzip` before this pass (raw unchanged, `+0.04 kB` gzip — the optional hook parameter only). The workspace remains absent from the main chunk and present only in its own lazy chunk. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports up to date; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| RBAC / permissions | PASS | No new permission; `rbac/catalog.py` untouched; route/nav/audit-link gating unchanged. |
| Governance accuracy (D5) | PASS | `MODULE_STATUS.md`'s Chat History pending-work cell corrected to name media-only and audit-scoped filtering alongside the existing date-range/campaign/export/Download Center gaps; completion percentage unchanged at `55%`. |
| Scope discipline | PASS | D9–D12 (the `dateTime` attribute, the `/phone-numbers` duplicate cache key, general test observations, button-vs-anchor) were left untouched, as instructed. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes remain unproven by repository gates. |


## Dedicated Chat History read workspace over the existing conversation and message contract

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified root cause | PASS | `GET /conversations`, `GET /conversations/{id}` and `GET /conversations/{id}/messages` already existed and were `inbox:read`-gated, but the only frontend consumers were Live Chat (live triage) and Customer 360's exact-contact projection — no route reproduced the full, filterable, provider-independent history the product itself named as a gap. |
| No second query authority | PASS | `useConversations`, `useConversation`, `useMessages` and `useAssignableUsers` are imported unmodified from `features/inbox/api.ts`; the only change to that file is one additive `number` field on `toListQuery`, also used by nothing else in Live Chat's own behaviour (defaults to `null`, dropped by the client's query serializer). |
| Supported filters | PASS | Search (`q`), status, assignee and tag map onto the identical query params Live Chat already sends; `number` (channel) is a new, additive, contract-backed filter (the backend already accepted it — only the shared frontend type was missing it). Date-range and campaign-generated filtering are not offered; both are honestly named in the page header as not yet available rather than shown as disabled controls. |
| Read-only boundary | PASS | No assignment, status, tag, note or send control exists on the route; a dedicated regression (`18. exposes no composer or write action…`) asserts the absence of a composer textbox and every write-action button by name. |
| Live Chat deep link | PASS | "Open in Live Chat" navigates to `/inbox?conversation={id}` — the exact query shape `Inbox.tsx`'s own `readFilters` already parses. |
| Audit deep link / RBAC | PASS | Gated on `useHasPermission("audit:read")`, the same convention `CustomerProfile.tsx` already uses; hidden (not disabled) without the permission. Route and navigation entry both carry `inbox:read`, matching the endpoints' own guard; no new permission was introduced and `rbac/catalog.py` is untouched. |
| Tenant isolation | PASS | No client-supplied organization id exists anywhere in the diff; every read stays scoped server-side through the reused hooks and their existing endpoints. |
| Cursor pagination / bounded fetch | PASS | Conversation list uses the existing 25-row cursor page and `Pagination` control; message history uses the existing infinite-query "Load older messages" control (50-row pages). A dedicated regression asserts exactly one initial fetch per list with a `limit` query param, and that a further page is never fetched automatically. |
| Frontend lint | PASS | `eslint .` clean. |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Chat History tests | PASS | 22 new tests in `chat-history.test.tsx`, covering every required scenario (loading, empty, no-results, list/message error+retry, cursor progression, all five filter mappings, deep links, RBAC visibility, write-action absence, route/nav permission, cache reuse, bounded fetch, accessibility). |
| Relevant consumer tests | PASS | `inbox.test.tsx` (26, including the updated `toListQuery` shape), `customer-profile` (13), `components/layout` (21) — all pass unchanged in behaviour. |
| Full frontend suite | PASS | 37 files / 754 tests passed (731 before this remediation). |
| Production build | PASS | Main chunk `207.50/57.23 kB gzip` against `206.66/57.05 kB gzip` before this remediation (`+0.84 kB` raw, `+0.18 kB` gzip — route/nav/lazy-import registration and the additive `number` field only). The workspace itself is verified absent from the main chunk (zero matches for panel-unique text) and present only in its own lazy `ChatHistoryPage` chunk. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports up to date; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| Reference boundary | PASS | No reference file, screenshot, MHTML, rendered HTML or extracted asset was staged; captured AI Sensy screens informed workflow/hierarchy and visual-quality expectations only. |
| Remaining scope | Honestly recorded | Date-range filtering, campaign-generated identification, transcript export and a Download Center are not implemented — each requires a separately authorized backend change (`MessageResponse.campaign_id`, a date-range query param, a new export entity) and is recorded, not built, per the strict boundary. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes remain unproven by repository gates. |


## User Attributes management interface over the existing Custom Attribute contract

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified root cause | PASS | `GET/POST/PATCH/DELETE /api/v1/custom-attributes` existed and was contract-exposed with 7 passing backend tests, but the frontend issued only the list read consumed by the Contacts filter bar, campaign audience rules and segment predicates — no organization could define a typed field from the product. |
| Contract fidelity | PASS | Only generated fields used: `key_name` (1–60, immutable), `label` (1–120), `data_type` (one of `string`/`number`/`datetime`/`boolean`/`enum`, immutable), `enum_values` (required non-empty for `enum`), `is_indexed`, `is_pii`. No status, category, required/active flag, created-by display or unsupported ownership field was invented. |
| Immutable fields | PASS | `key_name` and `data_type` are offered only in the create dialog; the edit dialog shows both as read-only facts via the `DefinitionRow`/`<dl>` pattern (no `Field htmlFor` pointing at a non-labelable element), matching the update schema, which carries no field for either. |
| Frontend lint | PASS | `npm run lint` clean (one unescaped-apostrophe fix applied before commit). |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Settings tests | PASS | 23 new tests (20 panel + 3 pure-function) in `settings.test.tsx` — 97 passed (74 before). |
| Relevant consumer tests | PASS | Contacts, campaigns, segments and customer-profile test files — 181 passed, unchanged. |
| Full frontend suite | PASS | 36 files / 731 tests passed (708 before this remediation). |
| Backend attribute regressions | PASS | `tests/test_api_attributes.py` — 7 passed; no backend file changed. |
| 204 deletion handling | PASS | `useDeleteAttributeDefinition` checks `{ error }` directly rather than `unwrap`, matching the established pattern; the delete regression stubs an empty response and asserts the dialog closes. |
| Production build | PASS | Main chunk `206.66/57.05 kB gzip` against `206.24/56.97 kB gzip` before this remediation (`+0.42 kB` raw, `+0.08 kB` gzip — new route/lazy-import registration only). The panel itself is verified absent from the main chunk (zero matches for panel-unique text) and present only in the lazy settings chunk. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports up to date; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| Permission and tenant behaviour | PASS | Reads gated on `contacts:read`, writes on `contacts:write`, matching the endpoints; the route guard carries the same code; write controls are hidden rather than shown disabled. Tenant isolation remains entirely server-side in `AttributeService`; no client-supplied organization id exists anywhere in the diff. |
| Cache invalidation | PASS | Writes invalidate the literal `["custom-attributes"]` key `contactKeys.attributeDefinitions` already uses, plus the `["campaigns","pickers"]` prefix that already covers the campaign/segment picker's own key. A dedicated regression renders the panel beside the real `useCustomAttributeDefinitions` hook from `customer-profile/api.ts` under one shared `QueryClient` and proves a create refreshes that picker without a manual reload. |
| Stale-error isolation | PASS | Mutation state resets the moment a create/edit/delete dialog opens, the same fix already proven on Tags and Canned Messages; a dedicated regression fails one attribute, cancels, opens a dialog for a different attribute, and asserts no stale error carries over. |
| Reference boundary | PASS | No reference file, screenshot, MHTML, rendered HTML or extracted asset was staged; the only screen referenced (`0042_09_manage_05_user_attributes`) informed workflow/hierarchy only. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes, and behaviour at a realistic attribute volume remain unproven by repository gates. |


## Canned message scope accessibility fix

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified finding addressed | PASS | Independent audit Minor finding: `Field htmlFor="canned-message-scope"` labelled a non-labelable `<div>` in the edit dialog's read-only Scope row, creating no real accessible association. Replaced with the existing `DefinitionRow`/`<dl>` pattern already shipped in `OrganizationPanel`/`ApplicationPanel`; no fake input introduced. |
| Frontend lint | PASS | `npm run lint` clean. |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Settings tests | PASS | `settings.test.tsx` — 74 passed, unchanged; the existing edit-dialog and read-only-scope assertions pass against the corrected markup without modification. |
| Full frontend suite | PASS | 36 files / 708 tests passed, unchanged — a markup-only accessibility fix with no behavioural change. |
| Diff scope | PASS | One file changed: `frontend/src/features/settings/CannedMessagesPanel.tsx`. No backend, migration, OpenAPI, generated type, RBAC, ADR or roadmap file touched. |
| Host validation | PENDING – Host Machine Validation | A real screen-reader pass confirming the corrected association remains unproven by repository gates. |


## Canned Messages management interface over the existing Quick Reply contract

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified root cause | PASS | `GET/POST/PATCH/DELETE /api/v1/quick-replies` existed and was contract-exposed with 19 passing backend tests, but the frontend issued only the list read from `MessageComposer.tsx`, which rendered a dead-end "No quick replies yet." with no create path. |
| Contract fidelity | PASS | Only generated fields used: `shortcut` (1–60), `title` (1–120), `body` (1–4096), `shared` (boolean, creation-only). `usage_count` is read but intentionally not shown in the primary table — no send path increments it. No status, category, favourite, pinning, created-by display or unsupported ownership field was invented. |
| Immutable scope | PASS | `shared` is offered only in the create dialog; the edit dialog shows scope as a read-only badge with explanatory text and renders no toggle, matching the update schema, which carries no field for it. |
| Frontend lint | PASS | `npm run lint` clean. |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Settings tests | PASS | 18 new `CannedMessagesPanel` tests plus 1 section-permission test in `settings.test.tsx` — 74 passed (55 before). |
| Focused Inbox tests | PASS | 2 new tests proving the composer's empty-state Settings link appears only for `inbox:write`; `inbox.test.tsx` — 26 passed (24 before). |
| Full frontend suite | PASS | 36 files / 708 tests passed (687 before this remediation). |
| Backend quick-reply/tag regressions | PASS | `tests/test_api_quick_replies.py` and `tests/test_api_tags.py` — 25 passed; no backend file changed. |
| 204 deletion handling | PASS | `useDeleteQuickReply` checks `{ error }` directly rather than `unwrap`, matching the established pattern for an empty-body success; the delete regression stubs an empty response and asserts the dialog closes. |
| Production build | PASS | Main chunk `206.24/56.97 kB gzip` against `205.81/56.88 kB gzip` before this remediation (`+0.43 kB` raw, `+0.09 kB` gzip — the composer's new link). The panel itself is verified absent from the main chunk (`grep` for panel-unique text returns zero matches) and present only in the lazy settings chunk. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports up to date; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| Permission and tenant behaviour | PASS | Reads gated on `inbox:read`, writes on `inbox:write`, matching the endpoints; the route guard carries the same code; write controls are hidden rather than shown disabled. Tenant and ownership isolation remain entirely server-side in `QuickReplyService`; no client-supplied organization id exists anywhere in the diff. |
| Cache invalidation and composer refresh | PASS | Writes invalidate the literal `["quick-replies"]` key `inboxKeys.quickReplies` already uses; a dedicated regression renders the panel beside the real `useQuickReplies` hook from `inbox/api.ts` under one shared `QueryClient` and proves a create refreshes the composer's picker without a manual reload. |
| Stale-error isolation | PASS | Mutation state resets the moment a create/edit/delete dialog opens, mirroring the fix already proven on Tags; a dedicated regression fails one reply, cancels, opens a dialog for a different reply, and asserts no stale error carries over. |
| Composer empty-state change | PASS | Minimal, permission-correct: an `inbox:write` agent sees a link to Settings → Canned Messages; a read-only agent sees the same empty message with no link. The rest of the composer is unchanged. |
| Reference boundary | PASS | No reference file, screenshot, MHTML, rendered HTML or extracted asset was staged; the only screen referenced (`0045_09_manage_06_canned_message`) informed workflow/hierarchy only, and its create-modal internals were never captured, so no proprietary detail was available to copy. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes, and behaviour at a realistic canned-message volume remain unproven by repository gates. |


## Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

| Validation item | Status | Latest evidence |
|---|---|---|
| Scope | PASS | Frontend-only follow-up to the Tag management interface remediation, addressing five independently-audited findings; no backend, migration, OpenAPI, generated type, RBAC/permission, architecture or reference-material change. |
| Stale mutation state on reopen | PASS | `create`/`update`/`remove` mutation state is now reset at the moment a dialog opens, not only on success, so a prior failure cannot resurface as a false error in a freshly opened dialog for a different tag. |
| Delete-failure error visibility | PASS | The failed-delete `ErrorState` moved from the page top (rendered behind the still-open confirmation modal's backdrop) into the confirmation modal itself, where it is genuinely visible and announced (`role="alert"`) at the moment of failure. |
| Accessible row-action names | PASS | Row `Edit`/`Delete` buttons carry a per-tag `aria-label` (e.g. `Edit Prepaid`); visible text is unchanged. |
| Cross-feature cache-invalidation test | PASS | New regression renders `TagsPanel` alongside the real `useTags` hooks from `customer-profile/api.ts` and `campaigns/api.ts` under one shared `QueryClient` (no new cache-key system) and proves a create through Settings refreshes both existing pickers without a manual reload. |
| Duplicate-name conflict test | PASS | New regression injects a 409-shaped write failure via an additive, opt-in test-harness map (`writeErrors`, empty by default, does not alter any existing test) and proves the create dialog stays open, the typed name is retained, and the conflict is announced via `role="alert"`. |
| Failed-delete test | PASS | New regression proves the confirmation dialog stays open, the tag remains in the list, the error is visible, and retrying after the injected failure clears succeeds; the original successful `204` path continues to pass unchanged. |
| Loading-state test | PASS | New regression asserts `role="status"` / "Loading tags…" renders synchronously before the list query resolves. |
| Stale-error-does-not-leak test | PASS | New regression fails an edit and, separately, a delete on one tag, cancels each, then opens a dialog for a different tag and asserts no `role="alert"` is present — direct proof of the reset-on-open fix. |
| Frontend lint | PASS | `npm run lint` clean. |
| TypeScript | PASS | `tsc --noEmit` clean. |
| Focused Settings tests | PASS | `settings.test.tsx` — 55 passed (49 before this follow-up). |
| Full frontend suite | PASS | 36 files / 687 tests passed (681 before this follow-up). |
| Backend tag/quick-reply regressions | PASS | `tests/test_api_tags.py` and `tests/test_api_quick_replies.py` — 25 passed; no backend file changed. |
| Production build | PASS | Main chunk `205.81 kB / 56.88 kB gzip`, unchanged from the prior remediation — no new production dependency was introduced. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports `openapi.json is up to date`; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| Diff scope | PASS | Exactly two files changed: `frontend/src/features/settings/TagsPanel.tsx` and `frontend/src/features/settings/settings.test.tsx`; no untracked or reference material staged. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes remain unproven by repository gates. |


## Tag management interface (verified UI remediation)

| Validation item | Status | Latest evidence |
|---|---|---|
| Verified root cause | PASS | `GET/POST/PATCH/DELETE /api/v1/tags` existed and was contract-exposed, but the frontend issued only the list read, and `ContactTagsRequest` accepts ids of tags that already exist — so no tag could be created from the product. |
| Frontend lint | PASS | `npm run lint` clean. |
| TypeScript | PASS | `tsc --noEmit` clean for the application and browser test projects. |
| Focused panel tests | PASS | 10 new tests cover listing, the persistent empty-state create action, create/edit/delete requests, search and usage filtering, colour validation, read-only behaviour and error retry. |
| Existing settings and tag regressions | PASS | `settings.test.tsx` 49 passed; full frontend suite 36 files / 681 tests passed (671 before this change). |
| Backend tag regressions | PASS | `tests/test_api_tags.py` and `tests/test_api_quick_replies.py` 25 passed; no backend file changed. |
| Production build | PASS | Built in 4.32s. Main chunk `205.81 kB / 56.88 kB gzip` against a measured `205.36 kB / 56.80 kB gzip` baseline on the same checkout — `+0.45 kB` raw, `+0.08 kB` gzip, with the panel itself in the lazy settings chunk. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` reports `openapi.json is up to date`; path count unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` passed all six steps, including backend lint and strict types across 287 source files. |
| Migration head | PASS | `0041_channel_sync_control_plane`, 41 revisions — unchanged. |
| Permission and tenant behaviour | PASS | Reads gated on `contacts:read` and writes on `contacts:write`, matching the endpoints; the route guard carries the same code, and write controls are hidden rather than shown disabled. Tenant scoping stays server-side in `TagService`. |
| Contract honesty | PASS | Only contract fields are rendered. Tags have no status column, so the filter is usage derived from `usage_count`; no backend field was invented and no reference-specific concept was reproduced. |
| Self-review defect found and fixed | PASS | Pre-commit review caught the delete path calling `unwrap` on a `204 No Content` response. `unwrap` throws on an absent body, so every **successful** delete would have surfaced an error and left the dialog open. Corrected to the repository's established 204 pattern (`const { error } = await api.DELETE(...)`), and the regression now stubs an empty body and asserts the dialog closes. |
| Reference boundary | PASS | Capture inspected outside the repository; no reference file, asset, markup, style or copy was staged or reproduced. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual review, browser/device matrix, keyboard-only and screen-reader passes, and behaviour at a realistic tag volume remain unproven by repository gates. |


## M13-06B Provider-neutral History & Media Control Plane

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `f9a110d34f2095a3e9dbe61a779825edade38bda` on `ui/taste-modernization`. |
| Frozen architecture reuse | PASS | Existing M13-06A checkpoint/media records, ChannelConnection/Endpoint, MediaAsset, feature flags, RBAC and Audit remain the only authorities; ADR-0020/0021 and Design Document 33 are unchanged. |
| Provider-neutral lifecycle | PASS | Legal checkpoint transitions, monotonic progress, cutover/watermark bounds, resumable failed/cancelled state and fresh completed-run reset execute without provider I/O. |
| Tenant / object authorization | PASS | Actor organization, scoped connection/endpoint/media/reference ownership and foreign-id non-disclosure fail closed. |
| RBAC / feature flags | PASS | Dedicated `channels:history_sync` permission and default-off `omnichannel_qr_history` gate every write; reads require `channels:read`. |
| Capability boundary | PASS | History preparation requires declared `history_sync`; media registration requires declared upload/download media capability and an enabled endpoint. |
| Concurrency / idempotency | PASS | Optimistic row versions reject stale mutations; one checkpoint per scope and one provider media identity per endpoint are reused idempotently. |
| Secret / audit safety | PASS | Cursor and provider metadata reject secret-shaped content; lifecycle/progress/media actions emit redacted immutable Audit evidence. |
| Provider-certification boundary | PASS | No adapter, QR/login, provider cursor, live event ingestion, history retrieval, media-byte transfer, queue task, API or frontend execution surface exists. |
| Ruff / mypy | PASS | Ruff and strict mypy pass in workflow `31038662241`. |
| Backend tests | PASS | Five focused M13-06B tests and all 985 backend tests pass in workflow `31038662241`. |
| OpenAPI / generated client | PASS | OpenAPI remains semantically unchanged at 200 paths and generated TypeScript has no drift. |
| Migration | PASS | Permission-only `0041_channel_sync_control_plane` upgrades, downgrades to `0040`, and upgrades again; no table or high-volume ledger change. |
| Frontend / bundle | PASS | Frontend source is unchanged; ESLint, TypeScript, 36 files / 671 tests and production build pass; main remains `199.78/54.87 kB gzip`. |
| Security gates | PASS | Bandit, Python/frontend/browser dependency audits and tracked-source vulnerability/secret/IaC scan pass. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL permission migration, production KMS/flags/RBAC commissioning, provider certification, real cursors/events/media, monitoring and recovery remain unproven. |
| Milestone boundary | PASS | Exactly eight product/test/migration files plus six synchronized tracking ledgers; no provider dependency, API, frontend, governance or frozen-architecture change. |

## UI-TASTE-05 Owner Review, Release Candidate Audit and Merge Readiness

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `96bf0a8fcda01703b376a4ebf8f6f6e498a10108` on `ui/taste-modernization`. |
| Full repository review | PASS | Dashboard, Reactivation, Contacts, Customer 360, Inbox, Campaigns, Templates, Analytics, Notifications, Settings, Authentication, RBAC, Customer Identity, shared components and provider-neutral Module 13 foundations were reviewed as one release candidate. |
| Verified Major defect | PASS | Campaign create/edit route chunks imported `CampaignWizard` through a barrel re-export that Rollup warned could create broken execution order; direct module imports remove the cycle. |
| Navigation / integration | PASS | Route guards, deep links, URL-backed state, search, filters, pagination, modal/form/loading/error/empty/shared-component behavior remain covered by existing contracts and regressions. |
| RBAC / tenant / object authorization | PASS | Existing permission gates and tenant-scoped backend tests pass; no permission catalog, repository authority or audit behavior changed. |
| Backend gates | PASS | Ruff, strict mypy, bytecode/import integrity, semantic OpenAPI drift and all 980 backend tests pass in workflow `30982637585`. |
| Frontend gates | PASS | ESLint, TypeScript, 36 Vitest files / 671 tests and production build pass without the campaign circular chunk-order warning. |
| Security gates | PASS | Bandit, Python audit, E2E audit and Trivy high/critical source scan pass. Frontend production dependencies contain no high/critical advisory; two moderate React Router advisories remain recorded as non-Blocker/Major maintenance debt. |
| Performance | PASS | Main application JavaScript is `199.78/54.87 kB gzip`; existing authenticated route splitting and 250 ms global-search debounce remain intact. |
| Architecture / governance / provider boundary | PASS | No architecture, governance, provider certification, WAHA/Evolution, QR, runtime, live messaging, history or media-transfer work exists in this milestone. |
| Milestone boundary | PASS | Exactly two product files and six synchronized tracking ledgers change in one conventional commit. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual, browser/device, keyboard-only, screen-reader, contrast, touch, production-scale performance and deployed Playwright evidence remain unproven. |
| Merge readiness | PASS | No verified repository-scope Blocker or Major defect remains; branch is ready for explicit Owner Approval and Merge, not Production Ready. |

## UI-TASTE-04 Responsive, Accessibility and Performance Regression

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5af34560e4af99b476eabd9642f01d26af924eeb` on `ui/taste-modernization`. |
| Milestone boundary | PASS | Only eight verified UI quality defects, focused tests and six tracking ledgers changed; no feature, governance, architecture or provider work. |
| KYC permission truth | PASS | `/reactivation/kyc` reuses the existing `kyc:read` route guard. |
| Search efficiency | PASS | Record-search fan-out is delayed 250 ms and retains bounded permission-scoped APIs. |
| Keyboard and modal accessibility | PASS | Empty results keep index zero; shortcut guide uses shared focus entry/trap/Escape/restore; modal background scroll is locked. |
| Responsive pagination | PASS | Summary and controls wrap without requiring narrow-screen horizontal overflow. |
| Route performance | PASS | Authenticated page/panel modules lazy-load behind existing guards; main bundle improves to 199.78/54.87 kB gzip from 733.97/178.29 kB. |
| Dead code | PASS | Unrouted `ComingSoonPage` and its obsolete test are removed. |
| Ruff / mypy | PASS | Repository pre-merge quality gate passed in workflow `30980229127`. |
| Backend tests | PASS | All 980 backend tests pass. |
| OpenAPI / migration | PASS | OpenAPI remains 200 paths; migration head remains `0040_channel_sync_media_foundation`; no API or migration changed. |
| Frontend gates | PASS | ESLint, TypeScript, 36 Vitest files / 671 tests and production build pass. |
| Security gates | PASS | E2E TypeScript, Bandit, dependency audits and tracked-source vulnerability/secret/IaC scan pass. |
| Host validation | PENDING – Host Machine Validation | Authenticated visual, browser/device, keyboard-only, screen-reader, contrast, touch and production-scale performance evidence remain unproven. |
| Provider boundary | PASS | No provider evaluation/certification, WAHA/Evolution, QR runtime/session, ingestion/history/media, provider dependency or credential work exists. |

## UI-TASTE-03B Reactivation Operational Hierarchy

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5c3414bed1802276e99a9b02605dbde8e1cdcc36` on `ui/taste-modernization`. |
| Architecture and reuse | PASS | Existing Reactivation/Task/KYC/Document/Audit/Timeline and shared UI authorities are recomposed; no duplicate aggregate, reminder, saved-view, SIM, Activation or design-system authority exists. |
| CRM-first hierarchy | PASS | Reactivation root and historical operational links resolve to the real CRM or existing Contact import workflow; foundation placeholder tabs/panels are absent. |
| Permission truth | PASS | KYC, Document and Report navigation uses the same existing permissions as route guards; no RBAC policy changed. |
| Tenant-safe pagination | PASS | Additive non-negative offset uses the existing organization predicates, stable ordering, count query and bounded evidence projection; focused pagination regression passes. |
| URL-backed work context | PASS | Search/status/label/owner/reminder/date/view/page and factual due/overdue/completed work views survive refresh/share without claiming server-shared saved views. |
| Mutation and audit preservation | PASS | Transition, case edit, assignment, Task reminder, Audit, Customer Timeline and optimistic-concurrency paths are unchanged and existing workflow regressions pass. |
| Verified defects | PASS | Placeholder hierarchy, permission disclosure, 200-card render, lost filter context, duplicate filter controls, terminal drag, malformed separator and stale gating copy are corrected. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 4 focused Reactivation tests and all 980 backend tests pass in workflow `30953600784`. |
| OpenAPI / generated client | PASS | OpenAPI remains 200 paths with additive `offset`; generated TypeScript and drift checks pass. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 35 Vitest files / 668 tests and production build pass. |
| Security gates | PASS | E2E TypeScript, Bandit, Python dependency audit and tracked-source vulnerability/secret/IaC scan pass. |
| Migration | PASS | No migration is applicable; migration head remains `0040_channel_sync_media_foundation` and existing roundtrip tests pass. |
| Performance | PASS | Pipeline page is bounded to 25 cards; main is 733.97/178.29 kB gzip and Reactivation route is 82.25/19.37 kB gzip. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual/reference, screen-reader/device/browser matrix and production-scale query timing remain unproven. |
| Provider boundary | PASS | No provider evaluation/certification, WAHA/Evolution, QR runtime/session, live ingestion/history/media, provider dependency or production credential work exists. |
| Milestone boundary | PASS | Exact nineteen-file product/tracking boundary; Module 13 remains 44% and provider-dependent work remains blocked. |

## M13-06A Provider-neutral Sync & Media Persistence Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `2386b50bc1110e88f346ddff028cf1e017ad2503` on `ui/taste-modernization`. |
| Provider-neutral boundary | PASS | Sync/media state, models and repositories contain no WAHA, Meta or concrete provider branch and no executable provider path. |
| Existing-authority reuse | PASS | References existing ChannelConnection, ChannelEndpoint, JobMetadata and MediaAsset records; no duplicate channel, job, message, media or customer authority exists. |
| Tenant isolation | PASS | Every repository query requires organization scope; foreign organization lookups return no record. |
| Secret handling | PASS | Opaque cursor/provider metadata recursively rejects plaintext credential-shaped fields. |
| Persistence integrity | PASS | Scope/provider identity uniqueness, bounded non-negative progress and transfer-state constraints fail closed. |
| Runtime/certification boundary | PASS | No provider is certified; no adapter, runtime, pairing, event consumer, history executor, media transfer or queue task exists. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 18 focused channel/sync/media/migration tests and all 979 backend tests pass in workflow `30946554198`. |
| Frontend gates | PASS | Unchanged frontend passes production audit threshold, ESLint, TypeScript, Vitest and production build. |
| OpenAPI / generated client | PASS | OpenAPI remains semantically unchanged at 200 paths and generated TypeScript has no drift. |
| Migration | PASS | Additive `0040_channel_sync_media_foundation` upgrades, downgrades to `0039`, and upgrades again. |
| Dependency / security boundary | PASS | No dependency changed; Bandit and dependency audit pass. |
| Performance impact | PASS | No API query, worker, provider runtime or frontend bundle path changed; indexed bounded repository queries are the only new executable persistence surface. |
| Host validation | PENDING – Host Machine Validation | MySQL migration/rollback, production-scale query plans, real provider runtime, account/device evidence, monitoring, kill switch, recovery and certification remain unproven. |
| Milestone boundary | PASS | Only provider-neutral persistence/contracts/tests/status records changed; live M13-06 remains blocked. |

## M13-05 QR Pairing & Provider Runtime Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5d7ea154588418410611de4f568e978c2e3caba9` on `ui/taste-modernization`. |
| Provider-neutral runtime abstraction | PASS | Runtime metadata, lifecycle, events, health and pairing contracts contain no provider-specific branch and resolve execution only through the existing adapter seam. |
| Runtime registration/discovery/ownership | PASS | Thread-safe registry and tenant-scoped manager reject duplicate/conflicting runtime registrations, foreign organizations and unauthorized actors. |
| Session and persistence reuse | PASS | Runtime/pairing facts extend existing `ChannelSession` and `ChannelConnection`; no duplicate runtime, connection, credential, message or history authority exists. |
| Pairing lifecycle | PASS | UNPAIRED → PAIRING_REQUESTED → PAIRING_AVAILABLE with governed expiry/cancel/pair/active paths rejects illegal transitions and accepts no QR payload or token. |
| Runtime lifecycle/events/health | PASS | Factual lifecycle, event, health and capability observations persist with timezone-aware evidence and no live-provider claim. |
| Heartbeat, restart and recovery | PASS | Existing session heartbeat, lease/fencing, restart policy and recovery metadata are reused; stale holders and invalid fencing tokens fail closed. |
| Pairing expiry safety | PASS | Availability cannot be accepted after expiry, provider TTL is bounded, and expiry sweeps validate and limit batches to 1–1000 locked rows. |
| Security boundary | PASS | Tenant isolation, RBAC, disabled-by-default flags, constrained reason codes, secret-reference-only storage and Audit redaction are enforced. |
| Audit coverage | PASS | Runtime registration/ownership/lifecycle/health/capability/heartbeat/recovery and every pairing transition emit safe existing Audit evidence. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 20 focused channel/session/runtime/migration tests and all 976 backend tests pass in workflow `30933007710`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | Application and committed OpenAPI are semantically identical at 200 paths and generated TypeScript has no drift. Current dependency resolution exposes a pre-existing JSON key-order-only `--check` mismatch on the untouched M13-04 baseline; M13-05 adds no route/schema. |
| Migration | PASS | Additive `0039_qr_pairing_provider_runtime_foundation` upgrades, downgrades to `0038`, and upgrades again without destructive existing-schema changes. |
| Bandit / dependency / source scan | PASS | Bandit high-severity, Python dependency, frontend/browser audit thresholds and tracked-source vulnerability/secret/IaC scan pass. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL, real multi-node runtime/lease contention, provider certification, runtime supervisor/monitoring, KMS custody and representative tenant/RBAC/flag rollout remain unproven. |
| Milestone boundary | PASS | Exact sixteen-file implementation boundary before governance; M13-01–M13-04 remain authoritative and M13-06, provider adapters, QR image/login, sync, messaging, webhooks, routing and UI are absent. |

## M13-04 QR Session Manager Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `9d8f379f09719820c847be2b7c7df301e1617977` on `ui/taste-modernization`. |
| Provider-neutral session abstraction | PASS | Lifecycle, restart, health and capability contracts contain no Meta, WhatsApp or QR-specific branch and no provider adapter/runtime is registered. |
| Persistence reuse | PASS | One additive `channel_sessions` table links existing organization-owned `ChannelConnection`, optional endpoint/credential references and introduces no duplicate connection, credential, message or history storage. |
| Lifecycle and state transitions | PASS | REGISTERED → INITIALIZING → WAITING_FOR_PAIRING → ACTIVE → DEGRADED → RECONNECTING → PAUSED → EXPIRED → TERMINATED plus governed recovery paths reject illegal or terminal transitions. |
| Registration, discovery and ownership | PASS | Tenant-scoped repository/service registration, discovery and owner validation fail closed for foreign organizations and unauthorized users. |
| Health, heartbeat and expiration | PASS | Factual health/observation, heartbeat, lease expiry and explicit session expiry persist with timezone-aware evidence and no live-provider claims. |
| Recovery and restart policy | PASS | Provider-neutral recovery metadata, attempt counters, next-attempt facts and NEVER/ON_FAILURE/ALWAYS restart policies are durable and validated. |
| Locking and concurrency | PASS | Database leases, holder runtime ids, fencing tokens and optimistic row versions reject concurrent/stale runtime commands and support safe release/reacquisition. |
| Capabilities and provider metadata | PASS | Sessions reference normalized capability ids and existing provider/connection metadata; no new provider authority or provider-specific table exists. |
| Security boundary | PASS | Secret-shaped metadata is rejected, only existing credential references may be stored, Audit payloads serialize safe facts and no provider secret/API exposure exists. |
| Feature flags and RBAC | PASS | Disabled-by-default session read/write flags and `channels:read/manage/diagnose` permissions enforce organization-scoped discovery and mutation. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 279 source files. |
| Backend tests | PASS | 7 focused session/migration tests and all 970 backend tests pass in workflow `30913610932`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 remains 200 paths; generated TypeScript authority regenerates without drift. |
| Migration | PASS | Additive `0038_qr_session_manager_foundation` upgrades, downgrades to `0037`, and upgrades again without destructive existing-schema changes. |
| Bandit / dependency audit | PASS | Bandit high-severity gate and Python dependency audit pass; frontend production audit retains two pre-existing moderate React Router advisories and no high/critical failure. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration/rollback, real multi-node lease/fencing contention, runtime heartbeat/expiration/restart/recovery monitoring, KMS secret-reference custody and representative tenant/RBAC/flag rollout remain unproven. |
| Milestone boundary | PASS | Exact eleven-file implementation boundary before governance; M13-01–M13-03 behavior is preserved and M13-05, provider adapters/runtime, QR/login, sync, messaging, webhooks, routing and UI are absent. |

## M13-03 Persistent Channel Connections & Endpoint Records

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `283ebe83b53a510ce671f150bfe14fe38a5292f6` on `ui/taste-modernization`. |
| Provider-neutral persistence | PASS | Organization-owned connection, endpoint and credential records contain no Meta, QR or provider-specific schema/branch. |
| Tenant and organization isolation | PASS | Repository/service reads and writes require the actor organization and foreign identifiers disclose no record. |
| Immutable provider identifiers | PASS | Persisted connection and endpoint provider identifiers reject mutation; provider-neutral internal UUID ownership remains stable. |
| Lifecycle, health and metadata | PASS | Desired/observed state, factual health, provider/configuration/endpoint metadata, Audit references and timestamps persist without runtime/provider claims. |
| Soft delete and optimistic locking | PASS | Connections/endpoints/secrets carry deletion evidence and row versions; stale commands fail and logical connection deletion cascades endpoint deletion and credential revocation. |
| Encrypted credentials | PASS | AES-GCM sealed storage keeps ciphertext/nonce/tag only, rejects secret-shaped metadata, redacts representations and supports key/secret versions, rotation lineage, expiry, access evidence and revocation. |
| Secret exposure boundary | PASS | No public API route/schema was added; plaintext is absent from database metadata, Audit payloads, OpenAPI and generated client. |
| Feature flags | PASS | Existing disabled-by-default `omnichannel_connections_read/write` gates fail closed and preserve organization precedence. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 275 source files. |
| Backend tests | PASS | 4 focused persistence regressions and all 965 backend tests pass in workflow `30907651227`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 remains 200 paths; generated TypeScript authority regenerates without drift. |
| Migration | PASS | Additive `0037_persistent_channel_connections` upgrades, downgrades to `0036`, and upgrades again with the three new tables and no destructive existing-schema change. |
| Bandit / dependency audit | PASS | Bandit high-severity gate and Python dependency audit pass; frontend production audit has no high/critical failure and retains two pre-existing moderate React Router advisories. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration/rollback, production KMS/key custody, representative multi-tenant persistence, restore/retention policy and staged flag rollout remain unproven. |
| Milestone boundary | PASS | Exact nine-file implementation boundary before governance; M13-01/M13-02 behavior is preserved and M13-04, provider adapters/runtime, QR, sync, messaging, webhooks, routing and UI are absent. |

## M13-02 Customer Identity Resolution

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `c238bfa55d050310f865771be4654b90a5a993d2` on `ui/taste-modernization`. |
| Exact canonical identity | PASS | Organization/namespace/scope/value keys resolve only to the canonical Contact; fuzzy/profile-name matching is absent. |
| Immutable aliases and endpoint identities | PASS | Unique tenant-scoped ownership, provider/endpoint metadata and immutable links are enforced. |
| Ambiguity/conflict handling | PASS | Multiple/no authoritative candidates create a tenant-scoped review item; no automatic merge or ownership move occurs. |
| Recommendation decisions | PASS | Pending recommendations support explicit approve/reject with optimistic concurrency and never execute a merge. |
| RBAC, tenant and feature flag | PASS | Contact permissions, organization predicates and disabled-by-default `omnichannel_identity_resolution` fail closed. |
| Audit and Timeline | PASS | Link, conflict, recommendation and decision facts use existing Audit and Contact Timeline authorities. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 271 source files. |
| Backend tests | PASS | 22 focused identity/contact/channel tests and all 961 backend tests pass. |
| Frontend gates | PASS | Production audit, ESLint, TypeScript, Vitest and production build pass; application source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 has 200 paths and generated TypeScript authority is current. |
| Migration | PASS | `0036_customer_identity_resolution` upgrades, downgrades to `0035`, and upgrades again with all three tables present. |
| Bundle impact | PASS | Generated contract only; CSS, main and lazy-route application bundles remain unchanged and the existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration, representative operator review, production feature-flag rollout and runtime/security commissioning remain unproven. |
| Milestone boundary | PASS | M13-01 is unchanged and M13-03/provider/runtime/QR/UI work is absent. |


## M13-01 Generic Channel Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `8b878bdbd21877cf3f77eac5e9bb209d6b6022be` on `ui/taste-modernization`. |
| Existing adapter reuse | PASS | Provider metadata resolution delegates to the existing `get_adapter`; no second adapter factory or provider-specific service exists. |
| Provider/capability registries | PASS | Thread-safe registries reject conflicting metadata, expose factual capabilities and remain empty by default. |
| Communication intent and policy | PASS | Immutable organization-aware contracts cover channel, purpose, origin, bulk and required capabilities; policy evaluation fails closed with explicit reasons. |
| Health, lifecycle, metadata and enums | PASS | Immutable provider-independent states validate connector identity, timezone-aware observation, score and retry facts without inventing provider health. |
| Shared validation | PASS | Connector, text, organization, timestamp, score and capability validation use the existing channel error boundary. |
| Feature flags | PASS | `omnichannel_connections_read/write` use existing `feature_flags`; absent is off and organization rows override global rows. |
| Dependency injection | PASS | Cached empty foundation and request-scoped flag resolver are wired through existing API dependency conventions without startup/provider side effects. |
| Focused validation | PASS | Ruff, strict mypy and 46 channel/config tests pass, including seven new foundation regressions. |
| Full backend suite | PASS | 955 pytest tests pass in 260.89 seconds; strict mypy reports no issues across 263 source files. |
| Frontend repository gate | PASS | Unchanged frontend passes production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip and Operational Dashboard remains 31.96/8.61 kB gzip. |
| Migration/API/dependency boundary | PASS | Migration remains `0035_notification_center`, OpenAPI remains 193 paths, generated client and packages are unchanged. |
| Provider/runtime boundary | PASS | No QR/Meta runtime, pairing, session, history, live messaging, provider adapter or provider dependency exists. |
| Shared-authority boundary | PASS | Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, media, message and audit authorities are unchanged. |
| Exact changed-file boundary | PASS | Seven backend/test files only before governance; no migration, API v1, provider package, model table or frontend file. |
| Host/production evidence | PASS | Correctly limited to Repository Validated; no provider, host workflow, runtime performance, DR, Production Ready or Released claim. |
| Remaining contract gap | PASS | Persistent connection/endpoint/secret records and Meta backfill are explicitly recorded as Required and unimplemented. |
| Milestone boundary | PASS | M13-02 and all provider/runtime work remain unstarted. |

## M13-00 Architecture & Provider Lock

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Documentation work starts from `7e503a3f2e1d35d54548d9d8fe95e82591e26be1` on `ui/taste-modernization`. |
| Architecture decision | PASS | ADR-0020 is accepted and freezes one existing capability-based ChannelAdapter, one Contact/CRM/message ledger, endpoint-scoped conversations, independent provider failure domains and no automatic cross-provider failover. |
| Complete implementation contract | PASS | Design Document 33 covers all requested architecture, capability, provider, threat, security, session, identity, API, database, rollback, flag, rollout, DR, monitoring, performance, testing, acceptance, risk and dependency areas. |
| Existing-authority reuse | PASS | Contract names existing Meta adapter, ChannelAdapter, canonical models, Conversation/Message/Event/Send/Media services, Inbox, Customer 360, Timeline, Notification Center, Analytics, RBAC, tenant and Audit authorities; no duplicate service family is approved. |
| Provider capability matrix | PASS | Meta official capabilities and QR human/session/history/media capabilities are separated; templates, campaigns, broadcasts and bulk automation cannot route through QR. |
| QR provider gate | PASS | No vendor is fabricated. Required pass/fail evidence covers legal/policy, stable IDs, replay, ambiguous acknowledgement, secure session lifecycle, history, media, health, errors, isolation, support and testability. |
| Threat and security architecture | PASS | Assets, trust boundaries and spoofing/tampering/repudiation/disclosure/DoS/elevation/cross-tenant/split-brain/duplicate/merge/media/supply-chain threats have required controls and Blocker criteria. |
| Session lifecycle | PASS | Durable desired/observed states, legal transitions, single-holder lease, fencing, heartbeat, bounded reconnect, re-authentication and recovery rules are explicit. |
| Identity resolution | PASS | Exact organization/namespace/scope/value resolution, one identity-to-Contact ownership, no fuzzy auto-merge and restricted conflict handling are frozen. |
| API contract | PASS | Additive connection, lifecycle, QR-auth, endpoint/device/health, history and conversation-send resources follow existing `/api/v1`, UUID, RFC 7807, pagination, idempotency, concurrency and generated-contract conventions. |
| Database and migration contract | PASS | Eight approved generic records, additive existing-table links and expand/backfill/dual-write/verify/switch/contract stages are explicit; migration remains `0035` in M13-00. |
| Rollback, flags and rollout | PASS | Disabled-by-default server flags, Meta parity-first rollout, controlled QR pilots, explicit stop/go decisions and non-destructive rollback are defined. |
| DR, monitoring and performance | PASS | Durable/rebuildable state, recovery scenarios, safe dimensions/alerts and provisional latency/health/failover/zero-duplicate objectives are documented without claiming target-host measurements. |
| Testing and acceptance | PASS | Unit, API, migration, provider certification, security, browser/accessibility/operator, failure/DR suites and 27 final acceptance criteria are mapped to future executable milestones. |
| Gap analysis | PASS | Missing facts are classified as Required, Recommended or Future Enhancement; provider selection, legal review, production key management, migration evidence, runtime topology, idempotency, identity conflict handling, RPO/RTO, prerequisites and owner instruction are explicit Required gates. |
| Documentation consistency | PASS | The existing ChannelAdapter remains the only adapter abstraction. ADR-0020 additively resolves older Doc 07's Instagram exclusion only for future separately approved evaluation; no future provider is implemented or scheduled inside M13. |
| Product/change boundary | PASS | Diff is limited to ADR/design/governance Markdown. No backend, frontend, API, migration, generated contract, dependency, route, queue, runtime or deployment file changes. |
| Existing application evidence | PASS | Product source is unchanged, so existing `0035` / 193-path / 948-backend-test / 661-frontend-test baseline remains the applicable evidence; application suites are not falsely re-run or re-attributed to M13-00. |
| Host and production evidence boundary | PASS | M13-00 is correctly limited to `Repository Validated`; it claims no provider, browser, screenshot, operator, runtime performance, DR, Host Validated, Production Ready or Released evidence. |
| Milestone boundary | PASS | M13-01 and all implementation milestones remain unstarted and require a separate owner instruction. |

## UI-TASTE-03A operator-first Dashboard

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work begins from `7d826987c272d28038663ba9cb15c832c37e2b02` on `ui/taste-modernization`; no completed work is recreated. |
| Operator question coverage | PASS | Existing authorized sources answer attention, blocked customers, pending KYC, SIM SLA risk, overdue Activation, Campaign action, unread replies, blocked Templates, agent workload and today KPI change. |
| Source truth and boundaries | PASS | Dashboard composes existing APIs only; no backend, duplicate projection, fake count, local persistence or generated-contract edit exists. Failed sources are disclosed and never rendered as zero. |
| Permissions and tenant behavior | PASS | Queries are enabled only when their existing read permission is present; source APIs retain tenant/RBAC authority and deep links. |
| Loading, empty and error states | PASS | Accessible skeletons, factual empty states, partial-source warning, source-specific retry and permission-empty state are implemented. |
| Accessibility and responsive contracts | PASS | Semantic links/buttons/headings/tables, focus-visible treatment, live loading status, touch-safe actions and desktop-table/mobile-card transformations are present; existing layout regressions pass. |
| Decision rules | PASS | Four focused tests cover blockers, KYC/Campaign/Inbox/Template action classification, agent aggregation and metric-aware KPI direction. |
| Full frontend gates | PASS | Production audit, ESLint and TypeScript pass; 34 Vitest files / 661 tests pass; Vite production build passes. |
| Verified bug fixes | PASS | Strict typing caught and fixed KPI sentiment widening; full-suite regression caught and fixed loss of Live Chat/New Campaign link semantics. |
| Performance | PASS | Dashboard is lazy-split to 31.96 kB / 8.61 kB gzip; main chunk improves from 747.91 kB to 733.62 kB, though the existing >500 kB warning remains. |
| Migration/API/dependency boundary | PASS | Migration remains `0035_notification_center`; OpenAPI remains 193 paths; no generated client or package dependency changes. |
| Authenticated representative-data visual/reference review | PENDING – Host Machine Validation | Repository/jsdom/build gates cannot prove final density, long-content overflow, contrast, screen-reader behavior or approved-reference comparison on target devices. |
| Milestone boundary | PASS | Only Dashboard composition, conditional-query support, focused tests and required governance evidence are included; Reactivation redesign is absent. |

## UI-TASTE-02 shared enterprise design system

| Validation item | Status | Latest evidence |
|---|---|---|
| Starting baseline and branch | PASS | Implementation starts from `9043fe03a80b682a010304c88c5d29d8ec77d1fa` and targets `ui/taste-modernization`; the original CORE-09 lineage remains `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`. |
| Shared architecture | PASS | Existing React/Tailwind architecture is extended in place with named radius tiers, forward-ref form controls, toolbar/filter composition, cursor pagination, and refinements to existing Button/Card/PageHeader/PageContainer primitives; no parallel design system exists. |
| Product workflow preservation | PASS | Contacts URL filters/import/bulk flow, Inbox quick views/search shortcut/saved views/bulk mutations/thread flow, and Notification polling/read/team/deep-link behavior are unchanged. |
| Sidebar, navigation and contract boundary | PASS | Sidebar, TopNav structure, command palette, mobile navigation, routes, permissions, backend, migration `0035`, 193-path OpenAPI, generated client, and dependencies are unchanged. |
| Accessibility and responsive contracts | PASS | Shared controls retain labels, forward refs, focus-visible rings, invalid/disabled/busy semantics and mobile targets; existing 21 layout, 24 Inbox, 4 Contacts toolbar and 3 Notification Center tests pass. |
| Focused shared-primitive regression | PASS | Three new tests cover semantic labels/help/errors, invalid state, action slots, cursor pagination disabled/callback behavior, and loading-button accessible name/`aria-busy`. |
| Lint, typecheck and full frontend suite | PASS | ESLint passes; `tsc --noEmit` passes; 33 Vitest files and 657 tests pass. |
| Production build and bundle measurement | PASS | Vite transforms 2,599 modules and builds successfully; CSS is 49.39 kB / 9.79 kB gzip and the main application chunk is 747.91 kB / 181.62 kB gzip. The known >500 kB warning remains recorded debt. |
| Production dependency boundary | PASS | `npm audit --omit=dev --audit-level=high` reports only two moderate React Router advisories and no high/critical production finding. Combined development/build tooling reports 11 transitive findings and requires a separate upgrade milestone. |
| Originality and scope | PASS | Implementation is original, uses existing semantic product tokens and Lucide icons, imports no reference code/assets/branding/layout, adds no fake data/metric/placeholder, and introduces no heavy animation library. |
| Authenticated representative-data visual and reference comparison | PENDING – Host Machine Validation | Source review and jsdom tests cannot prove final visual density, long-content overflow, screen-reader behavior, or desktop/tablet/mobile comparison against the approved reference library. Owner/host review is required before Priority 2. |
| Milestone boundary | PASS | Only Priority 1 shared-system work and required governance evidence are included; Dashboard and all other Priority 2 screen redesign work remain absent. |

## CORE-07 Customer 360 domain convergence

| Validation item | Status | Latest evidence |
|---|---|---|
| One customer identity and source ownership | PASS | The existing public Contact id joins persisted source authorities; Customer 360 introduces no snapshot, duplicate model, local record, synthetic metric, or write authority. |
| Conversations and messages | PASS | Existing Inbox repository/service/API and Message ledger accept an exact tenant-scoped Contact filter; unknown/foreign identifiers disclose no records and malformed ids fail through shared validation. |
| Reactivation and Vi facts | PASS | Existing pipeline/case/Task/note/KYC/SIM/Activation contracts provide real status, labels, owner, reminders, SLA, reservation, family-plan, conversion and immutable evidence facts. |
| Documents, Tasks, Campaigns, Audit and Timeline | PASS | Existing permission-scoped sections and source deep links are reused; Timeline and Audit remain views over their existing immutable authorities. |
| RBAC, tenant isolation and read-only behavior | PASS | Backend exact-contact tenant regressions and frontend denied/error/read-only regressions pass; tag mutations are hidden without `contacts:write`. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover persisted composition and honest empty/error/denied states; authenticated 1280×720, 768×1024 and 390×844 review found no page overflow or console errors and verified Arrow-key tab navigation. |
| Reference and originality review | PASS | Paired `0001`, `0008`, `0010` and `0048` approved captures were reviewed for contextual hierarchy, density, tabs and activity patterns; no proprietary code, asset, branding, wording, exact styling or reference file is shipped. |
| Focused and full tests | PASS | Focused backend APIs pass 21/21 and Customer 360 passes 5/5; canonical suites pass 945/945 pytest and 651/651 Vitest. |
| Migration and API boundary | PASS | Migration remains the single `0034_reactivation_crm` head; OpenAPI remains 3.1.0 with 189 paths and regenerated TypeScript drift is clean. |
| Deployed runtime | PASS | Static/application/security/release steps passed; after aligning the stale E2E tab assertion, the rebuilt frontend/runner passed Playwright 1/1 in 11.1 seconds against fresh MySQL/Redis/Celery, with p95 10.4 ms across 30 reads. |
| Verified defect regressions | PASS | Tests cover exact-contact history, foreign/malformed filters, permission-safe tag actions, factual/no-placeholder composition and the converged production tab contract. |
| Milestone boundary | PASS | No CORE-08 approval engine, migration, endpoint family, duplicate authority, fake data, copied reference content, or completed-module rebuild was introduced. |

## CORE-05 lightweight Reactivation CRM correction

| Validation item | Status | Latest evidence |
|---|---|---|
| Primary status and labels | PASS | Exactly one of nine constrained current statuses and unique multi-label membership pass model/service/migration tests; current status/label concepts do not overlap and immutable legacy stage events are retained. |
| Follow-up and Release dates | PASS | Follow-up and Name Change require their governed dates, date-bearing labels require an assigned owner, timezone-aware inputs normalize to UTC, and removing a label cannot submit a stale date. |
| Reminder lifecycle | PASS | Existing TaskService owns create/update/Complete/Snooze/Reschedule, keeps overdue work open until resolved, enforces row versions, and records immutable Task, Audit and Customer Timeline evidence. |
| Due delivery and infrastructure | PASS | The existing Celery beat/worker topology registers 25 application tasks; the bounded due adapter uses `scheduler.tick`, marks durable assigned-user due evidence, and the deployed MySQL/Redis/Celery stack is healthy. |
| RBAC, tenant isolation and concurrency | PASS | Permission-scoped Reactivation/Task endpoints, organization-scoped joins/filters, ownership validation, stale versions and duplicate/idempotent commands fail closed in focused and full suites. |
| Real persisted UI | PASS | Existing board/list/drawer consume only generated API contracts and real projections; status/label/assignee/reminder-date filters, due counters, chips, pointer/keyboard movement and Complete/Snooze/Reschedule survive server refreshes. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover loading, empty, recoverable error, permission/read-only boundaries, labelled controls/dialogs, keyboard movement, desktop dense table/Kanban and mobile list/drawer transformation. |
| Authenticated representative-data visual review | PENDING – Host Machine Validation | Final target-browser/device and screen-reader review requires a host account with representative labels, due/overdue Tasks, users, and cases; repository component and deployed browser gates pass. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were reviewed for filters, chips, staff selection, forms and responsive hierarchy; no reference code, asset, branding, text, exact styling or file is shipped. |
| Focused and full tests | PASS | Focused Reactivation/API/KYC backend tests pass 11/11 and Reactivation/Tasks/KYC frontend tests pass 25/25; canonical deployed suites pass 943/943 pytest and 646/646 Vitest. |
| Migration and API boundary | PASS | One additive head `0034_reactivation_crm` advances 34 linear revisions; OpenAPI advances only from 188 to 189 paths (+1), generated contracts/drift pass, and the backend image registers 25 tasks. |
| Verified defect regressions | PASS | Tests cover stale date serialization, versioned reminder actions, owner-only reminder reassignment, server-required Not Required reasons, UTC normalization, populated-data migration rollback, updated image contract and five-entry beat schedule; no test or permission was weakened. |
| Milestone boundary | PASS | No heavy SIM fulfilment/Activation workspace, parallel reminder/notification store, fake data, local-only state, completed-module rebuild, migration downgrade, API removal, reference asset, or `.reference/aisensy/` content was introduced. |

## CORE-04 KYC operations

| Validation item | Status | Latest evidence |
|---|---|---|
| Creation prerequisites and governed checks | PASS | Eligible document-ready Reactivation cases create one tenant-scoped KYC case idempotently; holder, Delhi-presence and active-number checks plus invalid/stale commands pass service/API tests. |
| Protected document checklist | PASS | Aadhaar/PAN checklist entries reference verified same-tenant/same-contact Document Center records; protected-access denial passes and no schema/API/UI/audit field stores identity numbers. |
| Appointment lifecycle | PASS | Creation reuses idempotent TaskService; reschedule, completion and cancellation reuse existing Task commands, immutable events, audit and Customer Timeline evidence. |
| Reviewer/manager authority separation | PASS | Requester cannot review; manager must differ from requester and approved reviewer; structured rejection/information reasons, approval prerequisites and immutable decision history pass. |
| Reactivation handoff | PASS | Only valid manager approval advances the existing case through `kyc_pending` to `verification` using the CORE-02 transition authority, optimistic concurrency and immutable stage/audit/Timeline evidence. |
| RBAC and tenant isolation | PASS | KYC/document/task read-write-decide-approve permissions and cross-tenant denial pass focused service/API tests; UI exposes permission-aware read-only/denied states. |
| Customer 360 and shared reuse | PASS | Existing Reactivation drawer, protected DocumentWorkspace, Task lifecycle, Customer 360 section, Contacts/User directory, Audit, Timeline, RBAC, SLA and design-system states are extended; no parallel authority exists. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover factual queue/detail, checklist/actions, loading, empty, error, read-only, accessible labels/tabs/drawer, desktop table and mobile-card transformation, and no mock fallback. |
| Authenticated representative-data browser review | PENDING – Host Machine Validation | The local protected route and anonymous redirect were verified; a target-host account with representative KYC/protected-document data and final desktop/tablet/mobile browser matrix is required for authenticated visual/WCAG sign-off. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for density, filters, forms, action placement and layered workspaces; no proprietary code, asset, branding, exact styling, wording or reference file is shipped. |
| Focused and full tests | PASS | 24 focused backend and 33 focused cross-feature frontend tests pass; canonical suites pass 940/940 pytest and 646/646 Vitest. |
| Migration and API boundary | PASS | One additive head `0033_kyc_operations` fills verified reference/Task/reason constraints; OpenAPI advances only from 184 to 188 paths (+4) and generated TypeScript drift is clean. |
| Milestone boundary | PASS | No SIM fulfilment, Activation Queue, fake operational data, plaintext identity number, duplicate document/task/approval/timeline system, or completed-module rebuild was introduced. |

## CORE-03 Reactivation pipeline

| Validation item | Status | Latest evidence |
|---|---|---|
| Persisted pipeline and factual counts | PASS | Tenant-scoped joined projection returns all fifteen approved stage counts and bounded cards from real cases, contacts, owners, eligibility, tasks, documents, SLA, reservation, family, and conversion facts; no fixture fallback exists. |
| Governed transitions and concurrency | PASS | All permitted/rejected lifecycle moves pass exact matrix tests; drag, keyboard, and drawer actions use the CORE-02 transition service, server-published targets, idempotency, and `row_version`; stale writes return conflict. |
| RBAC and tenant isolation | PASS | Read/write/transition actions are permission-aware; cross-tenant pipeline, note, case, owner, task, and document access fails closed in service/API tests. |
| Assignment and immutable evidence | PASS | Assignment/number edits reuse the versioned CORE-02 update authority; transitions and notes retain immutable stage/audit/Customer Timeline evidence. |
| Shared module reuse | PASS | Existing Contacts/User directory, Customer 360, Tasks/reminders, Documents, Audit, Timeline, SLA, Modal, router, and design system are extended in place; no completed module was rebuilt. |
| UI states and accessibility | PASS | Focused tests cover loading, empty, error, permission, responsive board/list, pointer/keyboard movement, drawer labelling/focus, and no-mock guarantees. Authenticated 1280×720, 768×1024, and 390×844 review found no page-level horizontal overflow. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for shell, filters, density, modal/drawer and responsive patterns; no proprietary code, asset, branding, exact styling, wording, or reference file is shipped. |
| Focused CORE-03 tests | PASS | 6 focused backend service/API tests and 9 focused Reactivation/foundation frontend tests pass; the full suites pass 938/938 and 641/641. |
| Migration/API boundary | PASS | Migration remains single head `0032`; verified projection/note gaps add only 2 paths, advancing OpenAPI from 182 to 184 with generated TypeScript drift clean. |
| Milestone boundary | PASS | No KYC operations workspace, SIM fulfilment UI, Activation Queue, migration, mock lead card, fake count, local-only workflow state, or duplicate authority was introduced. |

## CORE-02 Vi domain foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Domain records and constraints | PASS | All ten approved records are registered; tenant/contact/case uniqueness, fixed values, positive/ordered SLA constraints, serial uniqueness, and immutable histories are covered by model/migration tests. |
| Transition and prerequisite rules | PASS | Reactivation, KYC preparation/approval, SIM fulfilment, activation approval/completion, and SLA command tests passed; invalid/stale commands fail closed. |
| Idempotency and concurrency | PASS | Same-key/same-command replays return existing outcomes; mismatched reuse and stale row versions return conflict evidence in focused tests. |
| RBAC and tenant isolation | PASS | Fifteen additive permissions, role defaults, API denial, manager approval boundaries, public UUID scoping, and cross-tenant 404 behavior passed. |
| Audit, Timeline, and durable facts | PASS | Material commands atomically append audit rows, Customer Timeline projections, and existing-ledger business events without introducing a parallel authority. |
| Milestone boundary | PASS | No Reactivation Kanban, KYC workspace, SIM fulfilment UI, Activation Queue, fake data, placeholder workflow, duplicate CRM pipeline, document store, timeline, or event bus was added. |
| Focused CORE-02 tests | PASS | 6 focused service/API/migration tests passed, including migration upgrade/downgrade/re-upgrade. |
| Deployed domain foundation | PASS | MySQL applied `0032`; API, Redis, Celery workers/beat, frontend, and nginx reached healthy state in the isolated ten-service stack. |

## CORE-01 navigation and product shell

| Validation item | Status | Latest evidence |
|---|---|---|
| Permitted navigation catalogue | PASS | Six-item task rail, grouped More surface, shared create actions, honest maturity labels, and permanent scope guard passed focused and full-suite tests. |
| RBAC and excluded concepts | PASS | Permission-filtered navigation/create/search tests passed; Ads, Payments, Billing, marketplace, SaaS/multi-project, and commerce destinations remain absent. |
| Keyboard and focus behavior | PASS | Menus, command palette, and mobile drawer expose state, close on Escape where applicable, trap dialog focus, and restore invoking focus. |
| Responsive active states | PASS | Compact/expanded rail, secondary routes, and primary mobile-overflow routes passed focused tests; mobile targets are at least 44px. |
| Reference and originality review | PASS | Six paired full/viewport workflows were inventoried; authenticated 1280×720 shell, More, and command palette were compared without importing reference code or assets. |
| Authenticated browser smoke | PASS | Dashboard shell and factual downstream-error states rendered at 1280×720 with a 72px rail, 672px command palette, and no horizontal overflow. |
| Focused frontend tests | PASS | 30/30 navigation/foundation tests passed after the final responsive active-state correction. |
| Source/migration/API boundary | PASS | Product scope sources, all 31 migrations, OpenAPI JSON, and generated TypeScript contract are unchanged from the CORE-01 baseline. |

## GOV-02 documentation and governance

| Validation item | Status | Latest evidence |
|---|---|---|
| Required governance files | PASS | All ten required root documents, ADR-0012, and Design Document 25 are present and non-empty. |
| Markdown structure and relative links | PASS | Heading/table structure and repository-relative Markdown links passed the GOV-02 static check. |
| Product-goal and priority consistency | PASS | Scope, rules, roadmap, tracker, ADR, and experience standard agree on the permanent target and ordered priorities. |
| Reference boundary and originality | PASS | Approved/conditional/prohibited categories, local-only ignore policy, fourteen-step review, and no-copy boundary are recorded consistently. |
| Exclusions | PASS | Ads, payments, billing/subscriptions, marketplace, reseller/multi-project, public signup, and commerce remain excluded. |
| No-placeholder and premium screen gate | PASS | Real-state rule, shared-component standard, continuous-quality boundary, and twenty-point Definition of Done are locked. |
| Changed-file boundary | PASS | GOV-02 changes only Markdown governance, ADR, and design files; no source, test, API, migration, configuration, or runtime file changed. |
| Reference library isolation | PASS | `.reference/` is locally ignored and no capture/archive file is tracked or staged. |
| Migration invariance | PASS | Migration head remains `0031_automation_trigger_receipts` with 31 linear revisions. |
| OpenAPI invariance | PASS | `frontend/openapi.json` remains OpenAPI 3.1.0 with 153 paths and is unchanged from the starting Git baseline. |

## Backend

| Validation item | Status | Latest evidence |
|---|---|---|
| Pytest | PASS | Canonical validation passed 945/945 backend tests in 523.29 seconds. |
| Migration validation | PASS | Single head `0034_reactivation_crm`; 34 linear revisions; SQLite upgrade/downgrade/re-upgrade and deployed MySQL upgrade passed. Generic SQLite `alembic check` remains non-authoritative because of pre-existing repository-wide reflection noise. |
| Ruff | PASS | Canonical deployed profile passed Ruff across application, tests, scripts, and root tools. |
| Mypy | PASS | Canonical deployed profile passed strict mypy across 253 backend source files. |
| Python compile | PASS | `compileall` passed for backend application/scripts and root scripts. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | Frontend and Playwright TypeScript checks passed in the canonical deployed profile with regenerated contracts. |
| ESLint | PASS | Frontend ESLint passed without errors or warnings after the final CORE-07 hook-dependency correction. |
| Vitest | PASS | Full suite passed 651/651 tests across 31 files. |
| Playwright | PASS | Isolated production owner journey passed 1/1 against the final CORE-07 images in 11.1 seconds. |
| Production build | PASS | TypeScript and Vite production build passed after final CORE-07 source and generated-contract changes; the known main-chunk warning remains non-blocking. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | Live generation and drift validation passed; OpenAPI 3.1.0 remains at 189 paths with optional exact-Contact filters and no removed path. |
| Generated TypeScript contracts | PASS | Exact-contact Inbox/Reactivation query contracts are regenerated; frontend typecheck and drift checks passed. |

## Infrastructure

| Validation item | Status | Latest evidence |
|---|---|---|
| Docker | PASS | Development/production Compose models, ten-service release contract, production builds, 189-path/25-task backend and frontend image contracts, Trivy source/image scans, SBOMs, and isolated deployment passed. |
| Celery | PASS | Realtime, bulk, and jobs workers plus beat reached healthy state; the backend image registered 25 tasks including due-reminder dispatch, and queued journey evidence passed. |
| Redis | PASS | Isolated Redis reached healthy state and supported the deployed queue/readiness journey. |
| Target production commissioning | PENDING – Host Machine Validation | TLS/host hardening, UAT, restore/rollback rehearsal, receiver delivery, and production approval require the target host. |

## Accessibility

| Validation item | Status | Latest evidence |
|---|---|---|
| Existing responsive/keyboard baseline | PASS | CORE-01/03/04/05 evidence remains green; CORE-07 adds labelled tab panels, Arrow/Home/End behavior, focus-safe source actions, denied/read-only states, zero-overflow desktop/tablet/mobile browser evidence, and no console errors. |
| Full final-scope WCAG regression | PENDING – Host Machine Validation | Must be repeated on every completed final-scope route with real domain data and the target browser/device matrix. |

## Performance

| Validation item | Status | Latest evidence |
|---|---|---|
| Standard-read canary | PASS | Deployed CORE-07 canary recorded p95 10.4 ms across 30 authenticated reads, below the 300 ms budget. |
| Full load/stress/spike/soak and 1M-contact certification | PENDING – Host Machine Validation | Requires the isolated Performance Lab and production-like capacity. |

## Known limitations

| Validation item | Status | Current limitation |
|---|---|---|
| Target observability receivers | PENDING – Host Machine Validation | Log shipping, dashboards, alert firing/dead-man delivery, and external synthetic checks need deployed receivers. |
| Production frontend bundle | PENDING – Host Machine Validation | The main chunk warning is 737.53 kB; further route splitting remains a performance task. |
| Docker-backed source scan | PASS | Trivy vulnerability, secret, and IaC scan passed; production backend/frontend image vulnerability scans and CycloneDX SBOM generation also passed. |
| React Router advisories | PENDING – Host Machine Validation | Two moderate advisories require an explicit React Router 7.18+ upgrade milestone, not a silent dependency change. |
| Customer 360 target commissioning | PENDING – Host Machine Validation | Repository/deployed representative-data checks pass; final target screen-reader/device matrix and production-scale query-budget certification remain host work. |
| Final domain workflows | PENDING – Host Machine Validation | CORE-07 completes Customer 360 convergence; General Approval, Notification Center, Google Sheets, Download Center and later roadmap domains remain. Heavy standalone SIM/Activation workspaces are not planned without explicit owner instruction. |

## Milestone closeout rule

A new result replaces prior evidence only after the exact command has completed. A failure remains
`FAIL` until rerun successfully. Environment-dependent checks stay
`PENDING – Host Machine Validation`; they must never be relabelled `PASS` from repository-only
inference.
