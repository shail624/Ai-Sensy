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

Last synchronized: `2026-08-05T17:00:00+05:30`.

## Module 13 — M13-06B Provider-neutral History & Media Control Plane

- **Milestone status:** `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED`.
- **Completion:** `48%` evidence-based estimate.
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
- **Next:** real WAHA host evidence and certification remain required before any live M13-06 behavior.

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
| Chat History | 40% | Exact-contact persisted conversation/message history is available in Inbox and Customer 360 | Build dedicated route with agent/date/customer/media/campaign/resolution/audit filters and export. | Audit, Download Center |
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
| Settings | 70% | Organization/application/flags/preferences routes complete | Approved business/WhatsApp hours/messages, assignment/auto-resolve/read receipts, campaign/opt-in, pipeline/SLA/notifications/security/audit controls. | Domain configuration APIs, RBAC |
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
| Tags and Attributes | 90% | CRUD, contact links, custom attributes, filters complete | Required/active controls and final domain-specific fields; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 85% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 35% | Local favourites/recent destinations and inbox views exist | Server synchronization and sharing for contacts, campaigns, reactivation, KYC, reports, and chat history. | Users/RBAC, module filters |
| Audit Timeline | 90% | CORE-07 exposes distinct Customer Timeline and Audit views over existing immutable evidence, including source references and deep links | Normalize remaining old/new values, device/login, generalized approvals and document-access evidence. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
