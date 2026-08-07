# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-07 · QR-01 WAHA provider adapter foundation, on top of the QR-00 provider selection and provider-message identity foundation, the MySQL migration evidence hardening, the Alembic version-table MySQL fix (long revision ids), the Chat History pagination/polling/accessibility hardening, the Dedicated Chat History workspace, the User Attributes remediation, its test-hardening follow-up and M13-06B. Provider certification still blocks every live history, media, event and adapter behavior._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `1d109b984b165f166e8575e5fd4fa3648ce903dc` (`feat(channels): establish QR provider foundation`)
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0042_scope_provider_message_identity` (43 revisions, unchanged) · 200 paths — QR-01 and QR-02 add no migration, no route, no RBAC entry and no generated type
- **Current milestone:** `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED`
- **Latest change:** QR-05 — WAHA send path and delivery-state reconciliation: outbound text through the configured session, canonical provider-id capture, acknowledgement translation onto the platform's **existing** monotonic `messages.status` vocabulary, and an endpoint-scoped reconcile-before-resend primitive. Declares `TEXT`. **No blind retry, no teardown/reconnect, no media/history, no interactive/reaction/location/contact, no route, table or migration, and no UI.**
- **Previous change:** QR-04 — WAHA webhook ingestion: raw-body sha512 HMAC verification and provider event normalization onto the **existing** `ChannelAdapter` webhook seam and `webhook_events` ingest authority. Dedupe identity is scoped by session **and** event type because certification proved `envelope.id` alone is not unique. Declares `SESSION_STREAM`. **No new route, table or migration; no send path, no delivery-state persistence, no teardown, no history/media execution and no UI.**
- **Previous change:** QR-03 — WAHA QR pairing: create a session with the certified store configuration, fetch the transient QR challenge, and report provider-neutral pairing state. First declared capability since QR-01 (`QR_AUTH`). **QR-03 can bring a session up and cannot take one down — no stop/restart/logout/delete, no webhook ingestion, no send path, no media/history transfer, no session runtime, no public route and no UI.**
- **Completion:** Shared Enterprise Design System `94%` · Global Search `85%` · Reactivation `94%` · Module 13 `48%` · Chat History `55%` — all unchanged. QR-01 is adapter foundation only and raises no completion percentage; WhatsApp Scan/QR login remains unimplemented and non-functional.
- **Backend evidence:** Ruff PASS · strict mypy PASS (292 files) · 1099 full pytest tests PASS (1036 before QR-01; +63 WAHA adapter tests) · previously 999 (985 before the `0035a_widen_version_table` remediation, 991 after it; +8 in this evidence-hardening follow-up: `test_migrations_mysql.py` grew from 3 to 11 tests — the original 3 gained real `information_schema` `VARCHAR(255)`/idempotent-create-owner assertions in place, plus 8 new tests for the reachable/unreachable/misconfigured MySQL classification, 6 of which are hermetic and always run)
- **Frontend evidence:** unchanged by this follow-up (no frontend file touched); static quality gate frontend steps still pass
- **Provider selection:** WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0), ADR-0021 Class B. Approvals recorded in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`. The physical-phone evidence that record required was produced on 2026-08-08 and PASSED; the record itself still reads **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED** and needs an **owner decision** to advance, which QR-02 does not make on its own authority. QR-01 registers a `waha` adapter limited to an authenticated server probe; QR-02 adds a read-only session lifecycle mapping; `ProviderRuntimeRegistry` still has no WAHA runtime.
- **Physical-phone certification:** **PASSED** (2026-08-08) against the pinned certified build. Real QR pairing to `WORKING`, controlled-restart reconnect with no new QR, external outbound with `SERVER`/`DEVICE`/`READ` acknowledgement, external inbound text, external inbound JPEG with verified download, HMAC-verified webhook delivery, history/fullSync correlation, and logout with re-auth required. This unblocked QR-02.
- **Next milestone:** `QR-06 — reconnect/health/teardown`. Not started.
- **Last synchronized:** `2026-08-08T00:00:00+05:30`

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
  immediately afterward, including its documented idempotent re-run behaviour. This is
  repository/local-host evidence (a local `docker compose` MySQL 8 container) — not genuine
  target-host validation, which remains pending.
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
- **Known open defect, pre-existing and unrelated to this fix:** downgrading past
  `0036_customer_identity_resolution` or `0040_channel_sync_media_foundation` fails on real MySQL 8
  with `DROP INDEX ... needed in a foreign key constraint`; reproduced identically against the
  pre-fix migration graph, confirming it is not caused by `0035a_widen_version_table`. Hermetic
  (SQLite) downgrade coverage for these revisions passes and remains valid for what it tests, but
  does not prove MySQL rollback safety. Remediation is out of scope for this fix.
- **Known gap, pre-existing:** no CI pipeline exists in this repository, and the local quality gate
  does not provision MySQL before running tests, so `test_migrations_mysql.py` has no automated
  execution path today — it runs only when a developer manually starts MySQL first.

### QR-05 — WAHA send path and delivery-state reconciliation

- **Delivered:** `app/channels/waha/delivery.py` (ack vocabulary, `map_ack()`, `to_status_update()`,
  `extract_sent_id()`, `WahaSendIndeterminate`), client `send_text()`/`message_exists()`, adapter
  `_dispatch()`/`to_status_update()`/`reconcile_send()`, and `WahaCredentials.session` +
  `WAHA_SESSION_NAME`. Declares `TEXT`.
- **Monotonicity carry-forward closed:** the QR-05 acknowledgement-ordering constraint is satisfied
  by *reusing* `STATUS_RANK`/`advances()` rather than adding a second ordering. The certified
  out-of-order `DEVICE(2) → SERVER(1) → READ(3)` is proven to end at `read`, and every permutation
  of an interleaved ack sequence converges. Duplicate acks are idempotent; `failed` is terminal.
- **Ambiguous-send safety:** a transport failure is `WahaSendIndeterminate` — explicitly not a
  `ChannelTransportError`, so generic retry cannot sweep it up. Reconcile first; resend only on
  proven absence; a failed lookup stays indeterminate. No resend path exists.
- **Endpoint scoping is structural:** sends and lookups both go through `require_session()`, and the
  reconcile query runs inside that session's own chat. No global provider-message lookup.
- **QR-04 review:** the 128-character `event_identity` truncation was re-inspected. No collision
  defect was found — the envelope id is placed last so the discriminating component survives — so
  QR-04 was left unchanged.
- **Tests:** 46 new hermetic tests (`tests/test_channel_waha_delivery.py`); 241 across all five WAHA
  suites. Full suite 1277 passed (1232 before QR-05).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-04 — WAHA webhook ingestion

- **Delivered:** `app/channels/waha/webhook.py` (raw-body sha512 HMAC verification,
  `event_identity()`, `canonical_message_id()`, event normalization) plus the adapter's
  implementation of the existing `verify_webhook_signature`/`parse_webhook`/`to_inbound_message`
  seam. Configuration `WAHA_WEBHOOK_HMAC_SECRET` (empty default). Declares `SESSION_STREAM`.
- **No parallel ingest path:** events flow into the existing `WebhookService` → `webhook_events`
  authority, which already owns persist-first durability, dedupe and dead-lettering. No new route,
  table or migration.
- **Dedupe identity resolved:** the QR-04 carry-forward is closed. `envelope.id` alone is unsafe —
  one provider message arrives as both `message` and `message.any` sharing it — so the key is
  scoped by session and event type. Determinism proven by a 64-way concurrent test, because
  `messages` is partitioned and MySQL cannot enforce that uniqueness (error 1503).
- **Security:** verify before parse, over raw bytes, constant-time, 1 MiB bound enforced before
  hashing, unset secret rejects everything, no default secret, unknown/malformed shapes fail closed
  to `UNKNOWN` with no `event_id`.
- **Not pulled forward:** acknowledgements and outbound echoes are recorded as `UNKNOWN`, never
  applied — delivery state is QR-05. No teardown, history or media execution.
- **Tests:** 52 new hermetic tests (`tests/test_channel_waha_webhook.py`); 196 across all four WAHA
  suites. Full suite 1232 passed (1181 before QR-04).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-03 — WAHA QR pairing

- **Delivered:** `app/channels/waha/pairing.py` (`CERTIFIED_NOWEB_STORE`, `build_session_config()`,
  transient `WahaQrChallenge`), two client calls (`create_session`, `qr_challenge`) and three
  adapter methods (`begin_pairing`, `pairing_challenge`, `pairing_state`). `QR_AUTH` is declared —
  the first capability added since QR-01.
- **Up, never down:** no stop, restart, logout or delete exists on adapter or client, asserted by
  test. Teardown is QR-06, so nothing shipped so far can destroy a working pairing.
- **Silent-failure trap closed:** `fullSync` is camelCase and built in one place. Certification
  proved `full_sync` returns HTTP 201 and then silently stores `fullSync: false`, leaving a session
  that looks healthy with no history.
- **QR is a secret:** never persisted, never logged, excluded from `repr`. M13-05's boundary that
  QR images and challenge bytes are never stored is preserved rather than widened.
- **Pairing safety:** `pairing_state()` returns `None` on `STARTING`/`STOPPED`/`FAILED`; durable
  pairing truth is never overwritten from an ambiguous provider status.
- **Boundary tests re-pointed, not removed:** two guards moved with the milestone (see the QR-03
  changelog entry). `send_text` was dropped from a forbidden-name list because it is an inherited
  generic `ChannelAdapter` method whose presence proves nothing; the send path is now asserted
  behaviourally to still raise `ChannelNotSupported`.
- **Tests:** 30 new hermetic tests (`tests/test_channel_waha_pairing.py`). Full suite 1181 passed
  (1153 before QR-03).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-02 — WAHA session lifecycle read and provider-neutral mapping

- **Delivered:** `app/channels/waha/lifecycle.py` — `WahaSessionStatus` (the five statuses observed
  during physical-phone certification: `STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`),
  a pure `map_session_status()` onto `SessionState`/`PairingState`, `WahaSessionSnapshot`, and
  strict session-name validation. One authenticated client read (`GET /api/sessions/{name}`) and two
  adapter methods (`session_snapshot`, `session_status`).
- **Read-only:** no session is created, started, stopped, restarted, paired or logged out. Adapter
  and client are asserted to expose no such method. Driving a lifecycle is QR-03/QR-06.
- **Capability-neutral:** capabilities remain exactly `HEALTH`; `PROHIBITED_CAPABILITIES` untouched.
- **Honest ambiguity:** `STARTING`/`STOPPED`/`FAILED` return no pairing state, because certification
  observed `STARTING` on both a fresh session and a controlled restart of a paired one. `FAILED`
  maps to `degraded`, not a terminal state, because certification recovered it with a restart.
- **Carry-forward respected:** QR-02 introduces no delivery-state persistence and no event dedupe,
  so the out-of-order acknowledgement finding (`DEVICE(2) → SERVER(1) → READ(3)`) and the shared
  `envelope.id` finding constrain QR-04/QR-05, not this milestone. The mapping is pure and
  order-independent by construction.
- **Tests:** 54 new hermetic tests (`tests/test_channel_waha_lifecycle.py`). Full suite 1153 passed
  (1099 before QR-02).
- **Unchanged:** migration head, OpenAPI (200 paths), RBAC, generated types, frontend, Meta
  behaviour, and the absence of a WAHA entry in `ProviderRuntimeRegistry`.

### QR-01 — WAHA provider adapter foundation

- **Delivered:** connector identity `waha` on channel family `whatsapp`; a minimal typed async
  client (`app/channels/waha/client.py`) implementing exactly two authenticated reads — the server
  version/engine banner and `/health`; the adapter (`app/channels/waha/adapter.py`) behind the
  existing `ChannelAdapter` seam; inert static registration; and disabled-by-default configuration.
- **Capabilities:** only `HEALTH`. Withheld deliberately: `QR_AUTH`, `SESSION_STREAM`,
  `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`, `TEXT`, `MEDIA`, `MEDIA_UPLOAD`,
  `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION`, `CONTACT` — each either unimplemented
  here, unproven without a paired handset, or both. A provider endpoint existing is not evidence
  that this adapter can use it.
- **Permanently prohibited:** `BULK`, `CAMPAIGNS`, `TEMPLATE` (ADR-0020 section 5, ADR-0021, owner
  Class B approval). Recorded in `PROHIBITED_CAPABILITIES` and enforced by tests asserting they are
  never declared and that the capability gate refuses template/text sends.
- **Server health is not session health:** `authenticate()`/`status()` report `connected=False` with
  an explicit "No WhatsApp session" detail; `health_signal()` labels itself server-health-only.
- **Error mapping:** timeout and unavailable to `ChannelTransportError` (distinct messages);
  401/403 to `ChannelAuthError`; 5xx and other reached errors to `ChannelApiError` with status;
  malformed JSON, unexpected content type and non-object JSON to `ChannelApiError`; unconfigured to
  `ChannelConfigError` before any socket opens.
- **Version/engine safety:** baseline `2026.7.2`, `NOWEB` only. Unexpected engine fails closed;
  drift is reported and never auto-corrected; the spike pinned an immutable digest, not a floating
  tag.
- **Security:** API key sent only as `X-Api-Key`, never logged, never in an exception message,
  masked in `repr`; provider error bodies never echoed; error log carries status and path only.
- **Real validation:** isolated `devlikeapro/waha:noweb-2026.7.2` run locally on `127.0.0.1`; the
  committed adapter driven against it, 11/11 checks. No session created, no QR requested, no phone
  paired, nothing sent or received. Torn down and credentials removed; the committed
  `docker-compose.yml` was not edited.
- **Unchanged:** migration head, OpenAPI (200 paths), RBAC, generated types, frontend, Meta
  behaviour, and the QR-00 endpoint-scoped provider-message identity.

### QR-00 — WAHA Class B provider selection and provider-message identity foundation

- **Provider selection:** WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) recorded as the
  ADR-0021 Class B candidate in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`,
  the Design Document 33 §6.4 selection record. It succeeds — and does not rewrite — the earlier
  `waha-class-b-evaluation.md`, closing its E-005/E-006/E-010/E-011(partial)/E-015 items. Owner
  Approval, Architecture Approval, Security Approval and explicit acceptance of WhatsApp
  restriction/ban risk are recorded verbatim. Certification remains **CONDITIONALLY CERTIFIED —
  HOST/PHONE EVIDENCE REQUIRED**; production certification is **not** granted.
- **Message identity root cause:** `MessageRepository.get_by_wamid(wamid)` resolved a provider
  message id globally — no organization, connection or endpoint filter. Safe only while Meta (whose
  `wamid` is globally unique) was the sole provider; a QR provider's session-scoped ids may
  legitimately repeat across endpoints, which would let one endpoint resolve, or a delivery receipt
  advance, another endpoint's or another tenant's message. Contradicted ADR-0020.
- **Fix:** `get_by_provider_message_id(provider_message_id, *, phone_number_id)` — endpoint-scoped,
  with the scope keyword-only and required so an unscoped lookup cannot be written. No global
  variant exists. `phone_numbers.organization_id` is `NOT NULL`, so the endpoint transitively pins
  the tenant. All three call sites updated; `apply_status` now receives the endpoint the callback
  arrived on (already available and null-checked in `webhook_service`).
- **No backfill required and none performed.** `messages.organization_id`/`phone_number_id` have
  been `NOT NULL` since `0016_conversations_messages`; ownership is already explicit, not derived.
  Verified on the live database: 191 rows, 0 null owners, 0 orphaned endpoints, 0 org mismatches,
  0 duplicate `(phone_number_id, wamid)` pairs.
- **UNIQUE constraint proven impossible.** `messages` is `PARTITION BY RANGE COLUMNS(created_at)`;
  MySQL error 1503 requires unique keys on partitioned tables to contain the partition columns
  (reproduced on MySQL 8.0.46 against this schema). Adding `created_at` would permit the duplicate
  the rule exists to prevent. Uniqueness stays enforced by the scoped read plus persist-first
  ingestion, as it already is for Meta. Migration `0042_scope_provider_message_identity` adds only
  the supporting non-unique index `ix_msg_endpoint_wamid (phone_number_id, wamid)`.
- **Re-authentication health:** derived projection (`app/channels/attention.py`), not a new stored
  state — Option B. Projects `ProviderHealthState` + `SessionState` + `PairingState` into the four
  Doc 33 §6.1 signals (Healthy/Warning/Critical/Re-auth Required). Avoids duplicating state the
  session columns already carry and avoids widening `CHECK` constraints on three columns. Re-auth
  outranks observed health; `TERMINATED` never reports re-auth. No provider-specific value.
- **Tests:** 21 new in `tests/test_provider_message_identity.py` — same provider id on two
  endpoints resolves separately, endpoints cannot read each other's messages, organizations cannot
  read each other's messages, the scope cannot be omitted, plus total coverage of the projection
  across every state combination. Migration head pins updated in `test_migrations.py` and
  `test_migrations_mysql.py`.
- **Meta compatibility unchanged:** webhook ingestion, inbound dedupe, delivery/read reconciliation
  and Inbox suites pass unmodified. OpenAPI remains 200 paths; no route, schema, RBAC entry or
  generated type changed.
- **Explicitly not implemented by QR-00:** WAHA client/adapter/Docker service, provider runtime
  registration, QR API, QR image endpoint, QR persistence, QR frontend, webhook endpoint, inbound
  ingestion, outbound send, history sync, media sync, session worker, reconnect runtime, Unified
  Inbox QR integration, M13-07. QR login does not work and is not claimed to.

### MySQL migration evidence hardening (independent audit follow-up)

- **Governance correction:** the "Host evidence" row in `PROJECT_STATE.md` previously read
  "Target-host MySQL migration is now verified" — an overclaim, since the evidence was a local
  `docker compose` MySQL 8 container, not the project's target deployment host (the term
  "target-host" is used elsewhere in this repository specifically for that distinction). Reworded
  to state plainly that this is repository/local-host evidence and that genuine target-host
  evidence remains pending. No valid evidence was removed. `IMPLEMENTATION_TRACKER.md`'s own
  "Remaining work" list already correctly listed target-host evidence as pending — that
  inconsistency between the two files is now resolved.
- **Governance correction:** historical `VALIDATION_RESULTS.md` rows recording SQLite-hermetic
  downgrade passes for `0036_customer_identity_resolution` and `0040_channel_sync_media_foundation`
  are annotated to state plainly that they are hermetic/SQLite-only and do not prove MySQL rollback
  safety, cross-referencing the verified open real-MySQL downgrade defect recorded above. The
  historical PASS rows themselves, and the migration code they describe, are unchanged.
- **Test hardening:** `test_migrations_mysql.py`'s three live-MySQL tests now assert directly
  against `information_schema.COLUMNS` that `alembic_version.version_num` is genuinely
  `varchar(32)` before the repair and `varchar(255)` after it (both for a fresh base→head run and
  for the historical 0035→head transition) — real database inspection, not migration source text.
  `create-owner` is now exercised twice in one test: the first call creates the owner, the second
  is asserted idempotent (`owner_created`/`organization_created` both `False` on rerun), and a raw
  `SELECT COUNT(*) FROM users WHERE email = ...` confirms exactly one row exists after both calls —
  independent of what the returned dataclass claims.
- **Skip-logic hardening:** MySQL reachability is now classified into three states instead of two.
  A connection failure whose MySQL/pymysql error code indicates nobody answered (connection
  refused, timed out, unknown host) is `MySQLUnavailable` and skips cleanly, exactly as before —
  ordinary developers without Docker running still get a clean hermetic run. Any other failure
  (most commonly MySQL error 1045, "Access denied") means a real server answered and rejected the
  configured credentials; this is now `MySQLMisconfigured` and fails the live-MySQL tests loudly
  with a message naming the `DB_HOST`/`DB_PORT`/`MYSQL_ROOT_PASSWORD` environment variables to
  check — never the credential value itself, which pymysql's own error text already omits. Six new
  tests cover the classification logic hermetically (no network access), plus two new tests
  confirm the "reachable and correctly configured" and "reachable but rejects a wrong password"
  states against the real local MySQL 8 server when one is available.
- **Preserved, not modified:** `0035a_widen_version_table`, `0036_customer_identity_resolution`,
  and `0040_channel_sync_media_foundation` migration files are byte-for-byte unchanged; migration
  head remains `0041_channel_sync_control_plane`, revision count remains 42; no application
  endpoint, model, schema, RBAC definition, OpenAPI path, or frontend file changed;
  `scripts/export_openapi.py --check` and the full static quality gate both pass unchanged. No CI
  system was added — the real-MySQL downgrade defect at 0036/0040 and the absence of automated CI
  execution for `test_migrations_mysql.py` both remain open, explicitly recorded, and out of scope
  for this follow-up.

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

- QR-04 webhook ingestion, QR-05 send path, QR-06 reconnect/health, QR-07 QR frontend, QR-08
  Unified Inbox integration, QR-09 production validation — none started. QR-01 delivered an adapter
  that can probe the WAHA *server*; QR-02 added a read-only session lifecycle mapping; QR-03 added
  QR pairing. Nothing can yet ingest events, send, tear a session down or supervise one, and there
  is still no QR route or UI (QR-07).
- **QR-05 carry-forward (acknowledgement ordering):** physical-phone certification observed
  acknowledgements arriving `DEVICE(2) → SERVER(1) → READ(3)`. Any delivery-state persistence must
  advance monotonically (take the highest state reached); last-write-wins would regress a delivered
  message back to "sent".
- **QR-04 carry-forward (event identity):** the same underlying provider message was delivered as
  both `message` and `message.any` sharing one `envelope.id`. Deduplication keyed on `envelope.id`
  alone would silently drop a genuine event; the key must include the event type. Webhook delivery
  is at-least-once and redelivery repeats both `envelope.id` and `X-Webhook-Request-Id`, so neither
  distinguishes a retry from a first delivery.
- **QR-04 carry-forward (concurrency):** `messages` is partitioned, so DB-level endpoint/provider
  message-id uniqueness cannot be enforced by constraint (MySQL error 1503). Concurrent
  duplicate-event safety must therefore be proven independently — by test, not by schema — before
  QR-04 turns on live webhook ingestion. Partitioning is deliberately not redesigned.
- Physical-phone WAHA certification evidence (paired session reaching `WORKING`, real inbound,
  outbound send, delivery/read acknowledgement, media, history) — the four Required criteria that
  remain PENDING in the selection record.
- Genuine target-host MySQL migration evidence (repository/local-host `docker compose` evidence
  exists for upgrade paths — see `0035a_widen_version_table` remediation — but target-host itself
  remains unvalidated).
- Real-MySQL rollback/downgrade fix at `0036_customer_identity_resolution` and
  `0040_channel_sync_media_foundation` — a verified open defect (`DROP INDEX ... needed in a
  foreign key constraint`), pre-existing and confirmed unrelated to the `0035a` remediation;
  remediation is not part of that fix or this follow-up.
- Automated CI execution of the live-MySQL migration tests (`test_migrations_mysql.py`) — no CI
  pipeline exists in this repository today.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider certification host evidence and all live M13-06 inbound/history/media execution plus later messaging/operator milestones.

## Stop rule

This rule was written at M13-06B closeout. Its release conditions — "certification **and** a separate
owner instruction" — have both since been met, so it no longer blocks the QR sequence:

- **Certification:** physical-phone WAHA certification PASSED on 2026-08-08.
- **Owner instruction:** the owner authorized QR-01 through QR-04 individually, and QR-01, QR-02,
  QR-03 and QR-04 were delivered under that authorization.

Still gated, and each requiring its own owner instruction: QR-05 send, QR-06 reconnect/health/
teardown, QR-07 provider UI, QR-08 Unified Inbox, QR-09 production validation. Provider history
retrieval and media-byte transfer remain unimplemented. No Production Ready or Host Validated claim
is made, and the WAHA selection record's approval state is unchanged and remains an owner decision.
