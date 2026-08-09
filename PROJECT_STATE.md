# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Latest change | `QR-09L — WAHA ACK Routing and LID Recipient Identity Remediation: QR-09-D13 application-level REMEDIATED. Persisted endpoint ownership selects the WAHA ACK parser, while exact provider-native reply addresses remain separate from Contact telephone identity.` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `HEAD` (QR-09L remediation milestone, on top of QR-09J `8628e40d0529c0a282cffb910569a0ecd2383aef`; resolve after push) |
| Current milestone | `QR-09L — WAHA ACK Routing and LID Recipient Identity Remediation — REPOSITORY/RUNTIME VALIDATED`. QR-09-D13 is application-level `REMEDIATED`; correlated physical ACK certification remains pending. QR-09D/E/F/G/H/I/J/L are `REPOSITORY/RUNTIME VALIDATED`. `QR-09` remains `PARTIAL (BLOCKED)`; all earlier evidence remains preserved. |
| Current phase | `The new endpoint-owned ACK and provider-native recipient routing paths are repository/runtime validated. The next governed action is exactly one new QR09-L-ACK outbound from the actual Unified Inbox, followed by genuine phone read/ACK observation. Restart/reconnect, logout/re-authentication, Meta rotation and target-host/browser-matrix evidence remain outstanding.` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0043_conversation_channel_endpoints` (44 linear revisions) — **unchanged**. QR-09A repaired `0043`'s `downgrade()` ordering without adding a revision; the upgrade path, revision id and resulting schema are byte-for-byte unchanged, and up/down/up is now proven on real MySQL |
| OpenAPI | `3.1.0` · **`207` paths, unchanged**. Required drift gate now **PASSES**: the artifact was regenerated through the canonical exporter (the committed copy had been written with `ensure_ascii=True` while the exporter emits `ensure_ascii=False`). Zero route/schema churn; the only delta is D2's additive `provider_session_missing` property. No FastAPI/Pydantic version was pinned or changed |
| Backend evidence (QR-08, historical) | Ruff PASS · strict mypy PASS (300 files) · 1380 full pytest tests PASS (1367 before QR-08; +13) · Bandit PASS (only pre-existing Low findings) |
| Backend evidence (QR-09B release gate) | **1397 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **21/21 PASS**, including certified WAHA runtime health, Compose/release contracts, image contracts and scans |
| Backend evidence (QR-09C release gate) | **1399 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **22/22 PASS**, including provider-generated signed webhook/retry/restart runtime evidence |
| Backend evidence (QR-09E release gate) | **1407 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS**, including exact-certified-runtime JSON/PNG content-negotiation evidence |
| Backend evidence (QR-09F release gate) | **1408 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS**, including genuine provider-outage/recovery and certified WAHA runtime evidence |
| Backend evidence (QR-09G release gate) | **1418 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 506.1s, including the paused never-paired recovery, transition-before-lease ordering and certified WAHA runtime evidence |
| Backend evidence (QR-09D closure gate) | **1418 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 635.1s on the combined QR-09G backend + QR-09D frontend tree, including certified WAHA health/QR/webhook runtime evidence |
| Backend evidence (QR-09H release gate) | **1431 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 508.9s, including the certified expired-QR stop/start recovery and truthful reached-provider conflict classification |
| Backend evidence (QR-09I release gate) | **1436 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · **23/23 PASS**: canonical premerge 14/14 in 369.6s plus 9 release/runtime gates. The canonical live WAHA restart script was intentionally not run because it would restart the owner-linked session; an isolated container at the exact certified digest instead proved health success/failure and restart survival without touching live storage. |
| Backend evidence (QR-09J applicable gates) | **1437 passed, 0 skipped** · frontend **806 passed** · canonical premerge **14/14 PASS** in 684.7s · applicable release/runtime **8/8 PASS** in 87.9s, including exact-digest QR and provider-generated signed-webhook validators, production contracts/builds, image scans and SBOM. The unchanged health validator was not rerun because its canonical implementation restarts the protected linked WAHA service; QR-09I's isolated exact-digest health evidence remains current. |
| Backend evidence (QR-09L applicable gates) | **1444 passed, 0 skipped** · frontend **806 passed** · canonical premerge **14/14 PASS** in 433.6s · strict mypy **301 files** · applicable release/runtime **8/8 PASS** in 70.7s, including exact-digest QR and provider-generated signed-webhook/ACK validators, production contracts/builds, image scans and SBOM. The restart-bearing health validator was not pointed at the protected linked service; QR-09I's approved isolated exact-digest proof remains current and no health/deploy code changed. |
| Frontend evidence | ESLint PASS · TypeScript PASS · 38 Vitest files / **806 tests** PASS (798 before QR-09D; +8) · production build PASS · `npm audit --omit=dev` 2 moderate (pre-existing React Router advisories below the high/critical gate; dependency unchanged) |
| Bundle evidence | `InboxPage` chunk `37.28 kB` / gzip `10.28 kB` — unchanged by QR-09 |
| M13 contract | ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `52%` evidence-based estimate — **unchanged**. Remediation restores intended behaviour and adds a deployment definition; it delivers no new product capability |
| QR provider | WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0) — **CONDITIONALLY CERTIFIED — REMAINING HOST/PHONE EVIDENCE REQUIRED**, unchanged by QR-09L. The pinned digest has real pairing and inbound-text evidence, but the new correlated outbound/ACK, persistence/logout and target-host gates are incomplete, so certification approval does not advance. Declared capabilities remain `HEALTH`, `QR_AUTH`, `SESSION_STREAM`, `TEXT`, `SESSION_RECONNECT`, `SESSION_LOGOUT`; `BULK`/`CAMPAIGNS`/`TEMPLATE` permanently prohibited and test-enforced. No MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT. |
| Next Module 13 milestone | Send exactly one new QR09-L-ACK text from the actual Unified Inbox, then wait for the owner to receive/read and reply `QR09L ACK TEST READ`. Only genuine emitted ACKs may be correlated. Linked-session restart/reconnect, logout/re-authentication, Meta rotation and supported-browser/target-host evidence remain pending. |
| Host evidence | Repository/local-host evidence only: real MySQL 8.0.46, Redis 7.4.9, actual backend/worker and the exact pinned WAHA container. Real pairing and one real inbound external text are proven; two signed provider variants converged to one Inbox message. Genuine target-host evidence, outbound/ACK/persistence/logout evidence and the full browser/device matrix remain pending; no Host Validated or Production Ready claim. |
| Worktree expectation | QR-09L changes only persisted ACK connector resolution, existing Contact-identity-backed WAHA reply routing, focused regressions, one configured-host hermetic test correction and synchronized governance. No frontend source, migration, route, OpenAPI schema, RBAC, capability, provider configuration, session storage, screenshot, local env file, QR/rescan/logout or proprietary reference material. |
| Last update | `2026-08-09T22:56:26+05:30` (Asia/Kolkata) |

## QR-09F — Provider-Outage QR Availability Projection Remediation (REPOSITORY/RUNTIME VALIDATED)

- **QR-09-D8 (Major) reproduced:** with the real WAHA container stopped and one existing provider
  session, the application projected `provider_status: SCAN_QR_CODE` and `qr_available: true` from
  durable/stale facts. The frontend mounted the QR flow and repeatedly attempted the provider QR
  route during the outage.
- **Remediation:** reconciliation returns typed observation outcomes. QR availability requires a
  current live `SCAN_QR_CODE` observation; an outage projects null provider status, no action,
  `provider_unavailable` and safe retry text. Durable pairing/reauthentication truth is unchanged,
  and provider-session-missing remains its own state. Frontend outage priority prevents QR,
  creating, connecting and reconnect views from outranking current reachability.
- **Real runtime proof:** real MySQL, Redis, backend/frontend and the exact certified WAHA digest.
  A genuine outage remained active for more than three polling intervals with zero QR-handler
  requests. Restart restored the same container, persistent volume, single provider session and
  durable application session; a legitimate in-memory application QR fetch then returned PNG with
  private/no-store controls. No QR was shown, printed, stored or scanned.
- **UI evidence:** actual local 1920×1080 and 390×844 browser captures show the truthful unavailable
  state, no QR/action, no horizontal overflow and keyboard-reachable retry. This is not target-host
  or full supported-browser evidence.
- **Regression/gates:** focused backend 31 PASS and frontend QR 28 PASS. Full release gate **23/23
  PASS** in 474.4s: backend **1408 passed**, frontend **798 passed**, OpenAPI drift, builds,
  SAST/audits, source secret/IaC, certified WAHA health/QR/webhook gates, production contracts,
  image scans and SBOMs.
- **Boundary:** QR-09D remains externally preserved, unapplied and `PARTIAL`; QR-09 remains
  `PARTIAL (BLOCKED)`. Meta rotation is **PENDING — OWNER DEFERRED**. `Host Validated`,
  `Provider Validated`, `Production Ready`: NO; provider certification/approval is unchanged.

## QR-09E — WAHA QR Content Negotiation Remediation (REPOSITORY/RUNTIME VALIDATED)

- **QR-09-D7 (Major) reproduced:** the QR request inherited the WAHA client's JSON default
  `Accept` header. The exact certified provider therefore returned `200 application/json` from
  `?format=image`; the adapter correctly rejected that non-image and the application surfaced a
  truthful `409` rather than exposing or persisting the response body.
- **Remediation:** JSON API calls retain `Accept: application/json`; only the binary QR request now
  sends `Accept: image/png`. Authentication, timeout/error mapping, no-store HTTP response controls,
  transient challenge handling and fail-closed content-type validation are unchanged.
- **Certified runtime proof:** a disposable, loopback-only container at the exact digest reported
  `2026.7.2` / `NOWEB` / `CORE`. JSON negotiation reproduced `200 application/json`; the repository
  client returned `200 image/png` with a valid PNG signature in memory. Two live application fetches
  also returned PNG with `no-store`/private cache controls. Exactly one provider session and one
  durable connection/session remained; no duplicate was created.
- **Privacy/storage boundary:** QR bytes were never displayed, logged, printed, written to disk or
  committed and no physical scan occurred. The disposable regression mounted no session volume;
  the governed `waha-sessions:/app/.sessions` volume was not removed or altered.
- **Regression/gates:** request-header, exact-byte, non-image, auth, provider-error, timeout and
  transport regressions pass. Full release gate **23/23 PASS** in 800.3s: backend **1407 passed**,
  frontend **796 passed**, OpenAPI drift, builds, SAST/audits, source secret/IaC, certified WAHA
  health/QR/webhook runtime checks, production contracts, image scans and SBOMs.
- **Boundary:** UI preview is not applicable; frontend source is unchanged. QR-09D remains separately
  preserved and `PARTIAL`; it was not reapplied. QR-09 remains `PARTIAL (BLOCKED)`. Meta rotation is
  **PENDING — OWNER DEFERRED**. `Host Validated`, `Provider Validated`, `Production Ready`: NO;
  provider certification/approval is unchanged.

## QR-09C — WAHA Webhook Delivery Wiring and Credential Hygiene (PARTIAL)

- **QR-09-D5 (Major):** the signed backend receiver existed, but neither Compose service configured
  WAHA's sender. No global or per-session URL/events/HMAC were present, so provider events had no
  path into the existing webhook/MessageService/Unified Inbox authorities.
- **Design:** one global webhook only. Production callback is private `api:8000`; development uses
  Docker's internal host gateway. Events are exactly `message`, `message.any`, `message.ack`.
  Per-session webhooks remain absent because WAHA combines both modes (duplicate delivery) and would
  persist the HMAC key with session configuration.
- **Authentication/retry:** a dedicated `WAHA_WEBHOOK_HMAC_SECRET` feeds the provider sender and the
  unchanged fail-closed backend verifier. Raw-body SHA-512 is preserved. Retry configuration is
  explicit: 15 attempts, constant two-second delay. No Meta credential is reused.
- **Runtime evidence:** the exact certified image's own `WebhookSender` reached a private `api:8000`
  receiver, produced valid raw-body SHA-512 HMAC, retried one controlled `503` with byte-identical
  body/stable request id, then delivered a signed ACK after restart. Exact provider identity remained
  `2026.7.2` / `NOWEB` / `CORE`; zero sessions before/after; no QR or phone interaction.
- **Regression/gates:** full release gate **22/22 PASS** in 525.3s; backend 1399/0 skipped, frontend
  796, source secret/IaC, dependency, build, Compose, release, image, vulnerability and SBOM gates.
- **META WEBHOOK_VERIFY_TOKEN ROTATION:** **PENDING — OWNER DEFERRED**
- **Classification:** `QR-09C: PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING` ·
  `QR-09: PARTIAL (BLOCKED)` · `Host Validated: NO` · `Provider Validated: NO` ·
  `Production Ready: NO`. Provider certification/approval is unchanged.

## QR-09B — WAHA Runtime Healthcheck Remediation (REPOSITORY VALIDATED)

- **QR-09-D4 (Major) reproduced:** both Compose files invoked `wget`, which does not exist in the
  exact certified image; Docker health output was `exec: "wget": executable file not found in
  $PATH`, so the container remained `starting` although the provider API was responsive.
- **Certified-image inventory:** entrypoint `/usr/bin/tini --` with `/entrypoint.sh`; Node
  `v24.11.1` (built-in fetch available), `/bin/sh`, Bash `5.2.15`, and curl `7.88.1` exist; wget,
  BusyBox and Python do not. `/health` and `/api/server/status` require authentication (`401`
  without a key); provider-owned `/ping` is unauthenticated and returns `200 {"message":"pong"}`.
- **Remediation:** exec-form curl probe against loopback `/ping`, `--fail`, five-second maximum.
  It exposes no key and asserts process/API liveness only, not pairing/session `WORKING` state.
- **Runtime proof:** exact digest is WAHA `2026.7.2` / `NOWEB` / `CORE`; Docker transitions to
  `healthy`, the exact command succeeds against `/ping`, the same command returns non-zero against
  unavailable `127.0.0.1:1`, and Docker returns to `healthy` after restart.
- **Topology/storage:** development remains loopback-only; production publishes no WAHA port;
  restart policy is unchanged; the same named `waha-sessions` volume remains at `/app/.sessions`
  with no pre-existing file removed. No service depends on WAHA health, so no coupling was added.
- **Regression/gates:** `scripts/validate_waha_healthcheck.py` enforces the Compose and real-runtime
  contract in the release gate. All 21 release gates pass: backend 1397, frontend 796, source
  secret/IaC and dependency scans, builds, Compose/release/image contracts, app-image scans/SBOMs.
  The exact WAHA image separately passes the pinned Trivy image gate.
- **Boundary:** no QR displayed/scanned, no physical-phone evidence, no application/UI/capability
  change. QR-09 remains `PARTIAL (BLOCKED)`; provider certification approval and Host/Provider/
  Production Ready classifications are unchanged.

## QR-09A — Production Validation Remediation (REPOSITORY VALIDATED)

- **Scope:** exactly the blockers QR-09 recorded — nothing else. QR-09's own failure evidence is
  preserved verbatim below; a remediation milestone fixes causes, it does not retroactively pass the
  validation that found them.
- **D1 — `0043` is reversible on real MySQL.** The downgrade released `uq_conv_endpoint_contact`
  before `fk_conv_channel_endpoint`, but InnoDB borrows that index for the foreign key (MySQL 1553).
  All conversation-side drops now run in one batch in dependency order. **No new revision**: only the
  broken `downgrade()` body changed. A live-MySQL up/down/up regression proves seeded Meta data
  survives byte-for-byte, the recorded version is truthful at each step, and no `0043` column, index
  or constraint is left behind.
- **D2 — provider-up/session-absent is a recoverable state, not a 500.** `WahaSessionNotFound`
  narrows the provider's 404 at the client boundary; the service treats it as an observation and
  leaves durable pairing truth untouched, projecting the divergence instead. A previously paired
  connection is told it needs a fresh scan; a fresh one gets the ordinary connect-and-scan path.
  Reconnect refuses with `409`. A status read is proven to issue no write and fetch no QR. Genuine
  outages still report `provider_unavailable`, so QR-06 semantics are intact. The UI no longer
  renders this as "Starting the session…".
- **D3 — oversized delivery answers `413`.** The 1 MiB refuse-before-hashing bound is unchanged;
  only the missing HTTP mapping was added. This stops WAHA's at-least-once retry from looping on a
  `5xx`.
- **G1 — required OpenAPI drift gate is green.** Artifact regenerated canonically; 207 paths
  unchanged, one additive D2 property, generated client types back in sync. The historical
  "key-order/resolver" explanation is annotated as inaccurate rather than rewritten.
- **I1 — WAHA has a governed deployment.** Digest-pinned service in both compose files behind a
  `waha` profile, publishing **no port** in production, with a persistent `waha-sessions` volume at
  `/app/.sessions` and a full operator runbook (`deploy/DEPLOYMENT.md` §15). A real
  `docker compose restart waha` preserved the session; the same image without the volume returned
  `404 Session not found` — confirming the volume is what closes D2's underlying cause.
- **S1 — `cryptography` advisory resolved.** Floor raised `>=43` → `>=50` (no lock file exists, so
  the floor is the only guard); `pip-audit` reports no known vulnerabilities.
- **Unchanged:** migration head and revision count, OpenAPI path count, RBAC catalog, WAHA
  capabilities and prohibited capabilities, Meta behaviour, and the provider certification record.
- **Still outstanding (why QR-09 stays PARTIAL):** physical-phone provider E2E — including whether
  scanned credentials survive a restart, which was **not** demonstrated (only pre-pairing session
  persistence was) — and the supported-browser/target-host matrix. Running-app screenshots could not
  be captured in this environment; the state was verified live through the rendered DOM at desktop
  and mobile viewports instead.
- **Classification:** `Repository Validated: YES` for QR-09A · `Host Validated: NO` ·
  `Provider Validated: NO` · `Production Ready: NO`.

## QR-09 — Production Validation (PARTIAL — BLOCKED)

- **Scope:** validate QR-08's contract against production-representative infrastructure — real
  MySQL, real Redis, the real pinned WAHA container — instead of QR-08's own SQLite-only preview
  evidence. Validation only; no feature, migration, route, or capability work.
- **Environment:** MySQL `8.0.46` and Redis `7.4.9` via this repository's own `docker compose`;
  WAHA `2026.7.2`/`NOWEB`/`CORE` at the exact certified digest
  (`sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`). No physical handset
  was available, so physical-phone pairing/inbound/outbound/ACK-chain evidence is not claimed.
- **Closed a QR-08 evidence gap:** QR-08's preview recorded a `503 idempotency_unavailable` because
  its throwaway environment had no Redis. Against real Redis: normal send succeeds; a duplicate
  `Idempotency-Key` replays the original response with no second row; 6 concurrent requests sharing
  one key produce exactly one message; a Redis outage fails closed (`503`, zero rows); a Redis
  restart recovers.
- **Proved the decisive QR-08 dedupe claim on real MySQL, not only SQLite:** one underlying provider
  message delivered as `message`×2 + `message.any`×2 (4 deliveries) produced 4 `webhook_events` rows
  (event-layer persistence is intentionally at-least-once) but exactly **1** stored `messages` row.
- **QR-09-D1 (Major, open):** `0043_conversation_channel_endpoints`'s `downgrade()` fails on real
  MySQL — `uq_conv_endpoint_contact` is dropped before the foreign key that depends on it
  (`MySQL 1553`). The upgrade path itself is unaffected and independently verified to preserve
  existing Meta data byte-for-byte. Same defect class as the pre-existing, separately tracked
  `0036`/`0040` real-MySQL downgrade defect.
- **QR-09-D2 (Major, open):** `GET /channels/whatsapp-qr/session` returns `HTTP 500` when the real
  provider is reachable but the named session no longer exists there (reproduced deterministically
  after a provider restart with no persistent session storage) — `ChannelApiError`/404 is not
  translated into a truthful recoverable status, unlike genuine provider outage, which is handled
  correctly and distinctly.
- **QR-09-D3 (Minor, open):** an oversized webhook body is correctly refused before hashing but
  surfaces as `500` instead of a 4xx.
- **Required OpenAPI drift gate genuinely fails**, but this milestone **corrects** the previously
  recorded explanation: investigation proved generation is deterministic and the committed/generated
  JSON parse to exactly-equal objects (207 paths both); the sole byte difference is ASCII-escaping.
  Not a resolver key-order artifact as previously stated elsewhere in this repository's governance.
- **Unchanged:** migration head, OpenAPI path count, RBAC catalog, WAHA capabilities, prohibited
  capabilities, the WAHA selection/certification record. QR-01 through QR-08 unaffected; QR-08
  remains `COMPLETE`.
- **Classification:** `Repository Validated: NO` (a required gate is red and two Major defects are
  open) · `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.
- **Next milestone (not started):** `QR-09A — Production Validation Remediation` — fix D1/D2/D3,
  regenerate `openapi.json` with consistent ASCII-escaping, add a WAHA compose/deployment service
  with persistent session storage, triage the `cryptography` advisory, rerun QR-09, then pursue
  physical-phone and full browser/host evidence.

## QR-08 — Unified Inbox integration

- **Scope:** wires QR-04's inbound and QR-05's outbound/ack translation into the **same** existing
  `Conversation`/`Message`/`MessageService`/`ConversationService`/`InboxQueryService`/`SendService`
  authorities Meta already uses — not a second Inbox. Reuses the M13-03 `channel_endpoints` table
  QR-07 never populated (`WhatsAppQrService.connect()` now creates one idempotently).
- **Additive migration (`0043`):** `conversations`/`messages`/`webhook_events` gain a nullable
  `channel_endpoint_id`; `conversations.phone_number_id` widens to nullable, guarded by
  `ck_conv_endpoint_owner` (exactly one owner). No column dropped or renamed; no existing row
  changed.
- **Inbound stored-message dedupe is endpoint-scoped + canonical-provider-id, independent of
  event-level dedupe:** `message`/`message.any` (same envelope, two valid events per QR-04) collapse
  to one stored row; a same-event redelivery collapses too; the same provider id on two different
  endpoints does not collide.
- **Outbound routing is entirely server-derived.** `SendService.accept_for_conversation` resolves
  the provider from the conversation's own durable ownership; `MessageSendRequest.conversation_id`
  carries no provider field for a client to forge. A WAHA send that cannot be confirmed is marked
  `failed`/`indeterminate`, never auto-retried.
- **WAHA composer refuses to send truthfully** when the session is not `ACTIVE`+`PAIRED`, reusing
  QR-07's own live status read (no automatic reconnect from opening a conversation).
- **OpenAPI 206 → 207 paths** — `POST /webhooks/waha`, the WAHA analogue of the pre-existing
  `/webhooks/whatsapp` route QR-04 never got an HTTP route wired to.
- **Two real defects found and fixed**, both pre-existing in already-shipped QR-06/QR-07 code:
  QR-07's `_REAUTH_PAIRING` incorrectly included `UNPAIRED` (diverged from QR-06's own canonical
  definition); QR-04's `message.ack` classified `UNKNOWN` despite QR-05 already having built the
  translator for it.
- **Unchanged:** Meta behaviour, RBAC catalog, prohibited capabilities
  (`BULK`/`CAMPAIGNS`/`TEMPLATE`), no MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT for WAHA.
- **Still pending:** QR-09 production validation. History and media transfer remain unimplemented
  and are not assigned to a delivered milestone.
- **Known limitation:** the existing Meta-number-scoped analytics rollup excludes WAHA
  conversations rather than counting them under a fabricated dimension; QR-08 adds no WAHA
  analytics.

## QR-07 — WhatsApp Scan/Connect interface

- **Scope:** the first real operator-facing screen over the WAHA adapter (QR-01..06), bridging its
  live provider I/O to the existing M13-03/04/05 connection/session/pairing control plane. 6 new
  routes, gated on the pre-existing `channels:read`/`channels:authenticate` permissions.
- **Single-organization scope (ADR-0021):** one `WAHA_ORGANIZATION_ID`; every other organization,
  and an unconfigured deployment, see the identical `configured=false`.
- **No new persistence:** reuses `channel_connections`/`channel_sessions` from M13-03/04. No
  migration.
- **QR still never persisted:** fresh per request, `no-store`, held client-side only as a
  revoked-on-replace object URL.
- **Real M13-05 constraints surfaced and respected while integrating** (not worked around):
  pairing transitions require the session to still be `INITIALIZING`/`WAITING_FOR_PAIRING`;
  `PairingState.PAIRED` is terminal (logout registers a fresh revision rather than reversing one);
  `SessionManager.acquire_lock` refuses a `PAUSED` session.
- **OpenAPI 200 → 206 paths** — authorized by this milestone, unlike QR-01..06's own invariant.
- **Unchanged:** migration head `0042` (43 revisions), RBAC catalog, Meta behaviour, prohibited
  capabilities. No Production Ready, Host Validated or M13-07 claim.
- **Still pending:** QR-08 Unified Inbox integration, QR-09 production validation. History and
  media transfer remain unimplemented and are not assigned to a delivered milestone.
- **Known limitation:** retrying an expired, never-scanned QR surfaces the provider's real
  "session already exists" error rather than a fabricated retry success; a dedicated provider
  restart path is not built in this milestone.

## QR-06 — WAHA session recovery, health and teardown

- **Scope:** start/stop/logout behind a runtime lease, bounded reconnect planning, and a
  session-scoped health projection. Declares `SESSION_RECONNECT` and `SESSION_LOGOUT`.
- **Never guesses from ambiguous status:** reconnect is planned from the platform's durable pairing
  record, so the provider's `STARTING` — which QR-02 proved means either a fresh session or a paired
  one resuming — can never be read as evidence a session is unpaired.
- **Outage-safe:** an unreachable provider is "unknown", never "unpaired"; durable truth survives.
- **STOP keeps credentials; LOGOUT invalidates them** and deliberately produces re-auth-required
  truth that nothing auto-repairs. Session deletion is not exposed.
- **Ownership reuses the existing lease/fencing authority** — no second runtime ownership system.
- **Runtime registration is opt-in:** importing the package still registers no runtime.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities. No Production
  Ready, Host Validated or M13-07 claim.
- **Still pending:** QR-07 UI, QR-08 Unified Inbox, QR-09 production validation. History and media
  transfer remain unimplemented, and there is still no QR route or operator UI.

## QR-05 — WAHA send path and delivery-state reconciliation

- **Scope:** outbound text through the configured session, canonical provider-id capture,
  acknowledgement translation onto the platform's existing monotonic status vocabulary, and an
  endpoint-scoped reconcile-before-resend primitive. Declares `TEXT`.
- **Monotonic by reuse:** `STATUS_RANK`/`advances()` already make delivery one-way, so QR-05 only
  maps provider acks onto it. The certified out-of-order `DEVICE → SERVER → READ` ends at `read`;
  duplicate acks are no-ops; unknown acks make no state change.
- **Never blindly resends:** an uncertain transport outcome is surfaced as indeterminate. A resend
  is permitted only when reconciliation proves absence; a failed lookup stays indeterminate.
- **Endpoint-scoped:** one endpoint can never confirm or advance another's message, and no global
  provider-message lookup exists.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-06 reconnect/health/teardown, QR-07 UI, QR-08 Unified Inbox, QR-09
  production validation. Media, history, interactive, reaction, location and contact are all
  unimplemented, and there is still no QR route or operator UI.

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
semantic schemas are equal and M13-05 introduces no route or schema.
<!-- Annotation (QR-09A, 2026-08-08): the attributed cause above is now known to be wrong, and is
     left in place as the historical record rather than rewritten. QR-09 proved OpenAPI generation
     is deterministic (identical SHA-256 across processes) and that key order was identical; the
     committed artifact differed only by JSON ASCII-escaping, because it had been written with
     `ensure_ascii=True` while the exporter emits `ensure_ascii=False`. QR-09A regenerated the
     artifact through the canonical exporter and the drift gate now passes. No resolver or
     dependency was pinned or upgraded to achieve this. -->
It does not prove a live provider,
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
