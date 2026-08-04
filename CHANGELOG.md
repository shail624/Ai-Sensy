# Changelog

All notable changes to **frozen** design documents and (later) released modules are recorded
here. Frozen documents are not edited silently; any change to a frozen document must be
logged as an entry below, with date, document, rationale, and the nature of the change.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
will adopt semantic-ish versioning per document (e.g., `SRS v1.1`) once changes occur.

---

## [Unreleased]

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
