# Module Status

Completion percentages are evidence-based estimates against
`VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`, not measures of code volume or visual polish. Existing
foundations are preserved; percentages increase only when real backend contracts, permissions,
audit behavior, UI integration, and tests are complete.

GOV-02 adds a completion gate without changing any percentage: new or materially changed screens
must also pass ADR-0012 and the twenty-point premium screen Definition of Done in Design Document
25. Visual polish alone never increases completion, and a backend-complete workflow with a generic,
inaccessible, placeholder-driven, or inconsistent experience is not final completion.

The owner-corrected CORE-05 extends the existing Reactivation and Task authorities with nine primary
statuses, six labels, governed dates, due views/actions, assignment, Audit and Timeline. CORE-07
converges those facts with identity, WhatsApp history, documents, tasks, KYC/SIM/Activation,
campaigns and evidence inside the existing Customer 360 route. CORE-09 adds the durable unified
Notification Center without creating a second task, reminder, audit, or domain authority. Completed
authorities are reused; separate heavy SIM fulfilment and Activation operations remain owner-deferred.

Last synchronized: `2026-08-09T22:56:26+05:30`.

## Module 13 — QR-09L WAHA ACK Routing and LID Recipient Identity Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`. QR-09-D13 is application-level
  `REMEDIATED`; correlated physical ACK certification remains pending.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs already-approved ACK and
  text-reply behavior and adds no product capability.
- **Defects:** endpoint-owned persisted ACKs were reopened through the worker's Meta default; WAHA
  LID digits were collapsed into canonical phone identity and later reconstructed as `@c.us`.
- **Fix:** event ownership now selects the persisted endpoint's connector. Existing provider-scoped
  Contact identities preserve exact `@lid`, `@c.us` and `@s.whatsapp.net` routes, while only a
  factual phone JID establishes `whatsapp_phone`; endpoint replies reuse the observed route unchanged.
- **Evidence:** signed ACK integration proves DEVICE→delivered, late SERVER no-regression,
  READ→read, duplicate idempotency, unknown refusal and cross-endpoint isolation. Identity
  integration covers all three provider forms, historical replay without duplicate messages, and
  fail-closed LID handling. Canonical premerge 14/14 in 433.6s (backend 1444, frontend 806) and
  applicable release/runtime 8/8 in 70.7s pass.
- **Preserved:** genuine unmatched DEVICE ACK remains unattributed; its one normal replay reached
  WAHA parsing and endpoint correlation. The linked exact-digest provider remains healthy,
  WORKING/active/paired with the same volume and restart count 0. No QR, restart, logout, re-pair,
  resend, migration, route/OpenAPI, RBAC, capability, secret/configuration or approval change.
- **Next:** after the single QR09-L-ACK Inbox send is committed and pushed, wait for genuine phone
  read/ACK evidence. Meta rotation remains owner-deferred; `Host Validated`, `Provider Validated`,
  `Production Ready`: NO.

## Module 13 — QR-09J WAHA Inbound Timestamp Normalization Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`. QR-09-D12 is `REMEDIATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs certified inbound
  execution and adds no product capability.
- **Defect:** a real external text produced valid signed `message` and `message.any` events, but
  both dead-lettered because WAHA supplied aware UTC while repository/MySQL time is naive UTC.
  Conversation-window evaluation raised before a ledger row could be committed.
- **Fix:** normalize the provider epoch to repository-standard naive UTC at the WAHA translation
  boundary. Shared conversation/window logic, chronological ordering, two-event dedupe and ACK
  monotonicity remain unchanged.
- **Evidence:** both preserved source events were redriven through the normal queue and processed;
  actual Inbox APIs expose exactly one accepted inbound message, unread count 1, connector WAHA.
  Focused 174 PASS; canonical premerge 14/14 in 684.7s (backend 1437, frontend 806); applicable
  release/runtime gates 8/8 in 87.9s.
- **Preserved:** original D12 dead-letter rows, provider session and volume. Same container/start
  time, restart count 0, WORKING/active/paired/connected, no QR, rescan, logout or database rewrite.
- **Next:** after explicit approval, physical QR-09 resumes at the real outbound Inbox reply. Meta
  rotation remains owner-deferred; `Host Validated`, `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09I Pairing Window Renewal and Post-Scan Convergence Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`. QR-09-D11 is `REMEDIATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs pairing continuity and
  adds no product capability.
- **Defect:** the local QR representation expired while the same certified provider session had
  already reached identity-bearing `WORKING`. An explicit request for a new window was an
  equal-state no-op, and the general transition path correctly refused all expired transitions,
  trapping the application in `pairing_available` after a successful scan.
- **Fix:** explicit requests renew only the representation expiry under the existing
  lease/fence/version controls. A separate narrow completion path accepts only a fresh `WORKING`
  observation with identity for the configured session. Polling does not renew; ordinary expiry
  rejection remains intact; state/revision chronology and redacted Audit semantics are preserved.
- **Evidence:** real MySQL/Redis/application and the untouched exact WAHA 2026.7.2 / NOWEB / CORE
  container converged to active/paired/connected with no QR available. Provider/durable counts
  stayed one, restart count stayed zero, and linked message count stayed zero. Canonical premerge
  14/14 in 369.6s plus nine release/runtime gates passed; backend 1436, frontend 806.
- **Preserved:** no provider restart, logout, delete, create, QR generation/rescan, message, manual
  database mutation, frontend source, migration, route/schema, RBAC, capability or approval change.
- **Next:** physical QR-09 resumes at real inbound text. Meta rotation remains owner-deferred;
  `Host Validated`, `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09H Expired QR Existing-Session Recovery Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`. QR-09-D10 is `REMEDIATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this restores a blocked operator cycle
  and adds no product capability.
- **Defect:** QR-09-D10 (Blocker) — an unscanned QR lapses to `FAILED` while the provider session
  object survives, so every "Get a new QR code" retry hit the provider's `already exists` refusal,
  which the service reported as an outage. `reconnect` refused (never paired) and `connect` was a
  no-op, so the channel could never issue another QR without direct provider intervention.
- **Fix:** new `WahaChannelAdapter.prepare_pairing()` keeps `begin_pairing()` create-only (QR-03's
  no-guessing principle intact), attempts the create first, and only on a reached-provider refusal
  reads live state and applies the certified non-destructive `stop` → `start` recovery. Reuses an
  already-QR-eligible session, skips a redundant stop, and refuses both a provider-reported linked
  account and a durably `PAIRED` connection. Error classification corrected: transport → service
  unavailable, reached-provider → truthful conflict, provider wording never echoed.
- **Evidence:** exact certified WAHA `2026.7.2` / `NOWEB` / `CORE`. Measured: `start` alone cannot
  recover `FAILED`; `stop`+`start` reaches `SCAN_QR_CODE` with session count 1, `me: None` and
  config byte-identical. A genuinely expired QR recovered through the actual frontend under one
  lease; application QR returned `200 image/png` with no-store/private/no-cache. Release gate
  23/23; backend 1431, frontend 806 (unchanged). Thirteen new tests; 9 fail with the fix reverted.
- **Preserved:** no delete/recreate/logout, no new capability, no migration/route/schema/RBAC
  change; QR bytes never displayed, persisted, logged, audited or scanned.
- **Next:** physical-phone QR-09 validation. Meta rotation remains owner-deferred;
  `Host Validated`, `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09D Pairing Action State Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`. QR-09-D6 is `REMEDIATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this restores a reachable operator
  action and adds no product capability.
- **Defect:** QR-09-D6 (Major) — with a durable application session present and the provider
  reachable but holding none, the screen projected `ready-to-connect` and re-offered an idempotent
  `connect()` that cannot create provider state, so `POST /session/pair` was operationally
  unreachable and every status poll re-asserted the dead end.
- **Fix:** the durable application session is the boundary between the two honest actions. A
  provider-neutral `ready-to-pair` view state offers "Begin pairing" wired to `POST /session/pair`;
  no durable session still yields `ready-to-connect`. QR-09F outage truth still outranks it, and a
  previously paired connection is still resolved earlier as `reauth-required`.
- **Evidence:** exact certified WAHA `2026.7.2` / `NOWEB` / `CORE`, real MySQL/Redis/application.
  `ready-to-pair` held across eight live three-second polls; the actual UI action issued exactly one
  `/session/pair` and zero `/session/connect`; two application QR requests returned `200 image/png`
  with no-store/private/no-cache; a genuine outage produced zero new QR requests and recovered
  cleanly; QR-09G paused recovery re-proven through the same UI. Actual 1920×1080 and 390×844
  screenshots show ready-to-pair with no QR, no overflow, visible keyboard focus and a 118×40 mobile
  control. Release gate 23/23; backend 1418, frontend 806.
- **Preserved:** all QR-09F outage regressions retained; QR content never displayed, persisted,
  logged, audited or scanned; migration/OpenAPI/RBAC/capabilities/provider approval unchanged.
- **Next:** safe physical-phone QR-09 preparation, stopping at the mandated safety/manual action.
  Meta rotation remains owner-deferred; `Host Validated`, `Provider Validated`,
  `Production Ready`: NO.

## Module 13 — QR-09G Paused Never-Paired Session Recovery Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this restores a blocked recovery path
  and adds no product capability.
- **Defect:** QR-09-D9 (Blocker) — an ordinary `STOPPED` provider observation pauses the durable
  session; a `PAUSED` row cannot be leased, so for a never-paired connection status reconciliation
  stopped permanently, `pair` returned 409, `reconnect` returned 409 telling the operator to pair,
  and `connect` was a no-op. The channel was unrecoverable without direct database intervention.
- **Fix:** `begin_pairing()` reuses the `reconnect()` control-plane pattern — the legal, lease-free
  `PAUSED → INITIALIZING` transition first, then the ordinary runtime lease. The `SessionManager`
  PAUSED lease prohibition is unchanged. Recovery is narrow to non-`PAIRED` pairing states; a
  paused paired session keeps the existing refusal and stays in the reconnect/re-auth domain. A
  row that cannot be leased is still read, so status reports missing-session and outage facts
  truthfully without mutating anything.
- **Evidence:** exact certified WAHA `2026.7.2` / `NOWEB` / `CORE`, real MySQL/Redis/application.
  Preserved live D9 reproduction recovered: `pair` returned 200 (was 409), audit shows
  `transitioned` before `lock_acquired` (fencing 867 → 868), one provider session reached
  `SCAN_QR_CODE`, one durable connection/session, no DB intervention. Release gate 23/23; backend
  1418, frontend 798. Ten new tests; 8 fail with the fix reverted.
- **Preserved:** no QR displayed/persisted/scanned; migration/OpenAPI/RBAC/capabilities/provider
  approval unchanged. QR-09D remains externally preserved as `qr09d-post-qr09f-current.patch`.
- **Next:** resume and close QR-09D on top of this commit, then physical-phone QR-09 preparation.
  Meta rotation remains owner-deferred; `Host Validated`, `Provider Validated`,
  `Production Ready`: NO.

## Module 13 — QR-09F Provider-Outage QR Availability Projection Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this corrects state projection and
  adds no product capability.
- **Defect:** QR-09-D8 (Major) — during a real WAHA transport outage, durable pairing availability
  and stale `SCAN_QR_CODE` metadata incorrectly kept `qr_available` true; the frontend then mounted
  QR retrieval while the provider was unreachable.
- **Fix:** typed provider-observation outcomes; QR availability requires a current live
  `SCAN_QR_CODE` observation. Outage truth overrides every stale frontend action state without
  mutating durable pairing or reauthentication state. Missing-session behavior remains distinct.
- **Evidence:** exact certified WAHA `2026.7.2` / `NOWEB` / `CORE`, real MySQL/Redis/application;
  genuine outage held for more than three poll intervals with no QR-handler request, then the same
  container, volume and sessions recovered. Actual local 1920×1080 and 390×844 screenshots show the
  unavailable state with no QR/action or horizontal overflow. Release gate 23/23; backend 1408,
  frontend 798.
- **Preserved:** QR content was never displayed/persisted/scanned; migration/OpenAPI/RBAC/
  capabilities/provider approval unchanged. QR-09D remains externally preserved and unapplied.
- **Next:** stop after QR-09F. QR-09D and physical-phone QR-09 work require separate approval. Meta
  rotation remains owner-deferred; `Host Validated`, `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09E WAHA QR Content Negotiation Remediation

- **Milestone status:** `REPOSITORY/RUNTIME VALIDATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs provider response
  negotiation and adds no product capability.
- **Defect:** QR-09-D7 (Major) — QR byte retrieval inherited `Accept: application/json`, so the
  certified provider returned JSON despite `?format=image`; the adapter then failed closed and the
  application could not deliver the QR image.
- **Fix:** request-specific `Accept: image/png` for QR bytes only. Every JSON call retains JSON
  negotiation; API-key, error, timeout, content validation and no-store boundaries remain intact.
- **Evidence:** exact digest, WAHA `2026.7.2` / `NOWEB` / `CORE`; JSON baseline reproduced and PNG
  response proven through the real client; repeated live application fetches returned PNG without a
  duplicate session. Release gate 23/23; backend 1407, frontend 796.
- **Preserved:** no QR displayed/persisted/scanned; persistent volume, networking, capabilities,
  migration/OpenAPI/RBAC/UI and provider approval unchanged. QR-09D's frontend patch remains
  externally preserved and absent from this milestone.
- **Next:** stop after QR-09E. QR-09D reapplication/revalidation and QR-09 physical-phone closeout
  require separate explicit approval. Meta rotation remains owner-deferred; `Host Validated`,
  `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09C WAHA Webhook Delivery Wiring and Credential Hygiene

- **Milestone status:** `PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING`.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs deployment wiring and adds
  no product capability.
- **Defect:** QR-09-D5 (Major) — the governed signed receiver existed, but WAHA had no configured
  callback/events/HMAC sender, so provider traffic could not reach the Unified Inbox pipeline.
- **Fix:** one global private callback in each Compose topology; exact `message`, `message.any`,
  `message.ack` subscriptions; dedicated WAHA HMAC; unchanged raw-body SHA-512 verification;
  explicit 15-attempt/two-second constant retry contract. No per-session webhook duplication/key
  persistence, public provider exposure or new capability.
- **Evidence:** exact certified image's sender produced valid HMAC over private Docker networking,
  retried one controlled 503 byte-for-byte, and delivered a signed ACK after restart. Zero sessions,
  QR or phone actions. Existing receiver/dedupe suite 81 PASS; release gate 22/22, backend 1399/0
  skipped, frontend 796.
- **META WEBHOOK_VERIFY_TOKEN ROTATION:** **PENDING — OWNER DEFERRED**
- **Preserved:** QR-09/09A/09B history, migration/OpenAPI/RBAC/UI/capabilities, provider approval,
  production internal-only topology and `waha-sessions` data.
- **Next:** stop after QR-09C technical reporting. QR-09 physical-phone closeout requires separate
  approval after outstanding external gates. `Host Validated`, `Provider Validated`,
  `Production Ready`: NO.

## Module 13 — QR-09B WAHA Runtime Healthcheck Remediation

- **Milestone status:** `QR-09B — WAHA Runtime Healthcheck Remediation — REPOSITORY VALIDATED`.
- **Completion:** `52%` evidence-based estimate — unchanged; this repairs deployment liveness
  reporting and adds no product capability.
- **Defect:** QR-09-D4 (Major) — the exact certified image lacks the `wget` executable required by
  both committed healthchecks, leaving Docker in `starting` despite a responsive provider API.
- **Fix:** verified in-image curl `7.88.1`, exec-form and bounded to five seconds, checks provider-owned
  unauthenticated `/ping`; it does not check WhatsApp pairing/session state and contains no secret.
- **Evidence:** exact digest, WAHA `2026.7.2` / `NOWEB` / `CORE`; Docker healthy before and after
  restart; positive command exit 0 and unavailable-endpoint exit non-zero; development loopback-only,
  production internal-only, same persistent volume, no startup coupling. Full release gate 21/21,
  backend 1397 and frontend 796.
- **Preserved:** QR-09 and QR-09A historical evidence, migration/OpenAPI/RBAC/capabilities, provider
  certification status and session data. No UI or physical-phone evidence.
- **Next:** QR-09 remains `PARTIAL (BLOCKED)` pending explicit approval to resume real phone and
  target-host/browser validation. `Host Validated`, `Provider Validated`, `Production Ready`: NO.

## Module 13 — QR-09A Production Validation Remediation

- **Milestone status:** `QR-09A — Production Validation Remediation — REPOSITORY VALIDATED`.
- **Completion:** `52%` evidence-based estimate — **unchanged**. Remediation restores intended
  behaviour and adds a deployment definition; it delivers no new product capability, so completion
  does not move.
- **Scope:** exactly the blockers QR-09 recorded — D1, D2, D3, the OpenAPI required gate, the WAHA
  deployment gap and the `cryptography` advisory. No unrelated cleanup.
- **D1:** `0043`'s `downgrade()` now drops the foreign key before the index InnoDB borrows for it,
  so the revision is reversible on real MySQL. **No new revision** — the upgrade path, revision id
  and resulting schema are unchanged; head stays `0043` at 44 revisions. Covered by a live-MySQL
  up/down/up regression that also proves seeded Meta data survives and no partial schema remains.
- **D2:** a reachable provider reporting no session is now a truthful recoverable state instead of
  an HTTP 500. Durable pairing truth is preserved, a previously paired connection is correctly told
  it needs a fresh scan, reconnect refuses with `409`, and nothing recreates a session or requests a
  QR on a status read. QR-06 outage semantics are untouched. The UI no longer renders this as
  "Starting the session…".
- **D3:** an oversized webhook body is answered `413` rather than `500`; the 1 MiB
  refuse-before-hashing bound is unchanged.
- **Required gate:** the OpenAPI drift gate is green — artifact regenerated canonically, 207 paths
  unchanged, one additive D2 property. The previously recorded "key-order/resolver" explanation is
  annotated as inaccurate rather than rewritten.
- **Infrastructure:** digest-pinned WAHA service added to both compose files behind a `waha`
  profile, publishing no port in production, with a persistent `waha-sessions` volume at
  `/app/.sessions` and a full operator runbook (`deploy/DEPLOYMENT.md` §15).
- **Security:** `cryptography` floor raised to `>=50`; `pip-audit` reports no known vulnerabilities.
- **Evidence:** validated against real MySQL 8.0.46, real Redis 7.4.9 and the real pinned WAHA
  container. Backend 1397 passed / 0 skipped; frontend 796; 371 QR-01..08 regression tests.
- **Not advanced:** WAHA capabilities, prohibited capabilities, RBAC, provider certification.
  Credential survival across restart *after a real scan*, physical-phone E2E, and the browser/host
  matrix all remain outstanding, so `Host Validated`, `Provider Validated` and `Production Ready`
  stay **NO** and **QR-09 remains `PARTIAL (BLOCKED)`**.
- **Next:** rerun QR-09's external validation gates once physical-phone and host/browser evidence
  can be produced. Not started.

## Module 13 — QR-09 Production Validation

- **Milestone status:** `QR-09 — Production Validation — PARTIAL (BLOCKED)`. Validation attempted
  against production-representative infrastructure; not closed.
- **Completion:** `52%` evidence-based estimate — **unchanged**. QR-09 is validation, not feature
  delivery, so Module 13 completion does not move.
- **Environment:** real MySQL `8.0.46`, real Redis `7.4.9` (this repository's own
  `docker compose up -d`), and the real pinned WAHA container at the exact certified digest
  (`sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`, 2026.7.2/NOWEB/CORE) —
  in place of QR-08's SQLite-only preview evidence. No physical handset was available; physical-phone
  pairing/inbound/outbound/ACK evidence is not claimed.
- **Confirmed on real infrastructure:** the QR-08 stored-message dedupe contract (one underlying
  provider message delivered 4 ways collapses to exactly one stored message); Meta + WAHA coexisting
  in one Inbox; prohibited-capability enforcement; disabled-by-default staged rollout (`connect()`
  refused `403` until the org flag is enabled); real-Redis idempotency (closing the QR-08 preview's
  `503` limitation).
- **Two Major defects found and left open** (validation defect policy: discover, record, stop — do
  not silently remediate inside a validation milestone): QR-09-D1, `0043`'s real-MySQL `downgrade()`
  fails (index dropped before the foreign key that depends on it); QR-09-D2, the QR operator status
  endpoint returns `500` when the real provider is up but the session is gone. One Minor
  (QR-09-D3, oversized webhook body maps to `500` instead of a 4xx).
- **One required repository gate genuinely fails:** OpenAPI drift. Investigated and found to be a
  deterministic ASCII-escaping artifact difference (207 paths, exactly-equal parsed objects) — this
  **corrects** a previously recorded explanation elsewhere in governance ("resolver key-order
  mismatch"), which does not hold for this artifact.
- **Preserved:** migration head, OpenAPI path count, RBAC catalog, WAHA capabilities, prohibited
  capabilities (`BULK`/`CAMPAIGNS`/`TEMPLATE`), the WAHA selection/certification record. QR-01
  through QR-08 unaffected; QR-08 remains `COMPLETE`.
- **Classification:** `Repository Validated: NO` · `Host Validated: NO` · `Provider Validated: NO` ·
  `Production Ready: NO`.
- **Next:** `QR-09A — Production Validation Remediation`. Not started.

## Module 13 — QR-08 Unified Inbox integration

- **Milestone status:** `QR-08 — Unified Inbox integration — COMPLETE`.
- **Completion:** `52%` evidence-based estimate (was 48% through M13-06B/QR-07).
- **Delivered:** Meta and WAHA conversations in one Inbox — endpoint-scoped inbound stored-message
  dedupe (independent of QR-04's event-level dedupe), server-derived outbound provider routing
  (`SendService.accept_for_conversation`, no client-suppliable provider field), a channel badge and
  provider-aware composer in the existing Inbox UI, and a truthful refuse-to-send state when the
  WAHA session is not connected. Reuses `channel_endpoints` (M13-03) via `WhatsAppQrService.connect()`
  now creating one, rather than a second Contact/Conversation/endpoint authority.
- **Migration:** `0043_conversation_channel_endpoints` — additive expand stage; nullable
  `channel_endpoint_id` on `conversations`/`messages`/`webhook_events`,
  `conversations.phone_number_id` widened to nullable, `ck_conv_endpoint_owner` exactly-one-owner
  check. OpenAPI 206 → 207 paths (`POST /webhooks/waha`).
- **Security:** RBAC unchanged (`inbox:read`/`inbox:write`/`inbox:assign`/`messages:send` reused
  uniformly for both providers); cross-org conversation read/send rejected; a non-text send against
  a WAHA conversation refused (`ChannelCapabilityNotSupportedError`), never silently downgraded or
  rerouted to Meta.
- **Preserved:** Meta behaviour, prohibited capabilities (`BULK`/`CAMPAIGNS`/`TEMPLATE`), no
  MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT for WAHA, no history/media transfer.
- **Next:** `QR-09 — production validation` — attempted; see the section above (`PARTIAL — BLOCKED`).
  This QR-08 record and its `COMPLETE` status are unaffected.

## Module 13 — M13-06B Provider-neutral History & Media Control Plane

- **Milestone status:** `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED`.
- **Completion:** `48%` evidence-based estimate (superseded by QR-08 above, `52%`).
- **Delivered:** lifecycle management for existing history checkpoints and media references, dedicated
  RBAC/flag gates, tenant/object/capability checks, optimistic concurrency, monotonic progress,
  resume/fresh-run semantics, idempotent media identity and immutable Audit evidence.
- **Migration:** `0041_channel_sync_control_plane` seeds only `channels:history_sync`; schema records
  remain those introduced by M13-06A and OpenAPI remains 200 paths.
- **Security:** default-off execution, exact organization scope, disabled endpoint rejection, secret-shaped
  metadata rejection and no public/provider execution surface.
- **Preserved:** no certified provider, adapter, QR/login, provider cursor, event ingestion, history
  retrieval, media-byte transfer, queue task, API, generated contract or frontend change.
- **Next:** provider certification host evidence and separate owner instruction are mandatory before
  any live M13-06 behavior.

## Module 13 — M13-06A Provider-neutral Sync & Media Persistence Foundation

- **Milestone status:** `M13-06A — Provider-neutral Sync & Media Persistence Foundation — REPOSITORY VALIDATED`.
- **Completion:** `44%` evidence-based estimate.
- **Delivered:** provider-neutral history checkpoint and media-reference records, bounded progress/expiry state, tenant-scoped repositories, non-secret metadata validation and migration `0040`.
- **Security:** organization predicates, existing foreign authorities, no secret-shaped metadata, uniqueness/check constraints and optimistic row versions fail closed.
- **Preserved:** no provider certification, adapter, dependency, QR/login, live event ingestion, history execution, media transfer/processing, queue task, API, generated contract or frontend change.
- **Next:** physical-phone WAHA certification **PASSED** on 2026-08-08 and the adapter has since reached QR-03 (pairing). QR-04 event ingestion, QR-05 send/delivery reconciliation, QR-06 session recovery/teardown, QR-07 (the first real operator UI, over the existing session/pairing control plane; OpenAPI 200 to 206 paths) and QR-08 (Unified Inbox integration; OpenAPI 206 to 207 paths) are delivered. Provider history retrieval and media-byte transfer remain unimplemented and are not assigned to a delivered milestone. `QR-09 — production validation` is next; not started.

## Module 13 — M13-05 QR Pairing & Provider Runtime Foundation

- **Milestone status:** `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED`.
- **Completion:** `40%` evidence-based estimate.
- **Delivered:** provider-neutral runtime contracts/registry, runtime registration/discovery/ownership, health/lifecycle/events, capability publication, heartbeat/restart/recovery integration and no-store pairing lifecycle persisted on the existing session authority.
- **Security:** tenant/RBAC/flags fail closed; stale holders require valid fencing; pairing stores no QR/token/credential payload; reason codes are constrained and every transition is audited.
- **Preserved:** no QR image/scanning/login, WhatsApp protocol, provider adapter, synchronization, messaging, webhook, routing, Inbox/Customer 360/Analytics, API path or frontend change.
- **Next:** M13-06 is not started. Host MySQL, multi-node runtime, provider certification, supervisor/monitoring, KMS and rollout commissioning remain pending.

## Module 13 — M13-04 QR Session Manager Foundation

- **Milestone status:** `M13-04 — QR Session Manager Foundation — REPOSITORY VALIDATED`.
- **Completion:** `32%` evidence-based estimate.
- **Delivered:** provider-neutral session lifecycle and state transitions, durable connection-linked session records, discovery/ownership/health/heartbeat/expiration, recovery/restart metadata, capability references, database leases, fencing, optimistic concurrency, tenant/RBAC/flag boundaries and Audit evidence.
- **Security:** secret-shaped metadata is rejected; only existing credential references may be stored; no provider secret or public session API exists.
- **Preserved:** no QR generation/scanning/login, provider adapter/runtime, synchronization, messaging, webhook, routing, Inbox/Customer 360 UI, API path or frontend change.
- **Next:** M13-05 is not started. Host multi-node lease/fencing, runtime monitoring, MySQL/KMS and rollout commissioning remain pending.

## Module 13 — M13-03 persistent channel connections and endpoint records

- **Milestone status:** `M13-03 — Persistent Channel Connections & Endpoint Records — REPOSITORY VALIDATED`.
- **Completion:** `24%` evidence-based estimate.
- **Delivered:** provider-neutral connection/endpoint/encrypted-secret persistence, immutable provider identifiers, lifecycle/health/configuration/metadata facts, soft delete, optimistic locking, tenant repositories, feature gates, Audit references and migration `0037`.
- **Security:** AES-GCM cipher abstraction, secret/key versioning, rotation lineage and revocation; no plaintext API, metadata or Audit exposure.
- **Preserved:** no provider adapter/runtime, QR, synchronization, messaging, webhook, routing, Inbox/Customer 360 UI, API path or frontend change.
- **Next:** M13-04 is not started. Host MySQL/KMS/rollout commissioning remains pending.

## Module 13 — M13-02 customer identity resolution

- **Milestone status:** `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED`.
- **Completion:** `16%` evidence-based estimate.
- **Delivered:** canonical Contact identity aliases, exact scoped resolution, confidence, conflict detection, tenant review queue, recommendations, approve/reject, RBAC, feature flag, Audit/Timeline, migration/API/client.
- **Preserved:** no automatic/destructive Contact merge, provider runtime, QR workflow or M13-03 work.
- **Next:** M13-03 is not started. Host/provider/runtime commissioning remains pending.


- **Module:** Enterprise Omnichannel Channel Manager.
- **Milestone status:** `M13-01 — Generic Channel Foundation — REPOSITORY VALIDATED`.
- **Completion:** `8%` evidence-based estimate for provider-neutral in-process foundations.
- **Delivered:** immutable intent/policy/metadata/health/lifecycle contracts, shared enums and
  validation, provider/capability metadata registries over the existing adapter registry,
  existing-table feature-flag scaffolding and typed DI.
- **Preserved:** no provider, runtime, persistent connection record, migration, API route,
  generated contract, frontend or duplicate CRM authority.
- **Required gap:** persistent connection/endpoint/secret records and Meta backfill from the
  frozen contract remain unimplemented and require explicit sequencing.
- **Next:** M13-02 is not authorized and has not started.
- **Last synchronized:** `2026-08-04T12:56:16+05:30`.

## UI Taste Modernization — Owner Review, Release Candidate Audit and Merge Readiness

- **Status:** `UI-TASTE-05 — REPOSITORY VALIDATED`.
- **Defect fixed:** one verified Major campaign lazy-chunk import cycle; create/edit pages now import
  existing campaign modules directly and preserve all behavior/contracts.
- **Validation:** workflow `30982637585` passes 980 backend tests, 36 frontend files / 671 tests, lint,
  strict typing, OpenAPI/client drift, clean production build, audits and source security scanning.
- **Readiness:** no verified repository-scope Blocker or Major defect remains; branch awaits explicit
  Owner Approval and Merge. Host validation and Production Ready status are not claimed.
- **Completion impact:** Shared Enterprise Design System remains `94%`; Global Search remains `85%`;
  Reactivation remains `94%`; Module 13 remains `44%`. Review-only evidence does not inflate modules.
- **Next:** no implementation milestone is authorized; await Owner Approval and Merge.

## UI Taste Modernization — Responsive, Accessibility and Performance Regression

- **Status:** `UI-TASTE-04 — REPOSITORY VALIDATED`.
- **Delivered:** KYC deep-link permission truth, debounced workspace search, safe empty-result
  keyboard navigation, shared shortcut-modal focus behavior, modal scroll lock, narrow pagination,
  authenticated route splitting and verified dead-code removal.
- **Performance:** main application JavaScript is 199.78/54.87 kB gzip, down from
  733.97/178.29 kB gzip; route behavior and APIs are unchanged.
- **Validation:** workflow `30980229127` passes 980 backend tests, 36 frontend files / 671 tests,
  lint, strict typing, OpenAPI drift, production build, audits and source security scanning.
- **Completion impact:** Shared Enterprise Design System increases from `90%` to `94%`; Global
  Search / Command Palette increases from `80%` to `85%`. Reactivation remains `94%` and Module 13
  remains `44%` because no domain or provider behavior changed.
- **Host boundary:** authenticated browser/device/screen-reader, contrast, touch and production-scale
  performance evidence remains pending.
- **Next:** `UI-TASTE-05 — Owner Review, Release Candidate Audit and Merge Readiness` only after
  explicit owner instruction.

## UI Taste Modernization — Reactivation Operational Hierarchy

- **Status:** `UI-TASTE-03B — REPOSITORY VALIDATED`.
- **Completion impact:** Reactivation increases from `91%` to `94%` because this milestone adds a
  real bounded API query contract, URL-restorable operational views, permission-truthful connected
  navigation, and tested pagination—not visual polish alone.
- **Delivered:** CRM-first route hierarchy; due/overdue/completed prioritization; status, owner,
  label, reminder and date filters through shared controls; 25-case pagination; factual redirects;
  terminal drag correction; responsive board/list and existing drawer preservation.
- **Security:** existing RBAC visibility, tenant query predicates, audit/timeline mutation paths,
  optimistic concurrency, and sensitive-data boundaries remain authoritative.
- **Preserved:** Module 13 remains `44%`; no provider evaluation/certification/runtime/session,
  ingestion, history, media, dependency, migration, or production credential work.
- **Validation:** 4 focused backend tests, 980 total backend tests,
  35 frontend files / 668 tests, production build and security gates pass;
  authenticated host visual/WCAG/device/performance review remains pending.
- **Next:** `UI-TASTE-04 — Responsive, accessibility, and performance regression`.

## UI Taste Modernization — operator-first Dashboard

- **Starting baseline:** `7d826987c272d28038663ba9cb15c832c37e2b02`.
- **Status:** `UI-TASTE-03A` is implemented and repository-validated; authenticated representative-
  data visual/reference review remains pending.
- **Delivered:** cross-domain attention queue; blocked customer, KYC, SIM, Activation, Campaign,
  Inbox, Template, agent-workload and today-KPI decision support; signed-in task snapshot; truthful
  partial-source states; source deep links; responsive table/card transformations.
- **Preserved:** backend, migrations, 193-path OpenAPI, generated contracts, permissions, source
  workflows, sidebar/navigation, primary action links and existing shared design system.
- **Performance:** operational workspace is lazy-split at 31.96 kB / 8.61 kB gzip; main chunk is
  733.62 kB / 178.16 kB gzip, down from the Priority 1 measurement of 747.91 kB.
- **Next:** Reactivation operational hierarchy only; approved previously and not started on the target
  branch.

Completion percentages remain evidence-based domain/product estimates. Host visual acceptance and
production-scale exact aggregate totals are not claimed by repository-only validation.

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Dashboard | 82% | UI-TASTE-03A replaces the messaging-led home with a permission-aware operational desk over real Reactivation, KYC, Task, Campaign, Inbox, Template and Analytics sources; 661 frontend tests and production build pass | Authenticated representative-data visual/WCAG/browser review, server-owned exact cross-domain aggregate totals beyond bounded source reads, and final route-performance commissioning. | Reactivation, KYC, Tasks, Campaigns, Inbox, Templates, Analytics |
| Inbox | 91% | Shared Inbox + Live Chat plus CORE-07 exact-contact reuse; UI-TASTE-02 converges search, advanced filters, saved views, bulk selects, and pagination on shared accessible controls | Page-specific hierarchy polish, intervention-request lifecycle, SLA badges, and authenticated responsive/accessibility regression. | Notifications, SLA, shared design system |
| Chat History | 55% | A dedicated, permission-aware `/chat-history` route now composes the existing conversation/message contract — search, status, agent and channel filters, cursor pagination, full message history and an `audit:read`-gated audit-trail deep link — separate from Live Chat's live-triage workspace | Date-range and campaign-generated filtering require a contract extension (`MessageResponse` carries no `campaign_id`; the endpoints have no date-range query param); media-only filtering and audit-scoped filtering are not implemented; transcript export and a Download Center remain unimplemented. | Audit, Download Center |
| Contacts | 95% | FR-CON-04 baseline plus UI-TASTE-02 shared search/filter/mobile-sheet/pagination convergence | Page-specific table and bulk-action polish, final opt-in/eligibility/assignment/export regression, and server-shared saved views; no rebuild. | Saved Views, Reactivation, shared design system |
| Customer 360 | 90% | CORE-07 factual workspace composes identity/attributes, WhatsApp threads/messages, Reactivation CRM/reminders/notes/SLA, Tasks, Documents, KYC/SIM/Activation, Campaigns, Audit and Timeline with permission-aware source deep links | UI-TASTE hierarchy/density pass, target-device/WCAG, representative-data query-budget and production-scale commissioning; incorporate future approved source-domain facts without duplicating them. | Source domain milestones, performance lab, shared design system |
| Campaigns | 85% | Broadcast engine, guided journey and existing authorization safeguards complete | Conversion/ROI to reactivation, failed-message retry UX and complete audience reports; no generic approval engine is required. | Reactivation analytics |
| Templates | 80% | Registry, create/sync/status/media flows complete | Categories/favourites server sync, button/variable preview regression, usage analytics, explicit AI placeholder. | Analytics, settings/Meta sync |
| Segments | 75% | Dynamic/static segment and preset foundation | Complete reactivation/KYC/documents/activation/engagement predicates and shared saved filters. | Domain models, Saved Views |
| Automation | 65% | Definitions, safe test runtime, trigger receipts and existing authorization concepts complete | Governed live receipt consumption, conditions/actions, delays, reminders, module-specific handoff, idempotent effects and operational UI. | Notifications, domain services |
| Analytics | 55% | Messaging rollups and exports complete | Add reactivation funnel/drop-off, lead source, KYC turnaround, case outcomes, SLA, agent comparison, and date exports. | Domain events and reporting projections |
| Executive Reports | 25% | Analytics-backed report shell | Revenue/ROI/productivity/workload/SLA/case-outcome reports, schedules, CSV/PDF delivery. | Analytics, Download Center, Notifications |
| Reactivation | 94% | CORE-05/07/09 authorities plus UI-TASTE-03B CRM-first hierarchy, URL-backed work views, shared filters, permission-truthful connected navigation, bounded 25-case pagination and 668-test frontend validation | Server-shared saved views, reactivation analytics, authenticated representative-data visual/WCAG/device review and production-scale performance commissioning. | Tasks, Notifications, Analytics, shared design system |
| KYC | 85% | CORE-04 persisted queue/detail workspace, three governed checks, protected Aadhaar/PAN checklist references, Task-backed appointment lifecycle, separated reviewer/manager decisions, structured rejection, immutable audit/Timeline, SLA, Customer 360 and Reactivation handoff complete | Server pagination/saved views, production protected-media commissioning, high-volume performance, and target-browser/device WCAG regression. | Documents, Tasks, Reactivation, Customer 360 |
| Documents | 87% | Phase 4A governed documents plus CORE-04 verified Aadhaar/PAN purpose references without plaintext identity numbers | Download policies, generated-document links and final encryption/retention commissioning; no generic approval authority is required. | Download Center |
| SIM Orders | 35% | CORE-02 order/event lifecycle, address/service area, owner, serial, delivery/failure/customer confirmation, SLA and APIs are preserved; CORE-05 exposes the lightweight `SIM Required` case status | No standalone heavy UI is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, KYC evidence, SLA |
| Activation | 35% | CORE-02 record lifecycle, hand-off, verification/approval/completion/rejection rules, RBAC, audit and APIs are preserved; CORE-05 exposes `Activation Pending`, `Completed` and `Not Required` case outcomes | No standalone Activation Queue or generic approval engine is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, Notifications |
| Notifications | 85% | CORE-09 durable center plus UI-TASTE-02 shared type/status/date/assignee filters and action controls; polling, read-state, team view and deep links are preserved | Page-specific visual hierarchy, authenticated responsive review, notification settings, and separately approved optional channels. SSE/browser push/email/internal WhatsApp are not implied. | Tasks, Reactivation, user preferences, shared design system |
| Settings | 80% | Organization/application/flags/preferences routes complete, plus permission-aware Tags, Canned Messages and User Attributes administration panels | Approved business/WhatsApp hours/messages, assignment/auto-resolve/read receipts, campaign/opt-in, pipeline/SLA/notifications/security/audit controls. | Domain configuration APIs, RBAC |
| API | 87% | 200-path OpenAPI 3.1 contract; M13-02 adds seven identity-resolution/review paths with generated TypeScript authority | Remaining final-domain routes, usage logs/IP restrictions completeness, key regeneration/revocation UX, published documentation. | Each domain milestone, Download Center |
| Webhooks | 80% | Provider webhooks and operations surface complete | Subscription governance, delivery/retry visibility, outbound final-domain events, security/usage documentation. | Domain event taxonomy, API permissions |
| Google Sheets | 0% | Not implemented | Approved credential model, contact import/sync/export jobs, mapping, audit, retries, admin UX. | Jobs, API keys/secrets, Contacts |
| WhatsApp Scan | 15% | Honest non-executing Scan Studio shell | Compliant provider contract, upload/batches/dedup/queue/results/retry/export/segments/analytics; no unofficial Web scanning. | Owner-approved compliant method, Jobs, Segments, Download Center |
| Approval Workflow | 20% | **CORE-08 — Skipped: Not required by product owner.** Existing KYC-specific approval logic and completed campaign/automation authorization safeguards are preserved. | No Approval Center, generic approval framework, approval queue, escalation system or new approval authority will be built. | Existing module-specific RBAC and audit only |
| Download Center | 30% | Backend export jobs exist | Unified user route for CSV/PDF/campaign/contact/scan/generated artifacts, status, expiry, permissions, and history. | Export jobs, Documents |

## Additional scope modules

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Enterprise Omnichannel Channel Manager | 44% | M13-00–M13-06A are Repository Validated: provider-neutral contracts, exact Contact identity, persistent connections/secrets, durable session/runtime/pairing control plane, sync checkpoints and media references; migrations `0036`–`0040`; unchanged 200-path API | WAHA host certification, live QR/login, event ingestion, history execution, media transfer, messaging and UI remain pending and blocked | Existing Contact/Organization/ChannelConnection/ChannelSession/ChannelAdapter/MediaAsset/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020/0021 and Design Document 33 |
| Shared Enterprise Design System | 94% | UI-TASTE-02 implements governed radius/density, forms, toolbars, filters, pagination, page headers and shared surface refinements with 657-test validation | Authenticated representative-data visual/reference approval, remaining priority-screen adoption, remaining authenticated host visual/reference approval and final WCAG/browser matrix. | UI-TASTE-03–05 |
| Team Management | 80% | Users, roles, permissions, workload foundations complete | Online presence, assignment rules, login history, permission audit, final role matrix. | Notifications, audit, Settings |
| Tags and Attributes | 96% | Both halves of this row are now reachable in the product: tag CRUD through Settings → Tags (search, usage filter, create/rename/recolour/delete, usage counts) and attribute-definition CRUD through Settings → User Attributes (search, type filter, create/edit/delete, immutable key/type display); contact links, filters and existing domain schemas complete | Required/active controls and final domain-specific fields for attribute definitions; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 85% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 35% | Local favourites/recent destinations and inbox views exist | Server synchronization and sharing for contacts, campaigns, reactivation, KYC, reports, and chat history. | Users/RBAC, module filters |
| Audit Timeline | 90% | CORE-07 exposes distinct Customer Timeline and Audit views over existing immutable evidence, including source references and deep links | Normalize remaining old/new values, device/login, generalized approvals and document-access evidence. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
