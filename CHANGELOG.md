# Changelog

All notable changes to **frozen** design documents and (later) released modules are recorded
here. Frozen documents are not edited silently; any change to a frozen document must be
logged as an entry below, with date, document, rationale, and the nature of the change.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
will adopt semantic-ish versioning per document (e.g., `SRS v1.1`) once changes occur.

---

## [Unreleased]

### 2026-08-08 — QR-09: Production Validation — PARTIAL (BLOCKED, evidence-only)

**No product code, migration, OpenAPI, dependency, or capability change.** This entry records a
validation attempt only. Migration head remains `0043_conversation_channel_endpoints` (44
revisions); OpenAPI remains 207 paths; WAHA capabilities remain unchanged
(`HEALTH`/`QR_AUTH`/`SESSION_STREAM`/`TEXT`/`SESSION_RECONNECT`/`SESSION_LOGOUT`;
`BULK`/`CAMPAIGNS`/`TEMPLATE` still permanently prohibited).

**Environment.** Real MySQL `8.0.46` and Redis `7.4.9` (this repository's own
`docker compose up -d`), and the real pinned WAHA container
(`devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`,
2026.7.2 / NOWEB / CORE — the exact certified digest). No physical handset was available, so QR
scan-to-`WORKING`, real external inbound/outbound, ACK-chain reconciliation, reconnect-without-a-
new-QR, and logout/re-auth were **not** exercised.

**Closed a QR-08 preview limitation.** QR-08's own preview evidence was blocked by the absence of
Redis in that throwaway environment (`503 idempotency_unavailable`). Against real Redis, the full
contract holds: a normal send succeeds; a duplicate `Idempotency-Key` replays the original response
and writes no second row; 6 concurrent requests sharing one key produce exactly one message; a
Redis outage fails closed (`503`); a Redis restart recovers.

**Decisive dual-provider proof on real MySQL.** Delivering one underlying provider message as
`message` **and** `message.any`, each retried once (4 deliveries total), produced 4
`webhook_events` rows (event-layer persistence is intentionally at-least-once) but **exactly one**
stored `messages` row (`apply_inbound` outcomes: `applied`, then three `duplicate`) — proving
QR-08's endpoint-scoped stored-message dedupe end to end against real MySQL, not just SQLite.

**Two Major defects found, reproduced, and left unfixed (per validation defect policy — this
milestone stops on discovery, it does not silently remediate).**

- **QR-09-D1.** `0043_conversation_channel_endpoints`'s `downgrade()` fails on real MySQL 8:
  `(1553, "Cannot drop index 'uq_conv_endpoint_contact': needed in a foreign key constraint")`.
  `uq_conv_endpoint_contact` (leading column `channel_endpoint_id`) backs
  `fk_conv_channel_endpoint`; the downgrade drops the index before the foreign key. Because MySQL
  DDL is non-transactional, the failed attempt left `messages`/`webhook_events` columns already
  dropped while `alembic_version` still read `0043` — a schema matching neither revision. Same
  defect class as the already-tracked `0036`/`0040` real-MySQL downgrade defect. The upgrade path
  (`0042` → `0043`) is unaffected: verified to preserve seeded Meta rows byte-for-byte and to
  correctly enforce the exactly-one-owner `CHECK` at the database level.
- **QR-09-D2.** `GET /channels/whatsapp-qr/session` returns `HTTP 500` whenever the real provider
  is reachable but the named session no longer exists there (reproduced deterministically after a
  WAHA container restart with no persistent session volume — 30/30 calls during the performance
  run). Root cause: the provider's `404 Session not found` becomes `ChannelApiError`, which
  `WhatsAppQrService._reconcile()` only catches as `ChannelTransportError` and
  `get_status()` only suppresses as `ConflictError` — neither matches, so it propagates. A genuine
  provider outage (container stopped) is handled correctly today
  (`reconnect_blocked_reason: "provider_unavailable"`, `requires_reauthentication: false`); this
  specific state — provider up, session gone — is not.
- **QR-09-D3 (Minor).** An oversized WAHA webhook body is correctly refused before hashing
  (`WahaBodyTooLarge`, the 1 MiB bound holds) but surfaces as `HTTP 500` rather than a 4xx, because
  the exception has no HTTP mapping — inviting the provider's at-least-once retry rather than
  stopping it.

**A required repository gate genuinely fails.** `scripts/quality_gate.py`'s OpenAPI drift check
(`scripts/export_openapi.py --check`) reports `openapi.json` stale. Investigated rather than
dismissed: generation is deterministic (identical SHA-256 across processes); the committed file and
a fresh generation parse to **exactly equal** objects with **207 paths both**; re-encoding the
committed file with `ensure_ascii=False` (the exporter's own setting) produces a **byte-exact**
match to the fresh generation. Key order and content are identical — the only difference is JSON
ASCII-escaping (the committed artifact was written with `ensure_ascii=True` at some point in its
history). This **corrects** the explanation recorded elsewhere in this repository attributing
OpenAPI generation non-determinism to "a pre-existing JSON key-order mismatch under the unpinned
FastAPI/Pydantic resolver" — that explanation does not hold for this artifact; the true cause is a
one-time ASCII-escaping setting difference, not resolver non-determinism. The gate is real and
required, and it is red; QR-09 cannot close while it is.

**Real-infrastructure gate results.** Backend full suite **1385 passed, 0 skipped** (was 1380 passed
+ 5 skipped without MySQL) — the 5 previously-always-skipped live-MySQL tests now genuinely ran.
11/11 live-MySQL tests pass. Frontend 38 files / 793 tests, ESLint, TypeScript, and production build
all pass. Ruff and strict mypy (300 files) pass. Bandit: 0 High, 0 Medium, 28 Low (the documented
pre-existing `assert`-usage class, none new). `pip-audit`: one production advisory,
`cryptography 49.0.0` → `PYSEC-2026-3552`, fixed in `50.0.0` — **not upgraded** in this milestone.
`npm audit --omit=dev`: 2 moderate (a `react-router` SSR-hydration advisory; this is a
client-rendered SPA, not SSR). Latency measured against this repository's own documented budgets
(Doc 01 §5.1 `NFR-PERF-01` p95 < 300 ms reads; Doc 06 webhook ack < 200 ms) on a single developer
workstation: mixed-Inbox list p95 12.8 ms, thread load p95 5.2 ms, WAHA thread load p95 4.7 ms,
webhook ingest ACK p95 10.4 ms — all within budget, but **not** target-host, concurrency, soak, or
1M-contact-scale evidence.

**Infrastructure gap found.** No WAHA service, image pin, or persistent session volume is defined
in `docker-compose.yml`, `docker-compose.production.yml`, or `deploy/DEPLOYMENT.md` — the absence
that made QR-09-D2 reachable outside a lab environment is a genuine deployment gap, not only a
validation-harness artifact.

**Preserved, unchanged by this milestone.** QR-01 through QR-08 remain exactly as delivered; QR-08
remains `COMPLETE`. The WAHA selection record
(`docs/evidence/provider-evaluations/waha-class-b-selection-record.md`) and its
`CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED` status are untouched. No capability was
added, expanded, or removed. No migration, route, RBAC entry, or dependency was changed.

**Classification.** `Repository Validated: NO` (a required gate is red and two Major defects are
open) · `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`. Recommended next
milestone (not started): `QR-09A — Production Validation Remediation` — fix D1 (reorder the FK-then
-index drop in `downgrade()`, add a real-MySQL down/up regression test), fix D2 (translate a
provider-up/session-absent `ChannelApiError`/404 into a truthful recoverable status, add a
regression), fix D3 (map `WahaBodyTooLarge` to a 4xx), regenerate `openapi.json` with consistent
ASCII-escaping and correct the stale explanation elsewhere in governance, add a WAHA service
definition with persistent session storage to compose/deployment/runbook, triage the `cryptography`
advisory, rerun QR-09, then pursue physical-phone/host-browser evidence.

### 2026-08-08 — QR-08: Unified Inbox integration

**Added**
- `backend/alembic/versions/0043_conversation_channel_endpoints.py` — additive expand-stage
  migration: `conversations` gains a nullable, real-FK `channel_endpoint_id` and its
  `phone_number_id` widens to nullable, guarded by a new `ck_conv_endpoint_owner` check (exactly
  one of the two set); `messages`/`webhook_events` (both partitioned on MySQL) gain the same
  nullable, app-enforced `channel_endpoint_id` alongside their existing `phone_number_id`. No
  column dropped, renamed, or narrowed; every existing row's `phone_number_id` is untouched.
- `POST /webhooks/waha` — the WAHA analogue of the existing `/webhooks/whatsapp` route. QR-04
  (2026) built the HMAC verification and event parsing but never wired an HTTP route to it; this
  is that route, unchanged in shape from Meta's (public, signature-gated, persist-then-ack).
- `SendService.accept_for_conversation` / `.accept_endpoint` / `._deliver_endpoint` — the WAHA
  outbound path. Text-only; no window check (WAHA carries no Meta customer-service-window rule);
  refuses to send when the underlying session is not `ACTIVE`+`PAIRED`
  (`ChannelNotConnectedError`); a send whose outcome cannot be confirmed is marked
  `failed`/`error_code=indeterminate` and is never retried automatically.
- `MessageService._apply_inbound_endpoint` / `WebhookService` endpoint routing /
  `ConversationService.thread_for_endpoint` / `.open_for_inbound_endpoint` — the WAHA inbound
  path, mirroring the existing Meta path method-for-method rather than branching inside it
  (ADR-0020 "independent failure domains").
- `MessageRepository.get_by_provider_message_id_for_endpoint` /
  `ConversationRepository.get_for_endpoint_contact` /
  `WebhookEventRepository.resolve_endpoints` — the endpoint-scoped analogues of the existing
  phone-number-scoped lookups (ADR-0020, QR-00's provider-message-identity scoping), keyword-only
  and required, with no unscoped variant.
- `MessageSendRequest.conversation_id` (optional) — a reply to an existing thread. The provider is
  resolved entirely server-side from the conversation's own durable ownership; the request carries
  no provider/endpoint field for a caller to set. `phone_number_id`+`to` remain for the original
  "send to any number" contract, unchanged.
- `ConversationResponse.connector_type` — which provider owns the thread (`meta_cloud`/`waha`),
  display-only, server-derived.
- `frontend/src/features/inbox/` — mixed-provider channel badge (conversation list + thread
  header) and a provider-aware composer: no 24h-window check for a WAHA thread, and a truthful
  disabled/refuse state (reusing QR-07's own live session-status read, `useWhatsAppQrStatus`) when
  the WAHA session is not currently connected.
- `backend/tests/test_qr08_inbox_integration.py` — 13 new hermetic backend tests. `frontend`
  gains 4 new Inbox tests.

**Behaviour**
- **Stored-message dedupe is not event dedupe.** `message`/`message.any` share one `envelope.id`
  and represent the same underlying WAHA message; QR-04's event-level dedupe (scoped by session +
  event type) correctly treats them as two distinct, both-valid events — but
  `MessageService._apply_inbound_endpoint` additionally dedupes by
  `(channel_endpoint_id, canonical_provider_message_id)` before ever inserting a row, so the two
  events collapse to one stored message. Proven for a same-event redelivery too, and proven *not*
  to collapse across two different endpoints holding the same provider message id.
- **Contact identity is unified across providers without a second normalization rule.** A WAHA
  sender arrives as `<digits>@c.us`/`@lid`/`@s.whatsapp.net`; the existing `wa_id_from_e164`
  (digit-stripping) already reduces it to the same key Meta's `wa_id` uses, so the same phone
  number resolves to the same `Contact` regardless of which provider it messaged through
  (ADR-0020 "One Contact authority") — no new identity code was needed.
- **No cross-provider failover, enforced structurally, not by convention.** `conversations`'
  `ck_conv_endpoint_owner` check makes "owned by both" or "owned by neither" a schema violation,
  not just a code discipline; `accept_for_conversation` has no provider parameter to override.
- **Reused, not duplicated, QR-07's own `channel_endpoints`.** `WhatsAppQrService.connect()` (QR-07
  code) now also idempotently creates the connection's one `ChannelEndpoint`
  (`provider_endpoint_id` = the WAHA session name — stable across a logout/re-pair cycle, unlike
  the phone number behind it) — the durable, addressable identity a conversation is anchored to.
  QR-07 never created one because nothing needed it yet.

**Defects found and fixed (both pre-existing in already-shipped QR-06/QR-07 code, surfaced only
once QR-08 exercised paths nothing had exercised before)**
- QR-07's `_REAUTH_PAIRING` constant included `PairingState.UNPAIRED`, diverging from the
  canonical definition QR-06 already established (`app.channels.waha.recovery`, which correctly
  excludes it). Harmless in QR-07 alone; became load-bearing once QR-08 needed `connect()` +
  `_ensure_endpoint()` to always succeed for a fresh connection. Fixed to match QR-06's definition.
- QR-04's `parse_events` classified `message.ack` as `UNKNOWN` even though QR-05 had already built
  `to_status_update` specifically to translate it — the wiring between the two was simply never
  completed. Now routed as `InboundEventType.STATUSES`, reaching the existing monotonic
  `messages.status` machinery QR-05 targeted from the start.

**Permanently absent for WAHA (unchanged from QR-01..07, enforced again here at the send-routing
layer)**
- MEDIA, INTERACTIVE, REACTION, LOCATION, CONTACT, TEMPLATE, CAMPAIGNS, BULK — a non-text reply
  against a WAHA conversation is refused with `ChannelCapabilityNotSupportedError`, not silently
  downgraded or routed to Meta.
- WAHA history retrieval and media-byte transfer remain unimplemented; unrelated to this milestone
  and not silently added. Unsupported media in an inbound WAHA message continues to render
  truthfully (`message_type: "unsupported"`, per QR-04), never as blank text.

**Known limitation**
- Analytics' existing "throughput by number × agent" rollup (`AnalyticsRollupService`) is a
  Meta-number-specific dimension; a WAHA conversation (no `phone_number_id`) is excluded from it
  rather than counted under a fabricated dimension. QR-08 introduces no WAHA analytics.

### 2026-08-08 — QR-07: WhatsApp Scan/Connect interface

**Added**
- `backend/app/services/whatsapp_qr_service.py` — bridges the live WAHA adapter (QR-01..06) to the
  existing M13-03/04/05 durable connection/session/pairing control plane
  (`ChannelConnectionService`, `SessionManager`, `PairingManager`). Single-organization scope per
  ADR-0021 (`WAHA_ORGANIZATION_ID`); creates no new table.
- `backend/app/api/v1/endpoints/whatsapp_qr.py` — 6 routes under `/channels/whatsapp-qr`: session
  status, connect, pair, QR image (binary, `Cache-Control: no-store, private`), reconnect, logout
  (requires `{"confirm": true}`). Gated on the existing `channels:read`/`channels:authenticate`
  permissions; no RBAC catalog change.
- `backend/app/schemas/whatsapp_qr.py` — provider-neutral response contract. No WAHA credential,
  session secret or QR byte ever appears in a JSON field.
- WAHA runtime registration is now wired into `get_channel_foundation()` — the QR-06 opt-in entry
  point — gated on `WAHA_BASE_URL`/`WAHA_API_KEY`/`WAHA_SESSION_NAME` all being set. An
  unconfigured deployment still registers nothing (asserted by test).
- `frontend/src/features/whatsapp-qr/` — the operator-facing Scan/Connect screen: live status
  polling (adaptive rate), QR image as an in-memory object URL (never cached, never persisted),
  connect/pair/reconnect actions, and an explicit two-step logout confirmation. New route
  `/channels/whatsapp-qr` (own `channels:read` gate, distinct from the Meta `waba:read` shell),
  linked from the existing Channels page header.
- 30 new hermetic backend tests (`tests/test_whatsapp_qr.py`) and 23 new frontend tests
  (`whatsapp-qr.test.tsx`).

**Behaviour**
- **STARTING stays ambiguous through the UI, not just the backend.** The frontend's own view-state
  derivation refuses to call a `STARTING` provider status "connecting" unless durable
  `pairing_state` is already `paired` — otherwise it reads as "creating session", mirroring
  QR-02/QR-06 exactly rather than re-deriving the rule loosely in presentation code.
- **Pairing transitions are ordered around a real M13-05 constraint discovered while building
  this**: `PairingManager` only accepts a pairing transition while the session is still
  `INITIALIZING`/`WAITING_FOR_PAIRING`. Reaching `ACTIVE` must therefore happen *after* the pairing
  step lands, not before — the service now orders session/pairing transitions conditionally rather
  than in a fixed sequence.
- **`PairingState.PAIRED` is terminal**, by existing M13-05 design (the same rule that requires a
  new session revision to re-authenticate an `EXPIRED` one). Logout does not try to reverse a paired
  revision in place — it terminates it and registers a fresh `UNPAIRED` revision on the same
  connection, changing the session identity the caller sees. This is the correct signal, not an
  artefact.
- **`SessionManager.acquire_lock` refuses to lease a `PAUSED` session** (an existing invariant).
  Reconnect therefore moves `PAUSED → INITIALIZING` through the lease-free write path
  (`channels:manage`) before acquiring a lease and driving the actual reconnect.
- **The QR image is never persisted.** Fetched fresh per request from the adapter, served with
  `Cache-Control: no-store, private`, held client-side only as a revoked-on-replace object URL.
- **Every mutating action holds the real M13-05 database lease**, not a bespoke lock — a second
  request racing a mutation gets the existing "lease held by another active runtime" conflict.
- **No QR-08 leakage.** No Unified Inbox integration, no history/media sync, no
  interactive/reaction/location/contact. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently
  prohibited.

**Known limitation**
- Retrying an **expired, never-scanned** QR reuses the pairing-request path, which the certified
  provider correctly refuses once its own session object already exists (`ChannelApiError`,
  observed and asserted in QR-03's own suite). The UI surfaces that real error rather than hiding
  it; a dedicated provider-side session restart is not implemented in this milestone. Recorded here
  rather than silently left for someone to rediscover.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions — QR-07 reuses the *existing*
  `channel_connections`/`channel_sessions` tables from M13-03/04, no new migration). RBAC catalog
  (`channels:read`/`channels:manage`/`channels:authenticate`/`channels:diagnose` already existed
  from M13-05). Meta behaviour and `BULK`/`CAMPAIGNS`/`TEMPLATE` prohibition.

**OpenAPI**
- **200 → 206 paths.** The six new routes are QR-07's first public surface over the pairing
  control plane; two pre-existing invariant tests that asserted an exact path count of 200 were
  updated to 206 with an explanatory comment, since QR-07 explicitly authorizes this — the
  assertion that no *secret*-shaped field (`qr_payload`, `pairing_secret`, `pairing_reason_code`)
  ever appears is preserved unchanged.

### 2026-08-08 — QR-06: WAHA session recovery, health and teardown

**Added**
- `app/channels/waha/recovery.py` — `ReconnectDecision`, `plan_reconnect()`, `backoff_delay()`,
  `RuntimeLease`/`assert_lease_current()`/`StaleRuntimeLease`, `project_health()`, and the
  opt-in `waha_channel_metadata()`/`waha_runtime_metadata()`/`register_waha_runtime()`.
- `WahaClient.start_session()`, `stop_session()`, `logout_session()`.
- `WahaChannelAdapter.session_health()`, `plan_session_recovery()`, `reconnect_session()`,
  `stop_session()`, `logout_session()`.
- **`SESSION_RECONNECT` and `SESSION_LOGOUT` declared** — earned by implementing them.
- 62 tests in `tests/test_channel_waha_recovery.py`.

**Behaviour**
- **Reconnect never guesses from an ambiguous provider status.** QR-02 proved `STARTING` means
  either a fresh session heading to `SCAN_QR_CODE` *or* a paired one resuming to `WORKING`.
  `plan_reconnect()` is therefore driven by the platform's **durable** pairing record and consults
  it before the provider status; `STARTING` yields `WAIT`, never `RECONNECT` and never
  `REQUIRES_REAUTH`. A session whose durable state is not `PAIRED` is never auto-restarted.
- **Provider unavailability never destroys durable truth.** An unreachable provider yields
  `PROVIDER_UNAVAILABLE` — explicitly not `REQUIRES_REAUTH` — so a brief outage cannot unpair a
  customer. `session_health()` reports it as unknown-and-unhealthy rather than optimistically fine.
- **Reconnect is bounded.** Attempts stop at `DEFAULT_MAX_RECONNECT_ATTEMPTS`, and `backoff_delay()`
  grows exponentially to a 60s ceiling as a pure function of the attempt number — identical in every
  worker, no shared coordination, no reconnect storm. A `WORKING` session is never reported
  exhausted regardless of prior attempts.
- **STOP and LOGOUT stay semantically distinct.** STOP halts the session and leaves credentials
  (`pairing_state` stays indeterminate — it does not claim the session became unpaired). LOGOUT
  invalidates them, producing the certified `SCAN_QR_CODE` / `me=null` / re-auth-required outcome,
  which is the *intended* result and is never auto-repaired. Collapsing them would let a routine
  restart silently unpair an account. `DELETE` is deliberately not exposed at all.
- **Ownership reuses the existing lease.** `RuntimeLease` describes a lease the existing session
  authority already issued; `assert_lease_current()` requires **both** holder identity and fencing
  token to match, so a re-claimed session cannot accept a stale writer that happens to hold the same
  token number. Every lifecycle mutation refuses outright without a lease and makes **no** provider
  call in that case. No new ownership system was invented.
- **Health is session-scoped.** Only `WORKING` is healthy; a reachable server with no working
  session is not. A session awaiting a scan reports re-authentication required, which outranks
  generic provider health.
- **No auto-pairing.** Recovery never fetches a QR and never creates a session — `reconnect_session`
  issues `POST /sessions/{name}/start`, never `POST /sessions`.
- **Runtime registration is opt-in.** `register_waha_runtime()` is explicit and idempotent; merely
  importing the package still registers no runtime, preserving the invariant every milestone through
  QR-05 asserted. Runtime capabilities are asserted never to exceed the adapter's.

**Changed**
- Twelve milestone-boundary guards were re-pointed as `SESSION_RECONNECT`/`SESSION_LOGOUT` moved
  from withheld to declared and stop/logout legitimately began to exist. They now guard what remains
  unimplemented — permanent deletion, history and media transfer.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, **frontend untouched**, Meta behaviour, and the default
  `ProviderRuntimeRegistry` (still empty). `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently
  prohibited. No history/media sync, interactive, reaction, location, contact or UI.

### 2026-08-08 — Fix: WAHA webhook event identity collision

**Fixed**
- `event_identity()` in `app/channels/waha/webhook.py` built its dedupe key by concatenating
  `session`, `event_type` and `envelope_id` and slicing the result to 128 characters, on the belief
  that placing `envelope_id` last made it "survive truncation". That was backwards: Python's
  `s[:128]` keeps the **left** prefix and discards the right tail — placing `envelope_id` last made
  it the first thing cut. Once `session`/`event_type` alone reached 128 characters, every
  `envelope_id` was discarded and two genuinely different events collapsed onto one stored
  `webhook_events.event_id`, defeating the very dedupe scoping QR-04 introduced. A second,
  length-independent collision existed in the same concatenation: plain `":"` delimiters let one
  component's content be mistaken for another's boundary. Both are reproduced as regression tests
  that assert the removed algorithm collided and the replacement does not.
- Replaced with `"waha:" + sha256(canonical).hexdigest()` — a fixed 69 characters, always within
  the 128-character column regardless of any component's length. `canonical` is a netstring-style
  length-prefixed encoding (`f"{len(part)}:{part}|"` per component) that is unambiguous by
  construction, so no adversarial component content can forge a false boundary. Uses
  `hashlib.sha256`, not Python's per-process-randomized `hash()`.
- Corrected the inaccurate "envelope id survives truncation" claim everywhere it appeared:
  `webhook.py`'s docstrings, `VALIDATION_RESULTS.md`, and the QR-05 tracker entry that had reported
  the (wrong) prior review as clean.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, capabilities (`health`, `qr_auth`, `session_stream`, `text`), RBAC, generated types,
  frontend, Meta behaviour, and QR-05 send/delivery-state code. The fix is confined to
  `event_identity()`/`_canonicalize()`.

**Tests**
- 12 new tests in `tests/test_channel_waha_webhook.py`: the old algorithm reconstructed and shown
  to collide on the same long-input and delimiter-injection cases the new algorithm resolves,
  fixed-length-regardless-of-input-length assertions, five adversarial delimiter cases, a
  50-call determinism check, and a source assertion that `hash()` is not used.
- Full QR-04 suite: 64 passed (52 before). All five WAHA suites: 253 passed together. Full backend
  suite: **1289 passed** (1277 before; +12).

### 2026-08-08 — QR-05: WAHA send path and delivery-state reconciliation

**Added**
- `app/channels/waha/delivery.py` — `WahaAck`, `ACK_TO_STATUS`, `map_ack()`, `to_status_update()`,
  `extract_sent_id()` and `WahaSendIndeterminate`.
- `WahaClient.send_text()` (`POST /api/sendText`) and `message_exists()` — the endpoint-scoped
  reconcile-before-resend lookup.
- `WahaChannelAdapter._dispatch()`, `to_status_update()` and `reconcile_send()`.
- `WahaCredentials.session` / `require_session()` and `WAHA_SESSION_NAME`, mirroring Meta's
  `require_phone_number()`. **This is the endpoint scope.**
- **`TEXT` declared** — text send is implemented and was proven cross-account by certification.
- 46 tests in `tests/test_channel_waha_delivery.py`.

**Behaviour**
- **Monotonicity is inherited, not reinvented.** `messages` already ranks
  `accepted < sent < delivered < read` and `advances()` refuses anything that does not move forward
  (Doc 06 §11.3 / D16). QR-05 only *maps* provider acknowledgements onto that vocabulary — no second
  ordering, no last-write-wins path, no parallel status column. Certification's out-of-order
  `DEVICE(2) → SERVER(1) → READ(3)` becomes `delivered → sent → read`, the late `sent` is ignored,
  and the message ends `read`. Proven for **every permutation** of an interleaved ack sequence.
- **Duplicate acks are idempotent** — QR-04 delivery is at-least-once, so a repeated ack simply does
  not advance. `failed` is terminal and is never overwritten.
- **Unknown acks fail closed.** An uncertified code maps to `None` (no state change) and
  `to_status_update()` raises rather than guessing. A guess could invent progress or, at a low rank,
  look like a regression.
- **Ambiguous sends are never blindly retried.** A transport failure raises `WahaSendIndeterminate`,
  which is deliberately **not** a `ChannelTransportError` so generic retry handling cannot sweep it
  up. A caller must reconcile first and may resend only if the message is proven *absent*; if the
  reconcile lookup itself fails, the error propagates and the outcome stays indeterminate rather
  than being downgraded to "safe to resend". No `resend`/`retry_send` path exists anywhere.
- **Endpoint scoping is structural.** Sends and reconcile lookups both run through
  `require_session()`, and the lookup queries that session's own chat — so one endpoint can never
  confirm or advance another's message, and there is no global provider-message search.
- **Correlation is on the canonical trailing provider id.** The send response is `@s.whatsapp.net`,
  the ack arrives `@lid`, history is `@c.us`; only the trailing component is stable, and that is
  what is matched. Reconciliation matches across all three forms.
- **Text only.** A media, interactive or template send is refused, never degraded into a text send.
- A send that returns no provider id reports `accepted=False`: nothing could correlate an ack or be
  reconciled later, so it is not a success.

**Changed**
- Eight milestone-boundary tests were re-pointed as `TEXT` moved from withheld to declared. Two that
  asserted "QR-05 is not pulled forward" were re-aimed at what genuinely remains unimplemented
  (interactive/media), and the webhook-seam guard now protects Meta's `OFFICIAL_WEBHOOKS`
  handshake, which this provider must never declare.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, **frontend untouched**, Meta behaviour, and the absence of any WAHA
  entry in `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited
  and disjoint. No teardown, reconnect, media, history, interactive, reaction, location or contact.

### 2026-08-08 — QR-04: WAHA webhook ingestion

**Added**
- `app/channels/waha/webhook.py` — raw-body sha512 HMAC verification, provider event
  normalization, `event_identity()` and `canonical_message_id()`.
- `WahaChannelAdapter.verify_webhook_signature()` / `parse_webhook()` / `to_inbound_message()`,
  implementing the **existing** generic `ChannelAdapter` seam. No parallel ingest path.
- Configuration `WAHA_WEBHOOK_HMAC_SECRET`, empty by default.
- **`SESSION_STREAM` declared** — earned by implementing ingestion.
- 52 tests in `tests/test_channel_waha_webhook.py`.

**Behaviour**
- **Reuses the existing ingest authority.** Events flow into `WebhookService` → `webhook_events`,
  which already owns persist-first durability, dedupe and dead-lettering. No new table, no new
  route, no second dedupe store, no migration.
- **`envelope.id` alone is not the dedupe key.** Certification proved delivery is at-least-once,
  that a retry repeats both `envelope.id` and `X-Webhook-Request-Id`, and that one provider message
  arrives as both `message` and `message.any` **sharing one `envelope.id`**. `event_identity()`
  scopes the key by session **and** event type, so a retry collapses while two distinct event types
  over one message both survive. Session scoping also prevents cross-tenant collision on a
  provider-chosen id. Determinism is proven by test — including a 64-way concurrent duplicate —
  because `messages` is partitioned and MySQL cannot enforce that uniqueness (error 1503).
- **Signature is verified before parsing**, over the raw bytes the provider signed, with
  `hmac.compare_digest`. An absent, malformed or wrong-algorithm signature is a rejection.
  A body over 1 MiB is refused **before** hashing.
- **An unset secret rejects every delivery** — an unconfigured deployment cannot silently accept
  unsigned provider traffic. There is no default secret.
- **Unknown shapes fail closed but are never dropped.** Unrecognised event types and malformed
  envelopes become `UNKNOWN` so Doc 06 §11.6 can dead-letter them for inspection. A malformed
  envelope carries **no** `event_id`, so two different malformed deliveries can never collapse.
- **Outbound echoes and acknowledgements are recorded, not applied.** `fromMe: true` and
  `message.ack` become `UNKNOWN`; delivery-state persistence is QR-05.
- **Identity evidence is preserved, not normalised away.** `@c.us`/`@lid`/`@s.whatsapp.net` survive
  into the stored payload; the canonical trailing provider message id is exposed alongside. No
  global provider-message lookup is performed.
- **Media inbound is not faked as empty text** — it is reported as `unsupported` with a
  `provider_has_media` flag rather than being rendered as a blank message.

**Changed**
- Five milestone-boundary tests were re-pointed as `SESSION_STREAM` moved from withheld to declared.
  `test_adapter_declares_no_webhook_ingestion` now guards `to_status_update` (QR-05) instead of the
  webhook methods QR-04 was always scoped to implement.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited. No send
  path, no delivery-state persistence, no teardown, no history/media execution, no UI.

### 2026-08-08 — QR-03: WAHA QR pairing

**Added**
- `app/channels/waha/pairing.py` — `CERTIFIED_NOWEB_STORE`/`build_session_config()` (the session
  configuration certification proved is required) and `WahaQrChallenge`, a transient QR value that
  redacts its own bytes.
- `WahaClient.create_session(name)` — `POST /api/sessions`, the first provider **write**.
- `WahaClient.qr_challenge(name)` — `GET /api/{session}/auth/qr`, returning raw image bytes.
- `WahaChannelAdapter.begin_pairing()` / `pairing_challenge()` / `pairing_state()`.
- **`QR_AUTH` is now declared** — the first capability added since QR-01, earned by implementing
  pairing and proven end-to-end by physical-phone certification.
- 30 tests in `tests/test_channel_waha_pairing.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Up, but never down.** QR-03 can create and start a session; it deliberately has no stop,
  restart, logout or delete. Teardown is QR-06, so nothing shipped so far can destroy a working
  pairing. Asserted by test on both adapter and client.
- **`fullSync` is camelCase, in exactly one place.** Certification proved the provider accepts
  `full_sync` with HTTP 201 and then silently stores `fullSync: false`, leaving a session that looks
  healthy with no history. The payload is built centrally and asserted by test so the trap cannot be
  reintroduced per call site.
- **The QR challenge is treated as a secret.** It is never persisted, never logged, excluded from
  the dataclass `repr`, and `repr`/`str` render `data=***withheld***`. This preserves M13-05's
  boundary that QR images and challenge bytes are never stored.
- **Pairing safety.** `pairing_state()` returns `None` for `STARTING`/`STOPPED`/`FAILED` and callers
  must leave durable pairing truth untouched — certification proved `STARTING` occurs both for a
  fresh session and for an already-paired session restarting, so inferring "unpaired" would discard
  a real pairing on a transient restart.
- **No guessing on conflict.** If the provider reports a session of that name already exists, the
  error surfaces rather than the session being silently reused or recreated.
- **Fails closed** on a non-image QR response (an HTML login page or JSON error is never handed back
  as a QR), on an unapproved engine, and on an invalid session name before any URL is built.
- **Capability-gated before I/O**: without `QR_AUTH` all three pairing methods raise
  `ChannelNotSupported` and open no connection.

**Changed**
- Two milestone-boundary tests were re-pointed rather than deleted, because the boundary legitimately
  moved: bringing a session **up** is now allowed, tearing one **down** still is not. `QR_AUTH` was
  removed from the withheld-capability list and the capability assertion now expects
  `{HEALTH, QR_AUTH}`. `send_text` was dropped from one forbidden-name list — it is an inherited
  generic `ChannelAdapter` method present on every adapter, so its presence proved nothing; the send
  path is now asserted **behaviourally** to still raise `ChannelNotSupported`.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, RBAC,
  generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited and
  disjoint from the declared set. No webhook ingestion, send path, media, history, runtime or UI.

### 2026-08-08 — QR-02: WAHA session lifecycle read and provider-neutral mapping

**Added**
- `app/channels/waha/lifecycle.py` — `WahaSessionStatus` (the five statuses observed during
  physical-phone certification), a pure `map_session_status()` translating each to the platform's
  own `SessionState`/`PairingState`, `WahaSessionSnapshot`, and strict session-name validation.
- `WahaClient.session_status(name)` — one authenticated read, `GET /api/sessions/{name}`.
- `WahaChannelAdapter.session_snapshot(name)` / `session_status(name)` — provider-neutral lifecycle
  for a session the caller names.
- 54 tests in `tests/test_channel_waha_lifecycle.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Read-only.** QR-02 adds exactly one authenticated read. No session is created, started,
  stopped, restarted, paired or logged out; adapter and client are asserted to expose no such
  method. Driving a lifecycle is QR-03 (pairing) and QR-06 (reconnect/health).
- **No capability added.** Capabilities remain exactly `HEALTH`. Observing a lifecycle is not being
  able to drive one, and `PROHIBITED_CAPABILITIES` is untouched.
- **Ambiguous statuses refuse to guess a pairing state.** `STARTING`, `STOPPED` and `FAILED` return
  no pairing state. Certification observed `STARTING` both on a fresh session (`→ SCAN_QR_CODE`) and
  on a controlled restart of a paired one (`→ WORKING` with no new QR), so the status alone cannot
  distinguish "never paired" from "paired and reconnecting". The caller keeps its durable state
  rather than having it overwritten by an inference.
- **`FAILED` maps to `degraded`, not a terminal state**, because certification recovered a `FAILED`
  session with a controlled restart.
- **Order-independence by construction.** Certification observed acknowledgements arriving out of
  order (`DEVICE(2) → SERVER(1) → READ(3)`). QR-02 introduces no delivery-state persistence at all,
  and the mapping is a pure function of status, so no arrival order can regress state.
- **Fails closed on an uncertified status**, without echoing the raw provider value.
- **Session names are validated, not escaped**, before reaching a request path; a traversal attempt
  opens no connection.
- **Both `@c.us` and `@lid` are retained** — certification proved one account is addressed both
  ways — so provider-neutral identity boundaries are preserved rather than normalised away here.
- **Server health is still not session health.** `authenticate()`/`status()` remain
  `connected=False`; only `session_status(name)` may report a live session, and only for `WORKING`.

**Fixed**
- `authenticate()` detail said QR pairing arrives in "QR-02+". QR-02 exists and does not implement
  pairing, so the reference was corrected to `QR-03`. Documentation-only string; no behaviour change.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, RBAC,
  generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. No QR API, QR UI, webhook ingestion, send path, media or history.

### 2026-08-07 — QR-01: WAHA provider adapter foundation

**Added**
- `app/channels/waha/` — the `waha` provider adapter behind the existing `ChannelAdapter` seam
  (ADR-0021 Class B). Connector identity `connector_type="waha"` on channel family
  `channel_type="whatsapp"`: a second *implementation* of the same channel, never a second channel
  and never a parallel hierarchy.
- `app/channels/waha/client.py` — a minimal typed async client implementing exactly the two
  authenticated reads QR-01 needs: the server version/engine banner and `/health`.
- Configuration `WAHA_BASE_URL`, `WAHA_API_KEY`, `WAHA_TIMEOUT_SECONDS`,
  `WAHA_CERTIFIED_VERSION` (`2026.7.2`), `WAHA_APPROVED_ENGINE` (`NOWEB`). Unconfigured by
  default with **no default API key**; the application boots normally with none of them set.
- 63 tests in `tests/test_channel_waha_adapter.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Capabilities are deliberately minimal: only `HEALTH`.** The QR-00 spike proved the *provider*
  supports QR pairing, sessions, media and history, but a provider endpoint existing is not the
  same as this adapter being able to use it, and neither is the same as a paired WhatsApp account
  working. `QR_AUTH`, `SESSION_STREAM`, `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`,
  `TEXT`, `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION` and
  `CONTACT` are all withheld until the milestone that implements them.
- **`BULK`, `CAMPAIGNS` and `TEMPLATE` are permanently prohibited** for this provider (ADR-0020
  section 5, ADR-0021, owner Class B approval) — recorded in `PROHIBITED_CAPABILITIES` and enforced
  by tests that no future milestone may quietly relax.
- **Server health is not session health.** `authenticate()`/`status()` return `connected=False`
  with an explicit "No WhatsApp session" detail, and `health_signal()` labels itself
  server-health-only. A healthy WAHA server with zero paired sessions cannot message.
- **Deterministic error mapping**, each shape observed against the real certified build: timeout and
  unavailable to `ChannelTransportError` (distinct messages); 401/403 to `ChannelAuthError`; 5xx and
  other reached errors to `ChannelApiError` carrying the status; malformed JSON, unexpected content
  type (the real server answers `text/html` on its root path) and non-object JSON to
  `ChannelApiError`; unconfigured to `ChannelConfigError` before any socket opens.
- **Version/engine safety.** Certified baseline `2026.7.2`, `NOWEB` only. An unexpected engine fails
  closed because payload shapes differ between engines. Version drift is reported, never
  auto-corrected; nothing upgrades a provider on its own.
- **Registration is inert.** Static registration opens no socket, requires no API key and starts no
  runtime, so the provider is *resolvable* but *disabled*. `ProviderRuntimeRegistry` deliberately
  gains no WAHA runtime.

**Security**
- API key sent only as `X-Api-Key`; never logged, never echoed into an exception message, masked in
  `repr`. Provider error bodies are never quoted (they are attacker-influencable); the warning log
  records status and path only. No QR material exists to persist. Meta webhook security and the
  QR-00 endpoint-scoped provider-message identity are unchanged.

**Verified**
- An isolated `devlikeapro/waha:noweb-2026.7.2` (digest `sha256:33ecd1b7...`) was run locally on
  `127.0.0.1` and the committed adapter driven against it: 11/11 checks covering authenticated
  version/engine, authenticated health, wrong-key and missing-config rejection, unavailable, timeout,
  non-JSON handling and the engine guard. **No session was created, no QR requested, no phone
  paired, nothing sent or received.** Torn down afterwards with all credentials and artefacts
  removed; the committed `docker-compose.yml` was not edited.
- Ruff, strict mypy (292 files), **1099 backend tests (0 skipped)**, `export_openapi.py --check`
  (200 paths, unchanged) and `quality_gate.py static` all pass.

**Preserved**
- No migration (head remains `0042_scope_provider_message_identity`, 43 revisions), no OpenAPI
  change, no RBAC change, no generated-type change, no frontend change. Meta Cloud behaviour is
  untouched.
- **QR login does not work and is not claimed to.** No WhatsApp session, QR generation, pairing,
  webhook ingestion, send path, media or history transfer, session worker or UI exists. QR-02
  through QR-09 and physical-phone certification all remain pending; no Production Ready, Host
  Validated, provider-certified or M13-07 claim is made.


### 2026-08-07 — QR-00: WAHA Class B provider selection and provider-message identity foundation

**Added**
- `docs/evidence/provider-evaluations/waha-class-b-selection-record.md` — the Design Document 33
  §6.4 provider-selection record. WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) is selected as
  the ADR-0021 **Class B** owner-approved internal self-hosted candidate. Owner Approval,
  Architecture Approval, Security Approval and explicit acceptance of WhatsApp restriction/ban risk
  are recorded verbatim. Certification remains **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE
  REQUIRED**; production certification is not granted. Succeeds, without rewriting, the earlier
  `waha-class-b-evaluation.md`.
- `app/channels/attention.py` — provider-neutral `SessionAttentionState` projection supplying the
  four Design Document 33 §6.1 operator signals (Healthy / Warning / Critical / Re-auth Required)
  by **deriving** re-authentication from the existing `SessionState` + `PairingState` rather than
  adding a fourth persisted health value. Re-auth outranks observed health; a `TERMINATED` session
  never reports re-auth.
- `alembic/versions/0042_scope_provider_message_identity.py` — additive, index-only migration adding
  `ix_msg_endpoint_wamid (phone_number_id, wamid)`. No column added, no backfill, no data change.
- 21 tests in `tests/test_provider_message_identity.py` covering endpoint/tenant isolation and the
  full re-authentication projection.

**Fixed**
- **Provider message identity was globally resolvable.** `MessageRepository.get_by_wamid(wamid)`
  looked a provider message id up with no organization, connection or endpoint filter. Safe only
  while Meta — whose `wamid` is globally unique — was the sole provider; a QR/multi-device provider's
  ids are session-scoped and may legitimately repeat across endpoints, which would have let one
  endpoint resolve, or a delivery receipt advance, another endpoint's or another tenant's message.
  This contradicted ADR-0020 ("provider message identity is scoped by connection/endpoint").
  Replaced by `get_by_provider_message_id(provider_message_id, *, phone_number_id)`, whose scope is
  keyword-only and required so an unscoped lookup cannot be written; no global variant remains.
  `apply_status` now receives the endpoint the callback arrived on.

**Verified**
- No backfill was required: `messages.organization_id`/`phone_number_id` have been `NOT NULL` since
  `0016_conversations_messages`, so ownership is already explicit rather than derived. Live database
  check: 191 messages, 0 null owners, 0 orphaned endpoints, 0 organization mismatches, 0 duplicate
  `(phone_number_id, wamid)` pairs.
- A UNIQUE constraint is impossible and is recorded as such: MySQL error **1503** rejects a unique
  index that omits the partitioning columns, and `messages` is `PARTITION BY RANGE
  COLUMNS(created_at)`. Reproduced on MySQL 8.0.46. Uniqueness remains enforced by the scoped read
  plus the persist-first ingestion path, as it already was for Meta.
- Real MySQL 8: fresh base → `0042` and `0041` → `0042` with pre-existing data preserved.
- Ruff, strict mypy (289 files), **1036 backend tests (0 skipped)**, `export_openapi.py --check`
  (200 paths, unchanged) and `quality_gate.py static` all pass.

**Preserved**
- Meta Cloud behaviour is unchanged — webhook ingestion, inbound deduplication, delivery/read
  reconciliation and Inbox suites pass unmodified. No API route, schema, RBAC entry, generated
  frontend type or frontend file changed.
- **QR login is not implemented and is not claimed.** QR-00 adds no WAHA client, adapter, Docker
  service, provider runtime registration, QR API, QR image endpoint, QR persistence, QR frontend,
  webhook endpoint, inbound ingestion, outbound send, history sync, media sync, session worker or
  reconnect runtime. Only `meta_cloud` is a registered adapter. QR-01 through QR-09 and
  physical-phone certification all remain pending; no Production Ready, Host Validated or M13-07
  claim is made.


### 2026-08-07 — Alembic version-table MySQL fix: support long revision ids

**Fixed**
- `alembic upgrade head` failed on a real MySQL 8 database while transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Root cause: Alembic's own bookkeeping
  column, `alembic_version.version_num`, defaults to `VARCHAR(32)`; this repository's descriptive
  revision-id convention produces identifiers up to 43 characters, and
  `0036_customer_identity_resolution` (33 characters) was the first to exceed it. No real MySQL
  deployment had ever advanced past `0035_notification_center` — this blocked schema creation,
  `create-owner`, authentication, and every real UI preview on MySQL.
- Repaired with a new migration, `0035a_widen_version_table`, inserted between
  `0035_notification_center` and `0036_customer_identity_resolution`, widening
  `alembic_version.version_num` to `VARCHAR(255)` on MySQL only (dialect-guarded; SQLite enforces
  no such length and PostgreSQL is not part of this stack). `0036_customer_identity_resolution`'s
  `down_revision` was retargeted to the new revision — its own revision id, schema body and
  behaviour are unchanged. No revision was renamed, renumbered, squashed, reordered, or stamped
  past a failure; the migration head remains `0041_channel_sync_control_plane` and the chain stays
  linear with a single head.

**Added**
- Three hermetic regression tests in `test_migrations.py`: single migration head, linear revision
  chain (no merges), and every revision id fits the widened column (with an early-warning margin).
- A new `test_migrations_mysql.py`: three tests against a real, throwaway-per-test MySQL 8
  database — fresh base→head, upgrade from `0035_notification_center` to head (the exact
  historical failure), and `create-owner` immediately after. Skipped cleanly (never failed) when
  no MySQL server is reachable, so the hermetic default suite gains no new external dependency.

**Verified**
- Real MySQL 8, both automated (throwaway databases) and manual (the documented CLI workflow
  against a fresh `docker compose` instance): fresh base→head succeeds; `0035`→head succeeds;
  `python -m app.cli create-owner` succeeds and is idempotent on re-run.

**Preserved**
- No application endpoint, model, schema, RBAC definition, ADR, provider/Meta/WAHA code, or
  frontend file changed. `scripts/export_openapi.py --check` and the full static quality gate both
  pass unchanged.
- Does not unblock the separate Chat History UI-preview gap: a real, populated `/chat-history`
  screenshot still requires either live Meta WhatsApp Business API credentials or an approved
  development fixture mechanism for conversation/message data, neither of which exists. This fix
  repairs the schema/auth path only. No Host Validated or Production Ready claim is made.

### 2026-08-07 — Chat History pagination/polling/accessibility hardening (audit findings D1–D8)

**Fixed**
- Removed the Chat History conversation list's Previous control, which could never activate — the
  backend never returns `prev_cursor`. Replaced it with a forward-only `Next` plus a `Back to
  newest` reset, shown only once a later page has been loaded, that returns to the same bounded
  25-row first page rather than any backend cursor contract change.
- `useConversation`/`useMessages` (`features/inbox/api.ts`) gained an optional trailing
  `refetchInterval` parameter, defaulting to the existing 10s poll every current caller relies on;
  Chat History passes `false` for the selected conversation's detail and messages, since a
  read-only archive view has no live-triage need for it. Live Chat and Customer 360 are
  unaffected — neither passes the new argument.
- Selecting a conversation below the route's own `lg` list/detail breakpoint now moves focus into
  the detail pane (the "Back to conversation history" button); returning to the list restores
  focus to the row that was open. Neither happens at or above `lg`, where both panes stay visible.
  Reuses the existing `useMediaQuery` utility rather than a new breakpoint mechanism.
- The `contact` deep-link filter now participates in active-filter detection, so a contact filter
  matching nothing shows the same "No conversations match" / Clear filters state every other
  filter does, instead of the global "no history at all" empty state.
- The conversation list's status badge now colors `open` as success and every other status as
  neutral, matching Live Chat's own `ConversationList.tsx` convention exactly (previously every
  non-resolved status, including pending and snoozed, read as success).
- The message list gained `aria-label="Message history"`; the page title is now a real `<h1>` and
  the selected thread's contact name a real `<h2>` (matching `ConversationThread.tsx`'s own
  heading level for the identical field) — the route previously contributed no heading at all.

**Added**
- Twelve new tests in `chat-history.test.tsx` covering all of the above, plus a direct regression
  proving no conversation-detail or message request is made before a conversation is selected.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed; no new permission was introduced.
- `MODULE_STATUS.md`'s Chat History pending-work wording was corrected to keep naming media-only
  and audit-scoped filtering alongside the existing date-range/campaign-generated/export/Download
  Center gaps; completion remains `55%`, unchanged by this hardening pass.
- Audit findings D9–D12 (the `<time>` `dateTime` attribute, the `/phone-numbers` duplicate cache
  key, general test observations, button-vs-anchor deep links) were left untouched, as instructed.

### 2026-08-07 — Dedicated Chat History read workspace over the existing conversation and message contract

**Added**
- Added a `/chat-history` route and `inbox:read`-gated navigation entry: a read-only list/detail
  workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read. Reuses
  `useConversations`, `useConversation`, `useMessages` and `useAssignableUsers` from
  `features/inbox/api.ts` verbatim — no second conversation/message query authority was opened.
- Search, status, assignee and tag filters map onto the identical query params Live Chat's own
  filters already send. A new `number` (channel) filter is additive on the shared
  `InboxFilters`/`toListQuery` types both surfaces read from one definition — the backend already
  accepted `number`; only the frontend type was missing it.
- Cursor pagination for the conversation list and the existing infinite-query "Load older
  messages" control are both reused as-is, so neither list nor message history ever fetches an
  unbounded page.
- A deep link opens the selected conversation in Live Chat (`/inbox?conversation={id}`, the exact
  shape Live Chat's own route already parses); a second deep link to the audit trail is shown only
  to `audit:read` holders and hidden otherwise, following the same pattern Customer 360 already
  uses.
- The route exposes no assignment, status, tag, note or send control — those remain Live Chat's
  job. Date-range and campaign-generated filtering, and transcript export, are named in the page
  header as not yet available rather than offered as disabled controls, since none is backed by
  the current contract.
- Twenty-two focused tests, plus updates to `inbox.test.tsx`'s `toListQuery` fixtures and
  `phase1-foundations.test.ts`'s exact-order navigation assertion for the additive `number` field
  and new nav entry.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed. No new permission was introduced.
- Closes the frontend half of `ROADMAP.md`'s `CORE-10 — Dedicated Chat History`; its backend
  "Conversation query extensions" (a date-range query param, `MessageResponse.campaign_id`) and
  export capability are not implemented and remain recorded, open follow-up — not claimed here,
  not M13-07, and `ROADMAP.md` itself is unmodified.

### 2026-08-06 — User Attributes management interface over the existing Custom Attribute contract

**Added**
- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete — typed definitions
  (`string`/`number`/`datetime`/`boolean`/`enum`), org-scoped key uniqueness, `is_indexed`/`is_pii`
  flags — but the frontend only ever issued the list read consumed by the Contacts filter bar,
  campaign audience rules and segment predicates, so no organization could define a typed field
  from the product itself.
- Create, edit and delete for `contacts:write` holders. `key_name` and `data_type` are immutable
  after creation — the update contract carries no field for either — so the edit dialog presents
  both as read-only facts (via the same `DefinitionRow`/`<dl>` pattern used for Canned Messages'
  read-only scope) rather than disabled controls that would silently do nothing.
- Search across key name and label; a data-type filter; `Indexed`/`PII` shown as informational
  badges. The delete confirmation states plainly that removing a definition also removes every
  contact's stored value for it, matching the endpoint's real behaviour.
- Twenty-three focused tests, including three pure-function tests for the comma-separated
  enum-choice parser and its validation, and a cache-refresh regression against the real
  `useCustomAttributeDefinitions` hook the Contacts page already imports from
  `customer-profile/api.ts`, under one shared `QueryClient`.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed; migration head remains `0041_channel_sync_control_plane` and the contract remains
  drift-free.
- Only contract fields are shown; no status, category, required/active flag or other unsupported
  field was invented. `is_pii` is described honestly as not yet enforced elsewhere, since nothing
  else in the codebase reads it.

### 2026-08-06 — Canned message scope accessibility fix

**Fixed**
- The Canned Messages edit dialog showed its read-only Scope information through a `Field
  htmlFor="canned-message-scope"` label pointing at a plain `<div>`, which is not a labelable
  element and created no real accessible association. Replaced with the `DefinitionRow`/`<dl>`
  pattern already used for read-only information elsewhere in Settings (`OrganizationPanel`,
  `ApplicationPanel`) — no fake form control, no behaviour change.

### 2026-08-06 — Canned Messages management interface over the existing Quick Reply contract

**Added**
- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete — personal and shared canned
  replies, scope-aware shortcut uniqueness, soft delete — but the frontend only ever issued the list
  read from the Message Composer's `/shortcut` picker, so on an organization with no canned messages
  yet the picker stayed permanently empty with no way to populate it from the product.
- Create, edit and delete are offered to `inbox:write` holders; `shared` (Personal/Shared) is
  selectable only at creation, matching the immutable-after-creation contract — the edit dialog shows
  scope as read-only information rather than a control that would silently do nothing.
- Search across shortcut, title and body; a scope filter (All/Personal/Shared); a one-line body
  preview in the table. `usage_count` is read but not shown — no send path increments it yet, so
  presenting it as live usage would be dishonest.
- A minimal, permission-correct addition to the Message Composer's empty quick-reply state: an
  `inbox:write` agent gets a link to Settings → Canned Messages; a read-only agent sees the same
  empty message with no link, never a misleading action they cannot use.
- Eighteen focused Settings tests and two focused Inbox tests, including a regression that renders
  the panel beside the real `useQuickReplies` hook `MessageComposer.tsx` imports from `inbox/api`,
  under the identical `["quick-replies"]` cache key, and proves a create through Settings refreshes
  the composer's own picker without a manual reload.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed; migration head remains `0041_channel_sync_control_plane` and the contract remains
  drift-free.
- Only contract fields are shown; no status, category, favourite, pinning, created-by display, AI
  generation or unsupported ownership field was invented.

### 2026-08-06 — Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

**Fixed**
- Reset stale `create`/`update`/`delete` mutation state when a Tags panel dialog opens, so a
  previous failure can no longer resurface as a false error the moment a different tag's dialog is
  opened.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.

**Added**
- Six regression tests: cross-feature cache-invalidation (proved against the real `useTags` hooks
  in `customer-profile/api.ts` and `campaigns/api.ts` under one shared `QueryClient`, no new
  cache-key system), a duplicate-name 409 conflict, a failed delete with retry, an explicit loading
  state, per-tag accessible row-action names (e.g. `Edit Prepaid`), and a dedicated proof that a
  failed attempt's error does not resurface when a dialog is later opened for a different tag.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07; Settings/Tags/Attributes completion claims are
  unchanged.

### 2026-08-06 — Tag management interface (verified UI remediation)

**Added**
- Added a Settings → Tags panel so the organization's tag vocabulary can be created, renamed,
  recoloured, described and deleted from the product. The existing `GET/POST/PATCH/DELETE
  /api/v1/tags` contract was already complete, but the frontend only ever issued the list read, so
  no tag could be created anywhere in the UI.
- The panel reuses the shared enterprise primitives (`Section`, `FilterBar`, `Input`, `Select`,
  `Button`, `Badge`, `Modal`, `Pagination`, `EmptyState`, `ErrorState`, `TagChip`) and the generated
  API client; search, a usage filter, client-side paging, a live tag preview, inline validation and a
  delete confirmation that states how many contacts would be detached.
- Added ten focused tests covering listing, the persistent create action on an empty organization,
  create/edit/delete requests, search and usage filtering, colour validation, the read-only
  experience without `contacts:write`, and the error retry.

**Preserved**
- Frontend only. No backend file, migration, endpoint, permission definition, OpenAPI path or
  generated contract type changed; migration head remains `0041_channel_sync_control_plane` and the
  contract remains drift-free.
- Tags carry no status column in the contract, so the second filter is usage, derived from the
  `usage_count` the existing read already returns. No backend field was invented, and the reference
  product's `First Message` tag concept was deliberately not reproduced.
- Reads stay on `contacts:read` and writes on `contacts:write`, exactly as the endpoints enforce;
  users without write permission see no create, edit or delete control at all.

### 2026-08-05 — Provider-neutral History & Media Control Plane (M13-06B)

**Added**
- Added the repository-owned lifecycle service over the existing M13-06A history checkpoints and
  media references: create/reopen, bounded transitions, monotonic progress, factual media observations,
  optimistic concurrency, tenant/object authorization, feature flags, dedicated RBAC and Audit evidence.
- Added the frozen `channels:history_sync` permission through additive migration
  `0041_channel_sync_control_plane`; no table, provider dependency or public API was introduced.
- Added focused regressions for lifecycle legality, resume/fresh-run semantics, permission and flag
  failure, tenant isolation, capability gating, secret rejection, idempotency and API absence.

**Preserved**
- No provider is certified. No adapter, QR payload/login, provider cursor, event ingestion, history
  retrieval, media-byte transfer, queue execution, messaging, webhook, frontend or generated contract
  exists in M13-06B.
- ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative.

**Validated**
- Workflow `31038662241` passes Ruff, strict mypy, OpenAPI/client drift, 985 backend tests,
  36 frontend files / 671 tests, production build, E2E types, SAST, dependency audits and tracked-source
  vulnerability/secret/IaC scanning.
- Migration upgrade/downgrade/re-upgrade passes at `0041_channel_sync_control_plane`; OpenAPI remains
  200 paths and the main application bundle remains `199.78/54.87 kB gzip`.
- M13-06B reaches `Repository Validated`; live provider-dependent history/media behavior remains
  blocked by certification and Host Machine Validation.

### 2026-08-05 — Owner review, release candidate audit and merge readiness (UI-TASTE-05)

**Fixed**
- Removed the verified campaign create/edit lazy-chunk execution cycle by importing the existing
  `CampaignWizard`, form helpers and types from their direct modules instead of the campaigns barrel.
- Preserved the existing campaign workflow, API, permissions, route boundaries and feature behavior.

**Reviewed**
- Audited Dashboard, Reactivation, Contacts, Customer 360, Inbox, Campaigns, Templates, Analytics,
  Notifications, Settings, Authentication, RBAC, Customer Identity, shared components and the
  provider-neutral Module 13 foundations as one release candidate.
- No second authority, architecture drift, governance expansion, provider work or roadmap resequencing
  was introduced.

**Validated**
- Release-candidate workflow `30982637585` passes repository lint, strict typing, OpenAPI/client drift,
  980 backend tests, 36 frontend files / 671 tests, clean production build, E2E types, SAST, dependency
  audits and tracked-source vulnerability/secret/IaC scanning.
- Main application JavaScript remains `199.78/54.87 kB gzip`; the campaign chunk-order warning is absent.
- Authenticated representative-data browser/device/screen-reader and production-scale evidence remains
  `PENDING – Host Machine Validation`.

### 2026-08-05 — Responsive, accessibility and performance regression (UI-TASTE-04)

**Changed**
- Added the existing `kyc:read` route guard to the Reactivation KYC deep link without changing the
  permission catalog or backend authorization.
- Debounced permission-aware workspace record search and kept loading feedback truthful while
  preserving the existing bounded APIs.
- Lazy-split authenticated page and administrative panel routes behind the existing shell and route
  guards; no route, workflow or API contract changed.
- Made shared pagination wrap safely on narrow layouts and made shared modals lock background
  scrolling while retaining focus entry, trapping, Escape handling and focus restoration.

**Fixed**
- Prevented empty search-result collections from producing an invalid negative keyboard selection.
- Replaced the keyboard-shortcut overlay with the shared modal authority.
- Removed the verified unused `ComingSoonPage` and its obsolete test.

**Preserved**
- No new feature, API, migration, dependency, governance, architecture, provider, QR, runtime,
  messaging, history, media or production-credential work was introduced.
- Reactivation remains 94%; Module 13 remains 44%; all provider-dependent behavior remains blocked.

**Validated**
- Repository pre-merge quality gate passed in workflow `30980229127`: Ruff, strict mypy, OpenAPI drift,
  980 backend tests, ESLint, TypeScript, 36 frontend files / 671 tests, production build, E2E types,
  Bandit, dependency audits and tracked-source vulnerability/secret/IaC scan.
- Main application JavaScript reduced from 733.97/178.29 kB gzip to
  199.78/54.87 kB gzip through authenticated route splitting.
- Authenticated representative-data browser/device/screen-reader and production-scale performance
  evidence remains `PENDING – Host Machine Validation`.

### 2026-08-05 — Reactivation operational hierarchy (UI-TASTE-03B)

**Added**
- Added bounded offset pagination to the existing tenant-scoped Reactivation pipeline query and
  shared previous/next controls at 25 cases per page.
- Added URL-backed search, status, label, owner, reminder, date, display, page, and factual work-view
  state without claiming server-shared saved views.
- Added Design Document 34 and focused backend/frontend regressions for hierarchy, permission truth,
  redirects, pagination, terminal movement, and existing case workflows.

**Changed**
- Made the real Reactivation CRM the default Reactivation destination and limited primary
  sub-navigation to connected, permission-available CRM, KYC, Document, and Report surfaces.
- Redirected historical SIM, Activation, Completed, Interested, and bulk-eligibility routes to the
  existing filtered CRM or Contact import authorities.
- Reused shared filter, form, toolbar, pagination, loading, empty, error, and modal components;
  strengthened visible due/SLA/owner/document/next-task hierarchy.

**Fixed**
- Removed foundation-only executable-looking placeholder navigation and outdated KYC gating copy.
- Hid KYC, Document, and Report tabs when the existing route permission is absent.
- Stopped terminal cases from advertising drag behavior, fixed malformed result-summary encoding,
  and removed the 200-card unpaginated render path.
- Corrected governance stop wording so provider certification blocks Module 13 live/provider UI,
  not unrelated provider-neutral product milestones.

**Preserved**
- No provider evaluation, certification, WAHA, Evolution API, QR runtime, live session, ingestion,
  history synchronization, media transfer, provider dependency, migration, permission, audit, or
  tenant-authority change.
- Module 13 remains 44% and all provider-dependent work remains blocked.

**Validated**
- Ruff, strict mypy, OpenAPI/client drift, 4 focused backend tests, all
  980 backend tests, ESLint, TypeScript, 35 frontend files /
  668 tests, production build, E2E TypeScript, dependency audits, Bandit, and tracked
  source vulnerability/secret/IaC scan passed in workflow `30953600784`.
- Migration head remains `0040_channel_sync_media_foundation`; OpenAPI remains 200 paths.
- Authenticated representative-data visual/WCAG/device/performance acceptance remains
  `PENDING – Host Machine Validation`.

### 2026-08-05 — Provider-neutral Sync & Media Persistence Foundation (M13-06A)

**Added**
- Added the frozen-contract `channel_sync_checkpoints` and `media_channel_references` records with
  organization, connection/endpoint, checkpoint/progress, expiry, transfer-state, Audit and optimistic-
  concurrency facts.
- Added tenant-scoped repositories and provider-neutral sync/media state vocabulary, including the
  existing capability seam's `history_sync` value.
- Added migration `0040_channel_sync_media_foundation` and focused repository, tenant, secret-redaction,
  uniqueness, constraint and migration regressions.

**Preserved**
- No provider is certified. WAHA remains `Requires Additional Evidence`.
- No provider adapter, dependency, live QR pairing, live event ingestion, history job, media transfer,
  queue task, API route, generated contract, frontend behavior or production runtime was added.
- Existing Contact, Conversation, Message, MediaAsset, ChannelAdapter, ChannelConnection,
  ChannelSession, queue, RBAC, tenant, feature-flag and Audit authorities remain unchanged.

**Validated**
- Ruff and strict mypy pass; 18 focused tests and all 979 backend tests pass in workflow
  `30946554198`.
- Migration upgrade/downgrade/re-upgrade passes at `0040_channel_sync_media_foundation`.
- OpenAPI remains semantically unchanged at 200 paths; generated TypeScript and unchanged frontend
  lint, types, tests and production build pass.
- M13-06A reaches `Repository Validated`; all live provider-dependent M13-06 behavior remains blocked
  by certification and host evidence.


### 2026-08-04 — QR Pairing & Provider Runtime Foundation (M13-05)

**Added**
- Added provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing `ChannelAdapter` seam.
- Added tenant-scoped runtime registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat, restart/recovery metadata and durable session integration.
- Added a no-store pairing lifecycle with governed request/available/expired/cancelled/paired/active transitions, dedicated feature flags/RBAC/Audit and migration `0039_qr_pairing_provider_runtime_foundation`.

**Security**
- Runtime reports require valid lease fencing, pairing TTL and expiry are enforced, expiry sweeps are bounded, reason codes are constrained, and no QR payload, token, protocol credential or provider secret is stored or audited.

**Preserved**
- M13-01 through M13-04 channel, identity, persistence and session authorities remain intact; no duplicate provider/runtime/connection/message authority was introduced.
- No QR image generation/scanning, WhatsApp login/protocol, provider adapter, message/history synchronization, incoming/outgoing messaging, webhook, routing, Inbox/Customer 360/Analytics, API or frontend work is included.

**Validated**
- Ruff, strict mypy, 20 focused tests and all 976 backend tests pass in workflow `30933007710`.
- Migration round-trip, generated-client invariance, Bandit, dependency audits and tracked-source security scan pass; OpenAPI remains semantically unchanged at 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-05 reaches `Repository Validated`; host/provider/runtime commissioning remains pending.

### 2026-08-04 — QR Session Manager Foundation (M13-04)

**Added**
- Added provider-neutral session lifecycle/state contracts and durable `ChannelSession` records linked to existing organization-owned channel connections.
- Added tenant-scoped registration/discovery/ownership, factual health, heartbeat/expiration, recovery metadata, restart policy, capability references, database leases, fencing tokens, optimistic concurrency and Audit evidence.
- Added disabled-by-default session flags, channel session RBAC permissions and additive migration `0038_qr_session_manager_foundation`.

**Security**
- Session metadata rejects secret-shaped material and stores only optional references to existing encrypted credentials; provider secrets are never returned through APIs, OpenAPI, generated clients, logs or Audit payloads.

**Preserved**
- M13-01 through M13-03 channel, identity and persistence authorities remain intact; no duplicate connection, endpoint, credential, message or history storage was introduced.
- No QR code generation/scanning, WhatsApp login, provider adapter/runtime, message/history synchronization, sending, incoming webhook runtime, routing, Inbox/Customer 360 change or M13-05 work is included.

**Validated**
- Ruff and strict mypy across 279 source files pass; 7 focused session/migration tests and all 970 backend tests pass.
- Migration upgrade/downgrade/upgrade, OpenAPI/client regeneration, Bandit high-severity and dependency audits pass; OpenAPI remains 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-04 reaches `Repository Validated`; target-host multi-node/runtime/MySQL/KMS/rollout commissioning remains pending.

### 2026-08-04 — Persistent Channel Connections & Endpoint Records (M13-03)

**Added**
- Added provider-neutral, organization-owned persistent Channel Connection, Channel Endpoint and encrypted Channel Secret records with immutable provider identifiers, lifecycle/health/configuration/metadata facts, Audit references, soft delete and optimistic locking.
- Added tenant-scoped repositories and a disabled-by-default feature-gated persistence service, including logical cascade deletion and credential rotation/version/revocation/expiry/access evidence.
- Added an AES-GCM secret-cipher abstraction and migration `0037_persistent_channel_connections`; plaintext credentials are rejected from metadata and never exposed through APIs, OpenAPI, generated clients, logs or Audit payloads.

**Preserved**
- M13-01 channel foundations, M13-02 identity resolution, existing `ChannelAdapter`, Contact/Inbox/Customer 360/Timeline/Notification/Analytics authorities and the 200-path public API remain unchanged.
- No provider adapter/runtime, QR login/pairing/session, history or message synchronization, live messaging, webhook, routing engine, Inbox/Customer 360 UI or M13-04 work is included.

**Validated**
- Ruff and strict mypy across 275 source files pass; 4 focused persistence tests and all 965 backend tests pass.
- Migration upgrade/downgrade/upgrade, OpenAPI/client regeneration, Bandit high-severity and dependency audits pass; OpenAPI remains 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-03 reaches `Repository Validated`; target-host MySQL/KMS/rollout commissioning remains pending.

### 2026-08-04 — Customer Identity Resolution (M13-02)

**Added**
- Added exact tenant-scoped provider and endpoint identities linked to the canonical Contact, with immutable ownership, factual confidence, ambiguous/conflict detection and a restricted manual-review queue.
- Added non-destructive merge recommendations with explicit approve/reject decisions, RBAC, feature flags, Audit and Customer Timeline evidence.
- Added migration `0036_customer_identity_resolution`, seven additive API paths, generated OpenAPI/client authority and focused identity regressions.

**Preserved**
- M13-01 channel foundations, canonical Contact ownership and existing CRM, Inbox, Customer 360, Timeline and Audit authorities remain unchanged; approval never merges Contacts or moves identities.
- No M13-03 session/connection control-plane, provider runtime, QR pairing, messaging, UI route or provider selection work is included.

**Validated**
- Ruff, strict mypy across 271 source files, 22 focused tests and all 961 backend tests pass.
- Frontend production audit, ESLint, TypeScript, Vitest and production build pass; OpenAPI has 200 paths and the generated client is current.
- Migration upgrade/downgrade/upgrade passes. M13-02 reaches `Repository Validated`; host/runtime commissioning remains pending.

### 2026-08-04 — Generic Channel Foundation (M13-01)

**Added**
- Added provider-independent Communication Intent, Communication Policy, Channel Metadata,
  Provider Health and Provider Lifecycle contracts with shared enums and validation.
- Added provider metadata and capability registries that delegate adapter creation to the
  existing `ChannelAdapter` registry rather than creating a parallel provider system.
- Added two disabled-by-default generic connection flags over the existing organization-scoped
  `FeatureFlag` table and typed dependency-injection composition.
- Added seven focused tests for registry parity/conflict handling, policy decisions, factual
  health/lifecycle validation, feature-flag precedence and DI stability.

**Preserved**
- No provider implementation, QR pairing, session/runtime, history, live messaging, database
  migration, API route, OpenAPI/client, dependency, frontend or shared CRM-authority change.
- Contact, Customer 360, Timeline, Inbox, Notification Center, Analytics and the existing
  `ChannelAdapter` remain authoritative and unchanged.

**Validated**
- Ruff and strict mypy pass across 263 source files; 46 focused and 955 full backend tests pass.
- The unchanged frontend passes production audit high threshold, ESLint, TypeScript, 661 tests
  and build with no bundle change.
- M13-01 reaches `Repository Validated`; persistent channel records/Meta backfill remain a
  Required unimplemented contract gap, and M13-02 is not authorized.

### 2026-08-04 — Module 13 implementation contract (M13-00)

**Added**
- Added accepted ADR-0020 and frozen Design Document 33 for the Enterprise Omnichannel Channel
  Manager, preserving the existing capability-based channel seam and shared CRM authorities.
- Added the provider capability matrix, objective QR provider evaluation gate, threat model, security
  architecture, session lifecycle, exact customer identity contract, additive API/database plan,
  rollback, feature flags, staged rollout, disaster recovery, observability, performance objectives,
  testing strategy, acceptance criteria, risk register and external dependencies.
- Added a classified gap analysis with Required, Recommended and Future Enhancement findings.

**Clarified**
- Confirmed that Module 13 extends the existing `ChannelAdapter` rather than introducing a parallel
  adapter hierarchy or duplicate Contact, Inbox, message, media, notification, analytics or audit authority.
- Recorded ADR-0020 as the later owner decision permitting Instagram only as a future separately
  approved adapter possibility despite the older Doc 07 exclusion; no future-provider implementation
  is authorized by M13-00.
- Kept QR provider selection honest: no vendor is claimed until every Required criterion passes.

**Preserved**
- No QR login, session runtime, Channel Manager, backend, frontend, migration, API, generated contract,
  dependency, route, queue or deployment implementation was added.
- Repository remains `1.0.0-rc1`, migration `0035_notification_center`, OpenAPI 193 paths and Module 13
  implementation completion `0%`.

**Validated**
- M13-00 reaches `Repository Validated` through documentation structure, consistency, changed-file,
  gap-classification and governance checks. Host/runtime/provider/production evidence is intentionally
  not claimed, and M13-01 remains unstarted pending its explicit gates and owner instruction.

### 2026-08-04 — Operator-first operational Dashboard (UI-TASTE-03A)

**Added**
- Added a permission-aware operational desk that prioritizes blocked Reactivation customers, KYC
  reviews, SIM/Activation SLA risk, Campaign failures, waiting conversations, blocked Templates,
  agent workload and today KPI changes using existing source authorities.
- Added truthful loading, empty, partial-source error and permission states, governed source actions,
  signed-in task snapshot, responsive table/card transformations and four focused selector tests.

**Changed**
- Replaced the messaging-led Dashboard with decision-first operational intelligence while preserving
  Live Chat/New Campaign primary links and all source workflows.
- Added optional `enabled` controls to existing Reactivation, KYC, Template and Analytics query hooks
  so unauthorized Dashboard sources issue no request.
- Lazy-split the operational workspace behind an accessible skeleton. The main chunk improves from
  747.91 kB to 733.62 kB; the Dashboard workspace is 31.96 kB / 8.61 kB gzip.

**Fixed**
- Fixed strict TypeScript widening of KPI sentiment literals.
- Fixed a regression where primary Dashboard navigation actions had become buttons instead of real
  links; the established accessibility/navigation contract is restored.

**Validated**
- Production dependency audit, ESLint, TypeScript, 34 Vitest files / 661 tests and production build
  pass. Migration `0035`, 193-path OpenAPI, generated client, backend and dependencies are unchanged.
- Authenticated representative-data visual/reference review remains `PENDING – Host Machine
  Validation`; bounded source reads are not claimed as exact enterprise totals.

### 2026-08-04 — Shared enterprise design-system modernization (UI-TASTE-02)

**Added**
- Added original shared `Input`, `Select`, `Textarea`, `Field`, `Toolbar`, `FilterBar`, and cursor
  `Pagination` primitives with semantic focus, disabled, invalid, busy, label, help, error, icon,
  action, summary, and mobile touch-target behavior.
- Added named `control`, `surface`, and `overlay` radius tiers so enterprise density can converge
  without silently changing legacy sidebar or navigation utilities.
- Added three focused shared-primitive tests covering semantic labels, invalid state, pagination
  callbacks/disabled state, and loading-button accessibility.

**Changed**
- Refined shared Button, Card/CardHeader, PageHeader, and PageContainer hierarchy, spacing, elevation,
  responsive action alignment, and restrained interaction treatment.
- Replaced duplicated Contacts search/filter/mobile-sheet/pagination styling, Inbox search/advanced-
  filter/saved-view/bulk-select/pagination styling, and Notification Center filter/action styling
  with governed shared components. Existing URL state, shortcuts, bulk behavior, polling, read
  state, permissions, and source deep links are unchanged.

**Preserved**
- Sidebar, navigation, routes, backend, migrations, OpenAPI, generated contracts, dependencies,
  permissions, real workflows, keyboard/focus handling, reduced motion, responsive navigation, and
  source-domain ownership are unchanged. No heavy animation library, copied reference implementation,
  proprietary asset, fake metric, or parallel component system was introduced.

**Validated**
- ESLint and TypeScript pass; all 33 Vitest files and 657 tests pass; the production build passes
  after transforming 2,599 modules. The main application chunk is 747.91 kB minified / 181.62 kB
  gzip and retains the known >500 kB warning.
- The production dependency audit has no high/critical finding and reports two moderate React Router
  advisories. The combined development-tool inventory reports 11 transitive findings and remains a
  separately governed dependency-modernization task.
- Authenticated representative-data desktop/tablet/mobile and approved-reference visual comparison
  remains `PENDING – Host Machine Validation`; Priority 2 is blocked pending owner approval.

### 2026-08-02 — Customer 360 domain convergence (CORE-07)

**Added**
- Converged the existing Contact profile into one persisted, permission-aware workspace for identity
  and attributes, exact-contact WhatsApp conversations/messages, Reactivation status/labels,
  reminders, assignment, notes, SLA, Documents, Tasks, KYC/SIM/Activation facts, Campaign
  participation, Audit, and Customer Timeline.
- Added accessible Overview, Vi operations, Conversations, Timeline, Tasks, Documents, Campaigns,
  and Audit tabs, source-workflow deep links, loading/empty/error/denied/read-only states, and
  responsive desktop/tablet/mobile composition using the existing design system.
- Added optional exact Contact filters to the existing Inbox conversation query and Reactivation
  pipeline query; regenerated OpenAPI/TypeScript contracts at the unchanged 189-path boundary; added
  ADR-0018, Design Document 31, and focused backend/frontend regressions.

**Reused and preserved**
- Reused Contact, Conversation/Message, Inbox, Reactivation, Task/reminder, Document Center, KYC,
  SIM, Activation, Campaign, Audit, Customer Timeline, RBAC, tenant, and shared UI authorities.
  Customer 360 remains a read composition with no parallel model, repository, service, route family,
  synthetic metric, migration, fake data, or duplicated completed module.
- Reviewed the approved `0001`, `0008`, `0010`, and `0048` paired reference captures for contextual
  hierarchy, tabs, density, and activity patterns. Original code, wording, icons, colors, tokens,
  spacing, and breakpoints are retained; reference files remain ignored and uncommitted.

**Fixed**
- Fixed the workflow-blocking Contact conversation placeholder. Root cause: the existing Inbox list
  query could not request one exact public Contact. The query now resolves that id tenant-scoped and
  reuses the existing message authority; malformed, unknown, and foreign identifiers are covered by
  API regression tests.
- Fixed Contact tag mutation controls being exposed to read-only users. Root cause: the section did
  not apply the existing `contacts:write` permission to its action controls. It now renders an
  explicit read-only state with focused regression coverage.
- Removed attribute-derived Vi implications and the AI context placeholder from Customer 360;
  persisted source facts and honest empty states now define the workspace.
- Fixed the production owner journey asserting the superseded KYC, SIM, and AI placeholder tabs.
  Root cause: the release proof had not advanced with the converged information architecture. It now
  requires Vi operations, Conversations, Tasks, Documents and Audit and asserts the placeholder is
  absent; the rebuilt deployed journey passes.

**Validated**
- Focused backend API tests pass 21/21 and the focused Customer 360 frontend regression passes 5/5.
  Canonical suites pass 945/945 pytest and 651/651 Vitest with Ruff, strict mypy across 253 files,
  OpenAPI drift, TypeScript/ESLint, build, security scans, SBOMs, image contracts and MySQL/Redis/
  Celery health. The corrected production owner journey passes 1/1 in 11.1 seconds; desktop/tablet/
  mobile review found no overflow or console error, and the 30-read canary records p95 10.4 ms.

### 2026-08-02 — Lightweight Reactivation CRM correction (CORE-05)

**Added**
- Replaced the planned heavyweight SIM fulfilment direction with the owner-approved single-case CRM:
  exactly one of nine primary statuses, six multi-select labels, Follow-up/Release date controls,
  assignment, notes, premium chips, due counters, and status/label/assignee/date filters.
- Added Task-backed Follow-up and Name Change reminders with Upcoming, Due Today and Overdue
  projection, shared Complete/Reschedule/Snooze actions, assigned-user due evidence, optimistic
  concurrency, RBAC, tenant isolation, Audit and Customer Timeline.
- Added additive migration `0034_reactivation_crm`, the Task Snooze path, OpenAPI 3.1.0 at 189
  paths, generated TypeScript contracts, ADR-0017, Design Document 30, and focused regression tests.

**Reused and preserved**
- Extended the existing Reactivation model/repository/service/API/workspace, Task lifecycle and work
  queue, Contact/User authorities, Celery, Audit, Customer Timeline, RBAC, and shared UI primitives.
  CORE-02/04 KYC, SIM, Activation, document, SLA and approval foundations remain intact.
- Added no parallel reminder/notification store, fake count/card, local-only workflow, copied
  reference content, standalone SIM/Activation workspace, or duplicate completed module.

**Fixed**
- Fixed stale Follow-up/Release dates being submitted after their labels were removed; root cause
  was unconditional drawer serialization. Dates now serialize only with their governing label and
  focused UI/contract tests protect the rule.
- Fixed shared Complete and Reschedule UI actions omitting `row_version`; root cause was an optional
  client parameter left unused. All reminder mutation actions now send the current version.
- Fixed Not Required being closable without a server-enforced disposition reason; the service now
  fails closed, matching the accessible confirmation UI.
- Fixed timezone-aware workflow dates reaching persistence without normalization; the request
  boundary now converts them to naive UTC before transactional Task composition.
- Fixed owner-only case updates leaving open reminders assigned to the previous staff member; the
  root cause was reminder synchronization being conditional on a labels payload. Owner/date/label
  changes now all reconcile through TaskService, with a focused assignment regression test.
- Fixed `0034` downgrade failing when real post-upgrade stage events used the corrected status
  vocabulary; the rollback now translates both current cases and event rows before restoring legacy
  constraints, and the migration roundtrip test inserts representative new-vocabulary evidence.

**Validated**
- Focused backend Reactivation/API/KYC regression tests pass 11/11; focused Reactivation/Tasks/KYC
  frontend tests pass 25/25. The canonical 22-step deployed profile passes 943/943 pytest and
  646/646 Vitest, Ruff, strict mypy across 253 files, OpenAPI drift, TypeScript/ESLint, production
  build, Python compile, Bandit, dependency/source/image scans, SBOMs, Compose/image contracts,
  MySQL migration `0034`, healthy Redis/Celery, and Playwright 1/1 in 11.338 seconds.
- Four paired approved reference workflows were reviewed for filter density, label chips, staff
  selection, form/modal hierarchy, and responsive collapse. Original components, tokens, icons,
  wording and breakpoints are retained; `.reference/aisensy/` remains ignored and uncommitted. The
  deployed 30-read canary records p50 10.168 ms and p95 17.761 ms (<300 ms).

### 2026-08-02 — Governed KYC operations (CORE-04)

**Added**
- Added the real tenant-scoped KYC operations projection and responsive queue/detail workspace over
  the existing CORE-02 KYC authority, with holder, Delhi-presence and active-number verification,
  factual progress/SLA, and truthful loading, empty, error, permission and read-only states.
- Added verified Aadhaar/PAN checklist references to existing protected Document Center records;
  the KYC schema, API, UI, audit evidence and migration store no identity numbers.
- Added idempotent Task-backed appointment creation and reused existing Task commands for
  reschedule, completion and cancellation with immutable Task/Customer Timeline evidence.
- Added structured rejection reasons, enforced requester/reviewer/manager separation, immutable
  decisions, optimistic concurrency, manager-approved Reactivation handoff, Customer 360
  projection, ADR-0016, Design Document 29, and focused backend/frontend tests.
- Added migration `0033_kyc_operations`; regenerated OpenAPI 3.1.0 at 188 paths and generated
  TypeScript contracts.

**Reused and preserved**
- Extended existing KYC, Reactivation, Contact, User, Document Center, Task, Customer 360, Audit,
  Customer Timeline, RBAC, SLA, shared form/table/drawer/status/state, and generated-client
  implementations in place. No completed module or parallel authority was rebuilt.
- Added no mock operational data, plaintext Aadhaar/PAN number, independent document store,
  appointment table, approval engine, timeline, SIM fulfilment, copied reference material, or
  tracked `.reference/aisensy/` content.

**Validated**
- The canonical 22-step deployed profile passed: 940 pytest tests, 646 Vitest tests, Ruff, strict
  mypy across 252 files, OpenAPI drift, TypeScript/ESLint, production build, Python compile,
  Bandit, dependency/source/image scans, SBOMs, Compose/image contracts, MySQL migration `0033`,
  healthy Redis/Celery services, and Playwright 1/1 in 8.635 seconds.
- Four paired approved full/viewport references were reviewed for queue density, filters,
  form/action hierarchy and responsive drawer behavior. Component tests pass accessibility and
  responsive transformations; authenticated representative-data live review remains target-host
  validation. The deployed 30-read performance canary recorded p95 12.551 ms (<300 ms).

### 2026-08-02 — Governed Reactivation pipeline (CORE-03)

**Added**
- Added a real tenant-scoped pipeline projection with factual fifteen-stage counts, joined contact
  and owner identity, eligibility/rejection evidence, task/document aggregates, reservation and
  family-plan facts, conversion indicators, SLA status, and server-published permitted moves.
- Added two permission-scoped API paths for the pipeline projection and immutable internal case
  notes; regenerated OpenAPI 3.1.0 at 184 paths and the TypeScript contract.
- Added pointer drag/drop, keyboard stage movement, responsive board/list views, assignment and
  number editing, immutable history/notes, Tasks/Documents reuse, Customer 360 links, truthful
  loading/empty/error/permission states, ADR-0015, Design Document 28, and focused tests.

**Reused and preserved**
- Extended the existing Reactivation route, CORE-02 Vi repository/service/API authority, Contact and
  User records, governed Documents, Tasks/reminders, Customer 360, RBAC, Audit, Customer Timeline,
  SLA, shared Modal, and premium responsive shell; no completed module or parallel authority was
  rebuilt.
- Added no migration, mock lead card, fake count, local-only workflow state, KYC operations UI,
  copied reference code/asset/branding, or tracked `.reference/aisensy/` content.

**Validated**
- Canonical release and isolated deployed profiles passed all 22 applicable steps: 938 pytest tests,
  641 Vitest tests, Ruff, strict mypy across 252 files, OpenAPI drift, TypeScript/ESLint, production
  build, security/dependency/source/image scans, SBOMs, Compose/image contracts, MySQL/Redis/Celery,
  and Playwright 1/1.
- Authenticated reference review passed at 1280×720, 768×1024, and 390×844 without page-level
  horizontal overflow; the deployed 30-read performance canary recorded p95 8.547 ms (<300 ms).

### 2026-08-02 — Vi domain foundation (CORE-02)

**Added**
- Added the ten approved tenant-scoped Reactivation, eligibility, KYC, SIM, Activation, and SLA
  records with immutable decision/event evidence, strong constraints, transition prerequisites,
  optimistic concurrency, UUID idempotency, and explicit approval boundaries.
- Added repository/service/schema layers and 29 permission-scoped lifecycle API paths; regenerated
  OpenAPI 3.1.0 at 182 paths and the TypeScript contract.
- Added fifteen additive RBAC permissions, seven durable business-event types, audit and Customer
  Timeline projections, ADR-0014, Design Document 27, and focused domain/API/migration tests.
- Added migration `0032_vi_domain_foundation` from the unchanged `0031` head.

**Preserved**
- Reused contacts, configurable lead pipelines, governed documents, tasks, audit, Customer
  Timeline, durable business events, automation receipts, and runtime RBAC as existing authorities.
- Added no Reactivation Kanban, KYC workspace, SIM fulfilment UI, Activation Queue, fake operational
  data, placeholder workflow, duplicate module, parallel event bus, or migration downgrade.

**Validated**
- Canonical pre-merge and release profiles passed: 936 pytest tests, 636 Vitest tests, Ruff, strict
  mypy across 252 source files, OpenAPI drift, ESLint, frontend/browser TypeScript, production build,
  Bandit, dependency audits, Trivy source/image scans, SBOMs, Compose and image contracts.
- SQLite migration upgrade/downgrade/re-upgrade passed. The isolated ten-service MySQL/Redis/Celery
  deployment applied `0032`, passed Playwright, and recorded p95 16.5 ms across 30 reads.

### 2026-08-02 — Governed premium product shell (CORE-01)

**Added**
- Accepted ADR-0013 and Design Document 26 for the canonical permission-aware navigation catalogue,
  reference comparison, originality boundary, responsive behavior, and accessibility evidence.
- Added a permanent runtime/test guard against excluded Ads, Payments, Billing, marketplace,
  SaaS/multi-project, public-signup/reseller, and commerce navigation concepts.
- Added honest `Foundation` and `Future` maturity labels and one shared permission-scoped quick-create
  catalogue for the top bar and command palette.

**Changed**
- Finalized the original Vi Reactivation dark-green desktop rail, grouped More surface, mobile task
  bar/drawer, active states, shared command palette, and dismissible create/account menus.
- Added dialog focus trapping/restoration, Escape behavior, live search-result announcements,
  explicit ARIA state, 44px mobile targets, and mobile More state for overflow destinations.
- Removed two incidental Billing references from user-facing administrative copy without changing
  API-key or role behavior.

**Preserved**
- The existing six-item primary order, all completed routes/modules, backend architecture, product
  scope, module percentages, permissions, OpenAPI 3.1.0 at 153 paths, and migration head `0031`.
- `.reference/aisensy/` remains ignored and untracked; no proprietary code, asset, branding, exact
  icon, exact color, wording, typography, screenshot, or pixel value was copied or shipped.

**Validated**
- Passed canonical static checks, Ruff, strict mypy, OpenAPI drift, frontend/Playwright TypeScript,
  ESLint, Python compile, migration head, generated-contract drift, 932 pytest tests, 636 Vitest
  tests, production build, Bandit, and dependency audits.
- Passed 30 focused navigation/foundation tests and authenticated 1280×720 browser comparison for
  the compact rail, More, command palette, factual error states, and horizontal-overflow boundary.
- Docker-backed Trivy/release/deployed reruns remain `PENDING – Host Machine Validation` because the
  Docker Desktop daemon was unavailable; prior successful deployed evidence remains preserved.

### 2026-08-02 — Premium AiSensy-parity product goal lock (GOV-02)

**Added**
- Accepted ADR-0012, permanently setting an original private enterprise-grade WhatsApp Business
  Platform for the Vi Reactivation Team as the product target, with functionality and premium
  presentation as equal acceptance requirements.
- Added Design Document 25 with experience principles, the fourteen-step approved-reference review,
  shared enterprise component catalogue, truthful state rules, responsive/accessibility acceptance,
  and the twenty-point premium screen Definition of Done.
- Recorded the permanent priority order, no-placeholder rule, original-implementation boundary, and
  bounded continuous-quality policy across the scope and governance ledgers.

**Changed**
- Synchronized the scope, rules, README, project state, implementation tracker, gap analysis, module
  status, roadmap, validation ledger, and changelog for the owner-approved GOV-02 documentation
  milestone.
- Clarified that GitHub remains the only implementation source of truth while the owner-approved
  AiSensy archive is a Git-ignored, local-only workflow and visual-quality benchmark that must never
  be staged, committed, bundled, imported, or copied.

**Preserved**
- Product feature scope, roadmap sequence and estimates, module completion percentages, architecture,
  requirements, migrations, OpenAPI, permissions, tests, and runtime behavior are unchanged.
- Ads Manager, Meta Ads, WhatsApp Payments, payment processing, billing/subscriptions/trials/upgrades,
  public signup, reseller/multi-project, marketplace, catalog, cart, checkout, orders, refunds, and
  commerce remain excluded. AI and Automation references remain milestone-gated.

**Validated**
- Passed GOV-02 Markdown structure/link, required-file/content, governance-consistency, changed-file,
  reference-ignore, exclusion, migration-invariance, and OpenAPI-invariance checks.
- Application tests were not rerun for this documentation-only milestone; their last successful
  evidence remains preserved in `VALIDATION_RESULTS.md` and `IMPLEMENTATION_TRACKER.md`.

### 2026-08-02 — Governance repository state synchronization

**Changed**
- Recorded owner approval of the completed GOV-01 governance baseline and retained CORE-01 as the
  next milestone requiring a separate owner instruction.
- Recorded migration head `0031`, OpenAPI 3.1.0 with 153 paths, 932 backend tests, 628 frontend
  tests, and the successfully completed repository validation pipeline.
- Removed local ZIP/archive exceptions from the active governance rules and roadmap. GitHub at the
  latest approved HEAD is the only implementation source of truth.

**Preserved**
- No backend, frontend, API, migration, test, architecture, or product behavior changed.
- `CURRENT_PROJECT_GAP_ANALYSIS.md` and `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` remain unchanged.

### 2026-08-02 — Permanent repository governance baseline (GOV-01)

**Added**
- Added root `PROJECT_STATE.md`, `VALIDATION_RESULTS.md`, `MODULE_STATUS.md`,
  `REPOSITORY_RULES.md`, and the canonical final-scope `ROADMAP.md` without overwriting the existing
  historical roadmap.
- Added a synchronized milestone closeout model covering Git state, migration/OpenAPI/test evidence,
  module completion, validation truth, one-milestone-per-commit discipline, and owner approval.
- Registered the explicitly supplied 73-state AiSensy capture set as permitted UI/workflow reference
  material while keeping ads, payments, billing, marketplaces, SaaS, and other scope exclusions out
  of the product roadmap.

**Preserved**
- `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` and `CURRENT_PROJECT_GAP_ANALYSIS.md` remain unchanged and
  retain product-intent and remaining-work authority.
- No backend, frontend, migration, API, queue, provider, permission, or runtime behavior changed.

**Validated**
- Verified branch `feature/module6-queue-engine` at `a8479e7`, migration head `0031`, OpenAPI 3.1.0
  with 153 paths and no export drift, 932 collected backend tests, and 628 enumerated frontend tests.
- Passed the repository static quality profile: Ruff, strict mypy across 247 files, OpenAPI drift,
  ESLint, frontend TypeScript, and Playwright TypeScript; the governance updater also compiles and
  passes focused Ruff validation.
- The last completed engineering milestone remains PAR-AUTO-03 with its recorded full release and
  deployed validation evidence. GOV-01 is documentation/governance only and was subsequently
  approved on 2026-08-02.

### 2026-07-30 — Durable automation trigger receipts (MD5 Phase 2C)

**Added**
- Added the governed `contact.created` event type, append-only business-event ledger, and migration
  `0031` with MySQL time partitioning and a reversible SQLite test path.
- Added atomic event publication from the existing API/import and system conversation contact paths.
  Only enabled, clean published flows with the matching immutable trigger receive a tenant-scoped,
  replay-safe receipt.
- Added the permission-scoped receipt history route, generated TypeScript contract, and a compact
  builder panel that labels real matches as evidence and explicitly states no action executed.

**Preserved**
- No receipt starts a run or applies a task, tag, assignment, notification, webhook, campaign,
  provider, approval, handoff, send, AI, Forms or commerce effect. Existing contact validation,
  permissions, audit, import queueing and transaction ownership remain unchanged.

**Validated**
- Passed 932 backend tests, Ruff, strict mypy across 247 files, OpenAPI drift validation, 628
  frontend tests, TypeScript, ESLint and production builds. Rebuilt production images expose 153
  paths and register the unchanged 24 Celery tasks. The complete deployed profile passed SAST,
  dependency/source/image scans, SBOM generation, MySQL migration, API/worker/queue health, real
  queued-import trigger receipt evidence, readiness/observability checks and a 19.002 ms p95 canary.

### 2026-07-30 — Deterministic automation test runtime (MD5 Phase 2B)

**Added**
- Added tenant-scoped immutable-version test runs, step-attempt evidence, durable UUID idempotency,
  deterministic DAG execution, checkpoint/resume, and migration `0030`.
- Added the `automation.run` Jobs-pool route and tracked Celery task using the existing job,
  retry and DLQ authorities; no new queue framework was introduced.
- Added three permission-scoped OpenAPI routes, generated frontend contracts, safe test submission,
  polling, recent run history and ordered attempt evidence in the existing automation builder.

**Fixed**
- Replaced the test-run UI's secure-origin-only `crypto.randomUUID()` assumption with UUID v4
  generation backed by `crypto.getRandomValues()`. The isolated HTTP production gate now submits
  and completes the real queued test run; a focused regression test covers the portable key path.

**Preserved**
- Test mode simulates every action. No live event or schedule, delay/wait, CRM/task/tag/assignment
  mutation, provider/webhook/campaign call, approval/handoff, send, AI, Forms or commerce behavior
  was introduced. Existing API, schema, permission and business behavior is otherwise unchanged.

**Validated**
- Passed 928 backend tests, Ruff, strict mypy across 242 files, OpenAPI drift validation, 627
  frontend tests, TypeScript, ESLint and production builds. The rebuilt backend exposes 152 paths
  and registers 24 tasks. The complete release and deployed profiles passed image contracts,
  SAST/dependency/source/image scans, SBOM generation, migration, API/worker/queue health, a real
  browser safe test run, readiness degradation, observability checks and an 18.423 ms p95 canary.

### 2026-07-30 — Versioned automation definitions (MD5 Phase 2A)

**Added**
- Added tenant-scoped automation drafts, bounded typed graphs, fail-closed semantic validation,
  immutable content-addressed published versions, restore/enable/disable controls, optimistic
  concurrency, audit events and migration `0029`.
- Added least-privilege `automations:read`, `automations:write` and `automations:publish` permissions,
  eight OpenAPI paths, regenerated TypeScript contracts, and a searchable versioned authoring
  workspace. Execution remains visibly unavailable until the governed runtime milestone.

**Fixed**
- Prevented the compact sidebar's advanced-navigation panel from opening over active advanced
  routes and intercepting workspace clicks.
- Kept the successful draft-save confirmation visible when refreshed server state synchronizes
  back into the builder.

**Preserved**
- No automation task, trigger, schedule, provider call, outbound webhook, CRM mutation, campaign
  dispatch or customer message was introduced. Existing API behavior, send authority, queue routing,
  Meta adapter, tenant isolation and business rules remain unchanged.

**Validated**
- Passed 921 backend tests, Ruff, strict mypy across 237 files, OpenAPI drift validation, 625
  frontend tests, TypeScript, ESLint and production builds. The production backend retains 23
  registered tasks and now exposes 149 paths. Rebuilt and contract-checked production images; the
  isolated ten-service deployment passed migration, API/worker/queue health, real browser
  create/save/publish, readiness degradation, log redaction and a 25.9 ms p95 read canary.

### 2026-07-30 — Campaign follow-up and chat-link acquisition

**Added**
- Added a clear `Create follow-up` action for completed campaigns. It composes the source definition
  into a fresh, distinctly named draft and preserves the existing audience, editing, scheduling,
  approval and dispatch authorities.
- Added a phone-number-level WhatsApp chat-link utility with an optional prefilled message, local QR
  generation, copy/test actions and a downloadable PNG. The QR encoder is loaded only when the
  dialog opens; no phone number, message or link is sent to a QR service.

**Preserved**
- No backend API, schema, permission, tenant-isolation, campaign dispatch, queue or Meta adapter
  behavior changed. Links are not shortened or tracked, and carousel support remains hidden because
  its end-to-end template/send contract does not exist.

**Validated**
- Passed all 621 frontend tests, ESLint, TypeScript and the production build. The production-only
  dependency audit remains at the two known moderate React Router advisories with no high/critical
  finding. Rebuilt the production frontend image, passed its nginx contract, recreated the container
  healthy, and returned HTTP 200 for the number-detail route with the current bundle. MD5 Phase 1
  repository implementation is release ready; task-time baselines remain target UAT evidence.

### 2026-07-30 — Audience and retargeting presets

**Added**
- Added four marketer-friendly audience templates—recently engaged, needs reactivation, new
  contacts and WhatsApp active—using only the existing segment rule grammar.
- Added one-click quick audiences in the campaign audience step when matching saved segments
  actually exist. Presets still open the normal segment editor for review and use the existing
  create endpoint, live campaign resolution, consent filtering and approval journey.

**Preserved**
- No API, schema, permission, tenant-isolation, campaign dispatch or queue behavior changed.
- Campaign-specific read/click/failed retargeting is not inferred from the recipient UI's partial
  page; it remains unavailable until a complete audience contract is separately approved.

**Validated**
- Passed all 617 frontend tests, ESLint, TypeScript and the production build. Rebuilt the production
  frontend image, passed its nginx image contract, recreated the frontend container healthy, and
  returned HTTP 200 for `/segments` with the current bundle.

### 2026-07-30 — Payment and commerce scope removal

**Changed**
- Recorded the owner's explicit decision that payments, transaction processing, product catalogs,
  carts, checkout, orders, refunds and commerce journeys are not product roadmap deliverables.
- Replaced the five-phase plan's former payment/commerce phase with advanced analytics, reporting
  and team operations.
- Removed the non-functional Payments placeholder from Customer 360, leaving 12 contract-relevant
  sections. No backend API, schema, permission or business behavior changed.

**Validated**
- Passed the focused Customer 360 regression, all 612 frontend tests, ESLint, TypeScript and the
  production build. Rebuilt the frontend image, passed its nginx image contract, recreated the
  frontend container healthy, and returned HTTP 200 for the Customer 360 route with the new bundle.

### 2026-07-30 — Five-phase parity execution plan

**Added**
- Added Design Document 21, a five-phase path from the verified repository baseline to an
  AiSensy-comparable but original product: simplicity/retargeting, automation/forms, ads,
  analytics/team operations, and governed AI/integrations.
- Defined the required data, API, permission, audit, failure-recovery and quality gates for every
  phase so genuine gaps cannot be presented as implemented UI.

### 2026-07-30 — Live Chat simplicity

**Changed**
- Replaced the crowded inbox folder strip with three task-first views: Requests (open and
  unassigned), Active (all open), and My chats (assigned to the current user). These use the
  existing status and assignment contracts and do not simulate chatbot or handoff state.
- Moved status, assignee, label and saved-view management behind one advanced Filters control while
  keeping search and saved inboxes immediately available.
- Simplified conversation rows around customer identity, message preview, unread urgency and aged
  waits; preserved status, service-window, labels, pinning and bulk selection.
- Reduced permanent thread chrome to status and assignment. Customer context, editable labels,
  notes, governed AI assistance, pinning and Customer 360 now open through the Details panel.
  APIs, permissions, schemas, tenant rules and message behavior are unchanged.

**Validated**
- Passed 612 frontend tests, ESLint, TypeScript and the production build. Rebuilt the production
  frontend image, passed its nginx image contract, recreated the frontend container healthy, and
  returned HTTP 200 for `/inbox` with the new production bundle.

### 2026-07-30 — Guided campaign journey

**Changed**
- Replaced the horizontally scrolling campaign step tabs with a compact progress rail that fits the
  full Audience → Template → Preview → Schedule → Approval → Confirmation journey and preserves
  completed-step navigation.
- Added consistent step context, larger accessible controls, audience and delivery choice cards,
  customer-facing message previews, a compact final review, and clearer sticky actions across create,
  duplicate, and edit flows.
- Kept the existing AI planning foundation available as an optional collapsed section so the default
  campaign journey stays focused. Campaign APIs, permissions, schedules, approval checkpoint,
  validation, dispatch authority, and business behavior are unchanged.

**Validated**
- Passed 610 frontend tests, ESLint, TypeScript, the production build, the frontend image contract,
  container health, and a direct production-route smoke check for `/campaigns/new`.

### 2026-07-30 — Simplified customer workspace

**Added**
- Added the active AiSensy-inspired parity roadmap, separating verified product coverage from
  genuine automation, forms, ads, AI-agent and integration contract work while explicitly
  excluding payments and commerce.

**Changed**
- Made the six-destination desktop task rail compact by default, with one permission-aware `More`
  flyout for every entitled advanced route. Users can still expand the rail and the preference is
  retained without changing routes or permissions.
- Replaced the generic purple accent with an original teal engagement palette. No competitor
  branding, assets, code, or unsupported capability claims were introduced.
- Reduced the default sidebar from the full module catalog to six task-first destinations; all
  entitled advanced, operational, and administrative areas remain available through one expanded
  `More` section and workspace search.
- Renamed the existing inbox destination to `Live Chat` in navigation, removed duplicate favorite
  links, moved theme and shortcut help into the account menu, and aligned desktop/mobile order.
- Replaced the chart-heavy executive home with a compact task-first dashboard: four operational
  indicators, two primary actions, the existing personal work queue, and setup steps. Redundant
  quick-access and recent-route cards were removed; empty task buckets use the compact state so
  mobile users do not scroll through oversized blanks.
- Added a setup-first WhatsApp overview derived only from the existing WABA and phone-number
  contracts: connection readiness, quality, send capacity, default identity, and three governed
  setup steps. Unsupported subscription, credit, quota, mobile-app, and advertising claims are
  deliberately absent.

**Fixed**
- Replaced the dashboard's dead `/settings/whatsapp` onboarding destination with the existing
  permission-governed account and number routes. APIs, permissions, schemas, and channel behavior
  are unchanged.

**Validated**
- Passed 608 frontend tests, ESLint, TypeScript, and the production build. Rebuilt the production
  frontend image and passed its nginx runtime contract. The isolated ten-service gate verified an
  authenticated browser journey, API/workers/queues/dependency health, cleanup, and a 22.7 ms p95
  across 30 reads (<300 ms). The live shell audit at 1440 × 900 and 390 × 844 found no horizontal
  overflow; the compact rail, expandable preference, mobile navigation, and advanced `More` panel
  remain usable against the production container.

### 2026-07-30 — Phase 4A governed customer documents

**Added**
- Added tenant-scoped customer document records with immutable media-backed versions, human
  verification/rejection, explicit expiry, archive, signed previews, audit history, customer
  timeline projection, optimistic concurrency, and migration `0028`.
- Added least-privilege `documents:read`, `documents:write`, and `documents:verify` permissions and
  one shared premium document workspace for Customer 360 and Reactivation.
- Added generated 141-path OpenAPI/TypeScript contracts, 10 backend API regressions, and 5 frontend
  workflow regressions.

**Fixed**
- Updated the production backend image contract from the stale 133-path assertion to the verified
  141-path contract. The failure was limited to release evidence; application APIs and behavior
  were already correct and remain unchanged. Regression coverage now pins the image assertion.

**Validated**
- Passed 912 backend and 600 frontend tests, Ruff, strict mypy, ESLint, TypeScript, OpenAPI drift,
  dependency/source/image security gates, production builds, image contracts/SBOMs, and the
  isolated API/worker/queue/browser smoke gate (30-read p95 19.4 ms, budget <300 ms).

### 2026-07-25 — Phase 3 reactivation platform and automation foundations

**Added**
- Added the complete Reactivation workspace navigation: eligible numbers, bulk eligibility,
  interested customers, customer pipeline, KYC, Document Center, SIM orders, Activation Queue,
  completed cases, and reports.
- Added an honest reactivation pipeline blueprint over the existing pipeline/stage authority,
  a real media-backed Document Center, real analytics-backed reports, and the complete 13-tab
  Customer 360 information architecture.
- Added a separate Scan Studio adapter/queue boundary and an accessible visual automation
  blueprint builder with trigger, condition, internal-action, delay, tag, assignment, wait,
  webhook, campaign, notification, and mandatory human-approval nodes.
- Added focused Phase 3 boundary tests and extended the isolated production browser journey
  through Reactivation, Automation, Scan Studio, and a 390 × 844 responsive check.

**Changed**
- Reactivation, Automation, and Scan Studio are route-split production chunks; the main bundle
  decreased from the Phase 2 baseline despite the new UI surfaces.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, Celery/task behavior,
  provider behavior, and business rules remain unchanged. Missing document/KYC/SIM/scan/
  automation-runtime contracts are shown as disabled, explicit boundaries rather than simulated data.

### 2026-07-25 — Phase 2 customer engagement platform

**Added**
- Added server-synchronized custom inboxes and pins, quick folders, teammate mention insertion,
  customer/notes/AI context, expanded bulk actions, and explicit contract-gated merge/timed-snooze states.
- Added a dedicated Broadcast Center over the existing campaign engine, template favorites, segment
  recents, factual engagement funnel, analytics dashboard navigation/export center, and Phase 2 AI seams.
- Added the Phase 2 realization record, updated research feature matrix, and focused architecture-
  boundary regression coverage.

**Changed**
- Extended the campaign journey through Confirmation and the post-launch Analytics destination, and
  upgraded Customer 360, Template Center, Segments, and Analytics entry points.
- Extended the isolated production browser journey through Broadcast Center, Analytics, the factual
  engagement funnel, and a 390 × 844 no-horizontal-overflow check.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, queue behavior, provider
  behavior, and business rules remain unchanged.

### 2026-07-25 — Phase 1 enterprise product transformation

**Added**
- Added a business-first premium shell with responsive navigation, command palette, cross-module
  search, favorites, recents, quick-create actions, keyboard shortcuts, and live attention signals.
- Added customer-360 context, inbox saved views/pins/bulk actions and unread-wait SLA signals, an
  approval-ready campaign journey, Operations control center, permission catalog, and honest
  Automation/Reactivation foundations.
- Added Phase 1 architecture-boundary regression coverage and the verified transformation record in
  `docs/design/16-PHASE-1-ENTERPRISE-PRODUCT-TRANSFORMATION.md`.

**Changed**
- Reorganized navigation around business workflows and upgraded dashboard, sign-in, contacts,
  customer profile, inbox, campaigns, Operations, Administration, Tasks, and Analytics presentation.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, queue behavior, Celery task
  registration, provider behavior, and business rules are unchanged.

### 2026-07-25 — Module 11 defensive observability contracts

**Added**
- Added canonical structured `http_request` events with request-id, method, path, status, and
  duration fields. Safe bounded client correlation ids are preserved across nginx and the API;
  unsafe values are replaced.
- Added formatter-boundary redaction for sensitive fields and recognizable credentials, email
  addresses, and international phone numbers in both JSON and text logs. ADR-0007 records the
  repository-versus-environment observability boundary.
- Extended the isolated deployed gate to prove edge and API runtime logs share correlation ids,
  contain none of its synthetic secret/PII values, and report Redis down with a 503 from `/ready`
  after that dependency is stopped.

**Changed**
- Disabled the duplicate uncorrelated Uvicorn access record; application middleware is now the
  canonical API access logger. The release contract also syntax-checks the actual mounted edge
  configuration with the digest-pinned production nginx image.
- API routes, response contracts, permissions, tenant scope, business behavior, and schema are
  unchanged.

### 2026-07-25 — Module 11 deployed-stack E2E and performance canary

**Added**
- Added the cumulative `deployed` quality profile. It starts the unchanged ten-service production
  topology under a unique Compose project with synthetic secrets and disposable volumes, bootstraps
  an Owner through the existing CLI, captures evidence, and guarantees project-scoped cleanup.
- Added a digest-pinned Playwright 1.61.1 Chromium runner and one focused real-UI journey: login →
  Contacts → CSV upload/mapping → queued import → persisted contact search/profile. This exercises
  nginx, the SPA, API, MySQL, Redis broker, and jobs worker without a provider or customer send.
- Added a 30-sample authenticated standard-read canary using nearest-rank p95 and the frozen <300 ms
  target; the first isolated run passed at 7.9 ms. ADR-0006 records the boundary from full load tests.

**Changed**
- Pinned the production MySQL 8.0 image by immutable manifest digest. The release contract now
  rejects unpinned third-party service images as well as unpinned application Dockerfile stages.
- Corrected the deployment smoke runbook to use the existing Contacts import UI instead of referring
  to a nonexistent direct-create control; APIs, permissions, routing, and product behavior are unchanged.

### 2026-07-25 — Module 11 security and release-gate automation

**Added**
- Added cumulative, provider-neutral `static`, `pre-merge`, and `release` quality profiles covering
  Ruff, strict mypy, OpenAPI drift, frontend lint/types, both full test suites, production build,
  Bandit SAST, dependency audits, tracked-source vulnerability/secret/IaC scanning, Compose/image
  contracts, production image scans, smoke checks, and CycloneDX SBOM evidence.
- Added deterministic tests for fail-fast orchestration, tracked-only scanner snapshots, Compose
  invariants, synthetic secret handling, and non-root/health image metadata. ADR-0005 records the
  gate boundaries and scanner pin.

**Security**
- The first blocking audit found `asyncmy` 0.2.11 affected by critical unpatched SQL injection
  (`GHSA-qhqw-rrw9-25rm`). Replaced only the SQLAlchemy driver boundary with pinned `aiomysql`
  0.3.2 / PyMySQL 1.2.0; application layering, SQLAlchemy repositories, schema, routes, permissions,
  queue behavior, and the 133-path contract are unchanged.
- Production application image tags now fail closed when `IMAGE_TAG` is absent, and the deployment
  template demonstrates the immutable release tag `1.0.0-rc1` instead of `latest`.
- Backend and frontend build/runtime bases, plus the production Redis and edge-nginx images, are
  pinned by immutable manifest digest. The application runtimes use current Alpine layers; both
  rebuilt application images pass the blocking HIGH/CRITICAL scan and emit CycloneDX SBOMs.
- The tracked source snapshot is clean at HIGH/CRITICAL across vulnerability, secret, and IaC
  scanning; backend SAST and production dependency audit are clean. Moderate React Router
  advisories remain visible and require an explicit later v7 migration.

### 2026-07-25 — Module 11 strict typing completion

**Added**
- Added precise SQLAlchemy result/expression types, analytics fact-model unions, callback/iterator
  contracts, JSON container types, and focused invariant tests across repository and service seams.
- Missing linked templates, WABAs, or campaign sending numbers now take explicit existing domain
  outcomes instead of surfacing as attribute errors; malformed internal priority cursors are rejected.

**Changed**
- Eliminated the remaining 120 strict-mypy findings across 45 files. Raw `mypy app` now passes for
  all 227 backend source files under the unchanged strict configuration and pinned mypy 2.3.0.
- Retired the temporary baseline, wrapper, and wrapper tests exactly as ADR-0004 required once the
  direct strict gate became clean. ADR-0004 is retained as a superseded transition record.
- Runtime APIs, routes, permissions, tenant scoping, SQL queries, queue behavior, database schema,
  migrations, and the 133-path OpenAPI contract remain unchanged.

### 2026-07-25 — Module 11 strict-mypy ratchet

**Added**
- Added a deterministic strict-mypy ratchet (`backend/scripts/check_mypy.py`) with a versioned
  baseline and focused tests. New or increased path/error-code allowances fail; reductions mark the
  baseline stale until it is explicitly lowered, and same-version writes cannot raise allowances.
- Added ADR-0004 to record the transitional baseline policy, exact checker-version requirement,
  and removal condition once raw strict mypy is clean.

**Changed**
- Pinned the development checker to mypy 2.3.0 while leaving the repository's strict mypy settings
  unchanged. The backend README now documents both the enforced ratchet and the raw-debt audit.
- Reduced strict findings from 251 across 67 files to 120 across 45 files by typing the existing
  Celery/async task boundary and SQLAlchemy model metadata/JSON containers. Runtime behavior,
  queues, retries, database schema, API routes, permissions, and contracts are unchanged.
- Remaining repository/service findings are retained as explicit Module 11 debt behind the ratchet,
  not suppressed or globally disabled. Count granularity avoids line churn; review remains the
  backstop for a same-code replacement within one file.

### 2026-07-25 — Excel import inspection (FR-CON-04)

**Added**
- Added the permission-gated `POST /api/v1/contacts/import/inspect` contract for workbook headers,
  one sample row, worksheet name, estimated data-row count, and non-mutating header validation.
- The inspection path reuses the importer's existing openpyxl parser and cell rendering, runs its
  synchronous workbook work outside the async request loop, and applies a 25 MB inspection ceiling.
- The contact import wizard now accepts `.xlsx`, uploads it for inspection before mapping, and keeps
  the existing browser parser for CSV. No SheetJS or second workbook parser was introduced.

**Changed**
- ADR-0002 moved from proposed to accepted. Docs 4 §14.1 and 5 B3.3 record the additive inspection
  API; the existing async import endpoint and its request contract are unchanged.
- Recovered the canonical project state from Git and executable gates: synchronized the README,
  implementation tracker, roadmap statuses, and deployment guide with the post-RC1 repository.
- Excluded generated `.pytest-run*` directories from Git and the backend Docker build context; an
  unreadable local pytest directory can no longer block production image packaging.

### 2026-07-23 — Docker deployment validation (first execution of the containerised stack)

The production stack was built and run for the first time. Four defects were reproduced in the
running deployment and fixed; none were visible to static review or to the test suite, because
each only manifests in a worker process or at the edge proxy.

**Fixed**
- **All async background work failed after the first task in each worker process.** Every task
  runs under its own `asyncio.run(...)`, which creates and then closes an event loop, while the
  SQLAlchemy engine and Redis client were cached in module globals. The second task in a process
  inherited a connection pool bound to a closed loop and raised
  `got Future attached to a different loop`. `scheduler_tick` was failing every minute; campaign
  dispatch, webhooks, imports, exports, media and analytics rollups were all dead. The engine and
  the Redis client are now rebuilt when the running loop changes
  (`app/db/session.py`, `app/core/redis.py`).
- **Storage backend unavailable in workers.** `app.storage.local` registers itself on import, and
  the only import lived in `app.main` — which a worker never loads. Every worker-side write failed
  with `storage backend 'local' is not available; registered: ()`. Registration moved into
  `app/storage/__init__.py` so it holds for every process.
- **nginx served 502 after any container recreation.** A statically named `upstream` server is
  resolved once at config load and cached for the process lifetime, so `docker compose up -d` —
  the documented upgrade step — left the edge proxying to the previous container's address.
  Reproduced (nginx held `172.19.0.7` while the API had moved to `172.19.0.6`) and fixed with a
  `resolver` plus request-time resolution; verified by moving the API to a new address and
  observing recovery with no reload. Costs the upstream keepalive pool, which open-source nginx
  cannot combine with re-resolution.
- **Duplicate security headers on `/health` and `/ready`.** The probe locations lacked the
  `proxy_hide_header` set that `/api/` already had, so each probe returned two copies of every
  security header and leaked the API's HSTS over plain HTTP.

**Correction (2026-07-24)** — this entry originally closed with a "Known, not fixed" note about
`ExportService.download_url` signing `export-<uuid>` onto a UUID-typed media route and returning 422.
That defect **was** fixed later the same day, in `c86d11c`, which added
`/api/v1/artifacts/{artifact_id}/download` and made `LocalStorageProvider.signed_url` route by id
shape; the note was simply never removed. Verified on 2026-07-24 against the running stack (the
artifacts route answers 400 for a missing signature rather than 404) and by
`tests/test_api_export.py::test_export_download_url_serves_the_csv`, which downloads a real export
with no `Authorization` header and asserts its bytes. Recorded as `docs/adr/0001`.

---

## [1.0.0-rc1] — 2026-07-23

First release candidate. Everything recorded below this heading is included in the tag
`v1.0.0-rc1`; entries above it are post-RC1 work.

### Added
- **Task & Activity Engine** (Doc 14) — models, migration `0026_tasks`, RBAC scopes, 15 endpoints.
- **Analytics & Reporting** (Doc 15) — migration `0027_analytics`, rollup pipeline, query service,
  report exports, 16 endpoints.
- **Frontend application** — authentication, dashboard, contacts, inbox, campaigns, templates,
  media, WhatsApp accounts, segments, pipelines, tasks, analytics, operations, admin, settings.
- **Production deployment** — multi-stage backend and frontend images, `docker-compose.production.yml`
  (10 services), edge and SPA nginx configuration, `deploy/DEPLOYMENT.md`, `.env.production.example`.
- `LICENSE` (proprietary, matching the terms already declared in `backend/pyproject.toml`).

### Fixed
- **Startup blocker** — `CORS_ORIGINS` was JSON-decoded by pydantic-settings before validators ran,
  so the empty and comma-separated forms both raised `SettingsError` at import. Every backend
  process (api, three worker pools, beat, migrate) failed to start. Now `Annotated[..., NoDecode]`.
- **Celery task registration** — workers imported no task modules, so every pool started with an
  empty registry and rejected all work. `include=TASK_MODULES` now registers all 23 tasks.
- **JSON logging** — the parent `uvicorn` logger held a plain stderr handler with `propagate=False`,
  so request lines never reached the JSON handler despite `LOG_JSON=true`.
- **`list` shadowing in `TaskService`** — a method named `list` shadowed the builtin for annotations
  later in the class body, so those signatures resolved to the method. Harmless at run time under
  deferred annotations, but it broke type resolution and `typing.get_type_hints()`.
- **`_fail` return type** in the segment compiler — annotated `NoReturn`, so the existing
  `if spec is None: _fail(...)` guard narrows as the code already reads.
- **`.gitignore`** — `.env.production.example` was matched by the broad `.env.*` rule and excluded
  from the repository, although `deploy/DEPLOYMENT.md` §2 begins by copying it.

### Changed
- Version aligned to `1.0.0-rc1` across `pyproject.toml` (PEP 440 `1.0.0rc1`), `app/__init__.py`,
  `Settings.app_version`, and `package.json`. `frontend/openapi.json` regenerated — the only
  semantic change is `info.version`.
- Frontend production build emits `sourcemap: "hidden"` and splits framework vendor chunks.

### Known limitations
- **The containerised deployment has never been executed.** No image has been built and no
  container started in any environment available to date. See §Remaining Blockers in the RC1
  report and `deploy/DEPLOYMENT.md`, which is written as a commissioning procedure.
- `tests/test_analytics_rollup.py` hard-codes `NOW = 2026-07-23 14:30`; two tests fail when real
  UTC falls inside the derived `[08:00, 14:00)` window on that date. Fixture defect, not a product
  defect.

---

### 2026-07-18 — Amendment: Message Reactions (Doc 7 → v1.1, Doc 4 v1.3 → v1.4, Doc 3 v1.3 → v1.4) — **FROZEN**
**Reason:** Phase 7 Step 9 (Message Reactions) was **blocked by a frozen-doc conflict.** Doc 4 §18.2
defines `POST /messages/{uuid}/reaction` (send a reaction), but Doc 7 §5.2's Meta capability column
declared `text/media/interactive/template/bulk` only — reaction was **deliberately undeclared** (the
Meta adapter surfaces `ChannelNotSupported`), so no channel could fulfil the endpoint. The canonical
seam (`MessageType`) and SendService likewise had no reaction path.

**Decision (owner):** amend additively so reaction is **adapter-capability-driven**; the Meta adapter
declares it (Meta Cloud API supports outbound reactions). Invent no behaviour beyond the frozen contract.

**Changed — Doc 7 (Integrations & Channel Architecture) → v1.1**
- **New §5.2a** — the Meta adapter additionally declares `send_reaction` (capability-flagged); the §5.2
  baseline matrix is unedited. Decision **CD20** (reaction is adapter-declared, not assumed).

**Changed — Doc 4 (API Design) v1.3 → v1.4**
- **§18.2** — appended the full `POST /messages/{uuid}/reaction` contract: `{emoji}` payload (empty =
  remove), single-emoji validation (`invalid_emoji`), `Idempotency-Key` required, `messages:send`, the
  24-hour free-form window rule (`window_closed`), `not_reactable`/`opt_out`, the `202` accept→deliver
  flow through SendService→Meta adapter, and failure handling. §18.2 table row unedited.

**Changed — Doc 3 (Database Design) v1.3 → v1.4**
- **New §9.2a** — confirms reaction storage: `message_type='reaction'` (already enumerated) + the
  `content_json` reaction format `{reaction:{message_id:<target wamid>, emoji}}`, target referenced by
  the target's `wamid`. **No new column, no migration.** §9.2 schema unedited.

**Decision records added:** Doc 7 **CD20**.
**Compatibility:** additive only — no schema/migration, no code (implementation follows on approval).
Docs 1, 2, 5, 6, 8–12 unedited.

### 2026-07-18 — Amendment (backfill log): Conversation Tags (FR-INB-07) — Doc 3 v1.2 → v1.3, Doc 4 v1.1 → v1.3 — **FROZEN**
**Backfilled.** The conversation-tags amendment shipped in commit `4ec1c34` with in-document `v1.3`
markers but was not logged here at the time; governance (top of file) requires every frozen-doc change
be recorded, so it is logged now.
**Changed — Doc 3:** new **§9.7 `conversation_tags`** (M:N junction reusing the `tags` taxonomy) + §12.3
M:N row, §13.2 reverse-index row, §19 sizing row. **Changed — Doc 4:** **§18.1** conversation-tag
endpoints (`POST`/`DELETE /conversations/{uuid}/tags`), the additive `tags[]` array on list/detail
reads, and the single-valued `tag` filter.
**Compatibility:** additive; realized by migration `0025_conversation_tags` (Phase 7 Step 5, HEAD
`16c65e2`). The Doc 4 marker used `v1.3` in lockstep with Doc 3 (Doc 4 `v1.2` is unused).

### 2026-07-17 — Amendment: FR-CAM-11 rate card & cost estimation (Doc 3 → v1.2, Doc 4 → v1.1) — **FROZEN**
**Reason:** Phase 6 Step 5 (Cost Engine) was **blocked**. The frozen set defined the cost engine's
*consumers* (`campaigns.estimated_cost`, `messages.cost_*`, `pricing_model`, `is_billable`) but never
its *source*: no rate-card entity or schema existed in Doc 3, Doc 7 contained no pricing content, and
Doc 12 §53 places Meta's pricing under "External … not restated here". Doc 4 §17 specified
`estimate-cost` by sample response only, with a bare `422` and no machine code. Gap analysis:
`docs/design/FR-CAM-11-GAP-ANALYSIS.md`.

**Decision (owner):** amend with the **minimum** required to unblock **pre-send estimation only**.
Invent no pricing data and no billing semantics.

**Changed — Doc 3 (Database Design) v1.1 → v1.2**
- **New §8.5 `rate_cards`** — entity, storage model, schema, resolution & money rules, country
  resolution, and an explicit deferred list. Global (no `organization_id`, per Doc 4 §17's "no
  reseller markup"), operator-managed, **ships empty**, versioned by effective dating (supersede,
  never mutate).
- **New §12.4a** — `rate_cards` value joins (no FK to contacts/templates/campaigns) + tenancy note.
- **§12.2** — `users` → `rate_cards` (`created_by`), the card's only FK.
- **§13.2** — rate-card lookup + uniqueness indexes.
- **§16 entity map** — Rate Card row added.

**Changed — Doc 4 (API Design) v1.0 → v1.1**
- **§17** — `POST /campaigns/{uuid}/estimate-cost` upgraded from sample to full contract: request,
  `200` shape with the `recipients == Σ breakdown[].count + unresolved.count` invariant, money
  serialization, the `campaigns.estimated_cost` side effect, and errors.
- **§17 wire format** — monetary fields (`unit`, `subtotal`, `estimated_total`) are **fixed-scale
  JSON strings**, not numbers: a JSON number carries no scale and most clients parse it into a
  binary float, the one representation money must not pass through. The v1.0 sample illustrated them
  as numbers; v1.1 makes the string format normative.
- **§17 route table** — bare `422` → `422(rate_card_not_configured)`, `404`.
- **New §17.1** — rate-card administration (the operator update mechanism). Requires **elevated
  administrative authority** (platform-level, never tenant-level, since the card is global); the
  concrete RBAC mapping is **left to the authorization model**, not frozen here. **Specified for
  future administration — not implemented in Phase 6 Step 5**, which delivers the read path only.
- **§31** — bulk `/estimate` cross-reference pinned to §17 as the single rate-card contract.

**Money rules fixed:** single-currency card (no FX); `unit_price DECIMAL(12,6)`; subtotals exact
(no intermediate rounding); total rounded **once** to 4 dp **ROUND_HALF_UP** at the storage boundary.

**Country resolution fixed:** `contacts.country_code IS NULL` ⇒ recipient is *unresolved* — counted
and reported, excluded from the total, **never** silently dropped and **never** derived from the
`wa_id` E.164 prefix (no prefix→country dataset is specified).

**Contradictions resolved:**
1. `messages.category` permits `service` while `ck_tpl_category` permits only three categories — a
   campaign always sends a template, so `service` is unreachable from an estimate. Doc 4 §17's sample
   note referencing free-tier **service** conversations was incorrect and is **corrected**.
2. Rate card treated as internal authority but declared external (Doc 12 §53) — resolved by making it
   operator-managed data that ships empty, with the platform restating no Meta pricing.
3. "No reseller markup" (global card) vs per-row `cost_currency` (per-tenant currency) — resolved by
   the single-currency invariant: `cost_currency` *records* the card's currency, it does not select one.
4. Precision mismatch (`DECIMAL(12,6)` per message vs `DECIMAL(14,4)` per campaign) — resolved by the
   round-once-at-the-boundary rule.

**Explicitly DEFERRED / OUT OF SCOPE** (unchanged, still undefined — Doc 3 §8.5.5):
`messages.pricing_model`, `messages.is_billable`, `messages.cost_*`, `campaign_recipients.cost_amount`,
**`campaigns.actual_cost` population**, the Meta pricing **webhook payload**, billing reconciliation,
and finance reporting.

> **Rationale — `campaigns.actual_cost` remains unset:** `campaigns.actual_cost` must represent the
> provider-authoritative charge. Computing it from the local rate card would produce another estimate
> rather than the provider's billed amount. Estimated and actual values may legitimately diverge due
> to provider pricing rules, discounts, credits, or future pricing changes. Therefore
> `campaigns.actual_cost` remains unset until an authoritative provider pricing source and contract
> are defined.

**Impact:** documentation only — no code, schema migration, or pricing data in this change. Docs 1, 2,
5–12 unedited. Implementation of Phase 6 Step 5 resumes from this amended specification on approval.

### Design documents — status
- **Doc 12 — Enterprise Governance** — `v1.1` (`12-ENTERPRISE-GOVERNANCE.md`; §1–§55 = v1.0 baseline, §56–§66 added in the governance-handbook enhancement pass; 66 sections, 22 diagrams). Master governance / single entry point referencing Docs 1–11 without duplication.
- **Doc 11 — Operations Runbook** — delivered, awaiting owner approval (`11-OPERATIONS-RUNBOOK.md`; 85 sections, 15 diagrams, OD1–OD40). Operational-only; references Docs 1–10 without redefining them.
- **Doc 9 — AI & Automation Architecture** — delivered, awaiting owner approval (`09-AI-AUTOMATION-ARCHITECTURE.md`; 52 sections, AD1–AD43). Additive; no frozen doc edited.
- **Doc 10 — Testing & QA Architecture** — `v1.1` **FROZEN** on 2026-07-15 (`10-TESTING-QA-ARCHITECTURE.md`; §1–§60 = v1.0 baseline, §61–§72 added in pass; 72 sections, 18 diagrams, TD1–TD65). Additive; references Docs 1–9 without duplication.
- **Doc 1 — SRS** — `v1.0` **FROZEN** on 2026-07-15 (authoritative specification).
- **Doc 2 — Expanded Feature Matrix** — `v1.0` **FROZEN** on 2026-07-15.
- **Doc 3 — Database Design** — `v1.4` **FROZEN** (v1.0 baseline; **§21 Business Event Ledger** → v1.1; **§8.5 `rate_cards`** + §12.4a/§12.2/§13.2/§16 → v1.2 on 2026-07-17; **§9.7 `conversation_tags`** + §12.3/§13.2/§19 → v1.3 on 2026-07-18; **§9.2a reaction payload** → v1.4 on 2026-07-18).
- **Doc 4 — API Design Specification** — `v1.4` **FROZEN** (v1.0 on 2026-07-15 incl. enhancement pass §29–§36 + §23.1/§24.1/§27.1/§27.2; **§17 estimate-cost** + **§17.1 rate-card admin** → v1.1 on 2026-07-17; **§18.1 conversation tags** → v1.3 on 2026-07-18; **§18.2 reaction contract** → v1.4 on 2026-07-18).
- **Doc 5 — UI/UX Design Specification** — `v1.1` **FROZEN** (v1.0 = Parts A–F incl. F1–F15; **Part G Executive Business Dashboard** added in the final additive pass).
- **Doc 6 — Queue & Scheduler Design** — `v1.2` **FROZEN** (pass 1 §21–§34 at v1.0; pass 2 §35–§46 → v1.1; final additive pass **§47 Enterprise Domain Event Bus** + **§48 Business KPI Metric Catalog** → v1.2).
- **Doc 7 — Integrations & Channel Architecture** — `v1.1` (delivered v1.0, awaiting owner approval; **§5.2a Meta `send_reaction` capability** amendment + decision **CD20** added on 2026-07-18 → v1.1). Realizes the dual-channel / Support Connector spec that frozen Doc 6 forward-references as "Doc 6.5" (content in `07-INTEGRATIONS-CHANNEL-ARCHITECTURE.md`; Doc 6 unedited). Defines new **additive** entities (connector registry/session/health, lead pipelines/stages, conversation tags, assignment rules) and additive columns (`connector_id`, lead references) to be applied via migration when built — no frozen doc edited.
- **Doc 8 — Deployment & DevOps Architecture** — `v1.2` **FROZEN** (`08-DEPLOYMENT-DEVOPS.md`; §1–§41 = v1.0 baseline, §42–§55 added in the enhancement pass; **§56 Platform Portability Appendix** added in the final additive pass; DD1–DD41).

### 2026-07-15 — Major requirement: dual-channel (Support Connector) architecture
**Reason:** Owner requires two channels — Channel 1 (Official Meta WhatsApp Cloud API) and Channel 2 (vendor-neutral **Support Connector** abstraction) — unified in one CRM, with the whole platform depending only on a Channel Abstraction Layer, never a specific connector implementation.
**Decision (owner Option 3):** Keep Docs 1–6 **frozen**; centralize all dual-channel design in a **dedicated Doc 6.5**. Docs 7+ reference Doc 6.5 rather than modifying frozen docs.
**Compliance advisory (logged):** The current QR-based connector is treated strictly as a swappable implementation detail; the architecture is designed around the abstraction only, not any specific unofficial implementation. Concrete adapters must comply with their channel's terms of service; official adapters are recommended where available. This advisory is retained so Doc 1 CMP-01 ("official API only") is read together with the dual-channel decision.
**Impact:** No edits to frozen Docs 1–6; new concepts (connector registry/session/health, lead management, connector dashboard, connector endpoints) live in Doc 6.5 and are referenced by later docs.
- **Doc 7 — Deployment Architecture** — not yet started.
- **Doc 8 — Development Roadmap** — not yet started.

### 2026-07-15 — Document order adjusted
**Reason:** Owner chose to design the UI/UX before the Queue & Scheduler internals.
**Changed:** Doc 5 = UI/UX Design; Doc 6 = Queue & Scheduler Design (was Doc 5); Docs 7–8 unchanged.
**Impact:** No change to frozen Docs 1–4.

### Notes
- No changes to frozen documents yet. When a major business requirement changes a frozen
  document, add a dated entry here (e.g., `### 2026-08-01 — SRS v1.0 → v1.1`) describing
  what changed and why, then bump that document's version header.

---

## Module releases

### 2026-07-17 — **Module 2 — CRM COMPLETE** FROZEN (`v0.5.4-module2-foundation`)
Closes the module opened by `v0.2.0-crm-foundation`, whose async half was deferred by dependency to
the Queue Engine + Storage. **Every mandatory SRS contact requirement is now built:** FR-CON-01/02
(CRUD, keyset pagination at 1M+), **03/04** (CSV **and Excel** import with column mapping + per-row
validation), **05** (async import: progress + downloadable error report), **06** (duplicate detection
with `skip`/`merge`/`overwrite` on import, plus a standalone dedup scan/merge), **07/08** (bulk edit
and bulk soft-delete over a selection or filter), **09** (tags), **10** (segments), **11** (typed
custom attributes), **12** (advanced AND/OR search), **14** (activity timeline), **15** (export to
**CSV / Excel / JSON**).

**Steps:** 1–4 = `v0.2.0-crm-foundation` (sync surface) · 5A `v0.5.0-module2-import` · 5B
`v0.5.1-module2-export` · 5C `v0.5.2-module2-bulk` · 5D `v0.5.3-module2-formats`.
**Migrations:** 0005–0008 (contacts, tags/events/leads, segments, custom attributes), 0011 (imports),
0012 (exports), 0013 (bulk_jobs).
**State at freeze:** 249 backend tests passing, ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations). RBAC uses only seeded catalog
permissions (`contacts:*`, `segments:*`).

**Architectural note.** The async CRM is deliberately thin: every bulk path (import, export,
bulk-update/delete, merge) resolves its audience through the **same rule compiler** as segments and
search, walks it in **keyset batches**, and applies each item **through the CRM's own services** — so
a row created by an import and a row edited in bulk obey exactly the same validation, timeline and
audit rules as one touched through the single-contact API. Format is only a rendering choice
(`app/crm/formats.py`); the audience and columns are shared.

**Still deferred (unchanged, by dependency — NOT missing):**
| Deferred | Reason | Lands with |
|---|---|---|
| Auto opt-out on "STOP" (FR-CON-13, the requirement's second half; status field itself is built) | Needs inbound message handling | Messaging (M4) |
| Internal notes, contact assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` | Inbox (M7) |
| `Idempotency-Key` (Doc 04 §8), `bulk`/`read`/`write` rate classes (Doc 04 §9) | **Cross-cutting** — belong to every side-effectful POST, not to contacts alone; import/export/bulk all shipped without them | Own hardening step |
| Doc 04 §30's wider bulk family (`/contacts/bulk` create, `bulk-tag`, `bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) | Out of §14.1's contact scope | Their own modules |

### 2026-07-17 — **Module 2 — Step 5D: Excel import, Excel & JSON export** (`v0.5.3-module2-formats`)
**Scope delivered (no migration, no new endpoint):** **`.xlsx` import** (FR-CON-04) and **Excel/JSON
export** (FR-CON-15) — the last two mandatory CRM requirements, and ones the schema already promised:
`exports.format`'s `ck_exports_format` constraint (Doc 03 §11.6) and Doc 06 §2.3 (`exports` =
"CSV/Excel/JSON") declared all three formats while the services accepted only CSV.

**Reuse over reimplementation:** `read_xlsx` returns the **same header-keyed rows** as `read_csv`, so
the import pipeline's mapping, validation and error report are format-agnostic and untouched; the
export gains a per-format **writer** while the audience, `EXPORT_COLUMNS` and keyset streaming loop
stay shared. CSV output is byte-for-byte unchanged (asserted by test). Excel quirks handled at the
reader: a phone typed as a number renders as `14155550001`, never `1.4155550001e+10`; blank trailing
rows are dropped. Adds `openpyxl` (read-only / write-only modes, so neither direction builds a full
cell graph). **State:** 249 tests passing (+11), ruff clean.

### 2026-07-17 — **Module 2 — Step 5C: bulk operations & duplicate merge** (`v0.5.2-module2-bulk`, migration 0013)
**Scope delivered:** the last CRM items deferred to the Queue Engine (CHANGELOG 2026-07-16 deferral
table) — **bulk update** (FR-CON-07: `add_tags` / `remove_tags` / `set_attributes`), **bulk delete**
(FR-CON-08, soft), and **duplicate scan / merge** (FR-CON-06, `report` or `merge`). All three are
async-only per Doc 04 §14.1: `POST /contacts/bulk-update`, `POST /contacts/bulk-delete`,
`POST /contacts/deduplicate` return **`202` + job** and run on the Queue Engine; progress and the
**§29 partial-success envelope** are polled at `GET /contacts/bulk/{uuid}`. RBAC `contacts:write`
(already seeded — no catalog change); every operation audited (`bulk.started`, `bulk.completed`,
`contact.merged`).

**Design decisions (each traceable to a frozen doc):**
- **Addressing** follows Doc 04 §30's two mutually-exclusive modes — explicit `ids` or a `filter` —
  with the optional **`expected_count` safety guard** (resolved count differs → **409**, act on
  nothing). Filters reuse the **same rule compiler** segments/search/export use, so one audience
  definition serves all four.
- **Per-item commit** (Doc 04 §29): a rejected contact lands in `errors[]` (capped at 100) plus a
  signed, downloadable `error_report_url`, and never rolls back the rest.
- **Idempotent by construction** (Doc 06 §8): attaching a present tag, deleting a deleted contact and
  merging an already-merged group are all no-ops, so at-least-once redelivery converges without
  snapshotting a million-row selection. Every action is applied **through the CRM's own services**, so
  a bulk edit obeys the same validation/timeline/audit rules as the single-contact endpoints.
- **Merge semantics** (FR-CON-06): the **oldest** contact of a group survives; blanks are filled from
  duplicates (a set primary field is never overwritten), tags and attribute values move across, the
  duplicate is soft-deleted, and the merge is recorded on the survivor's timeline (`contact_merged`).
  `wa_id`/`phone_e164` are never merged — they are the survivor's identity.
- **Memory-bounded**: the audience is walked in keyset batches and the dedup scan pages over *groups*,
  so a 1M-row table never materialises.

**State:** 237 backend tests passing (+16), ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations).

**Deferred (unchanged by this step):** `Idempotency-Key` (Doc 04 §8) and the `bulk`/`read`/`write`
rate classes (Doc 04 §9) are **cross-cutting** and remain unbuilt — import/export shipped without
them too. They should be retrofitted across every side-effectful POST in one step, not bolted onto
contacts alone. Doc 04 §30's wider bulk family (`/contacts/bulk` create, `/contacts/bulk-tag`,
`/contacts/bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) belongs to its own module;
this step delivers only the three endpoints Doc 04 §14.1 scopes to contacts.

### 2026-07-16 — **Module 2 — Step 5B: contact export (async)** (`v0.5.1-module2-export`, migration 0012)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `exports` (Doc 03 §11.6) + `POST /contacts/export` → **`202` + job** and
`GET /contacts/export/{uuid}` → progress + **signed, expiring download URL** (FR-CON-15, CSV at this
step; Excel/JSON landed in 5D). Runs on the Doc 06 §2.3 `exports` queue. The filter resolves through
the **same compiler** segments/search use, so an export returns exactly what its preview showed, and
the result is walked in **keyset batches** rendered incrementally — a 1M-row export never
materialises 1M ORM objects. The artifact is written through the **Storage** abstraction and bounded
by `expires_at` (an expired export stops serving a URL). Re-running regenerates rather than
duplicating (Doc 06 §8). RBAC `contacts:export`; audited (`export.started` / `export.completed`).
**State at the time:** 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Module 2 — Step 5A: contact import (async)** (`v0.5.0-module2-import`, migration 0011)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `imports` (Doc 03 §11.6) + `POST /contacts/import` → **`202` + job** and
`GET /contacts/import/{uuid}` → progress + **downloadable error report** (FR-CON-03/05/06). The
request path never parses a byte: the file is uploaded first via Media (§16) and referenced by
`upload_id`; the work runs on the Doc 06 §2.3 `imports` queue. Rows stream through the CRM's own
`ContactService`, so an imported contact is validated, deduped, timelined and audited by exactly the
same rules as one created through the API — no duplicated business logic. A bad row is collected
into the error report and **never aborts the import**; progress is committed as it goes and
already-imported rows are no-ops under `skip`/`merge`, so a retried task converges (Doc 06 §8).
Dedup `skip`/`merge`/`overwrite` on normalized `wa_id` (FR-CON-06). RBAC `contacts:import`; audited
(`import.started` / `import.completed`).
**State at the time:** 203 → 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Storage Foundation** FROZEN (`v0.4.0-storage-foundation`)
**Scope delivered (migration 0010):** storage abstraction + provider registry (Doc 8 §14,
FR-MED-06, DD16) with a **local volume provider** (default) and an **S3-compatible provider
contract** that registers without touching callers — selecting an unregistered backend fails
loudly rather than degrading; **signed URL framework** (FR-MED-09: HMAC binds media id to
expiry, constant-time verify, expired→410 distinct from invalid→403); **media validation**
(FR-MED-01..04: per-type MIME allow-lists + Cloud API size ceilings → 413/415/422 *before* any
bytes are stored); **virus scan interface** (Doc 8 §26 — contract + hook only, no scanner ships,
fail-closed if a configured scanner errors); **upload/download services** (validate → scan →
hash → dedup → store → record; SHA-256 dedup per org, FR-MED-05). `media_assets` (Doc 3 §7.2)
holds metadata + a reference — **never blobs**. APIs: `POST /media/upload`, `GET /media`,
`GET /media/{id}`, `GET /media/{id}/content` (signed URL), `GET /media/{id}/download`
(signature-authenticated), `DELETE /media/{id}`. RBAC `media:read`/`media:write`; audited.

**Security fix (found by test):** the local provider stripped `..` textually, which could yield
an absolute path that re-rooted the join and escaped the storage root. Keys are now resolved and
required to stay under the root.

**State at freeze:** 203 backend tests passing, ruff clean, migrations 0001–0010 reversible,
zero drift.

**Not built (their own modules):** media processing (thumbnails/transcode), Meta media-id
refresh/caching (FR-MED-07), retention sweeps (FR-MED-08), a concrete S3 provider, a concrete
virus scanner.

### 2026-07-16 — **Module 6 — Queue Engine Foundation** FROZEN (`v0.3.0-queue-foundation`)
**Scope delivered (branch `feature/module6-queue-engine`, migration 0009):** Celery application
(Redis broker/backend; `task_acks_late` + `task_reject_on_worker_lost` + `prefetch_multiplier=1`
= at-least-once with no hoarding, Doc 6 §3.4/D7); **queue registry** encoding the Doc 6 §2.3
master specification as data (18 queues with purpose/priority/pool/retry/timeouts/failure
destination) — routing, worker pools and the Queue Monitor all read this one source; **smart
retry framework** (Doc 6 §6: failure classes, per-class attempt caps, exponential backoff with
full jitter, pluggable per-channel error maps); **worker framework** (`TrackedTask`: durable
`job_metadata` state, structured logging, smart retry, terminal DLQ park); **DLQ foundation**
(Doc 6 §7: durable parked-task store, fingerprint grouping, replay through the same idempotent
processor, discard — all audited); **Redis worker registry + TTL heartbeat** (§3.4); **queue
health** from live broker depth + fleet (§13.2). APIs: `GET /jobs`, `GET /jobs/{id}`,
`POST /jobs/{id}/cancel`, `GET /queues` (`system:read`/`system:manage`).

**State at freeze:** 180 backend tests passing, ruff clean, migrations 0001–0009 reversible,
zero drift, OpenAPI 49 paths. Celery added to the environment (was declared, not installed).

**Deliberately not built (they bind to this fabric in their own modules):** domain tasks for
sends, webhooks, imports, exports, media, AI and the Support Connector; Celery Beat schedules;
rate gate / circuit breaker (Doc 6 §5/§6.4 — belong with the send pipeline);
`monitoring_metrics` time-series (Doc 3 §11.7 — Monitoring module).

### 2026-07-16 — **Module 2 — CRM Foundation** FROZEN (`v0.2.0-crm-foundation`)
**Scope delivered (branch `feature/module2-contacts-crm`, migrations 0005–0008):**
- **Step 1** (`v0.2.0-module2-step1`) — `contacts` (Doc 3 §6.1): CRUD, dedup by `(org, wa_id)`, E.164
  validation, opt-in transitions, optimistic concurrency, soft delete, keyset pagination, search,
  filters, whitelisted sorting.
- **Step 2** (`v0.2.0-module2-step2`) — `tags` + `contact_tags` (Doc 3 §6.2, FR-CON-09),
  `contact_events` timeline (Doc 3 §6.5, FR-CON-14), `lead_pipelines` + `lead_stages`
  configuration with the default pipeline (Doc 7 §19.2, §23.2).
- **Step 3** (`v0.2.0-module2-step3`) — `segments` + `segment_rules` (Doc 3 §6.4, FR-CON-10):
  saved dynamic filters, rule tree, preview, cached counts.
- **Step 4** (`v0.2.0-module2-step4`) — `custom_attribute_definitions` + `contact_attribute_values`
  (Doc 3 §6.3, FR-CON-11) and `POST /contacts/search` (FR-CON-12).

**State at freeze:** 153 backend tests passing, ruff clean, migrations 0001–0008 reversible, zero
model↔migration drift. RBAC uses only seeded catalog permissions (`contacts:*`, `segments:*`).

**Deferred by dependency (owner-approved; NOT missing — scheduled to their prerequisite module):**
| Deferred | Reason | Lands with |
|---|---|---|
| Contact Import / Export | Doc 4 §14.1 mandates async `202 + job`; FR-CON-05 requires async progress + error report | Queue Engine + Storage |
| Bulk update / delete, Duplicate merge | Doc 4 §14.1 `202 + job` (bulk class) | Queue Engine |
| Internal Notes, Contact Assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` (Doc 3 §9.5 `internal_notes.conversation_id NOT NULL`; SRS FR-INB-03/05) | Inbox / Messaging |
| Auto opt-out on "STOP" (FR-CON-13) | Requires inbound message handling | Messaging |

### 2026-07-16 — **Module 1 — Foundation** FROZEN (`v0.1.0-foundation`)
Auth, RBAC, users, organization, settings/feature-flags, API keys, audit read API, preferences.
110 tests, 91% coverage, migrations 0001–0004 reversible, OpenAPI 3.1.0 valid. Deferred to their
designated modules: password reset (email), MFA (Doc 12 §56 "Future"), user activity feed
(`activity_logs`), inbound API-key authentication (future public API).

---

## Change log entries

### 2026-07-17 — Implementation order: frontend (M2) deferred — backend-first until the APIs are complete
**Reason:** Owner ruling. The frontend is deliberately deferred until the backend API surface is
complete, so the SPA is built once against a settled contract rather than chased across modules.
**Deviation from:** Doc 12 §15 / §42, which order delivery **M1 → M2 (Frontend Shell + Auth UI) →
M3 (Contacts) → M4 …**. Implementation has instead run M1 → M3 (Contacts) → Queue Engine → Storage
→ M3 async completion, leaving **M2 unbuilt** (`frontend/` holds only the scaffold committed with
M1: shell, theme, React Query, two routes — no login, no protected routing).
**Why this is safe:** Doc 12 §14's dependency graph is **not** violated — M2 depends on M1 (built),
and nothing built so far depends on M2. Only the *order* changed, not the dependency rule. The
Queue Engine and Storage Foundation were likewise built ahead of their manifest position because
M3's import/export/bulk items depend on them (Doc 04 §14.1 mandates `202 + job`).
**Impact:** No frozen document edited. §15/§42 remain the canonical order; this entry records the
approved departure. M2 re-enters the sequence once the backend APIs are complete.
**Naming note (no code impact):** commit/tag labels do not match the Doc 12 §56 manifest — "Module 2"
in git history is manifest **M3 (Contacts)**, and "Module 6 — Queue Engine" is the async fabric, not
manifest **M6 (Campaigns)**, which is not started. The manifest remains authoritative.

### 2026-07-17 — Module 2 Step 5C — additive deviations required to deliver bulk operations
**Reason:** Delivering Doc 04 §14.1's `bulk-update` / `bulk-delete` / `deduplicate` surfaced two gaps
in the frozen set. Recorded here per the §27 change-management rule; **no frozen document edited**.
1. **New table `bulk_jobs`** (migration 0013), additive, reversible, sitting beside `imports`/`exports`
   in the Doc 03 §11.6 job-record family. *Why:* Doc 04 §30 says async bulk ops report
   `processed/total/succeeded/failed`, but Doc 03 §11.7's `job_metadata` has **no progress columns
   and no `organization_id`**, and `imports` cannot be reused (`format` is `NOT NULL`, and its
   `source_key`/`mapping_json` are file-import specific). Doc 12 §56 lists no bulk table for M3
   because §30 assumed `job_metadata` would carry this; it cannot.
2. **Poll endpoint `GET /contacts/bulk/{uuid}`** (`contacts:write`) instead of Doc 04 §30's
   "poll `GET /jobs/{uuid}`". *Why:* §22 gates `/jobs/{uuid}` behind **`system:read`** and
   `job_metadata` is organization-blind, so that route can serve neither a `contacts:write` operator
   nor tenant scoping — §30 and §22 contradict each other. The chosen shape is the one §14.1 already
   defines for the import/export progress endpoints.
3. **Queue placement:** bulk work runs on the existing **`imports`** queue — Doc 06 §2.3 scopes it to
   long-running CRM "parse, validate, dedup, upsert" work (P3, Jobs pool, 300s/600s,
   `job=failed + error report`), and Doc 12 §56 grants M3 no other write queue. **No queue was added**
   to the frozen §2.3 taxonomy; the three operations stay independently traceable via distinct task
   names.
**Impact:** Additive only. Docs 3/4/6/12 unedited; if the owner wants the frozen text reconciled to
match, that is a separate documentation pass.

### 2026-07-16 — FINAL architecture additive pass (A–E) — architecture PERMANENTLY FROZEN
**Reason:** Owner-approved final enterprise additions (A–E). Purely additive; existing content, numbering,
and section IDs preserved. After this pass **the architecture is permanently frozen** and implementation
(Module 1) resumes.
**Changed (append-only, before each doc's end marker; headers version-bumped):**
- **A — Business Event Ledger → Doc 3 (v1.0 → v1.1).** Appended **§21 Business Event Ledger & Enterprise
  Event Taxonomy**: `business_event_types` catalog + immutable, time-partitioned `business_events` ledger (DDL),
  a 25-event canonical taxonomy (`lead.created` … `customer.reactivated`, `ai.approved/rejected`, `data.exported`,
  …), append-only/versioned/replay-ready properties, and its relationship to `audit_logs` / `contact_events`.
- **B — Domain Event Bus → Doc 6 (→ v1.2).** Appended **§47 Enterprise Domain Event Bus & Extension Points**:
  durable-first bus over the ledger, event envelope, topics, publish/subscribe, per-subject ordering, idempotency,
  retry/DLQ, replay, fan-out (mermaid), decisions D35–D37.
- **C — Business KPI Metric Catalog → Doc 6 (→ v1.2).** Appended **§48 Business KPI Metric Catalog**: 15 KPIs
  (Reactivation Rate, Revenue Recovery, Cost per Reactivation, Campaign ROI, Lead Funnel/Velocity, AI Acceptance,
  Agent Productivity, Forecast Metrics, …) with Purpose / Formula / Source events / Refresh / Owner / Future
  columns; decision D38. Single source of truth for all business KPIs.
- **D — Executive Business Dashboard → Doc 5 (v1.0 → v1.1).** Appended **Part G — Executive Business Dashboard**:
  executive KPI cards, business trend charts, conversion funnel, revenue recovery, campaign ROI, lead-pipeline
  overview, agent performance, forecast widgets, business-health score; filters (date/campaign/agent/region/
  channel = Meta / Support Connector); export (PDF/Excel/scheduled reports); reads **only** the KPI Catalog
  (Doc 6 §48) from pre-aggregated rollups — **no operational-widget duplication** (those remain in B2).
- **E — Platform Portability Appendix → Doc 8 (v1.1 → v1.2).** Appended **§56 Platform Portability Appendix**:
  Full Data Export Guarantee, Data Ownership, Vendor Independence, Exit Strategy, open Export Formats,
  Validation/Audit/Integrity Verification, Backup Compatibility, Future Migration Readiness — an architecture
  guarantee built on existing backups (§9), storage (§10) and export APIs (Doc 4 §20).
**New governance items (additive to the Doc 4 §4.3 permission catalog; seeded when the corresponding module is
built, not now):**
- Permission **`analytics:executive`** — gates the Executive Business Dashboard (roles: Executive, Owner, Admin).
  Finance-sensitive figures (ROI/revenue/cost) additionally gated by existing **`finance:read`** (Doc 6 §37).
**Explicitly NOT created (per the owner's final ruling):** Plugin SDK / marketplace / general plugin framework,
legacy migration/ETL engine, data warehouse, MDM, or any additional standalone governance document.
**Impact:** Additive only — no existing section edited, renumbered, or deleted. Docs 3, 5, 6, 8 version headers
and end markers updated. **Architecture is now permanently frozen; Module 1 implementation resumes.**


### 2026-07-15 — Doc 12 (Enterprise Governance) v1.0 → v1.1
**Reason:** Owner-requested governance-handbook enhancement pass.
**Changed:** Appended **§56–§66** with no edits to §1–§55: §56 Enterprise Module Manifest, §57 Feature-to-Module Mapping, §58 Enterprise Permission Matrix, §59 Configuration Inventory, §60 Naming Standards, §61 Technology Dependency Inventory, §62 Software Lifecycle, §63 Documentation Ownership Matrix, §64 Readiness Scorecard, §65 Product Version Roadmap, §66 Enhancement Review. Added 2 diagrams (lifecycle, version roadmap).
**Impact:** Additive only; no frozen document edited. Makes Doc 12 the definitive governance handbook.


### 2026-07-15 — Doc 10 (Testing & QA) v1.0 → v1.1
**Reason:** Owner-requested first post-freeze additive enhancement pass.
**Changed:** Appended **§61–§72** with no edits to §1–§60: §61 Test Case Management, §62 Defect & Bug Management, §63 Release Certification Framework, §64 UAT, §65 Exploratory Testing, §66 Production Verification, §67 Certification Matrix, §68 Test Data Governance, §69 Cross-Document Traceability, §70 Testing Maturity Model, §71 Decision Appendix (TD52–TD65), §72 Final 15-perspective Review. Added 5 diagrams and 14 decision records; extended glossary + cross-references.
**Impact:** Additive only; no frozen document edited.


### 2026-07-15 — Doc 9 (AI & Automation Architecture) started
**Reason:** Owner requested the AI architecture document (`09-AI-AUTOMATION-ARCHITECTURE.md`, v1.0).
**Changed:** New document; architecture-only; plugs into frozen Docs 1–8 without modifying them. Any new data fields (AI interaction record: confidence/reasoning/sources/cost/latency/model_version) are **additive** extensions to Doc 3's AI tables, applied via migration when built.
**Impact:** No frozen document edited.


### 2026-07-15 — Doc 6 (Queue & Scheduler) v1.0 → v1.1
**Reason:** Owner-requested second additive enhancement pass (post-freeze), per the changelog-versioning policy.
**Changed:** Appended **§35–§46** with no edits to §1–§34: §35 Queue Analytics Engine, §36 Predictive Capacity Planning, §37 Cost Analytics Engine, §38 Queue Simulation Engine, §39 Queue Versioning Strategy, §40 Maintenance Mode, §41 Disaster Replay Architecture, §42 Enterprise SLA Matrix, §43 Queue Governance, §44 Queue Audit Architecture, §45 Architectural Decision Appendix (RabbitMQ/Kafka/Redis Streams/SQS/Pub-Sub/Service Bus/Temporal/BullMQ/NATS), §46 self-review. Added decisions D24–D34.
**Impact:** Additive only. Two new permissions flagged for the Doc 4 catalog (`finance:read` for cost data, `ops:emergency` + `ops:dlq_delete` for break-glass ops) — to be seeded when Module 1 RBAC is built; no edits to frozen Docs 1–5.

### 2026-07-15 — Doc 8 (Deployment & DevOps) v1.0 → v1.1
**Reason:** Owner-requested additive enhancement pass.
**Changed:** Appended **§42–§55** with no edits to §1–§41: §42 Environment Strategy (full lifecycle), §43 CI/CD Architecture, §44 Infrastructure Inventory, §45 Configuration Management, §46 Release Management, §47 Business Continuity Planning, §48 Compliance Architecture (GDPR/DPDP), §49 Dependency Governance, §50 Cost Optimization, §51 Production Readiness Checklist, §52 Operational KPIs, §53 Orchestrator Decision Appendix, §54 Cross-Document Traceability, §55 Final Self-Review. Added decisions DD33–DD41.
**Impact:** Additive only; no frozen doc edited.

### (older entries below)

<!-- Add newest entries at the top, using this template:

### YYYY-MM-DD — <Document> <old-version> → <new-version>
**Reason:** <business/requirement driver>
**Changed:**
- <bullet describing the change>
**Impact:** <downstream documents/modules affected>

-->
