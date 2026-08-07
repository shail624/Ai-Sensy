# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Latest change | `QR-01 — WAHA provider adapter foundation: connector identity, minimal typed client, authenticated server probe, deterministic error mapping, engine/version guard (no session, QR, pairing or messaging)` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `HEAD` (M13-06B closeout; resolve after push) |
| Current milestone | `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED` |
| Current phase | `Repository-owned history/media control plane validated; provider certification still blocks all live M13-06 execution` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0042_scope_provider_message_identity` (43 linear revisions — QR-00 adds one additive, index-only migration after `0041_channel_sync_control_plane`; no column added, no backfill, no data change) |
| OpenAPI | `3.1.0` · `200` paths · additive Reactivation `offset` query; no new route |
| Backend evidence | Ruff PASS · strict mypy PASS (292 files) · 1099 full pytest tests PASS (1036 before QR-01; +63 WAHA adapter tests) |
| Frontend evidence | ESLint PASS · TypeScript PASS · 37 Vitest files / 766 tests PASS (754 before this hardening pass) · production build PASS without the campaign circular chunk-order warning |
| Bundle evidence | Main `207.50/57.27 kB gzip`, against `207.50/57.23 kB gzip` before this hardening pass (raw unchanged, `+0.04 kB` gzip — the optional `refetchInterval` parameter on the shared hooks only); the Chat History workspace itself is verified absent from the main chunk (zero matches for panel-unique text) and present only in its own lazy `ChatHistoryPage` chunk |
| M13 contract | ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `48%` evidence-based estimate: M13-01–M13-05 plus M13-06A persistence and M13-06B repository-owned lifecycle controls |
| QR provider | WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0) selected as the ADR-0021 Class B candidate — **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED**. QR-01 adds a registered `waha` adapter performing **an authenticated server probe only** (version/engine banner and server health). It declares exactly one capability (`HEALTH`); `BULK`/`CAMPAIGNS`/`TEMPLATE` are permanently prohibited and test-enforced. **No WhatsApp session, QR generation, pairing, webhook ingestion, send path, history/media transfer, session runtime or UI exists.** `ProviderRuntimeRegistry` has no WAHA runtime. Unconfigured and disabled by default. QR login does not work and is not claimed to |
| Next Module 13 milestone | `QR-05 — send path`. Not started. Physical-phone certification **PASSED** on 2026-08-08 — paired session reaching `WORKING`, external inbound text and JPEG, external outbound with `DEVICE`/`READ` acknowledgement, HMAC-verified webhooks, history/fullSync correlation and logout are all certified — and has now been consumed by QR-02 (lifecycle mapping) and QR-03 (pairing) |
| Host evidence | Repository/local-host MySQL migration evidence (not target-host): against a real MySQL 8 instance run via this repository's own `docker compose up -d` on the development workstation, `alembic upgrade head` succeeds both from a fresh database and from one already stamped at `0035_notification_center` (the state every prior real MySQL attempt was capped at), and `python -m app.cli create-owner` succeeds afterward and is idempotent on rerun — see `0035a_widen_version_table` remediation below. This is local Docker evidence only; genuine target-host MySQL migration and rollback evidence remain pending. A real-MySQL downgrade defect at `0036_customer_identity_resolution`/`0040_channel_sync_media_foundation` (`DROP INDEX ... needed in a foreign key constraint`) is a separately tracked open defect, pre-existing and not introduced by this fix; remediation is out of scope here. Real multi-node runtime/lease contention, provider certification, runtime supervision/monitoring, KMS custody, staged tenant/RBAC/flag commissioning, automated CI execution of the live-MySQL migration tests, and a real, populated UI preview (blocked separately by the lack of an approved conversation/message fixture mechanism) remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | QR-01 adapter foundation: connector identity, minimal typed WAHA client, authenticated server probe, deterministic error mapping, engine/version guard, conservative capabilities. No migration, OpenAPI, RBAC or frontend change; no session, QR, pairing, webhook, send or runtime |
| Last update | `2026-08-07T05:00:00+05:30` (Asia/Kolkata) |

## QR-04 — WAHA webhook ingestion

- **Scope:** verify and normalize provider deliveries onto the **existing** `ChannelAdapter` webhook
  seam and `webhook_events` ingest authority. Declares `SESSION_STREAM`.
- **No parallel ingest path, no new route, table or migration** — the persist-first durability,
  dedupe and dead-letter behaviour already owned by `WebhookService` is reused, not duplicated.
- **Dedupe identity:** scoped by session and provider event type. Certification proved
  `envelope.id` alone is unsafe (one message arrives as both `message` and `message.any` sharing
  it) and that delivery is at-least-once with retries repeating every id. Determinism is proven by
  a concurrent test because `messages` is partitioned and MySQL cannot enforce the constraint.
- **Security:** signature verified before parsing, over raw bytes, constant-time, body bounded
  before hashing, unset secret rejects everything, unknown/malformed shapes fail closed to
  `UNKNOWN` and are dead-lettered rather than dropped.
- **Not pulled forward:** acknowledgements and outbound echoes are recorded, never applied —
  delivery state is QR-05. No teardown, history or media execution.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-05 send, QR-06 reconnect/health/logout, QR-07 UI, QR-08 Unified Inbox,
  QR-09 production validation. There is still no QR route or operator UI.

## QR-03 — WAHA QR pairing

- **Scope:** create a WAHA session with the certified store configuration, fetch the transient QR
  challenge a handset scans, and report provider-neutral pairing state. Declares `QR_AUTH`.
- **Up, never down:** no stop, restart, logout or delete exists on adapter or client. Teardown is
  QR-06, so nothing shipped so far can destroy a working pairing.
- **QR is never persisted or logged:** `WahaQrChallenge` is a transient value that redacts its own
  bytes, preserving M13-05's boundary that QR images and challenge bytes are deliberately absent
  from persistence.
- **`fullSync` camelCase, centrally built:** certification proved the snake_case spelling is
  accepted and then silently ignored, leaving a healthy-looking session with no history.
- **Pairing safety:** an ambiguous provider status (`STARTING`/`STOPPED`/`FAILED`) yields no pairing
  claim, so durable pairing truth is never overwritten by inference.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with **zero** QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health/logout, QR-07 UI,
  QR-08 Unified Inbox, QR-09 production validation. There is still no QR route or operator UI, so
  QR login is not usable by an operator and is not claimed to be.

## QR-02 — WAHA session lifecycle read and provider-neutral mapping

- **Scope:** read one named WAHA session's status and translate it into the platform's own
  `SessionState`/`PairingState` vocabulary. One authenticated read; a pure mapping; no runtime.
- **Read-only and capability-neutral:** nothing is created, started, stopped, restarted, paired or
  logged out; capabilities remain exactly `HEALTH`. Adapter and client are asserted to expose no
  session-mutation or QR method.
- **Mapping:** `SCAN_QR_CODE → waiting_for_pairing/pairing_available`; `WORKING → active/paired`;
  `STARTING`, `FAILED`, `STOPPED` → `initializing`/`degraded`/`paused` with **no** pairing claim,
  because the status alone cannot determine whether credentials exist. `FAILED` is deliberately not
  terminal — certification recovered it with a controlled restart.
- **Evidence basis:** every status and transition encoded here was observed during physical-phone
  certification against `devlikeapro/waha@sha256:33ecd1b7…` (2026.7.2 / NOWEB / CORE), not read off
  documentation. Tests are hermetic; the payloads they assert are the captured real shapes.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths, RBAC, generated types, frontend, and the absence of a WAHA entry in
  `ProviderRuntimeRegistry`. No Production Ready, Host Validated or M13-07 claim.
- **Still pending at QR-02:** QR-03 QR pairing (since delivered), QR-04 webhook ingestion, QR-05
  send, QR-06 reconnect/health, QR-07 UI, QR-08 Unified Inbox, QR-09 production validation.

## QR-01 — WAHA provider adapter foundation

- **Scope:** a registered `waha` adapter that can perform **one thing** — an authenticated probe of
  the WAHA *server* (version/engine banner and `/health`) — plus deterministic error mapping and an
  engine/version guard. Nothing else. No WhatsApp session is created, resumed or inspected; no QR is
  requested, generated, persisted or logged; no phone is paired; no webhook is received; no message
  is sent or ingested; no media or history is transferred; no session worker or reconnect runtime
  exists. `ProviderRuntimeRegistry` deliberately has **no** WAHA runtime.
- **Connector identity:** `connector_type = "waha"`, `channel_type = "whatsapp"` — a second
  *implementation* of the same channel family behind the existing `ChannelAdapter` seam, never a
  second channel and never a parallel hierarchy (ADR-0020 invariant 1).
- **Capabilities are deliberately minimal.** Only `HEALTH` is declared, because only `HEALTH` is
  both implemented here and evidenced end to end. The QR-00 spike proved the *provider* supports QR
  pairing, sessions, media and history, but a provider endpoint existing is not the same as this
  adapter being able to use it, and neither is the same as a paired account working. Declaring
  `QR_AUTH`, `SESSION_*`, `TEXT`, `MEDIA*`, `HISTORY_SYNC`, `INTERACTIVE`, `REACTION`, `LOCATION` or
  `CONTACT` would let the CRM offer an action that cannot run, so all are withheld until the
  milestone that implements them.
- **Permanently prohibited:** `BULK`, `CAMPAIGNS`, `TEMPLATE` — forbidden for this provider forever
  (ADR-0020 section 5, ADR-0021, owner Class B approval), recorded in `PROHIBITED_CAPABILITIES` and
  enforced by tests no later milestone may quietly relax.
- **Server health is not session health.** `authenticate()`/`status()` return `connected=False` with
  an explicit "No WhatsApp session" detail, and `health_signal()` states it reports server health
  only. A perfectly healthy WAHA server with zero paired sessions cannot message, and the adapter
  never implies otherwise.
- **Configuration:** `WAHA_BASE_URL`/`WAHA_API_KEY` are empty by default with **no default key**;
  the application boots normally with neither set. Registration is inert — it opens no socket, needs
  no credential and starts no runtime — so the provider is resolvable but disabled. Every QR feature
  flag remains off by default.
- **Deterministic error mapping** (each shape observed against the real certified build): timeout
  and unavailable map to `ChannelTransportError` with distinct messages; 401/403 to
  `ChannelAuthError`; 5xx and other reached errors to `ChannelApiError` carrying the status;
  malformed JSON, unexpected content type (the real server answers `text/html` on the root path) and
  non-object JSON to `ChannelApiError`. Unconfigured raises `ChannelConfigError` *before* any socket
  is opened.
- **Version/engine safety:** certified baseline `2026.7.2`; only `NOWEB` approved. An unexpected
  engine **fails closed** (`WahaEngineNotApproved`) because payload shapes differ between engines.
  Version drift is *reported, never auto-corrected* — nothing upgrades a provider on its own, and
  the evidence spike pinned an immutable digest rather than a floating tag.
- **Security:** the API key is sent only as `X-Api-Key`, never logged, never echoed into an
  exception, and masked in `repr`. Provider error bodies are never quoted (they are
  attacker-influencable); the error log records status and path only. No QR material exists to
  persist. Meta behaviour and the QR-00 endpoint-scoped provider-message identity are untouched.
- **Real validation:** an isolated `devlikeapro/waha:noweb-2026.7.2`
  (digest `sha256:33ecd1b7...`) was run locally, bound to `127.0.0.1` on its own network, and the
  committed adapter/client driven against it — 11/11 checks passed covering authenticated
  version/engine, authenticated health, wrong-key and missing-config rejection, unavailable, timeout,
  non-JSON handling and the engine guard. **No session was created, no QR requested, no phone paired,
  nothing sent or received.** The provider was then torn down and all spike credentials and artefacts
  removed; the repository's committed `docker-compose.yml` was not edited.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths, RBAC, generated types, frontend. No Production Ready, Host Validated, provider-certified or
  M13-07 claim.
- **Still pending at QR-01:** QR-02 session lifecycle (since delivered), QR-03 QR endpoint/state,
  QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health, QR-07 UI, QR-08 Unified Inbox,
  QR-09 production validation, and physical-phone certification evidence (since PASSED 2026-08-08).

## QR-00 — WAHA Class B provider selection and provider-message identity foundation

- **Scope:** foundation only. QR-00 adds a provider-selection governance record, hardens
  provider-message identity/tenant isolation, and adds a provider-neutral re-authentication health
  projection. **It does not implement QR login.** No WAHA adapter, client, Docker service, provider
  runtime registration, QR API, QR image endpoint, QR persistence, QR frontend, webhook endpoint,
  inbound ingestion, outbound send, history sync, media sync, session worker or reconnect runtime
  exists. Only `meta_cloud` is a registered adapter.
- **Provider selection:** WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) is selected as the
  ADR-0021 Class B candidate and is **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED**. The
  owner's Architecture Approval, Security Approval and explicit Risk Acceptance — including
  acceptance that WhatsApp may restrict or permanently ban connected numbers — are recorded verbatim
  in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`. NOWEB was chosen because
  it is the engine the certification spike actually exercised.
- **Message identity root cause:** `MessageRepository.get_by_wamid(wamid)` resolved a provider
  message id **globally**, with no organization, connection or endpoint filter. Meta's `wamid` is
  globally unique so this was survivable with a single provider; a QR/multi-device provider's ids are
  session-scoped and may legitimately repeat across endpoints, which would have allowed a second
  provider to resolve — or a delivery receipt to advance — another endpoint's or another tenant's
  message. Contradicted ADR-0020 ("provider message identity is scoped by connection/endpoint").
- **Fix:** replaced by `get_by_provider_message_id(provider_message_id, *, phone_number_id)`. The
  endpoint scope is keyword-only and required, so an unscoped lookup cannot be written; there is
  deliberately no global variant. `phone_numbers.organization_id` is `NOT NULL`, so the endpoint
  transitively pins the tenant. All three call sites (inbound dedupe, status reconciliation, dev
  fixtures) pass an endpoint they already held; `apply_status` now takes the endpoint the callback
  arrived on.
- **No backfill was required.** `messages.organization_id` and `messages.phone_number_id` have been
  `NOT NULL` since `0016_conversations_messages`, so every existing row already carries explicit,
  authoritative endpoint ownership — nothing had to be derived or invented. Verified against the
  live database: 191 messages, 0 null owners, 0 orphaned endpoints, 0 organization mismatches, 0
  duplicate `(phone_number_id, wamid)` pairs.
- **A UNIQUE constraint is impossible, and that is recorded rather than worked around.** `messages`
  is `PARTITION BY RANGE COLUMNS(created_at)`; MySQL requires every unique key on a partitioned table
  to contain the partitioning columns (error 1503, reproduced on MySQL 8.0.46 against this schema).
  Including `created_at` would permit the very duplicate the rule exists to prevent. Uniqueness
  therefore remains enforced by the scoped read plus the persist-first ingestion path, exactly as it
  already is for Meta. Migration `0042_scope_provider_message_identity` adds only the supporting
  non-unique index `ix_msg_endpoint_wamid (phone_number_id, wamid)`.
- **Re-authentication health:** implemented as a **derived projection**, not a new persisted state.
  `app/channels/attention.py` projects the existing `ProviderHealthState` + `SessionState` +
  `PairingState` into the four Doc 33 §6.1 operator signals (Healthy / Warning / Critical /
  Re-auth Required). Adding a fourth stored health value would have duplicated information those
  columns already carry and required widening `CHECK` constraints on three columns across three
  tables. Re-auth outranks observed health; `TERMINATED` never reports re-auth.
- **Meta compatibility:** unchanged. Meta webhook ingestion, inbound dedupe, delivery/read
  reconciliation and the Inbox are all covered by the existing suites, which pass unmodified.
  OpenAPI remains 200 paths; no route, schema, RBAC entry or generated type changed.
- **Still pending, unchanged by QR-00:** QR-01 provider adapter, QR-02 session lifecycle, QR-03 QR
  endpoint/state, QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health, QR-07 UI, QR-08
  Unified Inbox integration, QR-09 production validation, and physical-phone certification evidence.
  No Production Ready, Host Validated, provider-certified or M13-07 claim is made.

## Alembic version-table MySQL fix — support long revision ids

- **Verified failure:** `alembic upgrade head` on a real MySQL 8 database (the repository's own
  `docker compose up -d` MySQL/Redis, per `README.md`) failed transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Root cause: Alembic's own bookkeeping table
  (`alembic_version.version_num`) defaults to `VARCHAR(32)`; this repository's revision identifiers
  are descriptive slugs, not short hashes, and `0036_customer_identity_resolution` (33 characters)
  is the first to exceed it. No real MySQL deployment had ever advanced past `0035_notification_center`.
- **Repair:** inserted `0035a_widen_version_table`, a new revision between `0035_notification_center`
  and `0036_customer_identity_resolution`, widening `alembic_version.version_num` to `VARCHAR(255)`
  on MySQL only (SQLite has no such enforcement; PostgreSQL is not part of this stack).
  `0036_customer_identity_resolution`'s `down_revision` was retargeted to point at it — its own
  revision id, schema body and behaviour are byte-for-byte unchanged. No revision was renamed,
  renumbered, squashed, reordered, or stamped past. The migration head remains
  `0041_channel_sync_control_plane`; the chain remains linear with a single head (42 revisions, was 41).
- **Verified on real MySQL 8** (`docker compose up -d`, throwaway per-test databases): a fresh
  database walks base→head cleanly; a database stamped at `0035_notification_center` (the exact
  historical failure point) upgrades to head cleanly; `python -m app.cli create-owner` succeeds
  immediately afterward. Also reproduced manually via the documented CLI workflow against a fresh
  `docker compose` MySQL instance (not just the automated tests) — identical result.
- **Regression coverage:** `backend/tests/test_migrations.py` gained three hermetic (SQLite)
  checks — single head, linear chain (no merges), and every revision id fits the widened column,
  with a tighter early-warning margin. `backend/tests/test_migrations_mysql.py` is new: three tests
  against a real, throwaway-per-test MySQL 8 database (fresh base→head, `0035`→head, create-owner
  after upgrade), skipped cleanly — never failed — when no MySQL server is reachable, so the
  hermetic default suite gains no new external dependency.
- **Preserved:** no application endpoint, model, schema, RBAC definition, OpenAPI path or generated
  frontend type changed; `scripts/export_openapi.py --check` and the full static quality gate both
  pass unchanged. Frontend untouched.
- **Remaining blocker, unchanged by this fix:** a real, populated `/chat-history` UI preview is
  still blocked — now solely by the separate, pre-existing absence of any approved development
  fixture mechanism for conversation/message data (creating real conversations requires either live
  Meta WhatsApp Business API credentials this environment does not have, or fabricating data
  outside approved commands, which remains out of scope). This migration fix removes the schema/
  auth blocker only; it does not by itself unblock the UI preview. No Host Validated or Production
  Ready claim is made.
- **Evidence scope correction (this follow-up):** the MySQL migration evidence above is
  repository/local-host evidence (a local `docker compose` MySQL 8 container), not genuine
  target-host validation; the "Host evidence" row previously overstated this as "target-host"
  verified, which has been corrected. Independently of this fix, a real-MySQL downgrade defect
  was found at `0036_customer_identity_resolution` and `0040_channel_sync_media_foundation`
  (`DROP INDEX ... needed in a foreign key constraint`) — pre-existing, not introduced by this
  commit, and recorded as a separate open defect; its remediation is not part of this follow-up.
  Automated CI execution of the live-MySQL migration tests also remains pending — no CI pipeline
  exists in this repository, so `test_migrations_mysql.py` currently only runs when a developer
  manually starts MySQL first.

## Dedicated Chat History read workspace over the existing conversation and message contract

- Added a `/chat-history` route (`inbox:read`) and matching navigation entry — a read-only
  list/detail workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read, reusing
  `useConversations`/`useConversation`/`useMessages`/`useAssignableUsers` from
  `features/inbox/api.ts` verbatim rather than opening a second query authority.
- Supports search, status, assignee, tag and a new `number` (channel) filter — the `number` field
  is an additive entry on the shared `InboxFilters`/`toListQuery` types Live Chat's own filters
  also use, so both surfaces read it from one definition. Cursor pagination for the conversation
  list and the existing infinite-query "Load older messages" control are both reused as-is.
- No assignment, status, tag, note or send control is exposed; a deep link opens the selected
  conversation in Live Chat, and a second deep link to the audit trail is shown only to
  `audit:read` holders.
- Date-range filtering and transcript export are honestly disclosed in the UI as not yet
  available, rather than offered as disabled controls — neither is backed by the current contract.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed. Closes the frontend half of `ROADMAP.md`'s `CORE-10`; its
  backend "Conversation query extensions" and export capability remain open follow-up.

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

Written at M13-06B closeout. Provider certification PASSED on 2026-08-08 and the owner authorized the QR sequence, so certification no longer blocks the adapter and ingestion paths: QR-01 (adapter), QR-02 (session lifecycle), QR-03 (pairing) and QR-04 (webhook ingestion) are delivered. Still gated on a separate owner instruction each: QR-05 messaging/send, QR-06 reconnect/teardown, QR-07 provider UI, QR-08 Unified Inbox, QR-09 production validation. History retrieval and media-byte transfer remain unimplemented; no Production Ready or Host Validated claim is made.
