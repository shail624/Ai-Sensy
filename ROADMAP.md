# Final Product Implementation Roadmap

This is the canonical forward roadmap from the current repository baseline. It is additive to, and
does not overwrite, the historical module roadmap in `docs/ROADMAP.md` or the frozen design records
under `docs/design/`.

Last synchronized: `2026-08-05T17:00:00+05:30`.

## Authority and baseline

- Final product intent: `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`.
- Remaining-work baseline: `CURRENT_PROJECT_GAP_ANALYSIS.md`.
- UI Taste Modernization branch: `ui/taste-modernization`.
- UI Taste Modernization lineage baseline: `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`.
- Priority 1 starting baseline: `9043fe03a80b682a010304c88c5d29d8ec77d1fa`.
- GOV-02 starting baseline: Git `0ea14d6`, repository `1.0.0-rc1`, migration `0031`, OpenAPI 3.1.0
  with 153 paths, 932 backend tests, and 628 frontend tests.
- Current live baseline after CORE-09: repository `1.0.0-rc1`, migration
  `0035_notification_center`, OpenAPI 3.1.0 with 193 paths, and 948 backend tests.
- Existing functionality is reused. A milestone may close a verified gap but may not rebuild a
  completed module.
- GitHub remains the only implementation source of truth. The owner-approved AiSensy capture archive
  may be inspected only from Git-ignored `.reference/aisensy/` as a private workflow and visual-
  quality benchmark under ADR-0012 and Design Document 25. It is never staged, committed, bundled,
  copied, or treated as implementation truth. Cached repositories and previous implementation
  snapshots must not be consulted. Excluded ads, payments, billing, subscriptions, marketplace,
  signup, reseller, multi-project, promotional, and commerce surfaces are never in scope.
- Every implementation milestone includes the premium screen Definition of Done for each new or
  materially changed route. Functionality, original presentation, real state, shared-component
  reuse, responsive behavior, accessibility, reliability, and test evidence are co-equal acceptance
  requirements; this gate does not change the approved feature sequence below.
- Estimated path and migration changes are planning figures. The milestone design review must
  verify exact additive contracts before implementation.
- Exactly one implementation milestone is closed per reviewed commit. Stop after each milestone for
  owner approval.

Milestone status: `CORE-09 — Unified Notification Center` is complete at baseline `62d4daa`.
CORE-09 delivers durable tenant/user-scoped notifications, unread count, mark-one/all-read,
permission-aware read-only team filtering, source deep links, 15-second polling, Task/Reactivation
projection, Audit evidence, migration `0035_notification_center`, and a 193-path generated contract.
It deliberately does not claim SSE, browser push, email, or internal WhatsApp delivery. **CORE-08 —
Skipped: Not required by product owner.** No generic approval authority or Approval Center will be
built; existing KYC-specific approval logic and completed authorization safeguards remain preserved.

`UI-TASTE-01` documentation/audit and `UI-TASTE-02` shared design-system modernization are complete. `UI-TASTE-03A` operator-first Dashboard is implemented and repository-validated from baseline `7d826987`; authenticated representative-data visual/reference review remains pending. `UI-TASTE-03B` Reactivation operational hierarchy, `UI-TASTE-04` responsive/accessibility/performance regression and `UI-TASTE-05` owner review/merge readiness are Repository Validated. UI-TASTE-05 remains Repository Validated; the owner has separately authorized only M13-06B provider-neutral control-plane work.

## Module 13 — Enterprise Omnichannel Channel Manager

**Current status: M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED**

ADR-0020, ADR-0021 and Design Document 33 remain frozen. M13-01 supplies provider-neutral contracts
and registries; M13-02 exact Contact identity; M13-03 persistent connection/endpoint/encrypted-secret
records; M13-04 durable session lifecycle/lease/fencing; M13-05 runtime/pairing control-plane facts;
M13-06A adds inert sync checkpoints/media references; and M13-06B adds repository-owned lifecycle,
permission, flag, concurrency and Audit controls over those records. WAHA remains uncertified and no
live login, event ingestion, provider history retrieval or media-byte transfer exists.

Provider adapters, QR image generation/scanning, WhatsApp protocol, live synchronization, media-byte
transfer, messaging, webhook, routing and operator UI remain outside this milestone.

| Milestone | Objective | Status / start gate |
|---|---|---|
| M13-00 — Architecture & Provider Lock | Freeze architecture, provider, security, session, identity, API/database, rollback, rollout and validation contracts | **REPOSITORY VALIDATED** |
| M13-01 — Generic Channel Foundation | Add provider-independent domain contracts, registries, validation, generic flags and DI while reusing `ChannelAdapter` | **REPOSITORY VALIDATED**; no provider/runtime/persistence workflow |
| M13-02 — Customer identity convergence | Add exact scoped provider identities and conflict handling without duplicate Contacts | **REPOSITORY VALIDATED**; immutable aliases, review queue and non-destructive recommendations delivered |
| M13-03 — Persistent Channel Connections & Endpoint Records | Add organization-owned provider-neutral connection/endpoint records and encrypted versioned/revocable credentials with tenant isolation, lifecycle/health metadata, soft delete, locking, flags and Audit references | **REPOSITORY VALIDATED**; migration `0037`; no API/provider/runtime/UI behavior |
| M13-04 — QR Session Manager Foundation | Durable provider-neutral session state, lifecycle, heartbeat/expiration, recovery/restart metadata, capability references, tenant/RBAC/flags/Audit and lease/fencing concurrency controls | **REPOSITORY VALIDATED**; migration `0038`; no provider, live runtime, QR/login, API or UI behavior |
| M13-05 — QR Pairing & Provider Runtime Foundation | Provider-neutral runtime registry/manager, no-store pairing lifecycle, health/events/capabilities, heartbeat/restart/recovery and session persistence integration | **REPOSITORY VALIDATED**; migration `0039`; no provider adapter, QR image/login, messaging, API or UI behavior |
| M13-06 — QR inbound, history and media | Canonical live events, checkpointed history and existing-media reuse | **M13-06A persistence and M13-06B provider-neutral lifecycle control plane REPOSITORY VALIDATED**; provider adapters, live event ingestion, provider history retrieval and media-byte transfer remain blocked by certification |
| M13-07 — Provider-neutral outbound | Conversation-scoped send and approved manual QR messaging | Blocked by idempotency and ambiguous-send evidence |
| M13-08 — Unified operator experience | Provider-aware Inbox, Customer 360, Timeline, assignment, notes, tags and search | Blocked by stable source milestones |
| M13-09 — Notifications, analytics and diagnostics | Reuse existing authorities with factual provider dimensions | Blocked by stable unified sources |
| M13-10 — Production validation | Security, performance, browser, accessibility, operator, DR and staged rollout evidence | Blocked by all implementation milestones |

Stop after M13-06B. No provider adapter, QR image/login, live event ingestion, provider history
retrieval, media-byte transfer/processing, messaging, webhook, routing or UI work begins until
certification and a separate owner instruction.

## Phase 0 — Governance and scope lock

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| GOV-01 — Permanent governance baseline | Establish synchronized, durable repository control without changing product intent. | State, validation, module status, rules, final roadmap, closeout protocol, permitted UI-reference boundary. | Root governance Markdown; `CHANGELOG.md`; `IMPLEMENTATION_TRACKER.md`; optional governance helper under `scripts/`. | Markdown/link/required-field validation; Git/OpenAPI/migration/test-count evidence checks. | All governance records agree with current Git/worktree and source documents remain unchanged; owner approves before CORE-01. | +0 | None |
| GOV-02 — Premium AiSensy-Parity Product Goal Lock | Make premium functionality and presentation a permanent, original, evidence-based product acceptance standard without changing feature scope. | Product goal and priority order; reference-versus-copying boundary; no-placeholder rule; shared-component policy; 14-step review; 20-point premium screen Definition of Done; continuous-quality boundary. | Ten synchronized root governance documents; ADR-0012; Design Document 25; local-only ignored reference evidence. | Markdown structure and links; required-content/exclusion consistency; changed-file boundary; reference-ignore; migration/OpenAPI invariance. | All governance records agree; reference use is approved and bounded; exclusions remain permanent; no product code, migration, API, permission, architecture, or behavior changes. | +0 | None |

## Phase 1 — Core operations and real domain ownership

Phase 1 converts existing honest shells/projections into server-owned Vi operations. Existing
contacts, inbox, documents, auth, RBAC, audit, jobs, and Customer 360 foundations are extended, not
replaced.

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| CORE-01 — Navigation, scope, and UI-reference lock | Make approved navigation and design boundaries explicit before domain code. | Final navigation, remove/guard unrelated concepts, premium dark-green tokens, compact AiSensy-inspired permitted patterns, light/dark/responsive shell, no excluded routes. | `frontend/src/components/layout/*`; `frontend/src/routes/*`; shared UI/theme files; design decision record. | Navigation/RBAC/keyboard/mobile tests; excluded-route assertions; accessibility smoke. | Every approved destination is reachable or honestly labelled; no prohibited concept is visible; no existing feature is recreated. | +0 | None |
| CORE-02 — Vi domain foundation | Add the server-owned records required by the approved gap analysis as one coherent transactional domain baseline. | `ReactivationCase`, `ReactivationStageEvent`, `EligibilityCheck`, `KycCase`, `KycDecision`, `SimOrder`, `SimOrderEvent`, `ActivationRecord`, `SlaPolicy`, `SlaEvent`; repositories, services, schemas, RBAC, audit, tenant isolation, lifecycle APIs. | `backend/app/models/*`; repositories/services/schemas/endpoints; RBAC catalog; `backend/alembic/versions/0032_*`; generated OpenAPI/types; domain design/ADR. | Migration up/down/integrity; model constraints; transition matrices; approvals; permissions; audit; tenant isolation; API contract tests. | All listed records are persisted and exposed through additive, permission-scoped APIs; invalid transitions fail closed; OpenAPI/types have no drift. | +28–36 | `0032` domain foundation |
| CORE-03 — Reactivation pipeline | Connect the existing Reactivation workspace to real cases and transitions. | Persisted dashboard/Kanban/list, assignments, immutable history, notes/documents, eligibility/rejection reasons, reservation/family/conversion/SLA facts; the original stage catalogue is superseded by CORE-05 without rewriting history. | `frontend/src/features/reactivation/*`; domain API client hooks; focused backend service/endpoint adjustments. | Kanban keyboard/drag tests; optimistic concurrency; transitions; permissions; empty/loading/error/mobile states. | No mock lead cards remain; refresh preserves state; every transition produces immutable history/audit and respects RBAC/SLA. | +0–4 | None unless a reviewed constraint is missing |
| CORE-04 — KYC operations — COMPLETE | Deliver the complete protected KYC workflow on the shared domain foundation. | Profile, holder/Delhi/active-number checks, checklist, Task-backed appointments, protected Aadhaar/PAN references, structured rejection, reviewer/manager separation, immutable audit/Timeline, SLA and approved Reactivation handoff. | Existing KYC/Task/Document/Reactivation/Customer 360 authorities; dedicated KYC feature; migration `0033_kyc_operations`; generated contracts; ADR-0016; Design Document 29. | Checklist/decision/approval matrices; protected-document/tenant/RBAC denial; concurrency/idempotency; audit/Timeline/handoff; UI/accessibility/responsive states. | COMPLETE — real persisted workflow passes all repository/deployed gates; no identity number, fake data, protected-media bypass, parallel authority, or completed-module rebuild was introduced. | +4 actual | `0033` KYC operations (actual) |
| CORE-05 — Lightweight Reactivation CRM — COMPLETE | Replace the planned heavy SIM/Activation operating products with the owner-approved internal CRM while preserving their backend foundations. | Exactly one of nine primary statuses; six flexible labels; Follow-up/Release dates; Task-backed Upcoming/Due Today/Overdue reminders; Complete/Snooze/Reschedule; assignee, notes, chips, filters, Audit and Timeline. | Existing Reactivation/Task/Contact/User/Audit/Timeline/Celery/frontend authorities; migration `0034_reactivation_crm`; generated contracts; ADR-0017; Design Document 30. | Status/label/date constraints; Task lifecycle/due delivery; tenant/RBAC/concurrency; immutable evidence; filter/count; keyboard/drag; accessible responsive loading/empty/error/read-only UI. | COMPLETE — one factual server-owned CRM persists refreshes, uses no duplicate status/label concept or parallel reminder system, preserves historical evidence/foundations, and adds no fake workflow. | +1 actual | `0034` Reactivation CRM (actual) |
| CORE-07 — Customer 360 domain convergence — COMPLETE | Make the existing profile the authoritative operational workspace. | Real Reactivation/KYC/SIM/Activation facts, reminders, SLA, contact-scoped conversations, messages, campaigns, notes, documents, assignment, Tasks, Audit and Customer Timeline. | Existing Customer Profile, Inbox, Vi domain and shared section implementations; optional exact-Contact filters on existing APIs; generated contracts; ADR-0018; Design Document 31. | Exact-contact/tenant/RBAC API tests; factual composition, denied/read-only/error/no-placeholder tests; desktop/tablet/mobile and keyboard review. | COMPLETE — every section composes persisted source facts, respects permissions, deep-links to its source workflow, and introduces no duplicate record, synthetic metric, migration, or endpoint family. | +0 actual | None (actual) |
| CORE-08 — Skipped: Not required by product owner | General Approval Engine is not required. | Preserve existing KYC-specific approval logic and completed module-level authorization safeguards; do not build an Approval Center, generic approval framework, approval queue, escalation system, or new approval authority. | Governance records only; no product source, API, model, migration, permission, or UI files. | Governance consistency and changed-file boundary only. | SKIPPED — owner decision is recorded consistently and existing safeguards remain unchanged. | +0 actual | None |
| CORE-09 — Unified Notification Center — COMPLETE | Deliver durable, actionable in-app notification evidence over existing Task and Reactivation authorities. | Tenant/user-scoped records, unread count, mark-one/all-read, read-only team filter, source deep links, 15-second polling, Task due and Reactivation assignment/status projections, Audit evidence, lifecycle resolution and revision-safe redelivery. | Notification model/repository/service/endpoints, migration `0035_notification_center`, generated OpenAPI/types, top-nav center, tests, ADR-0019 and Design Document 32. | Tenant/RBAC/read-state/filter/deep-link/idempotency; task reassign/reopen/bulk/delete lifecycle; migration; generated-contract; frontend notification/layout accessibility tests. | COMPLETE — in-app evidence survives refresh/device use, stale task deliveries resolve, the correct recipient/revision can receive a fresh notice, and optional channels are not falsely claimed. | +4 actual | `0035` Notification Center (actual) |
| CORE-10 — Dedicated Chat History | Separate operational history from the live inbox. | Agent/date/customer search, media, campaign-generated, resolved records, full audit filters, saved view and export hooks. | Conversation query extensions; chat-history route/feature; navigation; export integration. | Filter/pagination/tenant/permission/query-budget tests; route/table/mobile/accessibility tests. | Dedicated page reproduces complete factual history without mutating live-chat queues and without loading unbounded conversations. | +2–4 | None |
| CORE-11 — Core settings, team, tags, and SLA controls | Close remaining administrative gaps using existing admin/settings foundations. | Working hours/messages, assignment, auto-resolve/read receipts, opt-in/out, pipeline/SLA rules, notification/security/audit settings; online/workload/login/permission audit; required/active attributes. | Existing settings/admin/tag/attribute backend/frontend files; possibly configuration migration. | Settings validation; role matrix; assignment/SLA calculations; audit; backward compatibility; responsive admin UI. | Every approved control is persisted, permission-scoped, audited, and consumed by the relevant service; existing APIs remain compatible. | +4–8 | Next additive revision only if persisted structures require it |

## Approved cross-cutting UI Taste Modernization

This sequence modernizes the existing product without changing feature scope or rebuilding the shell.
The sidebar, permission-aware navigation, routes, generated API contracts, source-domain ownership,
responsive/mobile navigation, keyboard/focus behavior, reduced motion, and semantic light/dark tokens
remain authoritative.

### Audit findings

1. Preserve and refine the strong shell/accessibility foundation rather than replacing it.
2. Reframe Dashboard hierarchy around factual Reactivation operator work, not messaging alone.
3. Separate connected Reactivation workspaces clearly from foundation/future capability.
4. Reduce overuse of large radii, nested cards, soft fills, gradients, and decorative elevation.
5. Converge Inbox, Contacts, and adjacent data-heavy screens on shared controls and state patterns.
6. Clarify role-relevant everyday navigation versus advanced controls without removing approved routes.
7. Require authenticated representative-data visual, responsive, accessibility, bundle, and
   performance evidence; source inspection is not final acceptance.

| Milestone | Objective | Scope | Completion criteria |
|---|---|---|---|
| UI-TASTE-01 — Documentation and audit baseline — COMPLETE | Freeze branch, baseline, findings, boundaries, priorities, and acceptance order before coding. | Governance records only; design variance `4/10`, motion `3/10`, density `8/10`. | COMPLETE at `9043fe03`; documentation-only boundary and remote HEAD were verified. |
| UI-TASTE-02 — Shared design-system modernization — COMPLETE AND OWNER-APPROVED | Establish consistent enterprise density and hierarchy before page work. | Named radius tiers; shared form, toolbar, filter and pagination primitives; Button/Card/PageHeader/PageContainer refinements; adoption in Contacts, Inbox and Notification Center. | Repository gates pass: lint, typecheck, 657 tests, build and production audit. Host visual/reference comparison remains pending; no parallel component system or navigation redesign exists. |
| UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED | Replace the messaging-led first screen with factual operational intelligence. | Cross-domain attention, blocked customers, KYC, SIM/Activation SLA risk, Campaigns, unread conversations, Templates, agent workload, today KPI changes, task snapshot and source actions. | Repository gates pass with 661 tests and split build; no fake metric/backend duplication; authenticated representative-data visual/reference review remains pending. |
| UI-TASTE-03B — Reactivation operational hierarchy — REPOSITORY VALIDATED | Apply the shared system to the highest-value Reactivation operator workflow without rebuilding its authority. | Stage/action hierarchy, due/reminder/SLA prioritization, connected-vs-foundation maturity, saved-view/pagination truth and responsive density. | Resume only from the latest approved Git HEAD when explicitly instructed; real persisted behavior, permissions, source contracts and representative-data review pass. |
| UI-TASTE-04 — Responsive, accessibility, and performance regression — REPOSITORY VALIDATED | Prove repository-verifiable modernization quality without claiming host evidence. | KYC route permission truth, debounced search, empty-result keyboard safety, shared modal focus/scroll behavior, narrow pagination, authenticated route splitting and dead-code removal. | **REPOSITORY VALIDATED** in workflow `30980229127`; main bundle 199.78/54.87 kB gzip; host browser/device/screen-reader evidence remains pending. |
| UI-TASTE-05 — Owner review and merge — REPOSITORY VALIDATED | Determine owner-approval and merge readiness without adding features or changing architecture/governance. | One verified Major campaign chunk-order correction, full repository audit and synchronized validation records. | **REPOSITORY VALIDATED** in workflow `30982637585`; no repository-scope Blocker/Major remains; host evidence stays pending; explicit Owner Approval and Merge are the only next actions. |

## Phase 2 — Messaging, growth, analytics, and integrations

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| GROW-01 — Campaign domain completion | Extend the release-ready broadcast engine only for final-scope gaps. | Broadcast/CSV/scheduled/API journeys, audience/segment/template/assignment, approval gating, delivery/read/reply/failure retry, conversion and campaign-to-reactivation facts, ROI inputs. | Existing campaign services/endpoints/UI; approval and reactivation links; analytics projections. | Approval/dispatch race; retry/idempotency; conversion attribution; permissions; end-to-end campaign reply-to-lead. | All approved campaign types and reports are factual; large campaigns cannot bypass approval; excluded Meta Ads functionality remains absent. | +3–6 | Future additive revision if required |
| GROW-02 — Template completion | Close template-management gaps without replacing the registry. | Draft/pending/approved/rejected, text/media/button formats, variables/preview, sync, favourites, categories, usage analytics, non-executing AI generator placeholder. | Existing template backend/frontend; favourite/category/analytics additions; generated contracts. | Meta sync/status/format/variable tests; favourite/permission/preview/accessibility tests. | Every approved template type and state is managed safely; placeholder is explicitly non-executing. | +2–4 | Future additive revision if required |
| GROW-03 — Segments and server-saved views | Make approved operational audiences reusable across users. | Dynamic/static segments, saved filters, Reactivation status/label/reminder/KYC/document/engagement predicates; private/shared views for all specified modules. | Segment extensions; saved-view models/services/APIs; additive migration; module UI integrations. | Predicate truth tables; share/RBAC/tenant/versioning; performance; route integration tests. | Views and segments are server-owned, reproducible, shareable only by permission, and usable by campaigns/reports without local-only drift. | +7–10 | Future additive revision |
| GROW-04 — Live simplified automation | Consume durable receipts through governed, idempotent effects. | Approved triggers/conditions/actions, delay/reminder, status/label movement, assignment, messages, notifications, stop/archive rules, approvals/handoffs, retries/DLQ, execution history. | Existing automation runtime; effect ledger/worker/services; builder/run UI; additive migration. | Effect idempotency; checkpoint/resume; approval/handoff; safe sends; domain transitions; failure/retry/DLQ; tenant/RBAC/audit; deployed Celery E2E. | The `Trigger → Conditions → Actions` examples in final scope execute through existing authorities with no duplicate side effects. | +5–8 | Future additive revision |
| GROW-05 — Domain analytics | Extend existing rollups with lightweight Vi CRM dimensions. | Campaign/conversation/agent/reactivation status/label/reminder/source/KYC/SLA/date analytics, comparisons and exports; SIM/activation represented by case status unless explicitly reauthorized. | Analytics models/tasks/queries/endpoints/UI; additive migration; charts and filters. | Rollup determinism/rebuild/time-zone/tenant/query-budget; metric fixtures; chart/export tests. | Every scope metric has a documented formula, source event, reproducible rollup, API, UI, and export; no invented values. | +6–10 | Future additive revision |
| GROW-06 — Executive reports and Download Center | Deliver governed scheduled management reporting and one artifact home. | Revenue, conversion, ROI, productivity, workload, SLA, case-status outcomes, source, daily/weekly/monthly schedules, CSV/PDF; downloads/status/history/expiry/permissions. | Report/export services/tasks/endpoints; artifact models; additive migration; reports and download-center UI. | Formula/schedule/time-zone/PDF/CSV/expiry/approval/download-security; worker and UI tests. | Executives can schedule and retrieve all approved reports; every artifact is permission-scoped, auditable, expiring, and visible in Download Center. | +8–12 | Future additive revision |
| GROW-07 — Google Sheets | Add the only missing approved integration without a marketplace. | Admin connection, secret handling, sheet/range mapping, contact import/sync/export jobs, dedup, retries, status, audit, revocation. | Integration model/service/adapter/endpoints/tasks; additive migration; settings UI; docs. | Credential encryption/redaction; mocked Google API; mapping/dedup/idempotency/retry/revoke/tenant tests; job UI. | Authorized sheets exchange data through queued, auditable jobs; failures are recoverable; no unused integrations are introduced. | +6–9 | Future additive revision |
| GROW-08 — Webhook completion | Extend existing webhook operations for final domain events. | Subscription management, secrets, event selection, delivery logs, signatures, retries/replay, final-domain events, usage visibility. | Existing webhook service/endpoints/worker/UI; event catalog/docs. | Signature/replay/dedup/retry/redaction/permission/tenant tests; final-domain event fixtures. | Consumers can safely subscribe to approved events with observable, replayable delivery; provider webhooks and outbound webhooks remain distinct. | +2–4 | None unless subscription persistence lacks fields |

## Phase 3 — Enterprise completion, API, and compliant future work

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| ENT-01 — API management and documentation | Complete the private integration surface over final-domain APIs. | Contact/campaign/reactivation/status-label-reminder/timeline/KYC APIs, preserved foundation APIs, subscriptions, API keys/permissions, usage logs, IP restrictions, regenerate/revoke, interactive docs. | Existing API-key/auth middleware; final-domain endpoints; usage models; developer UI/docs; generated contracts. | Key lifecycle/IP/RBAC/rate/usage/redaction/tenant; OpenAPI examples and compatibility tests. | Every approved resource is documented and permission-scoped; revoked/restricted keys fail immediately; OpenAPI never shrinks silently. | +4–7 | Future additive revision if required |
| ENT-02 — Global search and advanced audit | Index every approved entity and normalize enterprise evidence. | Customers/numbers/chats/campaigns/documents/cases/labels/reminders/notes/agents/tags search; old/new values, device/login, assignment/status/document/campaign/approval audit. | Search/audit services/endpoints/index tasks; command palette; audit timeline UI; possible index migration. | Search authorization/ranking/staleness/tenant; audit immutability/redaction; keyboard/action tests; performance. | Search returns only authorized current data and all approved mutations/access decisions produce attributable audit evidence. | +4–7 | Future additive revision if needed |
| ENT-03 — Command palette and advanced mobile | Complete fast keyboard and field-device operations across final routes. | All approved `Ctrl+K` actions, collapsible sidebar, drawers/modals, notification badges, skeleton/empty states, touch-safe tables/Kanban, responsive Customer 360. | Shared layout/UI primitives and module integrations; no parallel pages. | Keyboard/focus/touch/viewport/reduced-motion/high-contrast tests; route-level visual regression. | Every final route is operable on desktop keyboard and approved mobile widths with consistent, accessible primitives. | +0 | None |
| ENT-04 — WhatsApp Scan authorization contract | Approve a compliant technical method before enabling scan execution. | Provider/legal/security/data-retention contract, allowed results, rate/queue/export/analytics design; explicit ban on unofficial WhatsApp Web enumeration. | ADR/design/security/threat-model documents; feature flag policy. | Contract review, abuse/rate/privacy threat cases; no production execution test yet. | Owner and compliance approve a documented authorized method; otherwise the shell remains non-executing and the implementation milestone is blocked honestly. | +0 | None |
| ENT-05 — Compliant WhatsApp Scan implementation | Deliver the future module only under the approved contract. | Upload lists, batches, duplicates, queue, active/business/invalid results, retries, export, segment creation, analytics. | Scan models/services/adapter/endpoints/tasks; additive migration; existing Scan Studio UI; Download Center/Segments links. | Authorization boundary; dedup/idempotency/rate/retry/tenant/RBAC/audit/privacy; provider mocks; queued deployed E2E. | Every result comes from the approved method, is auditable/exportable, and cannot perform unofficial bulk enumeration. | +8–12 | Future additive revision |

## Phase 4 — Final quality, commissioning, and acceptance

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| REL-01 — Full-scope accessibility and UX acceptance | Validate the premium UI with real workflows and data. | WCAG-oriented audit, keyboard/focus, contrast, screen-reader labels, responsive/mobile, loading/empty/error states, final permitted workflow review. | Fixes only in existing components/routes; accessibility evidence and runbook updates. | Automated accessibility plus manual desktop/mobile/browser matrix; workflow UAT. | No critical accessibility issue; every approved route passes owner UX acceptance; excluded surfaces remain absent. | +0 | None |
| REL-02 — Security, resilience, and capacity certification | Prove scale and failure behavior after feature completion. | SAST/dependency/image scans, SBOM, backup/restore, Redis/Celery/provider loss, load/stress/spike/soak, 1M-contact target, bundle/query optimization. | Existing quality/deployment scripts; focused fixes; evidence artifacts/docs. | Full static/pre-merge/release/deployed gates; chaos/recovery/performance lab. | All repository gates pass; capacity budgets and recovery objectives have reproducible evidence; no known high/critical release blocker. | +0 | None unless an additive performance index is reviewed |
| REL-03 — Target-host commissioning and final acceptance | Close environment-only evidence and release the complete private platform. | TLS/host hardening, secrets, migrations, owner bootstrap, MySQL/Redis/Celery/nginx health, monitoring/log shipping/alerts/synthetics, UAT, restore and rollback rehearsal. | Deployment configuration/runbooks; final governance ledgers; release notes/tag. | Target-host smoke/E2E; alerts/dead-man; restore/rollback; acceptance checklist. | Every `VALIDATION_RESULTS.md` item is `PASS`, every module is 100% or explicitly owner-deferred, final scope traceability is complete, and owner approves release. | +0 | Upgrade through final additive head |

## Scope traceability

| Final-scope area | Roadmap coverage |
|---|---|
| Dashboard; Customer 360; Reactivation; KYC; Documents; SIM/Activation status facts; SLA | CORE-02–CORE-05, CORE-07, UI-TASTE-02–UI-TASTE-04, GROW-05, GROW-06; standalone heavy SIM/Activation workspaces require a later explicit owner instruction |
| Inbox; Chat History; Contacts | CORE-01, CORE-07, UI-TASTE-02–UI-TASTE-04, CORE-10, GROW-03 |
| Campaigns; Templates; Segments; Automation | GROW-01–GROW-04 |
| Analytics; Executive Reports | GROW-05–GROW-06 |
| Team; roles; tags; attributes; settings | CORE-11 |
| Notifications | CORE-09, UI-TASTE-03–UI-TASTE-04 |
| Google Sheets; Webhooks | GROW-07–GROW-08 |
| API and API keys | ENT-01 |
| Global Search; Command Palette; Audit Timeline; Saved Views | GROW-03, ENT-02, ENT-03 |
| Module-specific approval safeguards; Download Center | CORE-08 skipped by owner; existing KYC/campaign/automation safeguards preserved; GROW-06 covers Download Center only |
| WhatsApp Scan | ENT-04–ENT-05 |
| Dark/light, mobile, tables, charts, drawers, Kanban, loaders, empty states, badges, keyboard | CORE-01, UI-TASTE-02–UI-TASTE-04, module milestones, ENT-03, REL-01 |
| Accessibility, performance, Docker, Celery, Redis, security, production | Every closeout gate; UI-TASTE-04; REL-01–REL-03 |

## Roadmap completion rule

This roadmap ends only when every included requirement in the final product scope is implemented and
validated, or the owner explicitly approves a documented deferral. A percentage, route shell, mock,
or placeholder is not completion. Excluded features never become roadmap candidates merely because
they appear in reference captures.
