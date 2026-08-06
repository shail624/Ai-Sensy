# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-07 · Alembic version-table MySQL fix (long revision ids), on top of the Chat History pagination/polling/accessibility hardening, the Dedicated Chat History workspace, the User Attributes remediation, its test-hardening follow-up and M13-06B. Provider certification still blocks every live history, media, event and adapter behavior._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `4e745718a73e76630742aac5ba98f808367053f7`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0041_channel_sync_control_plane` (42 revisions, was 41) · 200 paths — head and OpenAPI path count both unchanged by this remediation; one revision inserted before the existing head
- **Current milestone:** `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED`
- **Latest change:** Repaired a verified MySQL-only migration failure (`alembic_version.version_num` too narrow for this repository's revision-id length) with a dedicated inserted revision, `0035a_widen_version_table` — a backend-migrations-only fix, not a roadmap milestone and not M13-07
- **Completion:** Shared Enterprise Design System `94%` · Global Search `85%` · Reactivation `94%` unchanged · Module 13 `48%` unchanged · Chat History `55%` unchanged (this fix removes a schema/auth blocker, not the separate UI-preview data blocker)
- **Backend evidence:** Ruff PASS · strict mypy PASS · 991 full pytest tests PASS (985 before this remediation; +6: 3 hermetic migration-graph checks + 3 live-MySQL migration/create-owner checks)
- **Frontend evidence:** unchanged by this remediation (no frontend file touched); static quality gate frontend steps still pass
- **Provider selection:** WAHA evaluation requires additional evidence; no provider is certified or registered
- **Next milestone:** `None`; provider certification and separate owner instruction are required before any live M13-06 work
- **Last synchronized:** `2026-08-07T02:00:00+05:30`

## Delivered

### Alembic version-table MySQL fix — support long revision ids

- **Verified failure:** `alembic upgrade head` against a real MySQL 8 database (this repository's
  own `docker compose up -d` infrastructure) failed transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Alembic's own `alembic_version.version_num`
  bookkeeping column defaults to `VARCHAR(32)`; this repository's descriptive revision-id
  convention produces identifiers up to 43 characters, and `0036_customer_identity_resolution`
  (33 characters) was the first to exceed it. No real MySQL deployment had ever advanced past
  `0035_notification_center` — this blocked all schema creation, `create-owner`, authentication,
  and any real UI preview on MySQL.
- **Repair:** a new revision, `0035a_widen_version_table`, inserted between
  `0035_notification_center` and `0036_customer_identity_resolution`, widens
  `alembic_version.version_num` to `VARCHAR(255)` on MySQL only (dialect-guarded; SQLite has no
  length enforcement and PostgreSQL is not part of this stack). `0036_customer_identity_resolution`'s
  `down_revision` was retargeted to the new revision; its own id, schema body and behaviour are
  byte-for-byte unchanged. No revision was renamed, renumbered, squashed, reordered, or stamped
  past a failure. Head remains `0041_channel_sync_control_plane`; the chain stays linear with a
  single head (42 revisions, was 41).
- Verified on real MySQL 8, both via automated tests (throwaway per-test databases) and by
  reproducing the documented CLI workflow manually against a fresh `docker compose` instance: a
  fresh database upgrades base→head; a database stamped at `0035_notification_center` (the exact
  historical failure point) upgrades to head; `python -m app.cli create-owner` succeeds
  immediately afterward, including its documented idempotent re-run behaviour.
- Regression coverage added: three hermetic checks in `test_migrations.py` (single head, linear
  chain, every revision id fits the widened column with an early-warning margin) plus a new
  `test_migrations_mysql.py` — three tests against real, throwaway MySQL databases, skipped
  (never failed) when no MySQL server is reachable, so the hermetic default suite gains no new
  external dependency.
- Frontend, application endpoints, models, schemas, RBAC, and OpenAPI are all unchanged;
  `scripts/export_openapi.py --check` and the full static quality gate both pass.
- **Does not unblock the separate Chat History UI-preview gap:** producing a real, populated
  `/chat-history` screenshot still requires either live Meta WhatsApp Business API credentials (to
  register a phone number and create genuine conversations/messages) or an approved development
  fixture mechanism, neither of which exists. This fix repairs the schema/auth path only.

### Dedicated Chat History read workspace over the existing conversation and message contract

- Added a `/chat-history` route and permission-aware `inbox:read` navigation entry — a read-only
  list/detail workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read, reusing
  `useConversations`/`useConversation`/`useMessages`/`useAssignableUsers` from
  `features/inbox/api.ts` verbatim — no second query authority.
- Supports every filter the current contract already backs: search (`q`), status, assignee, tag,
  and a new `number` (channel) filter — additive to `InboxFilters`/`toListQuery`, the same shared
  types Live Chat's own filters use, so the addition is available to both surfaces from one
  definition. Cursor pagination for the conversation list and the existing infinite-query
  "Load older messages" control are both reused as-is.
- Deliberately exposes no assignment, status, tag, note or send control — those remain Live Chat's
  job; this route only reads. A deep link opens the selected conversation in Live Chat; a second
  deep link to the audit trail is shown only to `audit:read` holders and hidden otherwise.
- Date-range filtering and transcript export are named in the UI as not yet available rather than
  offered as disabled controls — neither is backed by the current contract (`MessageResponse` has
  no `campaign_id`, the endpoints have no date-range query param, and no export entity exists for
  this data).
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed. Closes the frontend half of `ROADMAP.md`'s `CORE-10`; the
  backend "Conversation query extensions" and export capability it also names remain unimplemented
  and are recorded as open follow-up, not claimed here.
- **Follow-up hardening (same day):** removed the dead Previous-page control (the backend never
  returns `prev_cursor`) in favour of a bounded "Back to newest" reset; disabled the inherited 10s
  poll for the selected conversation's detail and messages via an optional, backward-compatible
  `refetchInterval` override on `useConversation`/`useMessages` (Live Chat and Customer 360 keep
  their existing default); moved focus into the detail pane on narrow viewports and restored it to
  the originating row on return; included the `contact` deep-link filter in active-filter
  detection; matched the status badge to Live Chat's open-only success convention; and added an
  accessible name to the message list plus a page/thread heading pair. Twelve new tests; no
  backend, contract, RBAC or percentage change.

### User Attributes management interface over the existing Custom Attribute contract

- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete, but the frontend only
  ever issued the list read consumed by the Contacts filter bar, campaign audience rules and
  segment predicates, so no organization could define a typed field from the product itself.
- Create, edit and delete for `contacts:write` holders; `key_name` and `data_type` are immutable
  after creation, shown as read-only facts in the edit dialog via the same `DefinitionRow`
  pattern Canned Messages already established, rather than disabled controls.
- Search, a data-type filter, and `Indexed`/`PII` shown as informational badges; the delete
  confirmation accurately states that every contact's stored value for the definition is removed
  too.
- Writes invalidate the exact `["custom-attributes"]` cache key the Contacts page already reads,
  plus the campaign/segment picker's key prefix, so a new attribute is selectable in both existing
  pickers without a reload.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed.

### Canned Messages management interface over the existing Quick Reply contract

- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete, but the frontend only ever
  issued the list read from the Message Composer's `/shortcut` picker, so the canned-message
  vocabulary could not be populated from the product on a new organization.
- Create, edit and delete for `inbox:write` holders; `shared` (Personal/Shared) is selectable only
  at creation, matching the immutable-after-creation contract, and shown as read-only information in
  the edit dialog rather than offered as a control.
- Search across shortcut/title/body, a scope filter, and a body preview; `usage_count` is read but
  intentionally not shown, since no send path increments it yet.
- Writes invalidate the exact `["quick-replies"]` cache key `MessageComposer.tsx` already reads, so a
  new canned message is selectable from the composer without a reload. A permission-correct link was
  added to the composer's empty state for `inbox:write` agents only.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed.

### Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

- Reset stale `create`/`update`/`delete` mutation state when a dialog opens, so a previous failure
  cannot resurface as a false error in a freshly opened dialog for a different tag.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.
- Added regressions for cross-feature cache invalidation (against the real `useTags` hooks already
  used by contact/inbox and campaign/segment/automation pickers, under one shared `QueryClient`, no
  new cache-key system), a duplicate-name conflict, a failed delete with retry, an explicit loading
  state, per-tag accessible row-action names, and a dedicated proof that a failed attempt's error
  does not resurface when a dialog is later opened for a different tag.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Settings/Tags/Attributes completion claims are unchanged from the prior remediation.

### Tag management interface (verified UI remediation)

- Added a Settings → Tags panel over the existing tag endpoints. The contract was already complete,
  but the frontend only issued the list read, and attaching a tag requires the id of one that already
  exists — so on a new organization the tag vocabulary could never be populated from the product and
  every shipped tagging surface stayed empty.
- Create, rename, recolour, describe and delete are now available to `contacts:write` holders, with
  search, a usage filter, client-side paging, inline validation, a live preview, and a delete
  confirmation that states how many contacts would be detached.
- Writes invalidate the shared `["tags"]` cache and the campaign picker cache, so a new tag is
  selectable in the existing contact and conversation attach flows without a reload.
- Frontend only: no backend file, migration, endpoint, permission definition, OpenAPI path or
  generated type changed. Module 13, its architecture and its provider boundary are untouched.

### M13-06B Provider-neutral History & Media Control Plane

- Added one provider-neutral service over the existing checkpoint/media-reference persistence; it
  owns no provider call, queue execution, API route, event ingestion, history retrieval or media bytes.
- History checkpoints are feature-gated, permissioned, tenant/object scoped, capability-gated and
  versioned; legal transitions, monotonic progress, cutover/watermark boundaries and restart semantics
  fail closed and emit immutable Audit evidence.
- Provider media identifiers reuse existing `MediaAsset` and `ChannelEndpoint` authorities; registration
  is idempotent, declared media capability is required and factual transfer observations reject secrets.
- Additive migration `0041_channel_sync_control_plane` seeds only `channels:history_sync`; OpenAPI and
  frontend remain unchanged.

### UI-TASTE-05 Owner Review, Release Candidate Audit and Merge Readiness

- Completed a full repository release-candidate audit across product routes, shared components,
  authentication/RBAC, tenant/object authorization evidence, API contracts, audits and Module 13
  provider-neutral boundaries.
- Fixed one verified Major defect: campaign create/edit lazy chunks no longer depend on a cyclic barrel
  re-export that Rollup warned could break execution order.
- Full repository validation passes in workflow `30982637585`; the main application bundle is `199.78/54.87 kB gzip`.
- No feature, architecture, governance, provider, QR, runtime, API, migration, dependency, permission
  catalog or roadmap-sequencing change was made.
- No verified Blocker or Major defect remains in repository-verifiable scope. The branch is ready for
  explicit Owner Approval and Merge, not Host Validated or Production Ready.

### UI-TASTE-04 Responsive, Accessibility and Performance Regression

- Reactivation KYC deep links now reuse the existing `kyc:read` route authority.
- Workspace record search waits 250 ms before issuing bounded permission-scoped requests; empty
  collections retain keyboard index zero and truthful loading feedback.
- Keyboard shortcuts use the shared modal authority; shared modals lock background scroll and shared
  pagination wraps without narrow-screen overflow.
- Authenticated pages and administrative panels load at their route boundaries; the main JavaScript
  bundle measures 199.78/54.87 kB gzip.
- Verified unused `ComingSoonPage` code is removed. No business workflow or route was added.

### UI-TASTE-03B Reactivation Operational Hierarchy

- Real Reactivation CRM is the default route; only connected and permission-available KYC,
  Document, and Report destinations remain in primary Reactivation navigation.
- Existing pipeline search/filters are URL-backed and use shared controls; factual All active,
  Due today, Overdue, and Completed work views preserve refresh/share context.
- Existing tenant-scoped stable ordering now supports additive non-negative offset pagination at
  25 cases per page without a new table, service, route, permission, or authority.
- Historical SIM/Activation/Completed/Interested/bulk links resolve to existing filtered CRM or
  Contact import workflows instead of placeholder operational shells.
- Design Document 34 records reuse, originality, responsive/accessibility, security, validation, and
  host-evidence boundaries.


### M13-06A Provider-neutral Sync & Media Persistence Foundation

- Added inert organization-scoped history checkpoints and endpoint-scoped provider media references from the frozen data model.
- Added bounded progress/count constraints, opaque non-secret cursor metadata, expiry/verification facts, optimistic concurrency and tenant-scoped repositories.
- Extended only the existing capability vocabulary with `history_sync`; no adapter implementation or provider branch exists.
- Additive migration `0040_channel_sync_media_foundation`; no API, generated-contract, queue, dependency or frontend source change.

### M13-05 QR Pairing & Provider Runtime Foundation

- Provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing adapter seam.
- Tenant-scoped runtime registration, discovery and ownership; durable capability observations, health/lifecycle reports, heartbeat, restart policy and recovery metadata on the existing `ChannelSession` authority.
- No-store pairing lifecycle with constrained state/reason/timestamp facts only; no QR payload, image, token, protocol credential or login implementation.
- Lease/fencing and optimistic-concurrency enforcement for runtime reports; holder-specific observations reset safely when runtime ownership changes.
- Disabled-by-default runtime/pairing flags, dedicated permissions, Audit coverage and bounded pairing-expiry processing.
- Additive migration `0039_qr_pairing_provider_runtime_foundation`; no API, generated-contract or frontend source change.

### Preserved M13-01 through M13-04 authorities

- Existing `ChannelAdapter`, provider metadata/capability registries, canonical Contact identity, persistent connection/endpoint/encrypted-secret records and durable session lifecycle/lease/fencing remain authoritative.
- No provider implementation, duplicate persistence authority or shared CRM/message/UI authority was added.

## Validation

- Repository pre-merge quality gate PASS in workflow `31038662241`.
- Ruff and strict mypy PASS; OpenAPI/generated-client drift PASS at 200 paths.
- Full backend regression: 985 PASS; migration head is `0041_channel_sync_control_plane`.
- Frontend ESLint and TypeScript PASS; 36 Vitest files / 671 tests PASS; production build PASS.
- E2E TypeScript, Bandit, Python/frontend/browser dependency audits and tracked-source
  vulnerability/secret/IaC scan PASS.
- Main application bundle remains 199.78/54.87 kB gzip; no frontend or API execution path changed.
- Five focused M13-06B tests cover lifecycle, RBAC/flags, tenant isolation, capability boundaries,
  idempotency, audit, secret rejection and absence of public/provider execution.
- Host/provider certification evidence remains `PENDING – Host Machine Validation`.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, live event ingestion,
provider history retrieval, media-byte transfer/processing, sending, incoming webhooks, routing, Inbox/Customer
360/Analytics changes, public runtime/pairing/sync APIs and provider-specific tables are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider certification host evidence and all live M13-06 inbound/history/media execution plus later messaging/operator milestones.

## Stop rule

Stop after M13-06B. No implementation milestone is authorized after this commit.

Do not begin provider adapter, QR image/login, live event ingestion, provider history retrieval,
media-byte transfer, messaging, webhook, routing or provider UI until certification and a separate
owner instruction.
