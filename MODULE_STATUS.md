# Module Status

## UI-REF-04 — Live Chat category semantics (2026-09-14, local)

Restores the owner's category definitions: Active = open; Requesting = open and
unassigned; Intervened = current assignment ownership across statuses. Switching
categories preserves only search. Reference-style captions are retained.
PASS: 32 focused inbox tests and frontend TypeScript checking. Added regression
coverage for conflicting status/assignee/tag filters while retaining search.
PENDING – Host Machine Validation: authenticated populated preview and release.
No completion percentage increase. Uncommitted on the existing dirty checkout;
this entry does not certify or commit the unrelated local work or full UI parity.


## UI-REF-03 — manual contact creation (2026-09-13)

Added permission-gated Add Contact and a responsive Create Contact form using the existing
POST /api/v1/contacts endpoint. Name, international mobile number and source are supported;
consent remains unknown. Pending submission is guarded; server errors remain visible and
successful creation refreshes contact search without changing active filters.

PASS: 48 files / 887 frontend tests (8.22s), ESLint, TypeScript and production build.
PASS: local preview created one explicitly named test contact in the isolated preview database;
desktop/mobile form screenshots saved under output/previews/ui-ref-03-create-contact-*.png.
No production data, backend contracts, migrations, GitHub or deployment changed.

Still pending: reference-equivalent DOB/tag entry, country picker, Contacts/Segments secondary
navigation, full action/filter menus and cumulative production acceptance. No completion
percentage increase or claim of full AiSensy parity. See design document 74.

## MAINT-02 — typed campaign list filters (2026-09-13)

Latest milestone: MAINT-02. Branch: `claude/sweet-darwin-5i66uq`; approved starting
HEAD: `6d755f250eb3cd1b2e3126ba2ba26ff32f8516b2`. Delivery HEAD is this milestone's
single commit (resolve from Git). Repository version remains `1.0.0-rc1`.

PASS: the approved branch reproduced an empty query-parameter declaration in live OpenAPI,
despite frozen API design section 17 requiring campaign name/status filtering. No frozen
requirement calls for the undeclared shape. The route now declares optional typed q/status;
status validation derives from the existing campaign status tuple. The existing legacy
status-filter spelling remains accepted with its existing precedence, without adding it
to the public generated query shape.

PASS: regenerated OpenAPI and frontend types; the generated client sends filters and query
cache keys include them. Removed duplicate client-side search/status filtering. Existing
local sorting and paging remain; no server pagination, new tabs, campaign kinds, migrations,
execution, scheduling, audience or dispatch changes. Empty filtered results are distinguished
from an empty registry; filter controls remain mounted while results load.

PASS: full backend suite **962 passed**, no failures/skips (176.71s); focused new backend
contract/filter/status/tenant checks **14 passed**. Frontend campaign tests **48 passed**;
full frontend suite **657 passed / 33 files** (5.64s). TypeScript, production build,
ESLint, changed-backend Ruff, endpoint mypy and OpenAPI drift check passed.
Build bundle-size and runtime/tool deprecation warnings remain non-blocking.
Initial sandbox restrictions on dependency installation/bundler startup were resolved;
the completed runs above are the acceptance results.

OpenAPI remains **193 paths**, migration head remains **0035_notification_center**.
No source-of-truth document changed. Existing module completion estimates are not increased.
PENDING – Host Machine Validation: deployed MySQL/browser/E2E commissioning was not run;
this bounded contract milestone is not a new production-readiness certification.

Design note: `docs/design/MAINT-02-CAMPAIGN-LIST-FILTER-CONTRACT.md`.
Decision: `docs/adr/0020-maint-02-campaign-list-filter-contract.md`.
Scope limited to MAINT-02; other local work was excluded through an isolated worktree.
Next action after the single commit/push: STOP; no next milestone is authorized.

## Historical records below — retained, not current MAINT-02 evidence

Completion percentages are evidence-based estimates against
`VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`, not measures of code volume or visual polish. Existing
foundations are preserved; percentages increase only when real backend contracts, permissions,
audit behavior, UI integration, and tests are complete.

UI-REF-02: Live Chat strip/search and empty desktop columns aligned; frontend **883/883**,
types/build/lint and desktop/mobile preview pass. Full populated parity remains pending in
Design Document 73. No module percentage increases and no production certification.

UI-REF-01 (2026-09-13): screenshot-aligned rail/Manage implemented; frontend **882/882**,
types/lint/build and bounded desktop/mobile preview pass. No estimate is raised. **77.0% is
the historical approved-scope estimate, not full AiSensy visual parity.** Detailed screen/button
comparisons remain open in Design Document 72. Unfinished segment work is not credited here.

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
CORE-11A/11B/11C now consume one validated Inbox policy for routing/read/consent, organization-
timezone hours, guarded customer replies and protected inactivity resolution; later administrative
slices remain explicit.

Last synchronized: `2026-09-13`.

## REL-CERT-01 — Consolidated Production Closure Certification

- **Status:** `REPOSITORY/LOCAL-DEPLOYMENT CERTIFIED`; the pre-PAR-AUTO-19 cumulative deployed gate
  remains **25/25 PASS** in **597.4s**, while PAR-AUTO-22 remains the last complete release profile
  at **23/23 in 685.9s**. The changed PAR-VIEW-05 tree awaits that Docker/security rerun.
- **Evidence:** last complete release evidence is **1521 backend tests with zero skips**, **832 frontend
  tests**, strict types across **305 backend files**, synchronized **211-path** OpenAPI, production
  build, clean SAST/dependency/source/image scans, exact 29-task backend image contract, frontend
  image contract and CycloneDX SBOMs. The preserved fresh disposable ten-service run passed the
  owner browser journey, Redis-down `503` readiness, zero synthetic-secret/PII leaks, and a
  **5.764ms p95** canary against a **300ms** budget.
- **Completion accounting:** this validation does not inflate feature percentages. Across the 31
  canonical module rows below, the simple unweighted average is **77.0%** and the recalculated
  median is **88%**.
  Automation/API are **99%**, Inbox/Contacts **98%**, Reactivation/Tags **96%**, KYC is **90%**,
  while
  Google Sheets, WhatsApp Scan, remaining Download Center artifact families, Executive Reports,
  segment predicates, Chat History, Analytics and enterprise/commissioning work keep the product
  below 100%.
- **Boundary:** repository and disposable local deployment are release-candidate clean. Target-host
  secrets/TLS, monitoring/alerts, backup-restore/rollback rehearsal, representative-data UAT and
  owner acceptance remain `PENDING – Host Machine Validation`; `Production Ready: NO` for a live
  customer launch until those external gates close.

## PAR-VIEW-05 — Governed Report Saved Views

- **Status:** `REPOSITORY IMPLEMENTED`; Executive Reports advances **75% → 80%**, Saved Views
  **85% → 95%**, and full scope **76.5% → 77.0%** (median advances **86% → 88%**).
- **Authority:** Reports extends the same workspace-view service/repository/table already used by
  KYC, Campaigns, Contacts and Reactivation. Every `analytics:read` user governs private
  definitions; `analytics:views_manage` protects team publishing/deletion. Workspace, tenant and
  private-user boundaries fail closed.
- **Portability/safety:** one exact period preset or complete custom range, day/week granularity and
  optional previous-period comparison are stored. Report tab, export format, schedule/progress and
  other transient state are excluded. Applying a view changes only the existing Analytics URL
  filter contract.
- **UI/evidence:** private/team chips and the responsive `Save / manage` sheet were verified in an
  authenticated local desktop and 390-pixel mobile preview. Focused backend contracts **12/12**,
  focused Analytics UI **41/41**, full frontend **47 files / 875 tests**, strict mypy **322 files**,
  static **6/6**, **235-path** OpenAPI drift and Vite **8.2.2** build pass. Full backend:
  **1579 passed / 6 MySQL-only skipped / 0 failed in 413.35s**.
- **Boundary:** remaining `GROW-03` work is the approved segment-predicate/saved-filter slice.
  Revenue/ROI and campaign attribution, capacity/utilization facts, representative-data WCAG/device
  review, production-scale commissioning and target-host release gates remain separate. No
  provider/customer call, commit, push, release or deployment occurred.

## PAR-VIEW-04 — Governed KYC Saved Views

- **Status:** `REPOSITORY IMPLEMENTED`; KYC advances **85% → 90%**, Saved Views **75% → 85%**,
  API **98% → 99%**, and full scope **76.0% → 76.5%** (median remains **86%**).
- **Authority:** KYC extends the same workspace-view service/repository/table already used by
  Campaigns, Contacts and Reactivation. Every `kyc:read` user governs private definitions;
  `kyc:views_manage` protects team publishing/deletion. Workspace, tenant and private-user
  boundaries fail closed.
- **Portability/safety:** trimmed customer search and one validated KYC lifecycle status are stored.
  Fetch limit, selected case, checklist/documents, appointments, SLA/detail and reviewer/manager
  decisions are excluded. Applying a definition clears selection and changes only URL filter state.
- **UI/evidence:** lock/team chips and the responsive `Save / manage` sheet reuse the existing KYC
  queue language and controls. Focused API/migration/OpenAPI contracts **12/12**, focused KYC UI
  **2 files / 8 tests**, full frontend **46 files / 870 tests**, strict mypy **321 files**, static
  **6/6**, OpenAPI drift and Vite **8.2.2** build pass. Full backend: **1574 passed / 6 MySQL-only
  skipped / 0 failed in 450.05s**.
- **Boundary:** Reports saved views and remaining segment predicates are still pending. Server
  pagination, protected-media/high-volume commissioning, authenticated representative-data
  WCAG/device review and target-host release gates remain separate. No provider/customer call,
  commit, push, release or deployment occurred.

## PAR-VIEW-03 — Governed Campaign Saved Views

- **Status:** `REPOSITORY IMPLEMENTED`; Campaigns advances **94% → 95%**, Saved Views **65% →
  75%**, API **97% → 98%**, and full scope **75.6% → 76.0%** (median remains **86%**).
- **Authority:** Campaigns extends the same workspace-view service/repository/table already used by
  Reactivation and Contacts. Every `campaigns:read` user governs private definitions;
  `campaigns:views_manage` protects team publishing/deletion. Workspace, tenant and private-user
  boundaries fail closed.
- **Portability/safety:** trimmed search, validated campaign lifecycle status and list sort are
  stored; local page number is excluded. Applying a definition returns to page one and changes only
  list URL state—the campaign roster, recipient paging, dispatch and lifecycle authorities remain
  untouched.
- **UI/evidence:** lock/team chips and the responsive `Save / manage` sheet reuse the existing
  Campaign list language and controls. Focused saved-view backend **16/16**, migration **5/5**,
  focused Campaign UI **54/54**, full frontend **45 files / 866 tests**, strict mypy **320 files**,
  static **6/6**, OpenAPI drift and Vite **8.2.2** build pass. Full backend: **1569 passed / 6
  MySQL-only skipped / 0 failed in 395.87s**.
- **Boundary:** KYC and Reports saved views plus remaining segment predicates are still pending.
  Campaign attribution/revenue/ROI, authenticated representative-data WCAG/device review,
  production-scale commissioning and target-host release gates remain separate. No campaign send,
  provider/customer call, commit, push, release or deployment occurred.

## PAR-VIEW-02 — Governed Contacts Saved Views

- **Status:** `REPOSITORY IMPLEMENTED`; Contacts advances **95% → 98%**, Saved Views **55% → 65%**,
  API **96% → 97%**, and full scope **75.2% → 75.6%** (median remains **86%**).
- **Authority:** Contacts reuses the Reactivation workspace-view persistence and governance service.
  Every `contacts:read` user governs private definitions; `contacts:views_manage` protects team
  publishing/deletion. Workspace, tenant and private-user boundaries fail closed.
- **Portability/safety:** search, tag UUID and validated enum-attribute selections are stored;
  cursors are excluded. Per-scope caps, case-insensitive names, organization locking, scoped
  indexes/checks and atomic Audit evidence remain common to both integrations.
- **UI/evidence:** the existing Contacts search/filter/mobile sheet, cursor paging, bulk actions and
  export rules remain authoritative. Lock/team chips and the responsive `Save / manage` sheet apply
  definitions without stale paging. Focused backend **16/16**, focused frontend **19/19**, full
  frontend **44 files / 863 tests**, complete backend **1564 passed / 6 MySQL-only skipped / 0
  failed in 506.04s**, strict mypy **319 files**, static **6/6** and Vite **8.2.2** build pass.
- **Boundary:** authenticated representative-data browser/WCAG/device review remains pending; the
  in-app local preview was attempted but local-page access was denied. No provider/customer/release
  action occurred.

## PAR-VIEW-01 — Governed Reactivation Saved Views

- **Status:** `REPOSITORY IMPLEMENTED`; Reactivation advances **94% → 96%**, Saved Views **42% →
  55%**, API **95% → 96%**, and full scope **74.7% → 75.2%** (median remains **86%**).
- **Authority:** every `reactivation:read` user may persist and delete personal definitions;
  `reactivation:views_manage` governs team publishing/deletion. Lists contain all tenant team views
  plus only the actor's private views; foreign/private UUIDs fail closed.
- **Portability/safety:** validated search, owner, status, label, reminder and date filters plus
  board/list mode are stored without pagination. Scopes are independently capped at 25, names are
  case-insensitively unique under an organization lock, visibility/display have database checks,
  and create/delete commit with Audit evidence.
- **UI:** compact lock/team chips apply a saved definition without stale page state. The responsive
  `Save / manage` sheet provides plain-language visibility, permission truth, grouped management,
  errors and explicit deletion confirmation while preserving all existing Reactivation controls.
- **Persistence/API:** `0057_reactivation_saved_views` adds the scoped table/indexes/checks and one
  permission, preserving one **58-revision** head. Three operations advance OpenAPI to **227 paths**
  with synchronized generated TypeScript.
- **Validation:** focused backend **13/13**, Reactivation UI **12/12**, full backend **1559 passed / 6
  MySQL-only skipped / 0 failed in 459.36s**, full frontend **43 files / 860 tests**, strict mypy
  **317 files**, changed-file Ruff/OpenAPI drift, lint/types and production build PASS.
- **Boundary:** saved views for Contacts/Campaigns/KYC/Reports, campaign conversion/revenue/ROI,
  target-scale and authenticated host/WCAG/device/release gates remain. No provider call, customer
  send, commit, push or deployment occurred.

## PAR-CAM-01 — Campaign Recipient Failure Operations

- **Status:** `REPOSITORY IMPLEMENTED`; Campaigns advance **90% → 94%** and full scope **74.5% →
  74.7%**. The current-table median is **86%**; this corrects the prior 85% summary rather than
  claiming another feature increase.
- **Complete ledger:** Campaign Detail no longer filters only the first 50 loaded recipients. The
  existing ledger endpoint declares exact status, bounded limit and cursor parameters; returns a
  total-aware page envelope while preserving v1 `has_more`; and the UI provides busy-safe forward/
  previous cursor navigation over the complete stored roster.
- **Operational evidence:** rows show tenant-safe current contact identity, status, safe failure
  code, retry count and latest lifecycle timestamp. Cross-tenant contact references resolve blank;
  provider/internal message identities and internal error detail stay out of the response.
- **Retry safety:** the existing `campaigns:send`-protected failed-recipient retry, rate gate,
  idempotent roster behavior, smart-retry engine, queue and Audit authority are preserved. A new
  confirmation states the exact failed count and that successful recipients are not sent again;
  errors remain visible in the dialog and state refreshes after success.
- **Persistence/API:** additive `0056_campaign_recipient_operations` adds the two composite indexes
  matching unfiltered and status-filtered `(created_at,id)` scans. One linear head advances to **57
  revisions**. OpenAPI remains **225 paths** with synchronized generated TypeScript.
- **Validation:** Campaign/migration regression **107/107**, focused Campaign UI **51/51**, complete
  frontend **43 files / 857 tests**, static **6/6**, strict mypy **314 files**, OpenAPI drift and
  Vite **8.2.2** build PASS. Complete backend: **1553 passed / 6 MySQL-only skipped / 0 failed in
  476.67s**. Campaigns chunk is **109.34/28.02 kB gzip**.
- **Boundary:** campaign-to-reactivation conversion and approved recovered-value/revenue/ROI facts,
  Docker/security rerun, target-MySQL scale evidence and authenticated target-host commissioning
  remain. No provider call, customer send, commit, push or deployment occurred.

## PAR-DL-03 — Governed Campaign Results Exports

- **Status:** `REPOSITORY IMPLEMENTED`; Campaigns advance **85% → 90%**, Download Center **80% →
  88%**, API **94% → 95%**, and full scope **74.1% → 74.5%** (median remains **85%**).
- **Authority/security:** new `campaigns:export` separates bulk extraction from campaign reading,
  sending and lifecycle management. Start/progress/Center access is tenant-, requester-, campaign-
  and current-permission-scoped; cross-campaign job substitution and foreign-user UUIDs return 404.
- **Artifact:** the persisted recipient ledger streams oldest-first in 500-row keyset batches with
  optional recipient-status filtering. Current contact identity, factual delivery state, safe error
  code, retry/cost and lifecycle timestamps are included; provider/message IDs, variables, internal
  error detail and storage/provider references are excluded. Formula-leading cells are neutralized.
- **Shared pipeline/UI:** PDF/CSV/XLSX/JSON reuse the existing export row, queue, storage, expiry,
  signed URL and audit flow. Campaign Detail adds a responsive export sheet with progress/direct
  download, and Download Center adds a permission-filtered Campaign results family.
- **Persistence/API:** additive `0055_campaign_results_exports` adds only the entitlement and keeps
  one **56-revision** head. Start/progress bring OpenAPI to **225 paths**; generated TypeScript and
  the **32-task** source image contract are synchronized.
- **Validation:** campaign/export backend **106/106**, provider/OpenAPI/smoke/image regression
  **32/32**, migration **5/5**, focused Campaign/Download/navigation UI **63/63**, complete frontend
  **42 files / 854 tests**, static **6/6**, strict mypy **314 files**, OpenAPI drift and Vite **8.2.2**
  build PASS. Complete backend: **1552 passed / 6 MySQL-only skipped / 0 failed in 475.58s**.
  Campaigns chunk is **108.35/27.75 kB gzip**;
  Download Center **7.18/2.54 kB gzip**.
- **Boundary:** Campaign conversion/ROI attribution and failed-message retry UX, compliant Scan and
  generated-document artifacts, Docker/security rerun and target-host commissioning remain. No
  campaign send, provider call, commit, push or deployment occurred.

## PAR-HIST-01 — Advanced Chat History Filters and Shared Views

- **Status:** `REPOSITORY IMPLEMENTED`; Chat History advances **70% → 88%**, Saved Views **35% →
  42%**, API **93% → 94%**, and full scope **73.3% → 74.1%** (median remains **85%**).
- **Factual filtering:** inclusive-`from`/exclusive-`to`, campaign, media and audit filters compose
  with existing status/assignee/number/tag/customer search and keyset pagination. Campaign/media
  predicates read the message ledger; audit scope reads direct conversation audit evidence and
  requires `audit:read`.
- **Shared views:** organization-scoped records store validated portable filters. Every inbox reader
  can apply ordinary team views; `inbox:views_manage` governs create/delete, audit-scoped views stay
  hidden without `audit:read`, mutations are audited, and foreign UUIDs cannot cross tenants.
- **UI:** immediate basic controls remain; compact team-view chips and a responsive Advanced bottom-
  sheet/dialog add date/campaign/media/audit controls, validation, Clear/Apply and manager-only view
  governance.
- **Persistence/API:** `0054_chat_history_filters_views` adds one table and one permission while
  preserving a single **55-revision** head. OpenAPI advances to **223 paths** with synchronized
  generated TypeScript.
- **Validation:** new backend **10/10**, Inbox/conversation/QR regression **77/77**, migration **5/5**,
  Chat History UI **41/41**, complete frontend **41 files / 850 tests**, static **6/6**, strict mypy
  **314 files**, OpenAPI drift and Vite **8.2.2** build PASS. Complete backend:
  **1547 passed / 6 MySQL-only skipped / 0 failed in 458.04s**. Chat History chunk is
  **23.82/6.91 kB gzip**.
- **Boundary:** authenticated representative-data WCAG/device/browser review and production-scale
  query commissioning remain. Docker/security rerun and target-host
  TLS/secrets/monitoring/restore/UAT/acceptance remain separate; no provider call, customer send,
  commit, push or deployment occurred.

## PAR-DL-02 — Governed Chat History Transcript Exports

- **Status:** `REPOSITORY IMPLEMENTED`; Chat History advances **55% → 70%**, Download Center
  **74% → 80%**, API **92% → 93%**, and full scope **72.5% → 73.3%** (median remains **85%**).
- **Authority/security:** a new `inbox:export` entitlement separates extraction from ordinary Inbox
  reading. Transcript creation, progress and Download Center visibility are tenant-, requester- and
  current-permission-scoped; start/completion remain in the existing immutable export audit flow.
- **Artifact:** one selected persisted conversation streams oldest-first from the indexed message
  ledger in 500-row keyset batches. Complete-thread or optional inclusive calendar-day ranges can
  generate PDF, CSV, XLSX or JSON. Provider message IDs, private media URLs, provider media IDs and
  internal storage references are deliberately excluded; spreadsheet formula triggers are neutralized.
- **Shared pipeline/UI:** transcript jobs reuse the existing `exports` row, `exports` queue, worker
  retry policy, storage provider, expiry, signed URL and personal Download Center. Chat History adds
  a permission-truthful export sheet with date range, live progress, direct download and Center link;
  Download Center adds the `chat_history` category and navigation entitlement.
- **Persistence/API:** additive `0053_conversation_transcript_exports` creates no table and preserves
  one linear **54-revision** head. Start/progress resources bring OpenAPI to **221 paths**; generated
  TypeScript and the **31-task** source image contract are synchronized.
- **Validation:** focused backend **35/35**, focused Chat History/Download/navigation UI **50/50**,
  complete backend **1537 passed / 6 MySQL-only skipped / 0 failed in 445.40s**, complete frontend
  **41 files / 845 tests**, static **6/6**, strict mypy **310 files**, migration round-trip and Vite
  **8.2.2** production build PASS. Chat History chunk is **15.34 kB / 4.90 kB gzip**.
- **Boundary:** list-level date/campaign/media/audit filters, server-shared Chat History saved views,
  campaign/Scan/generated-document artifact families, Docker/security rerun and target-host
  commissioning remain pending. No campaign send, provider call or live deployment occurred.

## PAR-REP-04 — Team Productivity and Current Workload

- **Status:** `REPOSITORY IMPLEMENTED`; Analytics advances **75% → 82%**, Executive Reports
  **65% → 75%**, Download Center **73% → 74%**, Team Management **82% → 86%**, and API **91% →
  92%**.
- **Authority:** historical productivity remains event-derived additive flow; current pending work
  is a bounded live snapshot over indexed tenant Conversation/Task authorities and is never summed
  across dates.
- **Productivity/UI:** conversation and task throughput now share a responsive Team Productivity
  workspace; managers also see unresolved/unread chats, open/overdue/due-today tasks, unassigned
  work and inactive owners still carrying pending items.
- **Reports:** Team Productivity extends the fixed catalogue to eleven and reuses PDF/XLSX/CSV/JSON,
  personal schedules, ready notifications, expiry, signed links and Download Center history.
- **Persistence/API:** additive `0052_team_productivity_reports` preserves one linear **53-revision**
  head; current workload plus named task productivity bring OpenAPI to **219 paths** with generated
  TypeScript synchronized.
- **Validation:** focused backend **79 passed / 6 MySQL-only skipped**, focused Analytics UI
  **36/36**, complete backend **1534 passed / 6 MySQL-only skipped / 0 failed in 367.01s**,
  complete frontend **41 files / 843 tests**, static **6/6**, strict mypy **310 files**, migration
  round-trip and Vite **8.2.2** production build PASS.
- **Boundary:** revenue/recovered value, campaign attribution/ROI, explicit capacity limits and
  utilization, online presence, login history, permission-audit UI and target-host acceptance remain.

## PAR-REP-03 — Domain Outcome Analytics

- **Status:** `REPOSITORY IMPLEMENTED`; Analytics advances **55% → 75%**, Executive Reports
  **50% → 65%**, Download Center **72% → 73%**, and API **90% → 91%**.
- **Authority:** one rebuildable domain-outcome fact family derives only from immutable business
  events; operational Reactivation/KYC/SIM/Activation/SLA aggregates remain authoritative.
- **Metrics:** factual case creation/stage/terminal outcomes, eligibility, KYC decisions and
  turnaround, SIM/Activation outcomes and SLA starts/breaches/resolutions with source/actor/outcome
  dimensions. Conversion/approval/breach/turnaround values are read-time formulas over additive
  components and return unknown when no denominator exists.
- **Reports/UI:** Analytics now presents a responsive Business outcomes tab and KPI cards. Three
  new Reactivation/KYC/Service-level report families reuse PDF/XLSX/CSV/JSON exports, schedules,
  ready notifications and Download Center delivery.
- **Persistence/API:** additive `0051_domain_outcome_analytics` produces one linear **52-revision**
  head; OpenAPI is **217 paths** and generated TypeScript is synchronized.
- **Validation:** focused backend **144/144**, focused Analytics UI **35/35**, complete backend
  **1532 passed / 6 MySQL-only skipped / 0 failed in 426.19s**, complete frontend **41 files / 842
  tests**, static **6/6**, strict mypy **309 files**, migration round-trip and production build PASS.
- **Boundary:** revenue, campaign conversion attribution/ROI, capacity/workload, remaining artifact
  families, external delivery and target-host acceptance remain pending.

## PAR-REP-02 — Scheduled Analytics Reports

- **Status:** `REPOSITORY IMPLEMENTED`; Executive Reports advance **35% → 50%**, Download Center
  **70% → 72%**, Notifications **85% → 86%**, and API **89% → 90%**.
- **Authority:** personal daily/weekly/monthly schedules create the existing Analytics export job;
  the current worker, storage, expiry, signed link and Download Center remain authoritative.
- **Safety:** both `analytics:export` and `analytics:executive` are required; schedules are personal
  and tenant-scoped, updates/deletes use row versions, due claims use `SKIP LOCKED`, and inactive or
  permission-revoked owners are disabled before any artifact is created.
- **Delivery/UI:** fixed report/format/range/grouping choices, IANA timezone/local-time recurrence,
  create/edit/pause/resume/two-step-delete controls, next-run truth and an idempotent `report_ready`
  notification deep-linking to Download Center.
- **Persistence/API:** additive `0050_scheduled_analytics_reports` produces one linear **51-revision**
  head; OpenAPI is **214 paths**, generated TypeScript and the 30-task inventory are synchronized.
- **Validation:** scheduled lifecycle **5/5**, combined backend **71/71**, focused Analytics UI
  **34/34**, complete backend **1530 passed / 6 MySQL-only skipped / 0 failed in 425.43s**, complete
  frontend **41 files / 841 tests**, static **6/6**, strict mypy **309 files**, migration round-trip,
  local browser boot/no-console-error check and production build PASS.
- **Boundary:** no new revenue/ROI/productivity/workload/SLA/case-outcome projection, transcript/
  campaign/Scan/generated-document family, external delivery channel or target-host acceptance.

## PAR-REP-01 — Analytics PDF Reports

- **Status:** `REPOSITORY IMPLEMENTED`; Executive Reports advance **25% → 35%** and Download Center
  advances **65% → 70%**.
- **Authority:** all seven existing analytics report families gain PDF through the same rollup,
  export job, queue, storage, expiry, signed-link and Download Center pipeline. Contact PDF remains
  rejected.
- **Artifact:** deterministic landscape-A4 tables with repeated headers/page numbers, bounded cell
  fitting, empty-result text and explicit micro-unit cost labels.
- **Persistence/API:** additive `0049_report_pdf_exports` produces one linear **50-revision** head.
  OpenAPI remains **212 paths** and generated TypeScript is synchronized.
- **Validation:** focused backend **139/139**, focused Analytics/Download UI **36/36**, complete
  backend **1525 passed / 6 MySQL-only skipped / 0 failed in 434.13s**, complete frontend **41 files /
  839 tests**, static **6/6**, strict mypy **306 files**, current backend dependency audit with no
  known vulnerabilities and production build PASS. A three-page sample passes Poppler page-by-page
  visual review and structural/text inspection.
- **Boundary:** schedules, revenue/ROI/productivity/workload/SLA/case-outcome reports, transcript/
  campaign/Scan/generated-document artifacts and target-host acceptance remain pending.

## PAR-DL-01 — Unified Download Center

- **Status:** `REPOSITORY IMPLEMENTED`; Download Center advances **30% → 65%**.
- **Authority:** one projection over existing `exports` jobs, storage artifacts and signed links;
  no duplicate job table, artifact store, queue or retry mechanism.
- **Security:** organization + requesting-user ownership and current `contacts:export` /
  `analytics:export` family permissions are enforced. Expired artifacts never receive a link.
- **UI:** entitled Tools tab, URL-backed type/status filters, keyset pagination, manual refresh,
  active-job polling and complete loading/error/empty/status/action states.
- **Validation:** Download API **5/5**, corrected path-count + API **7/7**, focused UI/navigation
  **14/14**, complete backend **1523 passed / 6 MySQL-only skips / 0 failed in 326.78s**, complete
  frontend **41 files / 838 tests**, static **6/6**, strict mypy **306 files**, synchronized
  **212-path** OpenAPI and production build PASS. `DownloadsPage` is **7.03/2.50 kB gzip**.
- **Boundary:** contact and analytics CSV/XLSX/JSON exports are connected. PDF, scheduled/executive
  reports, Chat History transcripts, campaign/scan exports and generated-document artifacts remain.
  No migration, permission code, queue, storage provider or customer send is added.

## PAR-AUTO-23 — Shared Delay Before Follow-Up

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while one shared follow-up may
  pause durably after either bounded Yes/No outcome.
- **Topology:** both branch terminals converge on exactly one Delay, which points to exactly one
  terminal trigger-safe shared effect. The existing four-effect ceiling is unchanged.
- **Replay/test safety:** the selected body checkpoints before the Delay. Early/duplicate delivery
  reuses one running attempt; due resume completes the timer, executes the shared effect once and
  skips only alternate-only nodes. Safe test mode mirrors the path without mutation.
- **UI:** `Add shared delay before follow-up` inserts a labeled `Shared delay`; removal reconnects
  both branch terminals, while removing its dependent follow-up removes the timer as well.
- **Validation:** live/safe runtime **54/54**, Automation/API/trigger/Schedule/migration **77/77**,
  focused UI **23/23**, full backend **1524/1524 in 475.70s**, full frontend **40 files / 833 tests**,
  static **6/6** and production build PASS; AutomationPage is **52.47/13.23 kB gzip**.
- **Release boundary:** the Docker/security release rerun was blocked when its required approval
  service exhausted usage. PAR-AUTO-22's **23/23 in 685.9s** remains the last complete release
  certificate and is not attributed to this tree.
- **Scope boundary:** no migration/route/permission/queue/provider/customer send. Branch-specific
  Delay/Wait, multiple timers, arbitrary/multiple merges, multiple/nested Conditions, longer bodies,
  external actions and operational reconciliation remain.

## PAR-AUTO-22 — Bounded Shared Follow-Up

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while both sides of one bounded
  Yes/No split may converge on one terminal trigger-safe internal effect.
- **Topology:** both branch terminals point to exactly one shared node. It has two incoming edges,
  no outgoing edge and stays under the existing four-effect graph ceiling. Each executable path
  keeps distinct effect kinds.
- **Replay/test safety:** only the selected branch and shared node execute. Unselected-only nodes
  are durably skipped; the shared node belongs to both path projections and executes once under
  existing node/domain idempotency. Safe test mode mirrors the same path without mutation.
- **UI:** the active branch exposes `+ Both` and labels the node `After both`; second branch steps
  can be inserted before the merge, and removal safely reconnects or removes the shared follow-up.
- **Validation:** live/safe runtime **51/51**, combined Automation/API/migration **78/78**, focused
  UI **22/22**, full frontend **40 files / 832 tests**, static **6/6**, and complete release profile
  **23/23 in 685.9s**. That run includes **1521 backend tests with zero skips**, strict mypy **305
  files**, OpenAPI **211 paths**, production build, image contracts/scans and SBOMs; AutomationPage
  is **50.52/12.77 kB gzip**.
- **Boundary:** no migration/route/permission/queue/provider/customer send. Arbitrary/multiple
  merges, multiple/nested Conditions, longer branch bodies, branch Delay/Wait, external actions
  and operational reconciliation remain.

## PAR-AUTO-21 — Bounded Multi-Step Branch Bodies

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while each side of one bounded
  Yes/No split may contain one or two ordered distinct internal effects.
- **Topology:** one event-backed Condition owns explicit `yes` and `no` edges. Each side remains a
  linear body of at most two trigger-safe effects under the existing four-effect total ceiling.
- **Replay/test safety:** only the selected body executes from durable node checkpoints; every
  unselected node is terminal skipped evidence. Safe test mode simulates the same selected body.
- **UI:** the active branch exposes a dedicated Yes/No effect palette, labels second steps, blocks
  unsafe reordering and permits only the terminal addition to be removed directly.
- **Validation:** live/safe runtime **48/48**, combined Automation/API/migration **75/75**, focused
  UI **21/21**, full frontend **40 files / 831 tests**, static **6/6**, and complete release profile
  **23/23 in 609.3s**. That run includes **1518 backend tests with zero skips**, strict mypy **305
  files**, OpenAPI **211 paths**, production build, image contracts/scans and SBOMs; AutomationPage
  is **48.38/12.24 kB gzip**.
- **Boundary:** no migration/route/permission/queue/provider/customer send. Multiple/nested
  Conditions, longer branch bodies, branch Delay/Wait, merging, external actions and operational
  reconciliation remain.

## PAR-AUTO-20 — Bounded Live Yes/No Branch

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while one real terminal decision
  split gains live and safe-test execution.
- **Topology:** exactly one event-backed Condition may own one `yes` and one `no` edge, each ending
  at one trigger-safe internal effect. Only the selected effect executes; the other receives durable
  skipped evidence containing the selected branch.
- **Replay/test safety:** existing node/domain idempotency protects the chosen effect. Safe test mode
  selects the same branch and simulates only that action without changing business state.
- **UI:** after exactly Trigger, Condition, Yes action and No action exist, the builder can label and
  lock the split or return it to a linear gate.
- **Validation:** live/safe runtime **45/45**, combined Automation/API/migration **60/60**, focused
  UI **20/20**, full frontend **40 files / 830 tests**, static **6/6**, and complete release profile
  **23/23 in 417.8s**. That run includes **1515 backend tests with zero skips**, strict mypy **305
  files**, OpenAPI **211 paths**, production build, image contracts/scans and SBOMs; AutomationPage
  is **44.79/11.20 kB gzip**.
- **Boundary:** no migration/route/permission/queue/provider/customer send. Multiple Conditions,
  nested or multi-step branch bodies, branch Delay/Wait, external actions and reconciliation remain.

## PAR-AUTO-19 — Live Lead-Stage Changed Automation

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while a fifth bounded trigger
  and third Wait event gain live evidence.
- **Authority/privacy:** the existing immutable `reactivation.stage.transitioned` fact is consumed
  as `lead.stage_changed`; Automation receives only previous/new stage and the tenant-checked public
  Contact ID. The private transition reason and internal Reactivation identifiers are excluded.
- **Live path:** Previous/New stage conditions may lead through one Delay or Wait to Contact-linked
  Task, Apply tag, Remove tag and internal Notification. No Conversation is fabricated; Handoff,
  Assignment, branches and external/customer actions remain fail-closed.
- **Wait/recovery:** only a future same-organization/Contact stage transition may resume the pinned
  receipt/run. Existing subscription, node-attempt and receipt-heartbeat evidence owns replay,
  timeout and enqueue-failure recovery.
- **Validation:** focused runtime **35/35**, combined Automation/Reactivation/migration **56/56**,
  Automation UI **19/19**, full frontend **40 files / 829 tests**, static **6/6**, and complete
  release profile **23/23 in 389.1s**. That run includes **1512 backend tests with zero skips**,
  strict mypy **305 files**, OpenAPI **211 paths**, production build, image contracts and scans;
  AutomationPage is **42.56/10.49 kB gzip**.
- **Boundary:** no migration/route/permission/queue/provider/customer send. Head remains `0048`
  (**49 revisions**). General branching, external/customer actions, recipient/team routing and
  operational reconciliation remain pending.

## PAR-AUTO-18 — Durable Task-Completed Wait

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while a second Wait event gains
  live same-customer evidence.
- **Task authority:** single and bulk completion append deterministic `task.completed` Business
  Events in the existing Task/history/Timeline/Audit transaction. Reopened/re-completed Tasks use a
  distinct completion revision.
- **Privacy/isolation:** only Task public ID, type, priority, completed status and revision are
  projected. Title, description and completion note are excluded; wrong-organization/Contact
  completions cannot resume a Wait.
- **Resume/recovery:** the matching fact releases the original receipt and the existing minute
  receipt heartbeat resumes the pinned run/checkpoints. Timeout and replay behavior are unchanged.
- **Validation:** focused **4/4**, Task/Wait **53/53**, combined **130/130**, Automation UI **18/18**,
  full frontend **40 files / 828 tests**, static **6/6**, strict mypy **305 files** and production
  build PASS; AutomationPage is **42.56/10.78 kB gzip**. Applicable backend is **1501 passed / 6
  MySQL skips / 1 Redis deselection** in **377.10s**.
- **Boundary:** no migration/route/permission/queue/provider/customer send. Head remains `0048`
  (**49 revisions**) and OpenAPI **211 paths**. Lead-stage projection is now delivered by
  PAR-AUTO-19; general branching, external/customer actions and operational reconciliation remain.

## PAR-AUTO-17 — Durable Wait for Event

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while one event-backed path gains
  durable wait/resume.
- **Wait contract:** one Wait may pause for the same Contact's future `message.received` event for
  60 seconds to 30 days and must precede a later approved internal effect.
- **Persistence:** additive `0048_automation_wait_subscriptions` owns organization/contact scope,
  original receipt/run/node lineage, deadline, match UUID and resolution state. Head is `0048`
  (**49 revisions**); OpenAPI remains **211 paths**.
- **Resume/recovery:** a matching inbound can dispatch the original receipt immediately; failed
  enqueue and due timeout are recovered by the existing minute receipt heartbeat. Duplicate work
  converges on the same Wait attempt and downstream checkpoints.
- **Validation:** Wait **3/3**, combined Automation **55/55**, wider regression **112/112**,
  Automation UI **17/17**, full frontend **40 files / 827 tests**, static **6/6**, strict mypy **305
  files** and build PASS; AutomationPage is **42.50/10.77 kB gzip**. Applicable backend is **1499
  passed / 6 MySQL skips / 1 Redis deselection** in **400.25s**; final temporal edge **3/3** passes.
- **Boundary:** Schedule Wait, multiple Waits, terminal Wait, general branching, external/customer
  actions, recipient/team routing and operational reconciliation remain pending. Task and
  Lead-stage event projections were subsequently delivered by PAR-AUTO-18 and PAR-AUTO-19.

## PAR-AUTO-16 — Durable Live Schedule

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while a fourth trigger gains
  bounded live execution.
- **Timezone schedule:** publishing projects the five-field cron to indexed UTC `next_run_at` from
  the organization IANA timezone. Disable clears it; enable and republish recompute it.
- **Durable claim:** the minute scheduler row-locks a bounded clean/enabled due set, writes one
  deterministic immutable `schedule` event and exact receipt, then advances to the first future
  occurrence. Existing stale-receipt recovery owns post-commit enqueue failure.
- **Live boundary:** Schedule may deliver one workspace-only Notification to the active eligible
  publisher, with one optional Delay. Condition, Task, tags, Handoff, Assignment, Wait, webhook,
  campaign and customer-message effects fail closed.
- **Migration/API:** additive `0047_automation_schedule_due` adds only the nullable projection and
  due index; head is `0047` (**48 revisions**), OpenAPI remains **211 paths**, and generated
  TypeScript is synchronized.
- **Validation:** Schedule **4/4**, combined Automation **42/42**, wider regression **222/222**,
  Automation UI **16/16**, full frontend **40 files / 826 tests**, static **6/6**, strict mypy **305
  files** and build PASS; AutomationPage is **41.90/10.62 kB gzip**. Applicable backend is **1496
  passed / 6 MySQL skips / 1 Redis deselection** in **376.13s**.
- **Boundary:** general branching, Wait-for-event, external/customer actions, recipient/team
  routing, capacity/skill routing and operational reconciliation remain.

## PAR-AUTO-15 — Conversation Auto-Resolved Live Follow-up

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while a third event type gains
  bounded live execution.
- **Event-safe path:** Conversation Auto-Resolved may create a publisher-assigned follow-up Task,
  Apply tag, Remove tag and internal Notification, with one approved Condition and one Delay.
- **Lineage:** public Contact/Conversation references are tenant-checked from immutable Business
  Event lineage for the run; stored event payload evidence is not changed.
- **Resolved-chat boundary:** Human handoff and Assignment fail closed before any effect, so the
  workflow cannot silently reopen or re-own the resolved Conversation.
- **Validation:** runtime **29/29**, combined regression **50/50**, wider regression **180/180**,
  Automation frontend **15/15**, full frontend **40 files / 825 tests**, static **6/6**, strict mypy
  **305 files**, OpenAPI **211 paths** and build PASS; AutomationPage is **41.33/10.48 kB gzip**.
  Applicable backend is **1492 passed / 6 MySQL skips / 1 Redis deselection** in **212.83s**.
- **Boundary:** general branching, Wait-for-event, further live events, external/customer actions,
  recipient/team routing, capacity/skill routing and operational reconciliation remain.

## PAR-AUTO-14 — Contact Created Live Consumer and Receipt Recovery

- **Status:** `REPOSITORY IMPLEMENTED`; Automation remains **99%** while a second event type gains
  bounded live execution.
- **Event-safe path:** Contact Created may execute Apply tag, Remove tag and internal Notification,
  optionally behind the approved source/opt-in Condition and one durable Delay.
- **Durable dispatch:** the existing scheduler queue scans once per minute, row-locks received or
  genuinely stale processing receipts, and hands them to the existing idempotent Automation worker.
  New rows are leased before dispatch; stale rows retain their recovery evidence.
- **Delay ownership:** a paused Delay has no processing lease and is excluded from the scanner; its
  already-scheduled continuation remains the sole resume owner.
- **Fail-closed boundary:** Handoff, Create task and Assignment require Conversation context and are
  rejected before any Contact Created effect. Other event types remain test-only.
- **Validation:** runtime **26/26**, focused trigger/scheduler/runtime **35/35**, wider regression
  **175/175**, Automation frontend **14/14**, full frontend **40 files / 824 tests**, static **6/6**,
  strict mypy **305 files**, OpenAPI **211 paths** and build PASS; AutomationPage is
  **40.93/10.39 kB gzip**. Canonical execution preserves **1489 passes / 6 MySQL skips / 1 known
  Redis-only failure**; applicable backend is **1489 passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** general branching, Wait-for-event, further live event consumers, external/customer
  actions, recipient/team routing, capacity/skill routing and operational reconciliation remain.

## PAR-AUTO-13 — Durable Live Delay

- **Status:** `REPOSITORY IMPLEMENTED`; completion advances **98% → 99%**.
- **Delay contract:** one 60-second-to-30-day Delay may pause an otherwise supported connected
  inbound sequence of up to four distinct internal effects.
- **Checkpoint/resume:** one running Delay attempt stores the due time. The existing Automation
  worker schedules the same receipt task; early duplicates cannot pass the checkpoint, and due
  delivery resumes without replaying completed upstream effects.
- **Fail-closed boundary:** multiple delays, branches, Wait-for-event nodes, repeated effect kinds,
  larger sequences and external/unsupported nodes apply no effect.
- **Validation:** live runtime **22/22**, wider regression **166/166**, Automation frontend
  **13/13**, full frontend **40 files / 823 tests**, static **6/6**, strict mypy **305 files**,
  OpenAPI **211 paths** and build PASS; AutomationPage is **40.53/10.33 kB gzip**. Canonical backend
  is **1485 passed / 6 MySQL skips / 1 known Redis-only failure**; applicable backend is **1485
  passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** general branching, event waits, other event consumers, recipient/team routing,
  campaign/webhook/customer-message actions and operational reconciliation remain future.

## PAR-AUTO-12 — Bounded Sequential Effect Runtime

- **Status:** `REPOSITORY IMPLEMENTED`; completion advances **96% → 98%**.
- **Sequence contract:** one inbound Trigger, one optional approved Condition and one to four
  distinct existing live effects execute in their connected order.
- **Checkpoint/replay:** completed node attempts are durable checkpoints. Retry resumes from the
  first incomplete node; existing effect idempotency prevents duplicate domain work.
- **Fail-closed boundary:** branches, repeated effect kinds, more than four effects, multiple
  conditions, waits/delays and external/unsupported nodes apply no effect.
- **Validation:** live runtime **19/19**, combined regression **88/88**, Automation frontend
  **12/12**, full frontend **40 files / 822 tests**, static **6/6**, strict mypy **305 files**,
  OpenAPI **211 paths** and build PASS; AutomationPage is **40.17/10.23 kB gzip**. Canonical backend
  is **1482 passed / 6 MySQL skips / 1 known Redis-only failure**; applicable backend is **1482
  passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** general branching, waits/delays, other event consumers, recipient/team routing,
  campaign/webhook/customer-message actions and complete retry/DLQ/reconciliation remain future.

## PAR-AUTO-11 — Live Internal Notification Executor

- **Status:** `REPOSITORY IMPLEMENTED`; completion advances **94% → 96%**.
- **Effect contract:** exact Trigger → Notification and Trigger → Condition → Notification paths
  create one Contact-linked internal Notification Center delivery for the active publisher.
- **Safety/replay:** the publisher must retain same-tenant `tasks:read` access. Receipt/node dedup
  makes crash replay `already_delivered`; conflicting evidence and invalid references fail closed.
  A false Condition records skipped and creates no delivery.
- **Boundary:** migration `0046` adds only `automation_attention` to the existing Notification type
  constraint. There is no new route, permission, queue, external channel, provider or customer send.
- **Validated:** runtime **15/15**, combined Notification/migration regression **23/23**, static
  **6/6**, strict mypy **305 files**, OpenAPI **211 paths**, migration round trip and canonical
  backend **1478 passed / 6 MySQL skips / 1 known Redis-only failure**; applicable backend **1478
  passed / 6 MySQL skips / 1 Redis deselection**. Frontend ESLint/TypeScript, focused Automation/
  Notification **14/14**, full frontend **40 files / 821 tests** and production build pass;
  AutomationPage is **40.08/10.20 kB gzip**.
- **Remaining boundary:** multiple effects/general branching, other event consumers, waits/delays,
  campaign/webhook/customer-message effects, recipient/team routing and complete retry/DLQ/
  reconciliation operations remain future PAR-AUTO work.

## PAR-AUTO-10 — Live Remove Tag Executor

- **Status:** `REPOSITORY IMPLEMENTED`; Remove tag is the fourth internal work effect while the
  general chatbot/automation engine remains partial.
- **Effect contract:** exact Trigger → Remove tag and Trigger → Condition → Remove tag paths detach
  the immutable published CRM tag from the inbound Contact through the existing tenant authority.
- **Concurrency/evidence:** Contact and Tag locks protect the association and usage counter. A new
  automatic removal creates one system Audit and one Timeline event; replay/already-absent is a
  successful no-op without duplicate domain evidence.
- **Condition/tenancy:** a false privacy-safe Condition records skipped and leaves the existing tag
  attached. Missing, deleted, malformed, nil and foreign Contact/Tag references fail closed.
- **Validation:** runtime **13/13**, combined runtime/Tag regression **45/45**, full frontend
  **40 files / 821 tests**, focused Automation **11/11**, static **6/6**, strict mypy **305 files**,
  OpenAPI **211 paths**, build PASS and AutomationPage **39.68/10.12 kB gzip**. Canonical backend:
  **1476 passed / 6 MySQL skips / 1 known Redis-only failure**; applicable: **1476 passed / 6 MySQL
  skips / 1 Redis deselection**.
- **Boundary:** multiple effects/general branching, waits/delays, notification/campaign/webhook/
  customer-message executors, other consumers and complete retry/DLQ/reconciliation operations
  remain pending.

## PAR-AUTO-09 — Live Assignment Executor

- **Status:** `REPOSITORY IMPLEMENTED`; Assignment is the third internal work effect while the
  general chatbot/automation engine remains partial.
- **Effect contract:** exact Trigger → Assignment and Trigger → Condition → Assignment paths assign
  the inbound Conversation to a published specific user or deterministic per-flow round robin.
- **Eligibility/ownership:** specific users and rotation candidates must be active same-tenant users
  with effective Inbox read access at execution. The locked Conversation keeps any existing owner;
  Automation never steals or replaces it.
- **Replay/evidence:** a new ownership change and one system `conversation.assigned` Audit commit
  together. Crash replay finishes as `already_assigned` without another mutation, version bump or
  Audit. A false privacy-safe Condition records skipped and no ownership effect.
- **Validation:** runtime **11/11**, combined Automation/Inbox regression **45/45**, full frontend
  **40 files / 820 tests**, focused Automation **10/10**, static **6/6**, strict mypy **305 files**,
  OpenAPI **211 paths**, build PASS and AutomationPage **38.91/10.05 kB gzip**. Canonical backend:
  **1474 passed / 6 MySQL skips / 1 known Redis-only failure**; applicable: **1474 passed / 6 MySQL
  skips / 1 Redis deselection**.
- **Boundary:** multiple effects/general branching, waits/delays, Remove tag, notification/campaign/
  webhook/customer-message executors, team capacity/skill routing, other consumers and complete
  retry/DLQ/reconciliation operations remain pending.

## PAR-AUTO-08 — Live Apply Tag Executor

- **Status:** `REPOSITORY IMPLEMENTED`; Apply tag is the second internal live effect while the
  general chatbot/automation engine remains partial.
- **Effect contract:** exact Trigger → Apply tag and Trigger → Condition → Apply tag paths attach
  the immutable published CRM tag to the inbound Contact through the existing tenant authority.
- **Concurrency/evidence:** Contact and Tag locks protect the association and usage counter.
  Automated writes create one system Audit and one Timeline event; replay/already-present is a
  successful no-op without duplicate domain evidence.
- **Condition/tenancy:** a false privacy-safe Condition records skipped and no CRM effect. Missing,
  deleted, malformed, nil and foreign Contact/Tag references fail closed inside the receipt tenant.
- **Validation:** runtime **9/9**, combined Tag regression **32/32**, full frontend **40 files / 819
  tests**, focused Automation **9/9**, static **6/6**, strict mypy **305 files**, OpenAPI **211 paths**,
  build PASS and AutomationPage **37.93/9.84 kB gzip**. Canonical backend: **1472 passed / 6 MySQL
  skips / 1 known Redis-only failure**; applicable: **1472 passed / 6 MySQL skips / 1 Redis
  deselection**.
- **Boundary:** Remove tag, multiple effects/general branching, waits/delays, assignment/
  notification/customer-message executors, other consumers and retry/DLQ/reconciliation remain.

## PAR-AUTO-07 — Live Create Task Executor

- **Status:** `REPOSITORY IMPLEMENTED`; the first internal work effect is live while the general
  chatbot/automation engine remains partial.
- **Effect contract:** exact Trigger → Create task and Trigger → Condition → Create task paths create
  one existing Task linked to the inbound Contact/Conversation. Published inputs are trimmed title,
  existing type, existing priority and a 5-minute-to-365-day due delay.
- **Ownership/evidence:** the active automation publisher is assignee; system creation reuses Task
  history, Contact Timeline and Audit. Missing/inactive/cross-tenant references fail closed.
- **Replay/condition:** receipt UUID plus canonical command hash recovers one Task after a worker
  crash and rejects command drift. A false privacy-safe Condition records skipped and no Task effect.
- **Validation:** runtime **7/7**, Task API **45/45**, full frontend **40 files / 818 tests**, focused
  Automation **8/8**, static **6/6**, strict mypy **305 files**, OpenAPI **211 paths**, build PASS and
  AutomationPage **37.59/9.76 kB gzip**. Canonical backend: **1470 passed / 6 MySQL skips / 1 known
  Redis-only failure**; applicable backend: **1470 passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** general branches, waits/delays, tag/notification/customer-message executors, other
  live consumers and complete retry/DLQ/reconciliation operations remain pending.

## PAR-AUTO-06 — Privacy-Safe Live Conditions

- **Status:** `REPOSITORY IMPLEMENTED`; one optional linear condition is live, while general
  branching and the broader chatbot engine remain partial.
- **Decision contract:** exact Trigger → Condition → Human handoff graphs may read only event type,
  source, message direction or message type with `eq`, `ne`, `contains` or `exists`. Every other
  field/operator/shape fails closed before an effect.
- **Evidence:** matching continues to the existing idempotent handoff; non-matching records a
  terminal `skipped` handoff and succeeds with no Conversation change. Decision evidence stores
  field/operator/presence/match only, never the actual private value.
- **Persistence/UI:** additive migration `0045` (46 revisions) adds skipped-attempt evidence.
  Automation suggests live-safe condition metadata and distinguishes completed no-effect runs.
  OpenAPI remains **211 paths**.
- **Validation:** conditional runtime/migration **10/10**, full frontend **40 files / 818 tests**,
  focused Automation **8/8**, static gate **6/6**, strict mypy **305 files**, build PASS and
  AutomationPage **35.98/9.43 kB gzip**. Canonical backend: **1468 passed / 6 MySQL skips / 1 known
  Redis-only failure**; applicable backend: **1468 passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** multiple conditions/general branches, waits/delays, other live consumers,
  task/tag/notification/customer-message executors and complete retry/DLQ/reconciliation remain.

## PAR-AUTO-05 — Automatic Inbound Handoff Runtime

- **Status:** `REPOSITORY IMPLEMENTED`; the exact inbound Trigger → Human handoff path is live,
  while the general chatbot/runtime remains partial.
- **Event/dispatch:** a new inbound Message records a connector-authored, content-free
  `message.received` Business Event and matching receipts atomically. Post-commit dispatch is
  deterministic; completed/failed receipts are not requeued and a stale processing lease can
  recover.
- **Execution/evidence:** one locked receipt creates one pinned `mode=live` run with trigger and
  handoff attempts. The existing idempotent handoff produces real Live Chat Requested; unsupported
  graph shapes fail closed with run/receipt evidence. Test mode remains simulated.
- **Persistence/UI:** additive migration `0044` (45 revisions) adds receipt/run lineage and terminal
  timestamps. Automation shows live/test Run history and actual receipt state with bounded polling;
  OpenAPI remains **211 paths**.
- **Evidence:** focused final regression **40/40**, full frontend **40 files / 817 tests**, static
  gate **6/6**, strict mypy **305 files**, migration round-trip **5/5**, build PASS and
  AutomationPage **35.10/9.16 kB gzip**. Canonical backend: **1465 passed / 6 MySQL skips / 1 known
  Redis-only failure**; applicable backend: **1465 passed / 6 MySQL skips / 1 Redis deselection**.
- **Boundary:** conditions/branching, waits/delays, other live event consumers and executors,
  customer-message actions and complete retry/DLQ/reconciliation UI remain pending.

## PAR-AUTO-04 — Governed Automation Human Handoff

- **Status:** `REPOSITORY IMPLEMENTED`; this is one real production action contract, not a claim of
  a general live automation runtime.
- **Authoring:** clean immutable definitions can include a typed `Human handoff` node with a bounded
  published reason. The original builder marks the node as a live contract; safe test runs remain
  fully simulated and side-effect-free.
- **Execution:** a publisher-scoped, UUID-idempotent API row-locks the same-tenant conversation and
  requests it through existing `pending`. Already requested/intervened chats are preserved;
  historical resolved ownership is cleared; old replays cannot requeue a claimed chat.
- **Evidence:** deterministic Business Event plus Audit evidence commit with the existing status/
  assignment facts. Backend Automation/Inbox **76/76**, focused definition/handoff **14/14**, full
  frontend **40 files / 817 tests**, OpenAPI **211 paths**, static gate **6/6** with strict mypy over
  **304 files**, production build PASS and applicable backend **1462 passed / 6 MySQL skips / 1
  known Redis-dependent deselection**.
- **Boundary at delivery:** no migration, new permission, queue, provider action or customer send.
  PAR-AUTO-05 has since added the exact automatic inbound run; general graphs, retry operations and
  every other executor remain future PAR-AUTO work.

## AiSensy-style navigation and Live Chat intervention follow-up

- **Status:** `REPOSITORY VALIDATED`; Inbox advances because the visible lifecycle now performs
  guarded server work rather than only relabelling filters.
- **Navigation:** named daily tabs are visible by default; Templates and every additional entitled
  product area remain under `Manage`; compact mode is still user-selectable.
- **Live Chat:** `Requested`, `Active` and `Intervened` are factual views over the existing pending,
  open and current-user assignment contracts. `Intervene` atomically claims a request, protects
  against double claim, audits ownership/status and is idempotent; only that owner can `Resolve`,
  including through the legacy status route. No migration, new permission or duplicate state
  machine is introduced.
- **Evidence:** intervention backend **24/24**, combined contract regression **26/26**, intervention/
  thread frontend **37/37**, complete frontend **40 files / 816 tests**, ESLint, TypeScript and
  production build PASS. OpenAPI/generated TypeScript are synchronized at **210 paths**.
- **Pending:** general chatbot execution beyond the exact automatic inbound handoff path, SLA badges, authenticated
  representative-data visual/accessibility/browser comparison and target-host concurrency.

## CORE-11C — Inactivity Auto-Resolve

- **Milestone status:** `REPOSITORY IMPLEMENTED`; CORE-11 remains `PARTIAL`.
- **Completion effect:** Settings and Inbox advance because a bounded timer now performs guarded
  conversation lifecycle work rather than storing an inert preference.
- **Reuse:** reserved Inbox Operations setting, Conversation status/activity facts, open Tasks,
  Audit, Business Event, existing Celery Beat and `scheduler.tick`. No migration, new path,
  permission, queue or workflow engine.
- **Safety:** disabled by default; 1–720-hour bound; only read inactive open/pending threads;
  snoozed/resolved/unread/recent/open-Task rows protected; row-locked recheck; deterministic event;
  new current inbound reopens, duplicate/older replay does not.
- **Evidence:** backend focused **48 passed**, applicable suite **1453 passed / 6 MySQL skips / 1
  Redis case deselected**; canonical unfiltered suite records the same 1453 passes plus the known
  Redis-only failure. Ruff, strict mypy (302 files), OpenAPI drift and static gate 6/6 PASS.
  Frontend **39 files / 811 tests**, lint/types/build PASS.
- **Pending:** authenticated representative-data visual/accessibility/browser review, target-host
  MySQL/Celery concurrency and remaining CORE-11 controls.

## CORE-11B — Working Hours and Guarded Automatic Replies

- **Milestone status:** `REPOSITORY IMPLEMENTED`; CORE-11 remains `PARTIAL`.
- **Completion effect:** Settings and Inbox advance because working hours and welcome/off-hours
  replies are now persisted, audited and consumed rather than display-only controls.
- **Reuse:** existing Organization timezone, reserved Inbox Operations setting, Conversation/
  Message ledger, Business Event, Audit, queue and provider adapters. No migration, new path,
  permission, scheduler or parallel authority.
- **Safety:** defaults off; exact opt-out suppresses; stale/future replay fails closed; off-hours
  precedes welcome and is limited to one per conversation/24 hours; welcome requires a newly opened
  24-hour customer window; duplicate reply delivery serializes on the durable Message row.
- **Evidence:** backend focused **40 passed**, delivery/Inbox **73 passed / 1 known Redis case
  deselected**, applicable suite **1450 passed / 6 MySQL skips / 1 Redis case deselected**; Ruff,
  strict mypy (302 files), OpenAPI drift and static gate 6/6 PASS. Frontend **39 files / 810 tests**,
  lint/types/build PASS.
- **Pending:** authenticated representative-data visual/accessibility/browser review, target-host
  concurrency and live delivery commissioning, plus remaining CORE-11 controls.

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
| Inbox | 98% | Shared Inbox + Live Chat with factual Requested/Active/Intervened views carrying server-owned counts scoped to the search term alone, so each badge equals the rows its own click produces, executable row-locked Intervene/owner-only Resolve and an automatic inbound published-automation Human handoff that safely produces Requested once without requeueing claimed chats; CORE-11A/11B/11C routing/read/hours/replies/auto-resolve plus existing search, filters, saved views, bulk selects and pagination remain | General chatbot execution beyond the exact inbound handoff path, SLA badges, target-host concurrency and authenticated responsive/accessibility regression. | Automation, Notifications, SLA, Settings, shared design system |
| Chat History | 88% | PAR-HIST-01 adds factual date/campaign/media/audit list filters and governed organization-shared views to PAR-DL-02 transcripts; the read-only route retains immediate search/status/agent/channel/tag controls, full bounded messages, audit deep link and secure Download Center delivery | Authenticated representative-data WCAG/device/browser review and production-scale/target-host query commissioning. | Audit, Download Center, Saved Views |
| Contacts | 98% | PAR-VIEW-02 adds governed tenant-scoped private/team definitions over the existing server-evaluated search/tag/enum-attribute filter contract while preserving URL state, mobile sheet, cursor paging, bulk actions and export audience truth | Final opt-in/eligibility/assignment/export representative-data regression, target-device/WCAG review and production-scale query commissioning; no rebuild. | Saved Views, Reactivation, shared design system |
| Customer 360 | 90% | CORE-07 factual workspace composes identity/attributes, WhatsApp threads/messages, Reactivation CRM/reminders/notes/SLA, Tasks, Documents, KYC/SIM/Activation, Campaigns, Audit and Timeline with permission-aware source deep links | UI-TASTE hierarchy/density pass, target-device/WCAG, representative-data query-budget and production-scale commissioning; incorporate future approved source-domain facts without duplicating them. | Source domain milestones, performance lab, shared design system |
| Campaigns | 95% | PAR-VIEW-03 adds governed private/team list definitions over the existing URL-backed search/status/sort contract to PAR-CAM-01 recipient operations and PAR-DL-03 exports; applying a view resets only transient page state | Campaign-to-reactivation conversion attribution and approved recovered-value/revenue/ROI facts; authenticated representative-data/scale commissioning; no generic approval engine is required. | Saved Views, Reactivation analytics, Download Center |
| Templates | 80% | Registry, create/sync/status/media flows complete | Category server sync, button/variable preview regression, usage analytics, explicit AI placeholder. Favourites are now server-owned per user. | Analytics, settings/Meta sync |
| Segments | 75% | Dynamic/static segment and preset foundation | Complete reactivation/KYC/documents/activation/engagement predicates and shared saved filters. | Domain models, Saved Views |
| Automation | 99% | Versioned definitions, safe test runtime and durable receipt dispatch drive event-safe connected effects with one optional approved Condition, one bounded durable Delay, same-customer Message-received, Task-completed or Lead-stage-changed Wait and checkpoint replay. One Condition may also split to one or two ordered distinct internal effects on each Yes/No side with durable unchosen-branch evidence and one optional terminal shared follow-up reached by both outcomes; that shared follow-up may pause once through a common durable Delay. Message Received validates all six internal effects; Contact Created validates tag changes/Notification; Conversation Auto-Resolved validates follow-up Task, tag changes and Notification; Schedule durably projects organization-timezone cron slots to workspace-only Notification; Lead Stage Changed validates previous/new-stage conditions, Contact-linked Task, tags and Notification without exposing transition reasons. | Multiple/nested Conditions, longer branch bodies, branch-specific Delay/Wait, multiple timers, arbitrary or multiple merges, additional event projections, campaign/webhook/customer-message executors, recipient/team notification routing, capacity/skill routing, and operational reconciliation UI. | Inbox, Tasks, Contacts/Tags, Notifications, Reactivation, domain services |
| Analytics | 82% | Messaging/campaign/domain facts now include PAR-REP-04 conversation/task teammate productivity plus a separately labelled live pending-work snapshot; factual KPIs, comparisons and governed exports remain source-aligned | Campaign-to-case conversion attribution, approved recovered-value/revenue/ROI formulas, explicit capacity/utilization inputs and production-scale query commissioning. | Domain events and reporting projections |
| Executive Reports | 80% | PDF, personal schedules, governed personal/team report views and eleven governed families now cover messaging, campaign, cost, Reactivation/KYC/SLA and Team Productivity evidence | Revenue/ROI, campaign conversion attribution, approved capacity/utilization reports and separately approved external delivery channels. | Analytics, Download Center, Notifications, Saved Views |
| Reactivation | 96% | PAR-VIEW-01 adds audited tenant-scoped personal/team saved filters and board/list definitions to the CORE-05/07/09 authority, CRM-first hierarchy, URL-backed work views, connected navigation and bounded pagination | Campaign-to-case conversion attribution, authenticated representative-data visual/WCAG/device review and production-scale performance commissioning. | Tasks, Notifications, Analytics, shared design system |
| KYC | 90% | PAR-VIEW-04 adds governed private/team definitions over URL-backed customer search and lifecycle status to the CORE-04 persisted queue/detail, protected-document checklist, Task appointment and separated decision workflow | Server pagination, production protected-media commissioning, high-volume performance, and target-browser/device WCAG regression. | Saved Views, Documents, Tasks, Reactivation, Customer 360 |
| Documents | 87% | Phase 4A governed documents plus CORE-04 verified Aadhaar/PAN purpose references without plaintext identity numbers | Download policies, generated-document links and final encryption/retention commissioning; no generic approval authority is required. | Download Center |
| SIM Orders | 35% | CORE-02 order/event lifecycle, address/service area, owner, serial, delivery/failure/customer confirmation, SLA and APIs are preserved; CORE-05 exposes the lightweight `SIM Required` case status | No standalone heavy UI is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, KYC evidence, SLA |
| Activation | 35% | CORE-02 record lifecycle, hand-off, verification/approval/completion/rejection rules, RBAC, audit and APIs are preserved; CORE-05 exposes `Activation Pending`, `Completed` and `Not Required` case outcomes | No standalone Activation Queue or generic approval engine is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, Notifications |
| Notifications | 86% | CORE-09 durable center plus UI-TASTE-02 filters/actions and PAR-REP-02 idempotent scheduled-report-ready deliveries with a Download Center deep link; polling, read-state and team view are preserved | Page-specific visual hierarchy, authenticated responsive review, notification settings, and separately approved optional channels. SSE/browser push/email/internal WhatsApp are not implied. | Tasks, Reactivation, Reports, user preferences, shared design system |
| Settings | 92% | CORE-11A/11B/11C provide one validated, audited, service-consumed Inbox policy for assignment, read-state, exact opt-in/out keywords, organization-timezone hours, guarded replies and inactivity auto-resolve; organization/application/flags/preferences plus Tags, Canned Messages and User Attributes remain complete | Campaign, pipeline/SLA, notification/security/audit controls and later team settings. | Domain configuration APIs, RBAC |
| API | 99% | 237-path OpenAPI 3.1 contract with in-place key rotation that preserves a key's identity, scopes and audit trail, with synchronized generated TypeScript; governed Reports, KYC, Campaign, Contacts and Reactivation personal/team views join campaign exports, Chat History, transcripts, Team workload, Analytics and Download Center resources | Remaining final-domain routes, usage logs/IP restrictions completeness, key regeneration/revocation UX, published documentation. | Each domain milestone, Download Center |
| Webhooks | 80% | Provider webhooks and operations surface complete | Subscription governance, delivery/retry visibility, outbound final-domain events, security/usage documentation. | Domain event taxonomy, API permissions |
| Google Sheets | 0% | Not implemented | Approved credential model, contact import/sync/export jobs, mapping, audit, retries, admin UX. | Jobs, API keys/secrets, Contacts |
| WhatsApp Scan | 15% | Honest non-executing Scan Studio shell | Compliant provider contract, upload/batches/dedup/queue/results/retry/export/segments/analytics; no unofficial Web scanning. | Owner-approved compliant method, Jobs, Segments, Download Center |
| Approval Workflow | 20% | **CORE-08 — Skipped: Not required by product owner.** Existing KYC-specific approval logic and completed campaign/automation authorization safeguards are preserved. | No Approval Center, generic approval framework, approval queue, escalation system or new approval authority will be built. | Existing module-specific RBAC and audit only |
| Download Center | 88% | One permission/status/expiry/signed-link history now carries contacts, eleven Analytics families/schedules, Chat History transcripts and PAR-DL-03 governed campaign recipient results | Add compliant Scan-result and generated-document sources plus any separately approved artifact retry controls. | Source export/report/document milestones |

## Additional scope modules

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Enterprise Omnichannel Channel Manager | 52% | M13-00–M13-06B and QR-01–QR-08 provide provider-neutral contracts, exact Contact identity, persistent connections/secrets, durable session/runtime/pairing control plane, signed inbound ingestion, approved manual text/ACK routing and unified Inbox integration; migration line is preserved through the current `0048` head | Target-host/provider acceptance, remaining correlated outbound/persistence/logout evidence, provider history retrieval, media-byte transfer, final analytics/diagnostics and full browser/device commissioning. | Existing Contact/Organization/ChannelConnection/ChannelSession/ChannelAdapter/MediaAsset/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020/0021 and Design Document 33 |
| Shared Enterprise Design System | 94% | UI-TASTE-02 implements governed radius/density, forms, toolbars, filters, pagination and page headers; the current parity follow-up adds expanded named daily navigation and a permission-aware Manage group without removing routes | Authenticated representative-data visual/reference approval, remaining priority-screen adoption, remaining authenticated host visual/reference approval and final WCAG/browser matrix. | UI-TASTE-03–05 |
| Team Management | 86% | Users/roles/permissions and least-open assignment now join PAR-REP-04 teammate conversation/task performance plus live unresolved/unread/open/overdue workload, including unassigned and inactive-owner risks | Online presence, richer capacity/skill rules, explicit capacity limits/utilization, login history, permission audit and final role matrix. | Notifications, audit, Settings |
| Tags and Attributes | 96% | Both halves of this row are now reachable in the product: tag CRUD through Settings → Tags (search, usage filter, create/rename/recolour/delete, usage counts) and attribute-definition CRUD through Settings → User Attributes (search, type filter, create/edit/delete, immutable key/type display); contact links, filters and existing domain schemas complete | Required/active controls and final domain-specific fields for attribute definitions; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 85% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 95% | One governed workspace-view authority now serves audited tenant-scoped private/team Reports, KYC, Campaign, Contacts and Reactivation definitions; personal Inbox settings and team Chat History views remain preserved | Complete the approved segment-predicate/saved-filter slice while retaining module-specific validation and Audit truth. | Users/RBAC, module filters, Segments |
| Audit Timeline | 90% | CORE-07 exposes distinct Customer Timeline and Audit views over existing immutable evidence, including source references and deep links | Normalize remaining old/new values, device/login, generalized approvals and document-access evidence. Trail pagination is now contract-declared and reachable from the generated client. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
