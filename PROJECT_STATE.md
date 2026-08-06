# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Latest change | `User Attributes management interface over the existing Custom Attribute contract (frontend only)` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `HEAD` (M13-06B closeout; resolve after push) |
| Current milestone | `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED` |
| Current phase | `Repository-owned history/media control plane validated; provider certification still blocks all live M13-06 execution` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0041_channel_sync_control_plane` (41 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · additive Reactivation `offset` query; no new route |
| Backend evidence | Ruff PASS · strict mypy PASS · 5 focused M13-06B tests PASS · 985 full pytest tests PASS |
| Frontend evidence | ESLint PASS · TypeScript PASS · 36 Vitest files / 731 tests PASS (708 before this remediation) · production build PASS without the campaign circular chunk-order warning |
| Bundle evidence | Main `206.66/57.05 kB gzip`, against `206.24/56.97 kB gzip` before this remediation (`+0.42 kB` raw, `+0.08 kB` gzip — the new route/lazy-import registration only); the User Attributes panel itself is verified absent from the main chunk and present only in the lazy settings chunk (`+~10.2 kB` there) |
| M13 contract | ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `48%` evidence-based estimate: M13-01–M13-05 plus M13-06A persistence and M13-06B repository-owned lifecycle controls |
| QR provider | WAHA evaluation requires additional evidence; no provider is certified and no adapter, QR image, protocol or live login exists |
| Next Module 13 milestone | None authorized; provider certification host evidence is mandatory before live provider-dependent M13-06 work |
| Host evidence | Target-host MySQL migration, real multi-node runtime/lease contention, provider certification, runtime supervision/monitoring, KMS custody and staged tenant/RBAC/flag commissioning remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | Frontend-only user-attribute management panel over the existing custom-attribute contract, plus synchronized tracking; no backend, migration, API, provider adapter or live execution |
| Last update | `2026-08-06T05:00:00+05:30` (Asia/Kolkata) |

## User Attributes management interface over the existing Custom Attribute contract

- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete, but the frontend only
  ever issued the list read consumed by the Contacts filter bar, campaign audience rules and
  segment predicates, so no organization could define a typed field from the product itself.
- Create, edit and delete for `contacts:write` holders; `key_name` and `data_type` are immutable
  after creation, shown as read-only facts in the edit dialog via the same `DefinitionRow` pattern
  Canned Messages already established.
- Search, a data-type filter, and `Indexed`/`PII` shown as informational badges; the delete
  confirmation accurately states that every contact's stored value for the definition is removed
  too.
- Writes invalidate the exact `["custom-attributes"]` cache key the Contacts page already reads,
  plus the campaign/segment picker's key prefix, so a new attribute is selectable in both without a
  reload.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07.

## Canned Messages management interface over the existing Quick Reply contract

- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete, but the frontend only ever
  issued the list read from the Message Composer's `/shortcut` picker, so the canned-message
  vocabulary could not be populated from the product on a new organization.
- Create, edit and delete for `inbox:write` holders; `shared` (Personal/Shared) is selectable only at
  creation and shown as read-only information in the edit dialog, matching the contract's
  immutable-after-creation rule.
- Search, a scope filter and a body preview over supported fields only; `usage_count` is read but not
  shown, since no send path increments it yet.
- Writes invalidate the exact `["quick-replies"]` cache key the composer already reads, so a new
  canned message is selectable there without a reload; a permission-correct link was added to the
  composer's empty state for `inbox:write` agents only.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07.

## Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

- Reset stale `create`/`update`/`delete` mutation state when a dialog opens, so a previous failure
  cannot resurface as a false error in a freshly opened dialog for a different tag.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.
- Added regressions for cross-feature cache invalidation (real `useTags` hooks, one shared
  `QueryClient`, no new cache-key system), a duplicate-name conflict, a failed delete with retry, an
  explicit loading state, per-tag accessible row-action names, and a dedicated proof that a failed
  attempt's error does not resurface when a dialog is later opened for a different tag.
- Frontend only. Not a roadmap milestone, not M13-07; Settings/Tags/Attributes completion claims are
  unchanged from the prior remediation.

## Tag management interface delivered as a verified UI remediation

- Added a Settings → Tags panel over the existing `GET/POST/PATCH/DELETE /api/v1/tags` endpoints.
  The contract was already complete and permission-scoped, but the frontend only ever issued the list
  read, and attaching a tag takes the id of one that already exists — so the tag vocabulary could not
  be populated from the product and every shipped tagging surface stayed empty on a new organization.
- Create, rename, recolour, describe and delete are offered to `contacts:write` holders only; readers
  get the same table with no write control rendered at all.
- Only contract fields are shown. Tags have no status column, so the filter is usage derived from the
  existing `usage_count`; no backend field was invented and no reference-specific concept was copied.
- Frontend only: no backend file, migration, endpoint, permission definition, OpenAPI path or
  generated type changed. This is not a roadmap milestone, not M13-07, and does not complete Settings.

## M13-06B delivered provider-neutral history and media control plane

- Added lifecycle commands and factual observations over M13-06A persistence without introducing a
  provider executor, queue task, event consumer, API or frontend surface.
- Dedicated `channels:history_sync` RBAC and `omnichannel_qr_history` default-off flag protect writes;
  organization, endpoint ownership, declared capability and optimistic versions fail closed.
- Checkpoints enforce legal state transitions, monotonic counts/watermarks, live cutover boundaries and
  distinct resumable-failure versus fresh-completed-run behavior.
- Media references reuse existing `MediaAsset`/endpoint authorities, are idempotent by provider identity,
  require media capability and accept only non-secret factual observations.
- Workflow `31038662241` validates 985 backend tests, unchanged 200-path OpenAPI and unchanged frontend.

## UI-TASTE-05 completed owner review and merge readiness

- Full repository review found one verified Major release-candidate defect in the campaign lazy import
  graph; direct module imports remove the Rollup circular execution-order risk without changing behavior.
- Workflow `30982637585` passes all applicable repository gates, with main JavaScript at `199.78/54.87 kB gzip`.
- No verified repository-scope Blocker or Major defect remains. Moderate dependency advisories and all
  authenticated target-host visual/device/screen-reader/performance evidence remain explicitly pending.
- The branch is ready for explicit Owner Approval and Merge; it is not Host Validated or Production Ready.

## UI-TASTE-04 delivered responsive, accessibility and performance regression

- Added destination-specific KYC route protection under the existing Reactivation permission shell.
- Debounced global record search, kept empty keyboard state valid and reused shared modal focus
  behavior for the shortcut guide.
- Shared modal background scrolling and shared pagination narrow-layout overflow are corrected.
- Authenticated route modules now split behind the existing shell and guards; main JavaScript is
  199.78/54.87 kB gzip.
- Removed only the verified unused `ComingSoonPage`; no feature, API, migration, permission,
  architecture, governance or provider behavior changed.

## UI-TASTE-03B delivered Reactivation operational hierarchy

- `/reactivation` now resolves to the real CRM; primary section navigation exposes only connected
  destinations allowed by existing route permissions.
- Pipeline filters/work views/display/page are URL-backed, use shared controls, and request 25
  tenant-scoped records through an additive offset query under the existing stable ordering.
- Historical foundation routes redirect to factual filtered CRM or Contact import authorities.
- Existing transitions, assignment, reminders, KYC, Documents, Audit, Customer Timeline and
  optimistic concurrency are unchanged.
- Reactivation is `94%`; Module 13 remains `44%` and all provider-dependent behavior remains blocked.

## M13-06A delivered provider-neutral sync and media persistence foundation

- Added `channel_sync_checkpoints` for organization/connection/endpoint-scoped opaque cursor, watermark, cutover, progress, status, error and optimistic-concurrency facts.
- Added `media_channel_references` to map existing `MediaAsset` records to endpoint-scoped provider media identifiers with expiry, verification and transfer-state facts.
- Added tenant-scoped repositories, non-secret metadata enforcement, bounded list queries and database constraints using the existing model/repository authorities.
- No provider runtime, adapter, queue task, history execution, media fetch/upload, event consumer or API was introduced.

## M13-05 delivered provider runtime and pairing foundation

- Added provider-neutral runtime metadata, lifecycle, event and health contracts plus a thread-safe runtime registry that resolves executable behavior only through the existing `ChannelAdapter` seam.
- Added `ProviderRuntimeManager` registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat integration, restart/recovery metadata and durable `ChannelSession` projection.
- Added a no-store `PairingManager` abstraction with governed `UNPAIRED`, `PAIRING_REQUESTED`, `PAIRING_AVAILABLE`, `PAIRING_EXPIRED`, `PAIRING_CANCELLED`, `PAIRED` and `ACTIVE` transitions; no QR payload, image, token or provider credential is persisted.
- Reused M13-04 lease/fencing, optimistic concurrency, session ownership, health, heartbeat, restart/recovery and Audit authorities rather than creating a second runtime truth table.
- Added disabled-by-default runtime/pairing flags, runtime/pairing RBAC permissions, additive migration `0039_qr_pairing_provider_runtime_foundation` and tenant-scoped expiry sweeps bounded to 1–1000 records.

## Preserved completed foundations

- M13-01 provider metadata/capability registries, M13-02 Contact identity, M13-03 connection/endpoint/encrypted-secret persistence and M13-04 session lifecycle/lease/fencing remain authoritative.
- Existing Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, message, media and Audit authorities remain unchanged.

## Preserved boundaries

- No QR image generation/scanning, WhatsApp login or protocol, provider adapter, history/message synchronization, incoming/outgoing messages, webhook runtime, routing, Inbox, Customer 360, Analytics or frontend behavior exists.
- No public API route, OpenAPI path, generated client surface, provider dependency, provider-specific table or runtime message storage was added.
- Pairing persistence contains state, timestamps and constrained reason codes only; secret references continue to use existing encrypted credential records.

## Validation boundary

Repository validation proves provider-neutral registry/runtime/pairing contracts, tenant/RBAC/flag
boundaries, durable session integration, lease/fencing enforcement, bounded expiry, health, heartbeat,
restart/recovery metadata, Audit redaction, additive migration, lint, typing, full regressions, source
security scans and unchanged frontend/API semantics. OpenAPI generation under the current unpinned
FastAPI/Pydantic resolver has a pre-existing JSON key-order mismatch at the untouched M13-04 baseline;
semantic schemas are equal and M13-05 introduces no route or schema. It does not prove a live provider,
QR scan/login, target-host multi-node runtime behavior, provider certification, production monitoring,
disaster recovery or rollout.

## Required remaining contract work

Target-host commissioning and provider certification remain mandatory. Live inbound events, history
execution, media transfer/processing, outbound messaging and unified operator experience remain
later gated milestones. M13-06A persistence plus M13-06B lifecycle controls do not satisfy provider certification or execute live work.

## Existing UI modernization state

UI-TASTE-03A, UI-TASTE-03B, UI-TASTE-04 and UI-TASTE-05 are repository-validated. Authenticated representative-data
visual/reference, screen-reader/device, and production-scale performance review remains pending.

## Maintenance rule

Stop after M13-06B. No later implementation milestone is authorized. Provider certification continues to block every live/provider adapter, ingestion, history retrieval, media transfer, messaging, routing and provider UI path.
