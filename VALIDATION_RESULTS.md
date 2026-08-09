# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence and
> separates repository-verifiable engineering gates from target-host visual/commissioning evidence.

Last synchronized: `2026-08-09T21:16:07+05:30`.

## QR-09J — WAHA Inbound Timestamp Normalization Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D12 is `REMEDIATED`. QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline | PASS | Local/origin matched `ui/taste-modernization` at `8385adc9a62fd9c570198ba7f2834154869031cc`; worktree clean except accepted `.claude/`. |
| D12 reproduction | PASS | The real external text reached `message` and `message.any` with `fromMe=false`, valid SHA-512 HMAC and the owned WAHA endpoint. Both processing attempts failed with `TypeError: can't compare offset-naive and offset-aware datetimes`; two dead letters were preserved and zero Inbox messages existed. |
| Root cause | PASS | WAHA translated the provider epoch to aware UTC, while `app.db.mixins.utcnow()` and MySQL DATETIME use naive UTC. Conversation window evaluation therefore compared an aware provider-derived value with naive repository time. |
| Remediation | PASS | The provider epoch is converted to UTC and stripped to naive UTC at `to_inbound_message()`, before it enters shared Contact/Conversation/Message authorities. Global datetime semantics, window rules, ordering, provider payloads and ACK ranks remain unchanged. |
| Unit/integration regression | PASS | New explicit timestamp-normalization test plus the existing certified `message`/`message.any` dedupe integration now carry a real provider timestamp and assert one conversation, one message, unread count 1 and naive `last_inbound_at`. Focused related selection **174 passed**. |
| Real MySQL replay | PASS | The two preserved failed source events were enqueued through the existing idempotent webhook processor, not edited in MySQL. Both source rows became `processed` on attempt 2; exactly one endpoint-scoped inbound text with provider identity was stored, and the duplicate variant did not increment unread count. The original dead-letter rows remain preserved as historical D12 evidence. |
| Actual Inbox API | PASS | Conversation detail and message-history endpoints both returned HTTP 200; the exact safe token appeared once as `direction: inbound`, `status: accepted`, connector `waha`, unread count 1 and matching preview. No phone/provider identity was exposed. |
| Provider preservation | PASS | Same live container id/start time, restart count 0, exact digest `sha256:33ecd1b7…f2d75e`, health `healthy`, loopback-only port and unchanged persistent volume. Provider remained WORKING and application active/paired/connected with no QR. |
| Canonical premerge | PASS | **14/14 PASS in 684.7s**: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1437 backend tests**; **806 frontend tests**; build; Bandit; dependency/browser audits; tracked-source vulnerability/secret/IaC scan. Two unchanged moderate React Router advisories remain below the high/critical gate. |
| Applicable release/runtime | PASS | **8/8 PASS in 87.9s**: development Compose, exact-digest QR negotiation, provider-generated signed webhook/retry/restart, production release contract/build, backend/frontend image contracts, image vulnerability scans and SBOM. The canonical health step was intentionally not rerun because it restarts the protected live service; no deploy/health code changed and QR-09I's isolated exact-digest health proof remains applicable. |
| UI preview | PASS | No frontend source changed. Runtime evidence used the actual Inbox JSON APIs; no screenshot or supported-browser/target-host claim is made. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route/schema/RBAC/capability/digest/config/storage/approval change; no secret, QR or unmasked identity emitted. Meta rotation remains `PENDING — OWNER DEFERRED`. |
| Remaining external gates | PENDING – Host Machine Validation | Real outbound Inbox reply, SERVER/DEVICE/READ and out-of-order ACK monotonicity, linked-session restart/reconnect, logout/re-authentication, Meta token rotation, and supported-browser/target-host evidence remain unperformed. |

## QR-09I — Pairing Window Renewal and Post-Scan Convergence Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D11 is `REMEDIATED`. QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline | PASS | Local/origin matched `ui/taste-modernization` at `e2f045fb517102e56ca9651726dfb9ef322cd861`; worktree clean except accepted `.claude/`. |
| D11 reproduction | PASS | Real MySQL held one durable `initializing`/`pairing_available` session whose short-lived availability expiry had passed, while the exact certified WAHA container held the same configured session at `WORKING` with an identity present. The old equal-state path neither renewed expiry nor allowed convergence, so polling remained trapped after a successful physical scan. |
| TTL contract | PASS | Repository contracts define `pairing_ttl_seconds` as the lifetime of the ephemeral pairing representation, not a deadline that invalidates provider-established credentials. The ordinary expired transition rejection remains unchanged. |
| Renewal | PASS | An explicit pairing request in `PAIRING_AVAILABLE` renews expiry through a lease/fence/version-checked manager operation. State, `pairing_revision` and `pairing_changed_at` remain stable; `row_version` and a redacted Audit event advance. Read-only polling does not renew. |
| Post-scan convergence | PASS | Expired local availability can converge only when a fresh provider observation is `WORKING`, contains an identity, and names the configured session. It transitions to `PAIRED`, clears expiry, preserves the pairing revision, and records only a boolean identity-presence fact. Missing identity, wrong session, outage and reached-provider conflict all fail closed. |
| Live application proof | PASS | The actual backend, real MySQL/Redis and unchanged linked WAHA container returned HTTP 200 with application state `active`/`paired`, provider `WORKING`, `connected: true`, `qr_available: false`, and only masked identity. Durable connection/session and provider session counts remained one; linked message count remained zero. |
| Provider preservation | PASS | Exact digest `sha256:33ecd1b7…f2d75e`, WAHA 2026.7.2 / NOWEB / CORE, same live container start time, restart count 0, health `healthy`, loopback-only development exposure, and unchanged `waha-sessions:/app/.sessions`. No stop/restart/logout/delete/create/new QR/rescan/message or manual database mutation. |
| Focused regression | PASS | Pairing/runtime/QR regressions **65 passed**; broader lifecycle/lease/Inbox/webhook selection **453 passed**; frontend QR suite **36 passed**. Renewal, stale lease/fence/version, narrow identity convergence and fail-closed cases are covered. |
| Full quality/release gates | PASS | Canonical premerge **14/14 PASS** in 369.6s: **1436 backend tests**, **806 frontend tests**, lint/types/OpenAPI/build/SAST/audits/scans. Nine release/runtime gates also passed: both Compose contracts, exact-digest isolated health positive/negative and restart proof, certified QR/webhook validators, release/image contracts, image scans and SBOM. |
| Live-health substitution | PASS (qualified) | The canonical health validator explicitly restarts service `waha`, so it was not run against the protected owner-linked container. A uniquely named, internal-only container and volume at the exact certified digest proved the same health command succeeds against responsive `/health`, fails against an unavailable target, reaches healthy before/after restart, retains zero sessions, and was then removed. This is recorded as a substitution, not a claim that the monolithic release runner executed unchanged. |
| UI preview | NOT APPLICABLE | No frontend source changed; existing QR tests prove the connected/no-QR view. Local screenshot automation was unavailable because its browser runtime could not initialize, so no screenshot or browser-matrix evidence is claimed. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route/schema/RBAC/capability/digest/storage/approval change; no QR, identity, token or secret emitted. Meta token rotation remains `PENDING — OWNER DEFERRED`. |
| Remaining external gates | PENDING – Host Machine Validation | Real inbound external text, outbound Inbox reply, SERVER/DEVICE/READ and out-of-order ACK monotonicity, linked-session restart/reconnect, logout/re-authentication, Meta token rotation, and supported-browser/target-host evidence remain unperformed. |

## QR-09H — Expired QR Existing-Session Recovery Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D10 is `REMEDIATED`. QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline | PASS | Local/origin matched `ui/taste-modernization` at `54453a58b575e0cec9afa7769d749c7c37b92c65`; worktree clean except accepted `.claude/`. |
| D10 reproduction | PASS | Natural unscanned QR lapse left provider session `waha` at `FAILED`, `me: None`, never paired, durable `waiting_for_pairing`/`pairing_available`. Governed "Get a new QR code" produced app `503` from provider `422 Session already exists`; `reconnect` `409`; `connect` idempotent no-op. |
| Certified provider matrix | PASS | On the exact digest, `start` on `FAILED` answers `201` and changes nothing (12 polls / 36s). `stop` → `STOPPED`; `start` → `STARTING` → `SCAN_QR_CODE` in ~6s. Session count 1, `me: None`, `noweb` store config byte-identical before and after. |
| Recovery primitive | PASS | Existing non-destructive `stop_session`/`start_session`. No delete, no recreate, no logout, no new client method, no `PUT`. |
| Adapter boundary | PASS | New `prepare_pairing()`; `begin_pairing()` unchanged, so QR-03's no-guessing-on-conflict principle and its regression still hold. Create is attempted first, so the ordinary first-pairing call sequence is byte-identical. |
| Case coverage | PASS | Missing session → create; already `SCAN_QR_CODE` → reused untouched; `FAILED` → stop+start; already `STOPPED` → start only, no redundant stop; provider-reported linked account → refused; durable `PAIRED` → refused before any provider call. |
| Error classification | PASS | `ChannelTransportError` → `ServiceUnavailableError`; reached-provider `ChannelApiError` → `ConflictError`; configuration/authentication keep existing semantics. Provider body text never echoed — asserted absent from operator messages. |
| Lease and concurrency | PASS | `prepare_pairing` refuses without a runtime lease; all provider mutation ran under one lease (single `request_id`); a stale row version is still refused by `acquire_lock`. |
| Focused regression | PASS | 13 new backend tests. With the fix reverted **9 of 13 fail**; the 4 that pass assert deliberately unchanged behaviour. Focused QR/pairing/adapter/recovery/lifecycle/session suites **270 passed**. |
| Real runtime recovery | PASS | Genuine natural expiry recovered through the **actual frontend**: one `request_id` performed refused create → live read → `stop` `201` → `start` `201`; UI advanced to the scan state. Provider 1 / durable connection 1 / durable session 1 throughout; no database intervention. |
| Application QR endpoint | PASS | Two consecutive requests returned `200`, `image/png`, `Cache-Control: no-store, private, max-age=0`, `Pragma: no-cache`; body measured for length only (5360 bytes) and never printed, saved, logged, audited or screenshotted. |
| Repeat recovery | PASS (qualified) | One runtime recovery from a **natural** expiry, plus a second runtime recovery from an already-stopped session proving the skip-redundant-stop branch. A controlled `stop` was **not** counted as a second natural expiry: it yields `STOPPED → PAUSED`, whereas natural expiry yields `FAILED → DEGRADED` — a materially different durable state. Deterministic repeatability is covered by `test_expired_qr_recovery_is_repeatable`. |
| Full release gate | PASS | **23/23 PASS** in 508.9s: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1431 backend tests**; **806 frontend tests**; production build; Bandit; dependency/browser audits; tracked-source vulnerability/secret/IaC scan; certified WAHA health, QR and webhook gates; production release/image contracts; image scan and SBOM. |
| UI preview | NOT APPLICABLE | Backend/provider orchestration only; no frontend source changed. The existing QR-expired action was exercised through the real application as runtime evidence. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route, schema, RBAC, capability, digest, storage or provider-approval change. |
| Known adjacent gap (not QR-09H) | RECORDED | With the durable row `PAUSED` and the provider session present but non-working, the QR-09G projection downgrades a successful observation to not-observed, so the surface renders provider-unavailable and offers no pairing action even though `POST /session/pair` recovers it. Reachable mainly through out-of-band provider administration, not natural QR expiry. Not a QR-09H regression; recorded for separate governance. |
| Remaining external gates | PENDING – Host Machine Validation | Meta token rotation owner-deferred. Physical-phone pairing, inbound/outbound/ACK, restart persistence, logout/re-authentication and the supported-browser/target-host matrix remain unperformed. |

## QR-09D — Pairing Action State Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D6 is `REMEDIATED` by repository,
real-runtime and local-browser evidence, on top of the committed QR-09G backend. QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline | PASS | Local/origin matched `ui/taste-modernization` at `a7b920e0ca9fcd7258f38b9fcb4afcbacf7f9178` (QR-09G). Tracked modifications were exactly the three QR-09D frontend files; the preserved patch `qr09d-post-qr09f-current.patch` re-verified at SHA-256 `2278b61072cf4959e83463d4eb579018598f2c941d64ff7f3bf2947abf896ffe` and reapplied with `git apply --check` clean and no conflict. QR-09G was not reverted or re-committed. |
| D6 root cause | PASS | With a durable session present and the provider reachable but holding none, the projection returned `ready-to-connect`, re-offering an idempotent `connect()` that cannot create provider state; `POST /session/pair` was therefore operationally unreachable and every poll re-asserted the dead end. |
| Fix | PASS | The durable application session is the boundary: no durable session keeps `ready-to-connect`; a durable never-paired session with a live session-missing observation projects a provider-neutral `ready-to-pair` whose primary action calls `POST /session/pair`. |
| State precedence | PASS | not-configured → connected → reauth-required → provider-unavailable → ready-to-pair → ready-to-connect → qr-available → STARTING ambiguity (QR-02/QR-06) → reconnect, all preserved. The session-missing branch is reached only on a live observation the backend emits exclusively of a transport outage, so QR-09F outage truth still outranks ready-to-pair, qr-available, creating-session, connecting and reconnect. |
| Test reconciliation | PASS | The historical patch's test file genuinely conflicted and was not applied; regressions were reconciled by hand. All QR-09F outage regressions preserved. Focused QR frontend suite **36 passed**; full Vitest **806 passed** across 38 files (798 → 806, +8). |
| D6 real runtime | PASS | Real MySQL/Redis/backend/frontend with certified WAHA `sha256:33ecd1b7…f2d75e`, `2026.7.2 / NOWEB / CORE`. `ready-to-pair` rendered from a genuine provider-reachable, session-absent, never-paired state and survived **eight consecutive live three-second polls** with Begin pairing present and Connect WhatsApp absent throughout. |
| D6 action integrity | PASS | Activating Begin pairing in the actual browser issued exactly **one** `/session/pair` and **zero** `/session/connect`, leaving exactly one provider session (`SCAN_QR_CODE`) and one durable connection and session. Server-side WAHA logs show one create per pairing action, no duplicates. |
| Application QR endpoint | PASS | Two consecutive requests returned `200`, `image/png`, `Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`; provider and durable counts unchanged. Bytes were consumed in memory and never printed, saved, persisted, logged, audited, displayed or scanned. |
| D8 outage regression | PASS | A genuine outage rendered the unavailable state with no pairing, connect, scan or connecting affordance; the QR request tally stayed frozen and no QR element mounted. The same container, volume, provider session and durable session recovered without duplication. |
| D9 recovery through the UI | PASS | A paused, never-paired session with the provider session absent renders `ready-to-pair`; activating it recovered to `waiting_for_pairing` with exactly one provider session and one durable connection/session, with no database intervention. |
| Local responsive/accessibility evidence | PASS | Actual running application at 1920×1080 and 390×844 in `ready-to-pair`, plus the provider-unavailable state. No QR visible (zero image elements) and no PII. No horizontal overflow at either size; keyboard `Tab` reaches Begin pairing with a visible 2px focus ring; mobile control measures 118×40 (118×36 desktop). Local runtime captures only — not target-host or browser-matrix acceptance. |
| Full release gate | PASS | **23/23 PASS** in 635.1s on the combined tree: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1418 backend tests**; **806 frontend tests**; production build; Bandit; dependency/browser audits; tracked-source vulnerability/secret/IaC scan; certified WAHA health, QR and webhook gates; production release/image contracts; image scan and SBOM. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route, schema, RBAC, capability, digest, storage or provider-approval change. No credential, QR or session material is exposed. |
| Remaining external gates | PENDING – Host Machine Validation | Meta token rotation owner-deferred. Physical-phone pairing, inbound/outbound/ACK, restart persistence, logout/re-authentication and the supported-browser/target-host matrix remain unperformed; QR-09 stays `PARTIAL (BLOCKED)`. |

## QR-09G — Paused Never-Paired Session Recovery Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D9 is closed by repository and
real-runtime evidence. QR-09D and QR-09 remain `PARTIAL (BLOCKED)`.
`Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline and QR-09D isolation | PASS | Local/origin matched `ui/taste-modernization` at `3bbde4ef16d1c3fa79c5ce2c980a717f82435cb0`. The current post-QR-09F QR-09D frontend work was preserved outside the repository as `qr09d-post-qr09f-current.patch`, SHA-256 `2278b61072cf4959e83463d4eb579018598f2c941d64ff7f3bf2947abf896ffe`, covering exactly `WhatsAppQrConnect.tsx`, `viewState.ts` and `whatsapp-qr.test.tsx`; the three files were restored to HEAD and `git apply --check` re-verified clean. QR-09G contains no frontend change. |
| D9 reproduction | PASS | Durable session `PAUSED` with `pairing_available` (never `PAIRED`), provider healthy and holding zero sessions. `GET` reported `provider_session_missing: false` with stale `provider_status: STOPPED`; `pair` returned `409 "The session is paused and cannot acquire a runtime lease"`; `reconnect` returned `409` instructing the operator to pair; `connect` was an idempotent no-op. No `lock_acquired` audit event occurred after the pause. |
| Root cause | PASS | `map_session_status` maps `STOPPED → PAUSED`; `SessionManager._assert_operable` refuses a lease for `PAUSED`; `get_status` suppressed that `ConflictError`, leaving `NOT_OBSERVED` and a stale projection permanently. The documented `PAUSED → INITIALIZING` escape was reachable only through `can_reconnect`, which requires durable `PAIRED`. |
| Invariant preserved | PASS | `SessionManager` still refuses to lease a `PAUSED` row; a direct `acquire_lock` probe on the paused session still raises `ConflictError`. QR-09G leaves `PAUSED` before leasing rather than weakening the rule, reusing the pattern `reconnect()` established. |
| Narrow recovery scope | PASS | Recovery applies only when the pairing state is not `PAIRED` — the sole state meaning credentials existed, terminal in `LEGAL_PAIRING_TRANSITIONS`, and covered by `can_reconnect`. A paused paired session still raises `ConflictError` from `begin_pairing`, creates no provider session, and keeps `PAIRED`/`PAUSED` intact. |
| Projection correction | PASS | A row that cannot be leased is still read. Missing-session and unreachable-provider facts are reported truthfully; a successful observation is downgraded to `NOT_OBSERVED` because it cannot be applied without the lease. Reads create/start/mutate nothing — verified all provider calls were `GET` with no QR request. |
| Focused regression | PASS | Ten new backend tests; `test_whatsapp_qr.py` **41 passed**. With the fix reverted **8 of 10 fail**; the 2 that pass assert deliberately unchanged behaviour. Focused QR/session/recovery/lifecycle regression **189 passed**. |
| Real runtime recovery | PASS | Real MySQL/Redis/application with certified WAHA `sha256:33ecd1b7…f2d75e`, `2026.7.2 / NOWEB / CORE`. Status stopped claiming a false outage while leaving `row_version` at `2221` (read mutated nothing); `POST /session/pair` returned **200**; session moved `paused → initializing → SCAN_QR_CODE`. |
| Transition-before-lease ordering | PASS | Audit trail: `channel_session.transitioned → initializing` (`row_version 2222`) precedes `channel_session.lock_acquired` (`row_version 2223`, fencing `867 → 868`), then `lock_released` (`row_version 2225`). |
| Session-count integrity | PASS | Exactly one provider session (`SCAN_QR_CODE`), exactly one durable connection and one durable session after recovery. No duplicate provider or durable session, and no database intervention was required. |
| Full release gate | PASS | **23/23 PASS** in 506.1s: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1418 backend tests**; **798 frontend tests**; production build; Bandit; dependency/browser audits; tracked-source vulnerability/secret/IaC scan; certified WAHA health, QR and webhook gates; production release/image contracts; image scan and SBOM. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route, schema, RBAC, capability, digest, storage or provider-approval change. No credential, QR or session material is exposed. No QR was displayed, persisted or scanned. |
| UI preview | NOT APPLICABLE | QR-09G is backend/control-plane only; no frontend source changed, so no preview evidence is claimed. |
| Remaining external gates | PENDING – Host Machine Validation | Meta token rotation owner-deferred. QR-09D closure and physical-phone QR-09 validation remain outstanding; QR-09 stays `PARTIAL (BLOCKED)`. |

## QR-09F — Provider-Outage QR Availability Projection Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D8 is closed by repository, real-runtime
and local-browser evidence. QR-09D and QR-09 remain `PARTIAL (BLOCKED)`.
`Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline and QR-09D isolation | PASS | Branch/local/origin matched `ui/taste-modernization` at `900eaf47a319734cc5df3d07cbb8348d2a47e96a`. The QR-09D three-file patch was preserved outside the repository with SHA-256 `bb78f0bf69acfd818cd7a7ae14ec1adfcb2ce3e4ac4c46a4a2c1dd6227562844`, reverse-restored, and direct apply-check passed before QR-09F work. |
| D8 clean-baseline reproduction | PASS | With genuine WAHA transport loss and one existing provider session, status returned durable `pairing_available`, stale `provider_status: SCAN_QR_CODE` and incorrect `qr_available: true`; the frontend mounted QR retrieval and backend logs recorded repeated `/api/waha/auth/qr` attempts. |
| Root cause | PASS | Backend reconciliation collapsed transport failure and successful observation into the same boolean path, then derived QR action from durable/stale facts. Frontend evaluated QR/action states before the current outage signal. |
| Backend fail-closed projection | PASS | Typed observation distinguishes observed, provider-session-missing and unavailable. During outage: provider status null, QR/connected/healthy/reconnect false, reason `provider_unavailable`, safe detail; durable pairing/reauthentication data remains unchanged. |
| Frontend fail-closed projection | PASS | Current `provider_unavailable` outranks stale QR, creating, connecting and reconnect states. Rendered regression proves unavailable UI, no QR image/action and zero QR request; manual retry after restored status mounts exactly one legitimate request. |
| Focused regression | PASS | Backend QR suite **31 passed**; frontend QR suite **28 passed**; TypeScript and ESLint pass. Tests also prove no create/start/delete/QR side effect and recovery without durable-state mutation. |
| Genuine outage and polling | PASS | Real MySQL, Redis, actual backend/frontend and exact certified WAHA. Outage projection held for more than three polling intervals; clean backend log windows contained zero QR endpoint/handler request and no unhandled error. |
| Recovery/session preservation | PASS | Same WAHA container returned healthy; exact digest/version/engine/tier and `waha-sessions:/app/.sessions` remained. Exactly one provider session survived in `SCAN_QR_CODE`; the same durable application session recovered without recreation. |
| Legitimate QR regression | PASS | After recovery, one application QR request returned `200 image/png`, `Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`. Bytes stayed in memory and were not printed, persisted, displayed or scanned. |
| Local responsive/accessibility evidence | PASS | Actual local route at 1920×1080 and 390×844 showed Unavailable, no QR/action/connecting state and no horizontal overflow. Keyboard focus reached “Check again”; mobile control measured 110×40. No PII, phone identifier or QR appears. |
| Full release gate | PASS | **23/23 PASS** in 474.4s: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1408 backend tests**; **798 frontend tests**; build; Bandit; dependency/browser audits; source vulnerability/secret/IaC scan; certified WAHA health, QR and webhook gates; production release/image contracts; image scans and SBOMs. |
| Contract/security invariants | PASS | Migration `0043`/44 revisions and OpenAPI 207 paths unchanged; no route/schema/RBAC/capability/digest/storage/approval change. Development WAHA remains loopback-only and production internal-only. No credential, QR/session material or proprietary reference asset is exposed. |
| QR-09D boundary | PASS | Preserved patch was not combined, reapplied or committed. Its post-commit compatibility is reported separately and never used to alter QR-09F. |
| Remaining external gates | PENDING – Host Machine Validation | Meta token rotation is owner-deferred. QR-09D revalidation, physical-phone scan/inbound/outbound/ACK/restart/reconnect/logout and supported-browser/target-host validation remain unperformed; QR-09 stays `PARTIAL (BLOCKED)`. |

## QR-09E — WAHA QR Content Negotiation Remediation

**Milestone status: `REPOSITORY/RUNTIME VALIDATED`.** QR-09-D7 is closed by repository and exact-
certified-runtime evidence. QR-09D and QR-09 remain `PARTIAL (BLOCKED)`.
`Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline and isolation | PASS | Branch/local/origin matched `ui/taste-modernization` at `e15919d5644ba2ca752af52b038458a006c601c4`. The three QR-09D frontend changes were exported outside the repository, verified as an exact three-file patch, and restored before QR-09E work; `.claude/` remained the only unrelated untracked path. |
| D7 reproduction | PASS | Exact authenticated provider matrix: `Accept: application/json` → `200 application/json`; no explicit Accept, `image/png`, and `image/*` → `200 image/png`. Clean-baseline application QR endpoint returned truthful `409 application/problem+json`; no QR body was printed or persisted. |
| Root cause | PASS | `WahaClient._get_bytes()` inherited the client's JSON default Accept header. WAHA 2026.7.2 honors response content negotiation even with `?format=image`, so it returned JSON and the adapter correctly failed closed on the non-image representation. |
| Selected negotiation | PASS | JSON requests retain `Accept: application/json`; only the QR byte request sends explicit `Accept: image/png`. Existing API-key authentication, timeout/error translation and content-type validation remain unchanged. |
| Focused regression | PASS | QR tests assert JSON/image header separation, API key presence without leakage, exact PNG bytes, JSON/HTML rejection, body secrecy, 401/403 handling, 400/404/500/503 status preservation, timeout and transport mapping. Focused WAHA/QR suite: **241 passed**. |
| Exact certified runtime | PASS | New isolated gate starts `devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`, verifies `2026.7.2` / `NOWEB` / `CORE`, reproduces JSON negotiation, then obtains an in-memory PNG through the repository client. |
| Live application endpoint | PASS | Two consecutive authenticated application QR fetches returned `200 image/png` with `Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`. Response bodies were consumed only in memory and discarded. |
| Duplicate/session invariant | PASS | Repeated application fetches left exactly one provider session, one durable connection and one durable session. The disposable regression creates exactly one ephemeral session, mounts no session volume and removes only its uniquely labelled container. |
| QR confidentiality | PASS | No QR body, screenshot or encoded value was displayed, logged, printed, saved, audited or committed; no physical scan occurred. Non-image error markers are absent from exceptions and logs. |
| Persistent storage/network | PASS | Governed `waha-sessions:/app/.sessions` remains intact. Runtime gates retain development loopback-only exposure and no production WAHA publication. No provider capability, pairing state or session storage was changed by the remediation. |
| Full release gate | PASS | **23/23 PASS** in 800.3s: Ruff; strict mypy (300 files); OpenAPI drift; frontend lint/types; browser-test types; **1407 backend tests**; **796 frontend tests**; production build; Bandit; Python/frontend/browser audits; source vulnerability/secret/IaC scan; certified WAHA health, QR and signed-webhook runtime gates; production release/image contracts; image vulnerability scans and SBOMs. |
| Dependency findings | PASS | Python audit found no known vulnerabilities; browser audit found none. Frontend production audit retains two moderate React Router advisories below the repository's high/critical failure threshold; no dependency changed in QR-09E. |
| Contract invariants | PASS | Migration head remains `0043` (44 revisions); OpenAPI remains 207 paths; frontend source, routes, schemas, RBAC, provider capabilities, certified digest and approval state are unchanged. |
| UI preview | PASS | Not applicable: QR-09E changes provider response negotiation only and introduces no operator-facing UI change or screenshot evidence. |
| QR-09D boundary | PASS | Preserved patch remains external and was not reapplied or committed. QR-09D remains `PARTIAL` pending its own reapplication/revalidation under explicit owner direction. |
| Remaining external gates | PENDING – Host Machine Validation | Meta token rotation is owner-deferred. Real physical-phone scan/inbound/outbound/ACK/restart/reconnect/logout evidence and browser/target-host validation remain unperformed; QR-09 stays `PARTIAL (BLOCKED)`. |

## QR-09C — WAHA Webhook Delivery Wiring and Credential Hygiene

**Milestone status: `PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING`.** QR-09-D5 is closed by
repository/runtime evidence; the milestone credential gate is not closed. QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

**META WEBHOOK_VERIFY_TOKEN ROTATION:**
**PENDING — OWNER DEFERRED**

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline and D5 reproduction | PASS | Branch/origin matched `ui/taste-modernization` at `0bbcd95a…`; only pre-existing `.claude/` was untracked. Existing receiver and raw-body SHA-512 verifier were present, while both Compose WAHA services had no webhook URL, event list or sender HMAC configuration. |
| Exact pinned provider contract | PASS | Certified image exports global `WHATSAPP_HOOK_*` settings and per-session `config.webhooks`; both modes are concatenated. Sender JSON-stringifies once, signs those exact bytes with SHA-512, sends `X-Webhook-Hmac`/algorithm/request-id/timestamp, and retries every error. |
| Global versus per-session decision | PASS | Global-only selected: one governed deployment receiver; key remains in runtime environment; restart reapplies it; no per-session persistence/API exposure. Per-session config remains absent, preventing duplicate delivery and a signing key in session storage. |
| Required event boundary | PASS | Exact subscriptions are `message,message.any,message.ack`; wildcard and every unrelated event are regression-rejected. Capabilities remain unchanged. |
| Dedicated credential boundary | PASS | `WAHA_WEBHOOK_HMAC_SECRET` is passed independently to WAHA and the existing backend verifier. Safe templates/runbook forbid reuse of Meta credentials, WAHA API key or session material. Production interpolation fails closed when the WAHA profile lacks it. No real deployment secret is read by the gates. |
| Development callback topology | PASS | WAHA calls `host.docker.internal:8000/api/v1/webhooks/waha` through host-gateway; provider host publication remains `127.0.0.1:3000` only. |
| Production callback topology | PASS | WAHA calls `http://api:8000/api/v1/webhooks/waha` over a shared private Compose network. Production publishes no WAHA port and adds no reverse-proxy route, Docker socket or host-path mount. |
| Provider-generated signature | PASS | The exact certified image's shipped `WebhookSender` reached a private `api:8000` receiver. The receiver verified the raw-body SHA-512 HMAC and `WAHA/2026.7.2` sender identity. Repository code did not manufacture the signature. |
| Retry and request identity | PASS | Controlled first response `503`; certified sender made exactly one retry after the configured delay. Body hash and request id were identical across both attempts, matching at-least-once redelivery semantics. |
| Backend rejection and dedupe | PASS | Focused receiver/integration suite: missing/forged/wrong-secret/tampered HMAC fail closed; same-event retries retain one deterministic identity; `message` + `message.any` converge to one stored message through existing MessageService authorities. **81 tests PASS.** |
| Restart/config persistence | PASS | Isolated provider restart preserved the exact global environment; a new signed `message.ack` delivery reached the private receiver afterward with a new request id. Existing Compose health regression preserved the repository `waha-sessions` volume. |
| Provider identity/session boundary | PASS | Exact digest reports `2026.7.2` / `NOWEB` / `CORE`. Session list remained empty before and after restart. No session created, QR requested/displayed/scanned, phone paired, or session data mutated. |
| Timeout semantics | PASS | Exact 2026.7.2 sender configures no Axios timeout (effectively unbounded per request); this provider limitation is recorded in the deployment runbook. Retry quantity is bounded at 15 but does not bound a hung request. |
| Startup dependency behavior | PASS | No service depends on WAHA health and no new coupling is introduced. WAHA retry semantics cover a temporarily unavailable API callback without blocking unrelated stack startup. |
| Runtime regression | PASS | `scripts/validate_waha_webhook.py` renders both profiles with distinct synthetic credentials and runs exact-image private callback/HMAC/retry/restart/session-zero assertions. It is release gate step 17. |
| Full release gate | PASS | **22/22 PASS** in 525.3s: backend **1399 passed, 0 skipped**, frontend **796**, lint/types/OpenAPI/build/SAST/audits/source secret-IaC scan, both certified WAHA runtime gates, Compose/release/image contracts, app-image vulnerability scans/SBOMs. |
| Contract invariants | PASS | Migration head `0043` (44 revisions), OpenAPI 207 paths, application source, routes, schemas, RBAC, UI, provider capabilities, restart policy and certified digest unchanged. |
| UI preview | PASS | Not applicable: runtime infrastructure configuration only; no operator-facing UI change and no screenshot claimed. |
| Deferred credential gate | PENDING – Host Machine Validation | Owner deferred the Meta verification-token rotation. QR-09C cannot pass and no credential-hygiene completion or production-readiness claim is made. |
| QR-09 boundary | PASS | QR-09/09A/09B evidence remains preserved. No physical-phone, provider acceptance, target-host/browser or production-deployment evidence is invented; provider certification/approval is unchanged. |

## QR-09B — WAHA Runtime Healthcheck Remediation

**Milestone status: `QR-09B — WAHA Runtime Healthcheck Remediation — REPOSITORY VALIDATED`.**
QR-09-D4 is closed by repository/runtime evidence; QR-09 remains `PARTIAL (BLOCKED)`.
`Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Baseline and D4 reproduction | PASS | Branch/HEAD matched `ui/taste-modernization` at `835e5253…`; only pre-existing `.claude/` was untracked. Both Compose files used `wget`. Exact-image Docker health output: `exec: "wget": executable file not found in $PATH`. |
| Certified-image executable inventory | PASS | `/usr/bin/tini --` + `/entrypoint.sh`; Node `v24.11.1` with built-in fetch, `/bin/sh`, Bash `5.2.15`, curl `7.88.1`; no wget, BusyBox or Python. |
| Health endpoint semantics | PASS | Unauthenticated `/health` and `/api/server/status` return `401`; provider-owned `/ping` returns `200 {"message":"pong"}` without a secret and represents service/API liveness, not pairing state. |
| Selected probe | PASS | Exec-form `curl --fail --silent --show-error --max-time 5 http://127.0.0.1:3000/ping`; bounded, no shell, no external package, no key on the command line, and non-zero on transport or failing HTTP status. |
| Compose models | PASS | Development config and `--profile waha` resolve; production `--profile waha` resolves. Exact digest, restart policy and `waha-sessions:/app/.sessions` unchanged. |
| Positive runtime proof | PASS | Exact certified WAHA `2026.7.2` / `NOWEB` / `CORE` reaches Docker `healthy`; committed health command exits 0. No false `starting` loop. |
| Negative runtime proof | PASS | The same curl flags against controlled unavailable loopback endpoint `127.0.0.1:1` exit non-zero. No stopped-container `unhealthy` claim and no session/image corruption. |
| Restart and persistence | PASS | WAHA reaches healthy before and after restart; same named session volume remains mounted and no pre-existing session file is removed. No QR pairing performed. |
| Networking | PASS | Development publishes only `127.0.0.1:3000`; production publishes no WAHA port. No Docker socket/host-path mount introduced. |
| Startup dependencies | PASS | No service depends on WAHA or `condition: service_healthy`; no new startup coupling introduced. |
| Runtime regression | PASS | `scripts/validate_waha_healthcheck.py` validates both rendered Compose models, exact image/provider identity, executable health success/failure, Docker health/restart, exposure, dependency and volume contracts; it is step 16 of the release gate. |
| Full release gate | PASS | **21/21 PASS** in 373.4s: backend **1397**, frontend **796**, lint/types/OpenAPI/build/SAST/audits/source secret-IaC scan/Compose/release and image contracts/app-image vulnerability scans/SBOMs. Exact WAHA image also passes the pinned Trivy image gate. |
| Contract invariants | PASS | Migration head `0043` (44 revisions), OpenAPI 207 paths, 25 application tasks, RBAC and WAHA capabilities unchanged. The stale image smoke assertion was synchronized 193 → 207. |
| UI preview | PASS | Not applicable: infrastructure healthcheck only; no operator-facing UI change and no screenshot claimed. |
| QR-09 boundary | PASS | No QR displayed/scanned and no phone/provider/host acceptance evidence invented. QR-09/QR-09A history preserved; certification approval and Host/Provider/Production Ready statuses unchanged. |


## QR-09A — Production Validation Remediation

**Milestone status: `QR-09A — Production Validation Remediation — REPOSITORY VALIDATED`.** Fixes
exactly the blockers QR-09 recorded. **QR-09 itself stays `PARTIAL (BLOCKED)`** — the evidence below
shows the causes are repaired, not that the external validation gates QR-09 could not reach have
since been satisfied. `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.

| Validation item | Status | Latest evidence |
|---|---|---|
| D1 — `0043` downgrade on real MySQL | PASS | `alembic downgrade 0043 → 0042` succeeds on real MySQL 8.0.46. All conversation-side drops now run in one batch in dependency order (check → foreign key → index → column), releasing `fk_conv_channel_endpoint` before the `uq_conv_endpoint_contact` index InnoDB borrows for it. |
| D1 — up/down/up round trip with data | PASS | `test_qr08_revision_survives_upgrade_downgrade_upgrade_on_real_mysql`: clean DB → `0042` → seed a representative Meta WABA/number/contact/conversation/message → `0043` (rows byte-for-byte identical, `channel_endpoint_id` NULL — no invented backfill) → downgrade → upgrade again. |
| D1 — no partially-applied schema remains | PASS | After downgrade, asserted directly against `information_schema`: `channel_endpoint_id` absent from all three tables; `uq_conv_endpoint_contact`, `ix_msg_channel_endpoint_wamid`, `ix_whe_endpoint` absent; `ck_conv_endpoint_owner` and `fk_conv_channel_endpoint` absent. |
| D1 — version truthful after each transition | PASS | `alembic_version` asserted at `0042` after downgrade and `0043` after each upgrade — the state that was previously left lying (version `0043` over a half-reverted schema). |
| D1 — no new migration introduced | PASS | Head remains `0043_conversation_channel_endpoints`; **44 revisions, unchanged**. Only the broken `downgrade()` body changed; the revision id, `upgrade()` and resulting schema are untouched, so nothing already applied is rewritten. |
| D1 — hermetic SQLite coverage retained | PASS | `tests/test_migrations.py` unchanged and passing; SQLite batch mode rebuilds the table and never reproduced this, which is why the new regression is asserted against a real server. |
| D2 — provider up + session absent returns a real state | PASS | Reproduced live against the real pinned WAHA container: provider `/api/server/version` `200`, its session deleted, provider answering `{"message":"Session not found","statusCode":404}`. `GET /channels/whatsapp-qr/session` returned **HTTP 200** with `provider_session_missing: true`. QR-09 recorded HTTP 500 on 30/30 calls. |
| D2 — not misreported as an outage | PASS | `reconnect_blocked_reason` is `provider_session_missing`, never `provider_unavailable`; `test_session_absent_is_not_reported_as_provider_unavailable`. |
| D2 — genuine outage semantics preserved (QR-06) | PASS | `test_provider_unreachable_is_still_an_outage_not_a_missing_session`: a transport failure still preserves durable `PAIRED` truth and does **not** set `provider_session_missing`. |
| D2 — durable pairing truth never destroyed | PASS | `test_session_absent_after_pairing_requires_reauth_but_keeps_durable_truth`: the row still reports `pairing_state = paired` after the observation; the divergence is projected, not persisted. |
| D2 — credentials-lost vs never-paired distinguished | PASS | Previously paired → `requires_reauthentication: true` and "must be paired again"; fresh connection → `requires_reauthentication: false` and the ordinary connect-and-scan copy. |
| D2 — no destructive or silent side effects | PASS | `test_session_absent_does_not_recreate_a_session_or_request_a_qr` fails if a status read issues **any** POST or touches `auth/qr`. No automatic session recreation, no silent pairing, no QR fetch. |
| D2 — reconnect refuses truthfully | PASS | Live: `POST /session/reconnect` → **409** "WhatsApp no longer has this connection's session…". QR-06 restarts an existing session; there is none to restart. `test_reconnect_refuses_when_the_provider_has_no_session`. |
| D2 — no provider internals leaked | PASS | `test_session_absent_state_leaks_no_credential_url_or_traceback`: no API key, no internal WAHA URL, no `404`, no traceback in the operator-facing detail. |
| D2 — UI shows a truthful recoverable state | PASS | `deriveViewState` previously returned `creating-session` for this state, rendering "Starting the session…" — false progress. Now `ready-to-connect`, carrying the server's own explanation and the "Connect WhatsApp" action. Three new frontend tests, including one asserting it is **not** `provider-unavailable`. |
| D3 — oversized body is a client error | PASS | Live: a 1,050,702-byte signed delivery returned **HTTP 413** (`payload_too_large`), where QR-09 recorded 500. Matters operationally: WAHA retries a `5xx`, so the old answer looped redelivery forever. |
| D3 — bound still enforced before hashing | PASS | Unchanged QR-04 behaviour; `test_oversized_waha_delivery_persists_nothing` asserts zero `webhook_events` and zero `messages` rows. |
| D3 — no body echoed | PASS | `test_oversized_waha_delivery_echoes_no_body_content`; verified live that the response contains no payload content. |
| D3 — normal and forged deliveries unchanged | PASS | Live and unit: valid HMAC → `200`, invalid HMAC → `403`. |
| G1 — OpenAPI drift gate | PASS | `scripts/export_openapi.py --check` reports up to date; `scripts/quality_gate.py static` passes **all six steps** including the OpenAPI drift step that was red. Artifact regenerated through the canonical exporter — not hand-edited. |
| G1 — no route or schema drift | PASS | **207 paths, unchanged.** Added routes: none. Removed routes: none. Added/removed component schemas: none. The only delta is D2's additive `provider_session_missing` property on `WhatsAppQrStatus`. |
| G1 — generated client synchronized | PASS | `npm run gen:api` regenerated `schema.d.ts`; the diff is the single corresponding property. |
| G1 — no dependency pinned or upgraded for this | PASS | FastAPI/Pydantic untouched. The cause was the committed artifact's `ensure_ascii=True` encoding versus the exporter's `ensure_ascii=False`, not resolver behaviour. |
| G1 — stale explanation corrected, not erased | PASS | The inaccurate "key-order / unpinned resolver" text in `PROJECT_STATE.md` and `VALIDATION_RESULTS.md` is **annotated** in place, preserving the historical record per `REPOSITORY_RULES.md`. |
| I1 — WAHA service defined | PASS | Added to `docker-compose.yml` and `docker-compose.production.yml`, both behind a `waha` profile so the default stack is unchanged (`docker compose config --services` → `mysql redis`; with `--profile waha` → `mysql redis waha`). |
| I1 — exact certified digest, not a tag | PASS | `devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`; the running container's image id was verified to equal it. |
| I1 — NOWEB pinned | PASS | `WHATSAPP_DEFAULT_ENGINE: NOWEB` set explicitly rather than relying on an image default; the adapter fails closed on any other engine. |
| I1 — not publicly exposed in production | PASS | Production `waha` declares **no `ports:`**; rendered production config shows the only port-publishing service is `nginx`. Development binds `127.0.0.1` only. |
| I1 — persistent session storage | PASS | `waha-sessions` → `/app/.sessions`, verified on the running container. Path established empirically against this digest: `noweb/waha.sqlite3` (session registry) and `noweb/<session>/` (per-session store/config). |
| I1 — restart preserves the provider session | PASS | Real `docker compose restart waha` with the volume: session `default` still present afterwards and the app status endpoint returned `200`. Control (same image, no volume, recreated) returned `404 Session not found` — the exact QR-09-D2 condition, confirming the volume is what closes it. |
| I1 — credentials survive a real pairing | PENDING – Host Machine Validation | Only **pre-pairing** session persistence was demonstrated. Proving that scanned WhatsApp credentials survive a restart requires a physical handset; not simulated, not claimed. |
| I1 — secrets via existing mechanism | PASS | `WAHA_API_KEY` and `WAHA_WEBHOOK_HMAC_SECRET` come from the environment/secret store like every other credential; production requires the API key when the profile is enabled. Nothing hardcoded. |
| I1 — disabled by default | PASS | Backend WAHA settings default to empty in production compose; with them unset the adapter reports `configured=false` and registers no runtime, so a deployment that has not adopted the channel is unaffected. |
| I1 — healthcheck / restart policy | PASS | `/health` probe with a start period; `restart: unless-stopped`, matching the other services. |
| I1 — operator documentation | PASS | `deploy/DEPLOYMENT.md` §15: topology table, why the volume is not optional, per-failure-mode operator procedures (outage vs session-gone vs paused vs deliberate logout), backup entry for `waha-sessions`, and disable/rollback. No automatic session deletion exists in any path. |
| S1 — cryptography advisory | PASS | `PYSEC-2026-3552` (affects 49.0.0, fixed in 50.0.0) resolved: `pip-audit` reports **no known vulnerabilities**. Declared floor raised `>=43` → `>=50` because this repository ships no lock file, so the floor is the only guard against a constrained resolve picking a vulnerable build. |
| S1 — upgrade is safe | PASS | `pip check` clean; 94 crypto/auth/credential/token tests pass; full backend suite passes against the upgraded library. No unrelated dependency changed. |
| Backend full suite (real MySQL) | PASS | **1397 passed, 0 skipped** (1385 before QR-09A; +12 — one D1 live-MySQL regression, seven D2, four D3). |
| Live-MySQL migration suite | PASS | **12 passed** (11 before). |
| QR-01..08 regression | PASS | **371 passed** across all five WAHA suites plus `test_whatsapp_qr`, `test_qr08_inbox_integration`, `test_provider_message_identity`, `test_api_webhooks` and `test_api_messages` run together. |
| Frontend suite / lint / types / build | PASS | **796 passed** (793 before; +3), 38 files; ESLint, `tsc --noEmit` and production build all clean. |
| Ruff / strict mypy | PASS | Clean; mypy no issues in 300 source files. |
| Bandit | PASS | 0 High, 0 Medium, 28 Low — unchanged pre-existing `assert`-usage class, none new. |
| npm production audit | Honestly recorded | 2 moderate (`react-router` SSR-hydration advisory; this application is client-rendered). Unchanged by this milestone and not in its scope. |
| Compose config validation | PASS | `docker compose config` and `docker compose -f docker-compose.production.yml --profile waha config` both validate. |
| Capability boundary | PASS | Declared exactly `health, qr_auth, session_logout, session_reconnect, session_stream, text`; prohibited exactly `bulk, campaigns, template`. Nothing added, nothing relaxed. |
| Migration / OpenAPI invariants | PASS | Head `0043_conversation_channel_endpoints`, **44 revisions**; OpenAPI **207 paths**. No new revision, route, or RBAC entry. |
| Running-app UI screenshots | **BLOCKED** | The Browser pane could not composite frames in this environment, so no image was captured. The state itself was verified live at both viewports through the rendered DOM — see the QR-09A final report. |
| Provider certification record | Unchanged | `docs/evidence/provider-evaluations/waha-class-b-selection-record.md` untouched; still `CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED`. |


## QR-09 — Production Validation

**Milestone status: `PARTIAL — BLOCKED`.** Validation was attempted against real MySQL 8.0.46, real
Redis 7.4.9, and the real pinned WAHA container at the certified digest. Two Major defects and one
required-gate failure remain open; no product code was changed to work around them, per the
validation defect policy. `Repository Validated: NO` · `Host Validated: NO` ·
`Provider Validated: NO` · `Production Ready: NO`. QR-01 through QR-08 are unaffected and QR-08
remains `COMPLETE`.

| Validation item | Status | Latest evidence |
|---|---|---|
| Real MySQL 8 reachable, live migration suite | PASS | `docker compose up -d` (`wa_mysql`, MySQL `8.0.46`); 11/11 `test_migrations_mysql.py` tests pass (previously 5 of these always skipped for lack of MySQL). |
| Upgrade `0042` → `0043` preserves existing Meta data | PASS | Staged a throwaway MySQL database at `0042`, seeded a representative `WABA`/`PhoneNumber`/`Contact`/`Conversation`/`Message`/`WebhookEvent` row set, upgraded to `0043`: every seeded row's queried columns are byte-for-byte identical before/after; the new `channel_endpoint_id` column is `NULL` on the pre-existing row (no fabricated backfill). |
| `0043` schema objects correct on real MySQL | PASS | `fk_conv_channel_endpoint` → `channel_endpoints` (`RESTRICT`) present; `ck_conv_endpoint_owner` present and semantically exactly-one-owner; `uq_conv_endpoint_contact` (unique), `ix_msg_channel_endpoint_wamid`, `ix_whe_endpoint` all present with the expected columns; `conversations`/`messages`/`webhook_events`.`channel_endpoint_id` nullable as designed. |
| Partition compatibility preserved | PASS | `messages` and `webhook_events` remain partitioned after `0043`; `channel_endpoint_id` on both carries **no** foreign key (app-enforced, matching `phone_number_id`'s existing precedent) — a partitioned table cannot hold a unique/foreign key that omits its partition column. |
| Exactly-one-owner invariant enforced by the database | PASS | A conversation row with neither `phone_number_id` nor `channel_endpoint_id` set is rejected (MySQL error 3819, `CHECK` violation); a row with both set is also rejected; a WAHA-owned row (`channel_endpoint_id` only) and a Meta-owned row (`phone_number_id` only) are both accepted. |
| `uq_conv_endpoint_contact` / FK `RESTRICT` enforced | PASS | A duplicate `(channel_endpoint_id, contact_id)` insert is rejected (MySQL 1062); deleting a `channel_endpoints` row still referenced by a conversation is rejected (MySQL 1451). |
| `0043` downgrade on real MySQL | **FAIL — QR-09-D1 (Major)** | `alembic downgrade` from `0043` to `0042` on a clean real-MySQL database fails: `(1553, "Cannot drop index 'uq_conv_endpoint_contact'; needed in a foreign key constraint")`. `downgrade()` drops the index before the foreign key that depends on it; dropping the FK first, then the index, was independently proven to succeed. MySQL DDL is non-transactional, so the failed attempt left a partially-downgraded schema (`messages`/`webhook_events` columns already dropped) while `alembic_version` still read `0043`. Same defect class as the already-tracked open `0036`/`0040` real-MySQL downgrade defect; not previously exercised because QR-08's own evidence was SQLite-only ("both directions test-covered" refers to the hermetic suite). |
| Idempotency: normal send | PASS | Real Redis (db-scoped instance): a text reply to a Meta conversation with a fresh `Idempotency-Key` returns `202` and stores exactly one new `messages` row. |
| Idempotency: duplicate key does not double-send | PASS | Repeating the identical `Idempotency-Key` returns the original response (same message id) and creates **no** second row. |
| Idempotency: same key, different payload | PASS | A different body under the same, already-claimed key replays the original stored response rather than creating a second message — the key answers once, not per-payload. |
| Idempotency: concurrent duplicate submissions | PASS | 6 concurrent requests sharing one fresh `Idempotency-Key` produce exactly one stored message; the atomic `SET NX` claim in `app.core.idempotency.begin()` resolves the race — one `202`, five `409 idempotency_in_flight`. |
| Idempotency: Redis outage fails closed | PASS | Stopping the real Redis container mid-test makes the next send return `503 idempotency_unavailable` and write **zero** rows — the documented fail-closed design (`app/core/idempotency.py`) holds against a real outage, not just a unit-level fault injection. |
| Idempotency: Redis restart recovers | PASS | Restarting Redis and retrying with a fresh key succeeds (`202`, one new row) once the container reports `PONG` again. |
| Idempotency records genuinely persisted in Redis | PASS | `idem:*` keys are present in the configured Redis logical database with a ~24h TTL and contain only the stored response envelope — no request body, no secret. |
| QR-08 preview 503 limitation closed | PASS | QR-08's own evidence recorded a `503 idempotency_unavailable` because its throwaway preview had no Redis. Against real Redis the full send path completes normally; this row supersedes that limitation. |
| Real pinned WAHA provider reachable | PASS | `devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e` (`noweb-2026.7.2`) running; `/api/server/version` reports `version=2026.7.2 engine=NOWEB tier=CORE` — the exact certified build, not a floating tag. |
| `connect()` creates the QR-08 endpoint against the real provider | PASS | With the org's omnichannel flags enabled, `POST /channels/whatsapp-qr/session/connect` returns `200`/`201` and creates exactly one `channel_endpoints` row (`provider_endpoint_id` = the configured WAHA session name), reused by `ConversationService.thread_for_endpoint`. |
| Disabled-by-default proven live | PASS | Before the org's `omnichannel_connections_write` flag is enabled, `connect()` is refused with `403 "Omnichannel connection writes are disabled for this organization."` — the staged-rollout gate is real, not documentation-only. |
| QR operator status endpoint, provider up + session absent | **FAIL — QR-09-D2 (Major)** | `GET /channels/whatsapp-qr/session` returns `HTTP 500` (30/30 reproductions) after the real WAHA container is restarted with no persistent session volume. The provider's `404 Session not found` becomes `ChannelApiError`; `_reconcile()` only catches `ChannelTransportError` and `get_status()` only suppresses `ConflictError`, so neither absorbs it. A genuine provider **outage** (container stopped) is handled correctly and distinctly (`reconnect_blocked_reason: "provider_unavailable"`, `requires_reauthentication: false`) — only the provider-up/session-gone state 500s. |
| WAHA provider outage keeps durable pairing truth honest | PASS | Stopping the real WAHA container: `session_state`/`pairing_state` unchanged in the database; status read reports `provider_unavailable`, not `requires_reauthentication`; conversation history (Meta + WAHA) remains fully readable via the API throughout the outage. |
| Backend restart preserves durable session/message state | PASS | Restarting the backend process against the same real MySQL database: the durable `channel_sessions` row, all conversations (Meta + WAHA), and the deduped WAHA message all read back unchanged. |
| Oversized WAHA webhook body bounded | **FAIL — QR-09-D3 (Minor)** | A body over `WahaBodyTooLarge`'s 1 MiB bound is correctly refused **before** hashing (the security bound holds), but the endpoint returns `HTTP 500` rather than a 4xx, because `WahaBodyTooLarge` (a bare `ValueError`) has no HTTP mapping — this invites the provider's at-least-once retry rather than stopping it. |
| Physical-phone E2E (scan→`WORKING`, real inbound/outbound, ACK reconciliation, reconnect-without-new-QR, logout/re-auth) | PENDING – Host Machine Validation | No physical handset was available in this environment; not simulated, not claimed. |
| Message + message.any (real MySQL) collapse to ONE stored message | PASS | One underlying provider message delivered as `message` ×2 and `message.any` ×2 (4 total deliveries against the real webhook route) produced 4 `webhook_events` rows (event-layer persistence is intentionally at-least-once) but exactly 1 stored `messages` row; `MessageService.apply_inbound` outcomes were `applied`, `duplicate`, `duplicate`, `duplicate` — the endpoint-scoped stored-message dedupe QR-08 introduced holds on real MySQL, not only SQLite. |
| Same canonical provider id on different endpoints does not collide | PASS | The same `wamid` inserted against a second `channel_endpoints` row co-exists with the original — 2 rows total, confirming endpoint scoping rather than a global lookup. |
| Meta + WAHA coexist in one real-MySQL-backed Inbox | PASS | `GET /conversations` returns both `connector_type: "meta_cloud"` (30) and `connector_type: "waha"` (1) rows in one list; confirmed additionally via the running frontend's rendered DOM ("Official WhatsApp" vs "WhatsApp (QR)" badges) against this same real-MySQL backend. |
| Prohibited capability enforced against real MySQL | PASS | A `TEMPLATE` send against the WAHA conversation is refused with `capability-not-supported`, unchanged from QR-08's SQLite-only evidence. |
| WAHA reply refused honestly when not paired | PASS | A text reply against the (unpaired) real-provider WAHA conversation is refused with `channel-not-connected` — accurate, since no handset was paired; not silently downgraded or rerouted to Meta. |
| Webhook HMAC: valid accepted | PASS | A correctly SHA-512-HMAC-signed WAHA delivery against the real backend returns `200`. |
| Webhook HMAC: invalid / missing / wrong-secret rejected | PASS | All three return `403`. |
| SHA-256 webhook event identity regression (real MySQL) | PASS | Stored `event_id` values follow the `waha:` + 64-hex-digest form on real MySQL, matching the QR-04 defect fix. |
| Unauthenticated access rejected | PASS | Unauthenticated `GET /conversations` and `GET /channels/whatsapp-qr/session` both return `401`. |
| Cross-permission WAHA session discovery rejected | PASS | An authenticated agent without `channels:read` receives the same `403`/non-configured response as an unconfigured deployment — existence is not confirmed to a caller who does not own it. |
| No API key / HMAC secret / QR bytes / internal URL in responses or logs | PASS | The status payload and 942 lines of backend logs captured during this validation contain zero occurrences of the configured WAHA API key, webhook HMAC secret, owner/agent passwords, access tokens, or `data:image`/base64 QR payload text. |
| Backend full suite (real MySQL) | PASS | **1385 passed, 0 skipped** (was 1380 passed + 5 skipped without MySQL — the previously-always-skipped live-MySQL tests now genuinely ran). |
| Frontend full suite | PASS | 38 files / 793 tests, unchanged from QR-08. |
| Ruff / strict mypy | PASS | Clean; mypy 300 source files, no issues. |
| ESLint / TypeScript / production build | PASS | All clean; build succeeds. |
| Bandit | PASS | 0 High, 0 Medium, 28 Low (the documented pre-existing `assert`-usage class; none new). |
| Python dependency audit (`pip-audit`) | **FAIL (open advisory, not remediated)** | One production advisory: `cryptography 49.0.0` → `PYSEC-2026-3552`, fixed in `50.0.0`. Not upgraded during QR-09 (dependency changes are out of scope for a validation milestone per this task's own instruction). |
| Frontend dependency audit (`npm audit --omit=dev`) | Honestly recorded | 2 moderate (a `react-router` SSR-hydration advisory; this application is a client-rendered SPA, not SSR-rendered, so applicability is limited). Full audit (incl. dev/build tooling) separately reports higher counts in `vitest`/`vite`/`@redocly` build-time dependencies, not shipped to production. |
| OpenAPI drift required gate | **FAIL — QR-09-G1 (required gate)** | `scripts/quality_gate.py` step `export_openapi.py --check` reports `openapi.json` stale in a clean repository checkout (no local `.env`). Investigated: generation is deterministic (identical SHA-256 across independent processes); the committed file and a fresh generation parse to exactly-equal JSON objects, 207 paths both; re-encoding the committed file with `ensure_ascii=False` (the exporter's own setting) is byte-exact to the fresh generation. The only difference is JSON ASCII-escaping, not key order or content — **correcting** this repository's prior explanation ("JSON key-order mismatch under the unpinned FastAPI/Pydantic resolver") for this artifact, which is a genuine, deterministic drift, not toolchain non-determinism. This is a required gate (`quality_gate.py:98`) and it is genuinely red. |
| Latency vs. this repository's own documented budgets | PASS (measured, not target-host) | Doc 01 §5.1 `NFR-PERF-01` (API read p95 < 300 ms) and Doc 06 (webhook ack < 200 ms), single developer workstation, real MySQL + Redis: mixed-Inbox list p95 12.8 ms; conversation thread load p95 5.2 ms; WAHA thread load p95 4.7 ms; webhook ingest ACK p95 10.4 ms. All within budget on this hardware; concurrency, soak, 1M-contact scale, and target-host measurement remain unproven. |
| WAHA deployment/persistence definition | **FAIL (infrastructure gap)** | No WAHA service, image pin, or persistent session-storage volume exists in `docker-compose.yml`, `docker-compose.production.yml`, or `deploy/DEPLOYMENT.md` — the deployment gap underlying QR-09-D2's reproducibility outside a manually-run container. |
| Browser/device matrix (Chrome, Edge, Firefox; desktop `1920×1080` / mobile `~390px`) | PENDING – Host Machine Validation | Not executed this milestone; the dual-provider Inbox was confirmed functionally on the real-MySQL stack via the running frontend's accessibility tree and rendered DOM, not a full cross-browser visual pass. |
| Provider certification / approval state | Unchanged | `docs/evidence/provider-evaluations/waha-class-b-selection-record.md` remains `CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED`; not advanced or altered by this milestone. |


## QR-08 — Unified Inbox integration

| Validation item | Status | Latest evidence |
|---|---|---|
| Real BFF, not a stub | PASS | `MessageService`/`ConversationService`/`SendService`/`InboxQueryService`/`WebhookService` are the **same** classes Meta's inbound/outbound path already uses — no parallel Inbox/service family for WAHA. |
| Additive migration only | PASS | `0043_conversation_channel_endpoints`: nullable `channel_endpoint_id` added to `conversations`/`messages`/`webhook_events`; `conversations.phone_number_id` widened to nullable; `ck_conv_endpoint_owner` requires exactly one owner. No column dropped, renamed, or narrowed; no existing row's `phone_number_id` changed. Verified on SQLite via `alembic upgrade head`, both directions test-covered (`test_migrations.py`). |
| Stored-message dedupe ≠ event dedupe | PASS | `test_message_and_message_any_produce_one_stored_message` proves `message`/`message.any` (same envelope, two valid QR-04 events) collapse to one stored row; `test_concurrent_duplicate_waha_delivery_produces_one_message` proves a same-event redelivery does too; `test_same_provider_message_id_on_different_endpoints_does_not_collide` proves the same provider id on two endpoints does not collide. |
| No unscoped endpoint lookup | PASS | `get_by_provider_message_id_for_endpoint`'s `channel_endpoint_id` is keyword-only, required, no default — asserted directly (`test_endpoint_scoped_lookup_has_no_unscoped_variant`), mirroring QR-00's own `phone_number_id` discipline. |
| Outbound routing is server-derived | PASS | `test_meta_reply_routes_through_meta`/`test_waha_reply_routes_through_waha`/`test_forged_frontend_provider_cannot_reroute_a_waha_conversation` — `accept_for_conversation` takes no provider parameter at all; routing comes only from `conversation.phone_number_id`/`channel_endpoint_id`. |
| Prohibited capability enforced at send time | PASS | A `TEMPLATE` send against a WAHA conversation raises `ChannelCapabilityNotSupportedError`, asserted in the forged-provider test above; MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT remain absent from the WAHA adapter (QR-01..07 invariant, re-verified by the unchanged prohibited-capability test). |
| Ambiguous WAHA send never auto-retried | PASS | `test_ambiguous_waha_send_is_marked_indeterminate_not_auto_retried` — a transport failure is caught inside `_deliver_endpoint` and resolved to `fail(..., code="indeterminate")` directly, never re-raised to the queue's retry-classification handler; the message is left `failed`, `wamid` stays `null`. |
| Unavailable WAHA session blocks send truthfully | PASS | `test_waha_send_blocked_truthfully_when_not_connected` — `accept_endpoint` checks the current `ChannelSession` is `ACTIVE`+`PAIRED` before writing anything; refuses with `ChannelNotConnectedError`, zero messages written. |
| RBAC / tenant scoping | PASS | `test_cross_org_conversation_read_and_send_are_rejected` and `test_same_org_user_without_permission_cannot_read_or_send_to_waha_conversation` — reuses `inbox:read`/`inbox:write`/`inbox:assign`/`messages:send` unchanged; no separate, weaker WAHA permission surface. |
| No secret crosses the boundary | PASS | `ConversationResponse.connector_type` is a plain string (`meta_cloud`/`waha`); no WAHA credential, session id, or endpoint internals newly exposed. |
| Mixed Inbox list | PASS | `test_mixed_meta_and_waha_conversations_appear_in_one_inbox_list` — one `InboxQueryService.list_conversations` call returns both providers' threads; live-preview screenshot confirms the same at the UI layer (see below). |
| Contact identity unified across providers | PASS | WAHA's `<digits>@c.us` sender reduces through the existing `wa_id_from_e164` to the same key Meta's `wa_id` uses — asserted via the same-phone-number Contact resolution in the inbound test; no second identity/normalization path added. |
| Backend suite | PASS | **1380 passed**, 5 skipped (no MySQL locally), 0 failed. 13 new QR-08 tests (`test_qr08_inbox_integration.py`); two pre-existing OpenAPI-path-count invariants updated 206→207 with rationale. |
| Backend ruff / mypy / bandit | PASS | `ruff check` clean; `mypy app` — no issues in 300 source files; `bandit -r` on every changed file — only pre-existing Low `assert`-usage findings in QR-07 code, no new findings. |
| Frontend typecheck / lint / tests | PASS | `tsc --noEmit` clean; `eslint .` clean; **793 passed** (789 before; +4), 0 failed. |
| Frontend build | PASS | Production build succeeds; `InboxPage` chunk `37.28 kB` / gzip `10.28 kB`. |
| OpenAPI | PASS (changed, authorized) | **206 → 207 paths** (`POST /webhooks/waha`). `openapi.json` regenerated; frontend client regenerated (`npm run gen:api`). |
| Migration graph | PASS (changed, authorized) | 44 revisions (was 43), single linear head `0043_conversation_channel_endpoints`. |
| UI preview | PASS | Real running app (backend + frontend, throwaway SQLite, representative persisted preview fixtures — not fabricated provider connectivity): desktop mixed list, desktop selected Meta conversation, desktop + mobile selected WAHA conversation showing the genuine "Session state: degraded." / composer-disabled refuse-to-send state, mobile mixed list. See QR-08 final report for exact route/viewport/state per screenshot. |
| Defects found and fixed | PASS (disclosed) | QR-07's `_REAUTH_PAIRING` incorrectly included `UNPAIRED` (diverged from QR-06's canonical definition) — fixed to match. QR-04's `parse_events` classified `message.ack` as `UNKNOWN` despite QR-05 already building `to_status_update` for it — now routed as `STATUSES`. Both disclosed in CHANGELOG, not silently folded in. |
| Known limitation disclosed | PASS | The existing Meta-number-scoped analytics rollup excludes WAHA conversations rather than counting them under a fabricated dimension; no WAHA analytics added by this milestone. |


## QR-07 — WhatsApp Scan/Connect interface

| Validation item | Status | Latest evidence |
|---|---|---|
| Real BFF, not a stub | PASS | `WhatsAppQrService` drives the real WAHA adapter (QR-01..06) and the real `ChannelConnectionService`/`SessionManager`/`PairingManager` — no mock provider path in production code. |
| No new persistence | PASS | Reuses `channel_connections`/`channel_sessions` from M13-03/04; migration head unchanged at `0042` (43 revisions). |
| RBAC / tenant scoping | PASS | Routes gated on `channels:read`/`channels:authenticate` (pre-existing catalog entries, no migration). A different organization than `WAHA_ORGANIZATION_ID` receives the same `configured=false` as an unconfigured deployment — existence is never confirmed to a caller who does not own it. |
| No secret crosses the boundary | PASS | `WhatsAppQrStatus` carries no WAHA API key, HMAC secret, or QR byte; identity is pre-masked server-side. The QR image is a separate binary response, `Cache-Control: no-store, private, max-age=0`. |
| QR never persisted | PASS | Fetched fresh from the adapter per request; the frontend holds it only as a `URL.createObjectURL` object URL, revoked on refresh/unmount, never written to any store. |
| STARTING ambiguity preserved end-to-end | PASS | The service's read-repair only advances `pairing_state` when the live mapping is non-`None` and legal; the frontend's `deriveViewState` separately refuses to call `STARTING` "connecting" unless durable `pairing_state` is already `paired`. Both layers independently honour the QR-02/QR-06 rule. |
| Pairing/session transition ordering | PASS | A real M13-05 constraint (`PairingManager` requires `INITIALIZING`/`WAITING_FOR_PAIRING`) is respected by ordering pairing before session-state whenever the target is `ACTIVE`, and after otherwise; both orders are exercised by the certified-body fixture flow. |
| Logout is destructive-explicit and correctly modelled | PASS | Requires `{"confirm": true}`; terminates the paired revision (`PairingState.PAIRED` is terminal by existing design) and registers a fresh `UNPAIRED` revision — asserted to produce a new `session_public_id` and to leave the old row's history (`TERMINATED`/`PAIRED`) queryable, not rewritten. |
| Reconnect eligibility | PASS | `can_reconnect` requires durable `PAIRED` **and** a live `PAUSED`/`DEGRADED` observation; an unpaired session is asserted to refuse reconnect (`ConflictError`) rather than auto-restart into an unrequested QR. |
| PAUSED lease constraint handled | PASS | `SessionManager.acquire_lock` refuses a `PAUSED` session (existing invariant, not introduced here); reconnect moves it to `INITIALIZING` via the lease-free write path first, then leases normally. |
| Lease reuse, not reinvention | PASS | Every mutating action acquires/releases the real `SessionManager` DB lease; a concurrent claim on the same session is asserted to raise the existing `ConflictError`. |
| Frontend: 12 required states | PASS | `deriveViewState` unit-tested for all 12 (not-configured, ready-to-connect, creating-session ×2, qr-available, qr-expired, connecting, connected — priority-checked over stale flags, reconnect-available, provider-unavailable, reauth-required); rendering asserted for not-configured, connect action, qr-available (real `<img>`, not a placeholder), qr-expired retry, connected + logout, reconnect action, reauth-required, permission-denied, read-only actor (no action buttons), and that a QR image is never rendered outside `qr_available`. |
| Logout confirmation is a real gate | PASS | Asserted: opening the dialog does not call the API; cancelling does not call the API; only the in-dialog confirm button (disambiguated via `within(dialog)`) does. |
| Backend suite | PASS | **1364 passed**, 0 skipped (0 failed; two pre-existing OpenAPI-path-count invariants updated from 200→206 with rationale, since QR-07 explicitly authorizes new public routes). |
| Backend ruff / mypy | PASS | `ruff check app tests scripts ../scripts` clean; `mypy app` — no issues in 300 source files. |
| Frontend typecheck / lint / tests | PASS | `tsc --noEmit` clean; `eslint .` clean; **789 passed** (766 before; +23), 0 failed. |
| Frontend build | PASS | Production build succeeds; `WhatsAppQrPage` is its own lazy chunk (13.31 kB / 4.24 kB gzip), not inlined into the main bundle. |
| OpenAPI | PASS (changed, authorized) | **200 → 206 paths.** `openapi.json` regenerated and verified fresh (`export_openapi.py --check`); frontend client regenerated (`npm run gen:api`). |
| Migration graph | PASS (unchanged) | 43 revisions, head `0042_scope_provider_message_identity`. |
| Known limitation disclosed | PASS | Retrying an expired, never-scanned QR surfaces the provider's real "already exists" error rather than a fabricated retry success; recorded in CHANGELOG rather than hidden. |


## QR-06 — WAHA session recovery, health and teardown

| Validation item | Status | Latest evidence |
|---|---|---|
| WORKING session is healthy | PASS | `project_health()` reports `healthy=True` only for `WORKING`. |
| Server-up / session-down distinction | PASS | `STOPPED`, `STARTING` and `FAILED` all report unhealthy — QR-01's "server health is not session health" rule is preserved, not conflated. |
| Re-auth outranks generic health | PASS | A session awaiting a scan reports unhealthy with an explicit re-authentication detail, regardless of provider uptime. |
| Unreachable provider is unknown | PASS | `project_health(None)` is unhealthy and labelled unknown; `session_health()` maps a transport failure to it rather than raising or reporting fine. |
| STARTING ambiguity preserved | PASS | `plan_reconnect()` returns `WAIT` for `STARTING`, and is asserted to return neither `RECONNECT` nor `REQUIRES_REAUTH` — the QR-02 finding is enforced, not merely documented. |
| Paired session may reconnect | PASS | `STOPPED`/`FAILED` with a durable `PAIRED` record yield `RECONNECT`. |
| Unpaired session never auto-restarted | PASS | `UNPAIRED`, `PAIRING_EXPIRED`, `PAIRING_CANCELLED` all yield `REQUIRES_REAUTH`; restarting them could only raise a QR nobody asked for. |
| Indeterminate durable state waits | PASS | `PAIRING_REQUESTED`/`PAIRING_AVAILABLE` yield `WAIT` rather than a guess. |
| Provider unavailable preserves durable truth | PASS | Yields `PROVIDER_UNAVAILABLE`, asserted **not** to be `REQUIRES_REAUTH`, so an outage cannot unpair a customer. |
| Reconnect bounded | PASS | Attempts at `DEFAULT_MAX_RECONNECT_ATTEMPTS` yield `ATTEMPTS_EXHAUSTED`; a `WORKING` session is never exhausted even at 99 attempts. |
| Backoff bounded and deterministic | PASS | Monotonic, capped at 60s, identical across repeated computation (a pure function of attempt number — no shared coordination); negative attempts rejected. |
| Stop → STOPPED semantics | PASS | `POST /sessions/{name}/stop`; maps to `SessionState.PAUSED` and asserts `pairing_state is None` — STOP never claims the session became unpaired. |
| Logout → re-auth truth | PASS | `POST /sessions/{name}/logout`; certified `SCAN_QR_CODE` + `me=null` → `WAITING_FOR_PAIRING`, `PAIRING_AVAILABLE`, health unhealthy. The intended outcome, not a fault. |
| Stop and logout are distinct | PASS | Asserted to hit different provider endpoints; collapsing them would let a restart silently unpair an account. |
| Idempotent lifecycle operations | PASS | Repeating reconnect/stop/logout converges on the same reported state. |
| Stale fencing token rejected | PASS | A newer token raises `StaleRuntimeLease`. |
| Lost/absent lease holder rejected | PASS | A different `runtime_id`, and a `None` holder, both raise. |
| Matching token under a different owner rejected | PASS | Identity **and** token must match — a re-claimed session can reuse a token number, so a token alone is insufficient. |
| Mutation refuses without a lease | PASS | Reconnect, stop and logout each raise `ChannelConfigError` and are asserted to make **no** provider call. |
| No new ownership system | PASS | `RuntimeLease` only carries identifiers; issuing/extending/revoking remain `SessionManager`/`ProviderRuntimeManager` against `channel_sessions`. |
| No auto-pairing / QR retrieval | PASS | Recovery paths asserted never to touch `auth/qr`; `reconnect_session` asserted never to `POST /api/sessions`. |
| Session-name validation | PASS | `../admin` rejected on all three lifecycle operations before any request is issued. |
| Engine guard on lifecycle | PASS | A session reporting `GOWS` fails closed with `WahaEngineNotApproved`. |
| No startup network / registry side effect | PASS | Importing the package registers no runtime; the default `ProviderRuntimeRegistry` is asserted empty (`available() == ()`), preserving the QR-01..05 invariant. |
| Explicit registration works | PASS | `register_waha_runtime()` installs provider + runtime metadata, is idempotent, and is asserted never to advertise more than the adapter implements or any prohibited capability. |
| No DELETE surface | PASS | `delete_session`/`destroy_session`/`purge_session` absent from adapter and client — QR-06 needs stop and logout, and permanent deletion is unrecoverable if issued in error. |
| Capability gating | PASS | Without `SESSION_RECONNECT`, reconnect/stop raise; without `SESSION_LOGOUT`, logout raises. |
| No later capability | PASS | `HISTORY_SYNC`, `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION`, `CONTACT` all remain undeclared. |
| Prohibited capabilities | PASS | `BULK`/`CAMPAIGNS`/`TEMPLATE` disjoint from the declared set and from runtime metadata. |
| Meta regression | PASS | Full suite passes with Meta suites unmodified. |
| QR-01..05 + webhook digest regression | PASS | 313 tests across all six WAHA suites pass together, including the QR-04 identity-digest tests. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in **297** source files (296 before QR-06). |
| Full backend suite | PASS | **1349 passed**, 0 skipped (1289 before QR-06; +60). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, **43 revisions, unchanged**. QR-06 reuses the existing session/lease authorities; no migration is justified. |
| OpenAPI / routes | PASS | **200 paths, unchanged**; zero `qr`/`pair`/`waha` routes. |
| Frontend | PASS (unchanged) | `git status frontend/` reports zero changed files. |


## Defect fix — WAHA webhook event identity collision

| Validation item | Status | Latest evidence |
|---|---|---|
| Root cause reproduced | PASS | The removed algorithm (`f"waha:{session}:{event_type}:{envelope_id}"[:128]`) is reconstructed in a test and shown to collide: with a 120-character session, the fixed prefix alone exceeds 128 characters, so `envelope_id` is discarded entirely and two distinct events (`AAAA1111`, `BBBB2222`) produce an identical key. A second, length-independent collision is also reproduced: `(session="tenant", event_type="a:b")` and `(session="tenant:a", event_type="b")` collided purely from delimiter ambiguity. |
| New algorithm does not collide | PASS | The exact inputs that collided under the old algorithm produce distinct keys under the new one; five additional adversarial delimiter-injection cases (`:`, `\|`, digit-mimicking prefixes, empty components) all discriminate correctly. |
| Fixed-length, not truncated | PASS | The key is `"waha:" + sha256(...).hexdigest()` — a constant 69 characters — asserted to fit the 128-character column for component lengths from 0 to 1000. |
| Deterministic, no `hash()` | PASS | 50 repeated calls with the same inputs produce one identical key; source is asserted to contain `sha256` and not `hash(`. `hashlib.sha256` has no process-random seed, unlike Python's built-in `hash()`. |
| Canonicalization is injective | PASS | Length-prefixed (netstring-style) encoding: each component is preceded by its own exact character count, so no component's content can forge a boundary. Asserted against boundary edge cases (empty strings, digit-string components, components containing the delimiter characters). |
| Existing behavioural guarantees preserved | PASS | Retry-collapse, session-scoping, and the `message`/`message.any` distinction (all pre-existing, non-implementation-specific tests) pass unmodified against the new algorithm. |
| Tests | PASS | 12 new tests in `test_channel_waha_webhook.py`; full QR-04 suite 64 passed (52 before); all five WAHA suites 253 passed together. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in 296 source files (unchanged file count; fix is internal to an existing module). |
| Full backend suite | PASS | **1289 passed**, 0 skipped (1277 before the fix; +12). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, 43 revisions, unchanged. |
| OpenAPI / routes / capabilities | PASS | 200 paths unchanged; zero QR routes; capabilities unchanged (`health`, `qr_auth`, `session_stream`, `text`). |
| QR-05 / Meta unchanged | PASS | Send/delivery-state code untouched; Meta suites pass unmodified. |
| Frontend | PASS (unchanged) | `git status frontend/` reports zero changed files. |


## QR-05 — WAHA send path and delivery-state reconciliation

| Validation item | Status | Latest evidence |
|---|---|---|
| Successful text send | PASS | `POST /api/sendText` carries the configured session; the certified response yields `accepted=True` and the canonical id `3EB0D11C8F76C5EB15AD6B`. |
| Provider ID extraction/canonicalization | PASS | `key.id` is taken directly; a composite `true_…@c.us_<ID>` is reduced to the same trailing value; an absent id yields `None`. |
| Send without provider id is not accepted | PASS | `accepted=False` — nothing could correlate an ack or be reconciled, so it is not reported as success. |
| Send requires an endpoint scope | PASS | An unconfigured session raises `ChannelConfigError` and opens **no** connection; an invalid session name (`../admin`) is rejected before any request. |
| Non-text refused, not degraded | PASS | Media, interactive and template sends raise `ChannelNotSupported`, including when `_dispatch` is called directly. |
| Ambiguous send is indeterminate | PASS | A transport failure raises `WahaSendIndeterminate` whose message directs the caller to reconcile, and which is asserted **not** to be a `ChannelTransportError` so generic retry cannot sweep it up. |
| No blind retry path exists | PASS | `resend`/`retry_send`/`send_with_retry`/`auto_resend` are asserted absent from adapter and client. |
| Reconcile — known present | PASS | A matching id in the session's chat returns `True`; the message must not be resent. |
| Reconcile — known absent | PASS | A non-matching chat returns `False`. |
| Reconcile across addressing forms | PASS | A `@lid`-addressed history entry matches a `@c.us` send id on the trailing component. |
| Reconcile failure never downgrades to absent | PASS | A 5xx during lookup raises `ChannelApiError`; the outcome stays indeterminate rather than becoming "safe to resend". |
| Reconcile is endpoint-scoped | PASS | The request path is `/api/{configured session}/chats/...`; another session's name never appears. No global provider-message lookup. |
| ACK mapping | PASS | `ERROR→failed`, `PENDING→accepted`, `SERVER→sent`, `DEVICE→delivered`, `READ→read`, mapped onto the platform's own `messages.status` vocabulary. |
| Out-of-order chain stays monotonic | PASS | The certified `DEVICE(2) → SERVER(1) → READ(3)` becomes `delivered → sent → read`; the late `sent` is ignored by `advances()` and the message ends `read`. Last-write-wins would have regressed it. |
| Ordering respects the platform's ranks | PASS | Mapped statuses are asserted to be in ascending `STATUS_RANK` order — QR-05 imposes no second ordering. |
| Concurrent / interleaved ACKs converge | PASS | **Every permutation** of `[DEVICE, SERVER, READ, DEVICE]` converges on `read`. |
| Duplicate ACK idempotency | PASS | Re-applying `DEVICE` five times never advances state — required because QR-04 delivery is at-least-once. |
| Regressive ACK never moves state back | PASS | `PENDING`/`SERVER`/`DEVICE` are all refused against `read`. |
| `failed` is terminal | PASS | `MSG_FAILED` is in `TERMINAL_STATUSES` and no later ack overwrites it. |
| Unknown ACK fails closed | PASS | `99`, `-7`, `None`, `"3"`, `True`, `1.5` and dicts all map to `None`; `to_status_update` raises rather than applying an invented state. |
| ACK without message id rejected | PASS | Raises `ChannelApiError`. |
| `@c.us`/`@lid` correlation | PASS | An ack arriving `@lid` correlates to a send response id from `@s.whatsapp.net` on the trailing component. |
| Wrong endpoint cannot advance a message | PASS | A different session's chat does not contain the message, so reconciliation returns `False` and cannot confirm it. |
| Capability gating | PASS | Without `SESSION_STREAM`, `to_status_update` raises; `reconcile_send` requires `TEXT`. |
| Secret/log safety | PASS | A 401 during send is asserted free of the API key; `WahaCredentials.__repr__` shows the session scope but never the key. `WAHA_SESSION_NAME` defaults to `""`. |
| Prohibited capabilities remain absent | PASS | `BULK`/`CAMPAIGNS`/`TEMPLATE` disjoint; a template send is still refused, so QR is not a route around campaign controls. |
| No later capability | PASS | `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION`, `CONTACT`, `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC` all remain undeclared. |
| Meta regression | PASS | Full suite passes with Meta send, webhook, status-reconciliation and Inbox suites unmodified. |
| QR-01..04 regression | PASS | 241 tests across all five WAHA suites pass together. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in **296** source files (295 before QR-05). |
| Full backend suite | PASS | **1277 passed**, 0 skipped (1232 before QR-05; +45). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, **43 revisions, unchanged**. QR-05 reuses the existing `messages` authority; no migration is justified. |
| OpenAPI / routes | PASS | **200 paths, unchanged**; zero `qr`/`pair`/`waha` routes. |
| Frontend | PASS (unchanged) | `git status frontend/` reports zero changed files. |


## QR-04 — WAHA webhook ingestion

| Validation item | Status | Latest evidence |
|---|---|---|
| Valid HMAC accepted | PASS | Raw-body sha512 HMAC over the certified envelope verifies. |
| Raw-body verification | PASS | Re-serialising the same JSON (`{"a":1,"b":2}` → `{"a": 1, "b": 2}`) breaks verification — the bytes the provider signed are what is checked. |
| Missing / invalid signature rejected | PASS | `None`, `""`, `deadbeef`, non-hex and tampered bodies all reject. |
| Wrong secret rejected | PASS | A signature made with a different secret rejects. |
| Unset secret rejects everything | PASS | An empty secret rejects both correctly- and incorrectly-signed bodies; asserted the settings default is `""` so no default secret can be introduced silently. |
| Constant-time compare | PASS | `hmac.compare_digest`, asserted by source inspection. |
| Algorithm downgrade rejected | PASS | `md5` rejects; `SHA512` (case-insensitive) accepts. |
| Bounded body | PASS | A body over 1 MiB raises `WahaBodyTooLarge` **before** hashing. |
| Verify before parse | PASS | `WebhookService.ingest` verifies then parses; the adapter's `verify_webhook_signature` takes raw bytes and touches no payload field. |
| `envelope.id` alone is not the key | PASS | `message` and `message.any` sharing one `envelope.id` produce **two distinct** keys, asserted end-to-end through `parse_events`. |
| Retry collapses | PASS | Repeated delivery of the same envelope+type yields one identical key. |
| Session/tenant scoping | PASS | The same `envelope.id` under two different sessions yields different keys, so two tenants' sessions cannot collide on a provider-chosen id. |
| Key fits the column | PASS | `webhook_events.event_id` is `String(128)`; the key is a fixed 69-character SHA-256 digest (`waha:` + hexdigest), so it fits regardless of component length rather than depending on where a truncation cut lands — see the defect fix below. |
| Concurrent duplicate safety | PASS | 64 concurrent parses across 16 threads resolve to exactly one identity. Proven in code because `messages` is partitioned and MySQL cannot enforce endpoint/provider-id uniqueness (error 1503). |
| Unknown event types | PASS | `session.status`, `state.change` and arbitrary names emit `UNKNOWN` rather than being dropped, so Doc 06 §11.6 can dead-letter them. |
| Malformed JSON / envelope | PASS | Six malformed shapes (empty, missing session, missing event, wrong types) emit a single `UNKNOWN` event with **no** `event_id`, so two different malformed deliveries can never collapse into one. |
| Outbound echo not ingested | PASS | `fromMe: true` and `message.ack` become `UNKNOWN`; QR-04 records acknowledgements but applies no delivery state (QR-05). |
| Provider identity preserved | PASS | `@lid` sender survives into `from_id`; the canonical trailing provider message id is extracted alongside without discarding the composite. No global provider-message lookup. |
| Certified inbound TEXT path | PASS | The real certified inbound (`QRCERT-FINAL-INBOUND`) translates to `message_type="text"` with profile name and timestamp. |
| Media not faked | PASS | A media inbound becomes `unsupported` with `provider_has_media`, never an empty text message. |
| Secret/log safety | PASS | Neither the HMAC secret nor the API key appears in parsed output; payloads are stored for replay but no secret is logged. |
| Capability gating | PASS | Without `SESSION_STREAM`, `parse_webhook`/`to_inbound_message` raise `ChannelNotSupported`. |
| No later capability | PASS | `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`, `TEXT`, `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD` all remain undeclared. |
| Prohibited capabilities | PASS | `BULK`/`CAMPAIGNS`/`TEMPLATE` unchanged and disjoint from the declared set. |
| Meta regression | PASS | Full suite passes with Meta webhook, message, inbound-dedupe and Inbox suites unmodified. |
| QR-01/02/03 regression | PASS | 196 tests across all four WAHA suites pass together. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in **295** source files (294 before QR-04). |
| Full backend suite | PASS | **1232 passed**, 0 skipped (1181 before QR-04; +51). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, **43 revisions, unchanged**. QR-04 reuses `webhook_events`; no migration is justified. |
| OpenAPI / routes | PASS | **200 paths, unchanged**; zero `qr`/`pair`/`waha` routes. QR-04 adds no public route. |
| Frontend | PASS (unchanged) | No frontend file touched. |


## QR-03 — WAHA QR pairing

| Validation item | Status | Latest evidence |
|---|---|---|
| `QR_AUTH` declared and implemented | PASS | Capabilities are now exactly `{health, qr_auth}`. `begin_pairing`/`pairing_challenge`/`pairing_state` are implemented, and physical-phone certification paired a real handset through this provider path. |
| Capability gate precedes I/O | PASS | An adapter without `QR_AUTH` raises `ChannelNotSupported` from all three methods and is asserted to open **no** connection. |
| Certified session configuration | PASS | `build_session_config()` emits `{"noweb":{"store":{"enabled":true,"fullSync":true}}}`. Asserted camelCase, asserted `full_sync` absent from the request body, and asserted copied so a caller cannot corrupt the constant. Certification proved the snake_case spelling returns HTTP 201 and silently disables history. |
| QR treated as a secret | PASS | `WahaQrChallenge` excludes bytes from the dataclass `repr`; `repr`/`str` render `data=***withheld***` and are asserted not to contain the payload. Nothing persists, logs or audits it — M13-05's "QR images and challenge bytes are deliberately absent" boundary is preserved, not widened. |
| Pairing safety on ambiguous state | PASS | `pairing_state()` returns `None` for `STARTING`/`STOPPED`/`FAILED`; `begin_pairing()` on a `STARTING` response is asserted to claim no pairing and `connected=False`. Durable pairing truth is never overwritten from an ambiguous provider status. |
| No silent reuse on conflict | PASS | A provider "already exists" response surfaces as `ChannelApiError`; the session is not reused or recreated, because QR-03 owns no teardown. |
| Non-image QR rejected | PASS | `text/html` (the shape the real server returns on its root path) and JSON error bodies raise `ChannelApiError` instead of being returned as a QR. |
| QR not-ready surfaced | PASS | The certified build's `422` ("Session status is not as expected", `expected: ["SCAN_QR_CODE"]`) surfaces as `ChannelApiError` rather than being smoothed into a placeholder. |
| Session name validation | PASS | `../evil` and `a/b` raise `ChannelConfigError` and are asserted to open **no** connection, on both pairing methods. |
| Engine guard on pairing | PASS | A session created reporting `GOWS` fails closed with `WahaEngineNotApproved`. |
| Secret handling | PASS | A 401 during QR retrieval is asserted free of the API key; transport failure maps to `ChannelTransportError`. |
| No teardown surface | PASS | Adapter and client expose none of `stop_session`/`restart_session`/`logout`/`logout_session`/`delete_session`. QR-03 can bring a session up and cannot take one down. |
| No QR-04/QR-05 surface | PASS | No WAHA-specific `handle_webhook`/`ingest_event`/`verify_hmac`/`send_image`/`sync_history`/`download_media`/`get_messages`/`get_chats`. The inherited generic send seam is asserted **behaviourally** to still raise `ChannelNotSupported`. |
| Stream/runtime capabilities withheld | PASS | `SESSION_STREAM`, `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`, `TEXT`, `MEDIA` all remain undeclared. |
| No live WAHA runtime | PASS | `ProviderRuntimeRegistry` still has no `waha` entry and reports an empty registry; declaring `QR_AUTH` installs no supervisor. |
| Prohibited capabilities | PASS | `BULK`/`CAMPAIGNS`/`TEMPLATE` unchanged and asserted disjoint from the declared set — QR-03 is not a route around campaign controls. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in **294** source files (293 before QR-03). |
| Full backend suite | PASS | **1181 passed**, 0 skipped (1153 before QR-03; +28 net). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, **43 revisions, unchanged**. QR-03 adds no migration. |
| OpenAPI invariance | PASS | **200 paths, unchanged**; zero `qr`/`pair`/`waha` routes. No public API surface. |
| Frontend | PASS (unchanged) | No frontend file touched by QR-03. |


## QR-02 — WAHA session lifecycle read and provider-neutral mapping

| Validation item | Status | Latest evidence |
|---|---|---|
| Certified status vocabulary | PASS | `WahaSessionStatus` records exactly the five statuses observed during physical-phone certification: `STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`. No speculative member. |
| Provider-neutral mapping | PASS | `SCAN_QR_CODE → (waiting_for_pairing, pairing_available)`; `WORKING → (active, paired)`; `STARTING → (initializing, indeterminate)`; `FAILED → (degraded, indeterminate)`; `STOPPED → (paused, indeterminate)`. Every certified status is mapped; asserted by test. |
| `FAILED` is not terminal | PASS | Certification recovered a `FAILED` session with a controlled restart, so it maps to `degraded`, asserted absent from `SESSION_TERMINAL_STATES`. Marking it terminal would strand a revivable session. |
| Ambiguous statuses refuse to guess | PASS | `STARTING`/`STOPPED`/`FAILED` return pairing `None`. Certification observed `STARTING` on both a fresh session (`→ SCAN_QR_CODE`) and a controlled restart of a paired one (`→ WORKING`, no new QR), so status alone cannot decide; the caller keeps its durable pairing state. |
| Mapping is pure / order-independent | PASS | Certification proved provider events can arrive out of order (`DEVICE(2) → SERVER(1) → READ(3)`). The mapping is a pure function of status with no persistence and no call-order dependence, so it cannot regress durable state. Asserted with an interleaved sequence. |
| Uncertified status fails closed | PASS | An unrecognised status raises `ChannelApiError` and the raw provider value is **not** echoed into the message (asserted with a script-like payload). |
| Session name validation | PASS | The name is interpolated into a request path, so it is validated as a strict identifier, not escaped. `../admin`, `a/b`, `a?x=1`, `a b`, `a%2f`, over-length and empty all rejected; a traversal attempt is asserted to open **no** connection. |
| Session engine guard | PASS | A session payload reporting `GOWS` fails closed with `WahaEngineNotApproved` — an adapter certified against NOWEB must not interpret another engine's session payload. |
| Both addressing forms carried | PASS | Certification proved one account is addressed as both `@c.us` and `@lid`; `identity` and `lid` are both retained, neither normalised away. |
| Only `WORKING` is connected | PASS | `connected=True` only for `WORKING`. A reachable server, a booting session and a QR-showing session all report `connected=False`. |
| Server health vs session health preserved | PASS | `authenticate()`/`status()` still return `connected=False` with no identity; `session_status(name)` is the only method that may report a live session, and requires the caller to name it. |
| No capability added | PASS | Capabilities remain exactly `{HEALTH}`. Observing a lifecycle is not being able to drive one — `QR_AUTH` is QR-03, `SESSION_STREAM` QR-04, `SESSION_RECONNECT`/`SESSION_LOGOUT` QR-06. |
| No session mutation surface | PASS | Adapter and client expose none of `create_session`/`start_session`/`stop_session`/`restart_session`/`logout`/`delete_session`/`request_qr`/`qr`/`pair`; asserted by test. QR-02 adds exactly one authenticated **read**. |
| No live WAHA runtime | PASS | `ProviderRuntimeRegistry` still contains no `waha` entry (QR-01 assertion unchanged and still passing). |
| Secret handling | PASS | The API key is sent as `X-Api-Key` and asserted absent from the snapshot `repr`. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in **293** source files (292 before QR-02). |
| Full backend suite | PASS | **1153 passed**, 0 skipped (1099 before QR-02; +54). |
| Migration invariance | PASS | Head `0042_scope_provider_message_identity`, **43 revisions, unchanged**. QR-02 adds no migration. |
| OpenAPI invariance | PASS | **200 paths, unchanged**; no route, schema, RBAC entry or generated type added. |
| Frontend | PASS (unchanged) | No frontend file touched by QR-02. |


## QR-01 — WAHA provider adapter foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Connector identity | PASS | `connector_type="waha"`, `channel_type="whatsapp"` — a second implementation of the same channel family behind the existing `ChannelAdapter` seam, not a second channel. |
| Conservative capabilities | PASS | Declares only `HEALTH`. Parametrized tests assert `QR_AUTH`, `SESSION_STREAM`, `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`, `TEXT`, `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION`, `CONTACT` are all withheld — none is implemented here and none is proven with a paired handset. |
| Prohibited capabilities | PASS | `BULK`/`CAMPAIGNS`/`TEMPLATE` recorded in `PROHIBITED_CAPABILITIES`, asserted never declared, asserted disjoint from the declared set, and template/text sends proven refused by the capability gate. |
| Static registration | PASS | `waha` present in `available_adapters()` alongside `meta_cloud`; `get_adapter("waha")` returns a `WahaChannelAdapter`. |
| Zero startup network calls | PASS | Test patches `socket.socket.connect` to fail outright, then reloads the package and constructs the adapter — registration opens no connection and needs no API key. |
| Boots without WAHA config | PASS | With `WAHA_BASE_URL`/`WAHA_API_KEY` unset the application imports and the adapter constructs with `configured=False`. Verified by importing `app.main` with the variables cleared. |
| Disabled by default | PASS | Both settings default to `""` (asserted against the model fields, so no default key can be introduced silently); QR feature flags off by default. |
| No live WAHA runtime | PASS | `ProviderRuntimeRegistry` contains no `waha` entry; asserted by test. No session worker, supervisor or reconnect loop exists. |
| Authenticated server health | PASS (real provider) | Against isolated `devlikeapro/waha:noweb-2026.7.2` (digest `sha256:33ecd1b7...`): `/health` returns `status=ok`; adapter reports `healthy=True`. |
| Auth failure | PASS (real provider) | Wrong API key returns HTTP 401 and maps to `ChannelAuthError`; the key does not appear in the message. No key and wrong key behave identically. |
| Timeout / unavailable | PASS (real provider) | Real socket timeout maps to `ChannelTransportError` ("timed out"); a closed port maps to `ChannelTransportError` ("unavailable"). Distinct messages, both transient to the retry engine. |
| Malformed / unexpected content type | PASS | Non-JSON body maps to `ChannelApiError` ("malformed"); `text/html` maps to `ChannelApiError` ("unexpected content type") — the shape the real server returns on its root path. Non-object JSON also rejected. |
| Provider 5xx | PASS | HTTP 503 maps to `ChannelApiError` with `http_status=503` preserved for the retry engine. |
| Secret redaction | PASS | `redact_headers` masks `X-Api-Key`/`Authorization`/`Cookie`; `WahaCredentials.__repr__` hides the key; auth/API errors and the warning log are asserted free of the key; provider error bodies are never echoed. |
| NOWEB / version guard | PASS (real provider) | Real server reports `version=2026.7.2 engine=NOWEB`, no drift. `GOWS` and `WEBJS` both fail closed with `WahaEngineNotApproved`; engine comparison is case-insensitive; drift is reported in `authenticate()` detail and never auto-corrected. |
| Server health vs session health | PASS (real provider) | `authenticate()`/`status()` return `connected=False`, `identity=None`, detail "No WhatsApp session — QR pairing is not implemented (QR-03)" (the milestone reference was corrected from `QR-02+` by QR-02, which implements lifecycle reads but not pairing); `health_signal()` detail says "server health only, not session health". |
| No session/QR execution path | PASS | Adapter exposes none of `create_session`/`start_session`/`stop_session`/`logout_session`/`request_qr`/`get_qr`/`qr_image`/`pair`/`pair_phone`/`sync_history`; webhook and media methods remain `ChannelNotSupported`. |
| Meta unchanged | PASS | `meta_cloud` still registered; `test_api_webhooks.py`, `test_api_messages.py`, channel and QR-00 identity suites — 189 passed together, unmodified. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in 292 source files. |
| Full backend suite | PASS | **1099 passed**, 0 skipped (1036 before QR-01; +63). |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` up to date; **200 paths, unchanged**; no route added. |
| Static quality gate | PASS | `scripts/quality_gate.py static` — all 6 steps pass. |
| Migration invariants | PASS | Head remains `0042_scope_provider_message_identity`; 43 revisions; linear. No migration file touched. |
| Scope discipline | PASS | Zero changes under `frontend/`, `backend/alembic/`, `backend/app/rbac/`, `backend/app/api/`, `docs/adr/`. |
| Real-provider spike hygiene | PASS | Temporary WAHA torn down (`docker compose down -v`), spike directory and credentials deleted, committed `docker-compose.yml` untouched, and no spike key present anywhere in the repository. |
| UI preview | NOT APPLICABLE | QR-01 contains no user-facing QR interface. |

## QR-00 — WAHA Class B provider selection and provider-message identity foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Provider selection record | PASS | `docs/evidence/provider-evaluations/waha-class-b-selection-record.md` records WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0) as the ADR-0021 Class B candidate, with Owner/Architecture/Security approval and explicit WhatsApp restriction/ban risk acceptance quoted verbatim. Succeeds, and does not rewrite, the earlier `waha-class-b-evaluation.md`. |
| Certification status unchanged | Honestly recorded | Remains **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED**. QR-00 does not upgrade it. Four Required criteria (message identity, inbound replay, ambiguous send, plus media/history byte-level behaviour) remain PENDING until a physical handset is paired. |
| Message identity root cause | PASS | `MessageRepository.get_by_wamid(wamid)` resolved a provider message id globally with no organization/connection/endpoint filter — contradicting ADR-0020 "provider message identity is scoped by connection/endpoint". |
| Endpoint-scoped lookup | PASS | Replaced by `get_by_provider_message_id(provider_message_id, *, phone_number_id)`. Scope is keyword-only and required; `test_lookup_scope_cannot_be_omitted` asserts this by signature inspection and asserts `get_by_wamid` no longer exists. No global variant remains (`grep` returns zero call sites). |
| Tenant isolation | PASS | `test_organizations_cannot_resolve_each_others_messages`: the same provider message id in two organizations resolves to each tenant's own row and never the other's. `phone_numbers.organization_id` is NOT NULL, so an endpoint-scoped read cannot cross an organization boundary. |
| Endpoint isolation | PASS | `test_same_provider_message_id_can_exist_on_two_endpoints` and `test_endpoints_cannot_resolve_each_others_messages`: a colliding id resolves per endpoint; a foreign endpoint returns `None`. |
| Deterministic ownership / backfill | PASS | **No backfill required.** `messages.organization_id`/`phone_number_id` NOT NULL since `0016_conversations_messages`. Live database: 191 messages, 0 null `phone_number_id`, 0 null `organization_id`, 0 orphaned endpoints, 0 organization mismatches, 0 duplicate `(phone_number_id, wamid)` pairs. Nothing derived or invented. |
| UNIQUE constraint impossibility | Honestly recorded | `CREATE UNIQUE INDEX uq_msg_endpoint_wamid ON messages (phone_number_id, wamid)` fails with MySQL **error 1503** — "A UNIQUE INDEX must include all columns in the table's partitioning function" — reproduced on MySQL 8.0.46 against this schema (`messages` is `PARTITION BY RANGE COLUMNS(created_at)`). Recorded as an architectural limit; uniqueness stays enforced by the scoped read plus persist-first ingestion. |
| Migration graph | PASS | Single head `0042_scope_provider_message_identity`; 43 revisions; walk-chain length 43 equals revision count (linear, no branch/merge); base unchanged. |
| Real MySQL: fresh base → head | PASS | Throwaway MySQL 8 database: reaches `0042_scope_provider_message_identity`; `ix_msg_endpoint_wamid` present as `(phone_number_id, wamid)` **non-unique**. |
| Real MySQL: 0041 → head with data | PASS | Stopped at `0041`, seeded a representative message, upgraded to head: message preserved (1), 0 null endpoint owners, index created over real data. |
| Live-MySQL migration suite | PASS | `tests/test_migrations_mysql.py` 11/11 against real MySQL 8, head pins updated to `0042`. |
| Re-authentication health design | PASS | Option **B** (derived projection) chosen over a new persisted state: `app/channels/attention.py` projects `ProviderHealthState` + `SessionState` + `PairingState` into Healthy/Warning/Critical/Re-auth Required. Avoids duplicating state and avoids widening `CHECK` constraints on three columns across three tables. Re-auth outranks observed health; `TERMINATED` never reports re-auth; projection proven total over every state combination. |
| Provider neutrality | PASS | `test_projection_introduces_no_provider_specific_state` asserts the vocabulary contains no vendor name. No WAHA identifier exists anywhere in `app/`, `tests/` or `frontend/src`. |
| Meta Cloud compatibility | PASS | `test_api_webhooks.py`, `test_api_messages.py`, `test_api_inbox*.py`, `test_api_message_reactions.py`, `test_channels.py`, `test_channel_foundation.py`, `test_dev_fixtures.py` — 166 passed unmodified. Meta webhook ingestion, inbound dedupe and delivery/read reconciliation unchanged. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — no issues in 289 source files. |
| Full backend suite | PASS | **1036 passed**, 0 skipped (1015 before QR-00; +21), with MySQL reachable so every live test genuinely ran. |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` up to date; **200 paths, unchanged**; no route added. |
| Static quality gate | PASS | `scripts/quality_gate.py static` — all 6 steps pass. |
| Security posture | PASS | QR-00 introduces no provider credential, no QR material, no secret logging, no WAHA network path, no bulk/campaign/template capability, and no change to Meta webhook signature verification. |
| Scope discipline | PASS | No WAHA client/adapter/Docker service, provider runtime registration, QR API, QR image endpoint, QR persistence, QR frontend, webhook endpoint, inbound ingestion, outbound send, history sync, media sync, session worker or reconnect runtime was added. Only `meta_cloud` is a registered adapter. |
| UI preview | NOT APPLICABLE | QR-00 contains no user-facing QR interface. Running-app screenshots become mandatory at QR-07. |

## MySQL migration evidence hardening (independent audit follow-up)

| Validation item | Status | Latest evidence |
|---|---|---|
| Migration graph unchanged | PASS | Head remains `0041_channel_sync_control_plane`; revision count remains 42; `0035a_widen_version_table`, `0036_customer_identity_resolution`, and `0040_channel_sync_media_foundation` are byte-for-byte unchanged (`git diff` against the prior commit is empty for all three). |
| Fresh MySQL 8: base → head, with real column-width proof | PASS | `SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_NAME='alembic_version' AND COLUMN_NAME='version_num'` returns `varchar(255)` after upgrade to head — asserted directly in `test_fresh_mysql_database_upgrades_base_to_head`, not inferred from migration source. |
| MySQL stamped at 0035 → head, with real column-width proof | PASS | Same `information_schema` query returns `varchar(32)` immediately after reaching `0035_notification_center` and `varchar(255)` after reaching head — asserted directly in `test_mysql_database_at_0035_upgrades_to_head`. |
| `create-owner` idempotency, with real row-count proof | PASS | `test_create_owner_after_mysql_upgrade_is_idempotent_on_rerun` calls `bootstrap_owner` twice: the first call reports `owner_created=True`/`organization_created=True`; the second reports both `False`. `SELECT COUNT(*) FROM users WHERE email = ...` is asserted `== 1` after both calls — real database inspection, not just the returned dataclass. |
| Reachable-but-misconfigured MySQL no longer silently skips | PASS | Reproduced independently: pointing `MYSQL_ROOT_PASSWORD` at a wrong value against the live local MySQL container previously produced `3 skipped`; it now produces `3 errors` (fixture setup failure) with the message "a MySQL server is reachable at ... but rejected the configured root credentials (MySQL error 1045) — check DB_HOST/DB_PORT/MYSQL_ROOT_PASSWORD" — no credential value in the message. |
| Genuinely absent MySQL still skips cleanly | PASS | Reproduced independently: pointing `DB_PORT` at a port nothing listens on reproduces the original clean-skip behaviour (`SKIPPED ... no MySQL server answered ... error 2003`); the default hermetic suite (no MySQL running at all) behaves identically. |
| Skip/fail classification logic itself has coverage | PASS | 6 new hermetic tests (no network access) exercise `_classify_connection_error` directly against synthetic exceptions carrying real pymysql error codes (2003/2005 → unreachable, 1045/1130 → misconfigured, plus a credential-leak guard); 2 further tests confirm the "reachable and correctly configured" and "reachable but rejects a wrong password" states end-to-end against the real local MySQL 8 server. |
| Governance wording corrected | PASS | `PROJECT_STATE.md`'s "Host evidence" row no longer claims "Target-host MySQL migration is now verified"; it now states this is repository/local-host `docker compose` evidence and that genuine target-host evidence remains pending, reconciling it with `IMPLEMENTATION_TRACKER.md`'s "Remaining work" list, which already correctly listed target-host evidence as pending. No valid evidence was removed. |
| Pre-existing real-MySQL downgrade defect recorded, not fixed | Honestly recorded | Historical `VALIDATION_RESULTS.md` rows for `0036`/`0040` downgrade are annotated: they are hermetic/SQLite-only and do not prove MySQL rollback safety; the real-MySQL downgrade defect at these two revisions (`DROP INDEX ... needed in a foreign key constraint`) remains a verified, separately tracked open defect. Remediation is explicitly out of scope for this follow-up; `0036`/`0040` migration code is unchanged. |
| Ruff | PASS | `ruff check app tests scripts ../scripts` clean. |
| Strict mypy | PASS | `mypy app` — "Success: no issues found in 287 source files" (unchanged; this follow-up touches no `app` file). |
| Full backend test suite | PASS | 999 passed (991 before this follow-up; +8 — `test_migrations_mysql.py` grew from 3 to 11 tests, with MySQL reachable and correctly configured so every live test genuinely ran). |
| OpenAPI drift | PASS | `scripts/export_openapi.py --check` — "openapi.json is up to date"; 200 paths, unchanged. |
| Static quality gate | PASS | `scripts/quality_gate.py static` — all 6 steps pass; confirms no frontend, application, or migration file was touched. |
| Application/domain/migration unchanged | PASS | `git diff --name-status` against the prior commit shows exactly 3 modified governance/record files (`IMPLEMENTATION_TRACKER.md`, `PROJECT_STATE.md`, `VALIDATION_RESULTS.md`) and 1 modified test file (`backend/tests/test_migrations_mysql.py`). No migration, application endpoint/model/schema, RBAC, OpenAPI, provider/Meta/WAHA, or frontend file appears in the diff. |
| Remaining scope | Honestly recorded | Genuine target-host MySQL evidence, the real-MySQL rollback defect at `0036`/`0040`, automated CI execution of the live-MySQL tests, and the separate Chat History populated-UI-preview fixture/data blocker all remain pending — none are addressed by this follow-up. No Host Validated or Production Ready claim is made. |


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
| Remaining scope | Honestly recorded | This fix repairs the MySQL schema/auth blocker only. A real, populated `/chat-history` UI preview remains blocked by the separate, pre-existing absence of an approved development fixture mechanism for conversation/message data (requires live Meta WhatsApp Business API credentials to register a phone number and create genuine conversations, which this environment correctly does not have). Evidence above is repository/local-host (`docker compose`) evidence, not target-host validation, which remains pending; a pre-existing, unrelated real-MySQL downgrade defect at `0036`/`0040` and the absence of CI execution for these tests are recorded separately below. No Host Validated or Production Ready claim is made. |


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
| Migration | PASS | Additive `0040_channel_sync_media_foundation` upgrades, downgrades to `0039`, and upgrades again (hermetic SQLite suite). Real-MySQL downgrade at this revision is a separately tracked, verified open defect — see the "Alembic version-table MySQL fix" entry above; SQLite evidence does not prove MySQL rollback safety. |
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
| OpenAPI / generated client | PASS | Application and committed OpenAPI are semantically identical at 200 paths and generated TypeScript has no drift. Current dependency resolution exposes a pre-existing JSON key-order-only `--check` mismatch on the untouched M13-04 baseline; M13-05 adds no route/schema. **Annotation (QR-09A):** the "key-order" attribution here is historically inaccurate and is preserved rather than rewritten — QR-09 proved generation is deterministic and key order identical; the artifact differed only by JSON ASCII-escaping. QR-09A regenerated it canonically and the gate now passes. |
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
| Migration | PASS | `0036_customer_identity_resolution` upgrades, downgrades to `0035`, and upgrades again with all three tables present (hermetic SQLite suite). Real-MySQL downgrade at this revision is a separately tracked, verified open defect — see the "Alembic version-table MySQL fix" entry above; SQLite evidence does not prove MySQL rollback safety. |
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
