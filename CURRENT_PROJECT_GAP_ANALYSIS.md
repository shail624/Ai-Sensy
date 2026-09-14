# Current Source Project — Gap Analysis

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

This audit compares the uploaded old source project with the approved Private Vi Reactivation Operations Platform scope.

Latest local delta: **UI-REF-02** Live Chat shell; frontend **883/883**, types/build/lint and
desktop/mobile preview pass. Full populated-chat/profile/action parity is still pending in
Design Document 73. API 235, unfinished segment migration 0062 and production boundary unchanged.

## Latest working delta — UI-REF-01 (2026-09-13)

Screenshot-aligned compact rail, persistent Manage panel and real settings deep links implemented
locally. Frontend **882/882**, types/lint/build and bounded desktop/mobile preview: PASS.
Full screen/button parity remains pending in Design Document 72. Separate unfinished segment
work advances the source migration head to **0062**, with **235 OpenAPI paths** unchanged.
Cumulative backend/release revalidation and production acceptance remain pending. The historical
**77.0%** scope estimate is not visual parity and is not increased. GitHub remains `1865f4b`;
no push/deployment. PAR-VIEW-05 evidence below is historical, not current-tree certification.

Current release checkpoint: PAR-AUTO-22 remains the last complete release profile at 23/23 with
1521 backend tests and 832 frontend tests. The earlier PAR-VIEW-05 tree passed 1579 backend
tests with 6 MySQL-only skips and zero failures in 413.35s, 875 frontend tests,
focused Reports saved-view contracts 12/12, static 6/6, strict mypy across 322 files, synchronized 235-path OpenAPI and
production build; its Docker/security release rerun is
pending. `REL-CERT-01`'s prior repository/disposable-local-
deployment evidence remains preserved at 25/25. This document still describes product gaps;
a green release gate does not turn remaining scope or target-host commissioning into completed work.

## Owner-approved lightweight CRM correction

As of CORE-05, the canonical operating model is one Reactivation case with exactly one primary
status, multiple flexible labels, dated Task-backed reminders, assignment, notes, Audit, and
Customer Timeline. The completed CORE-02/04 KYC, SIM, and Activation backend foundations are
preserved, but separate new heavyweight SIM fulfilment and Activation Queue products are not a
remaining gap unless the owner explicitly reauthorizes them. SIM Required and Activation Pending
are current case statuses; Follow-up and Name Change are labels with governed dates. A concept is
never stored as both a current status and a label.

## GOV-02 quality and experience lens

This remaining-work baseline is unchanged. GOV-02 adds the permanent acceptance lens in ADR-0012
and Design Document 25: a route, shell, generic page, projected metric, browser-local substitute, or
visual placeholder does not close a product gap. Completion requires real authorized backend state,
the approved workflow, shared enterprise components, responsive and accessible behavior, complete
loading/empty/error/permission states, relevant tests, and premium original presentation.

The owner-approved local AiSensy capture library may be used only as a Git-ignored workflow and
visual-quality benchmark for the approved categories and active milestone. It is not implementation
truth and may not supply copied code, text, assets, branding, design tokens, or layouts. Conditional
AI and Automation references remain gated to their own approved milestones; prohibited ads,
payments, billing, marketplace, SaaS, reseller, multi-project, and commerce references cannot close
or create a gap.

## Already present and usable foundations

- Authentication and private-user shell
- Premium responsive layout
- Dark/light theme support
- Dashboard
- Shared Inbox / Live Chat
- Conversation filters, assignment, tags, notes, and quick replies
- Contacts, CSV import, bulk actions, tags, attributes, and segments
- Customer 360 profile converged over persisted identity, exact-contact conversations/messages,
  Reactivation CRM, reminders, notes, documents, tasks, KYC/SIM/Activation facts, campaigns, Audit,
  and Customer Timeline, with source-workflow deep links and no synthetic metrics
- Campaign management/wizard plus complete server-filtered recipient failure operations
- Governed campaign recipient-result exports with personal Download Center history
- WhatsApp template management
- Analytics foundation
- Simplified/versioned automation foundation
- Team, roles, permissions, API keys, and audit log
- Document storage, versions, verification, and signed access
- Global search and Ctrl+K command palette
- Browser-local favourites and recent destinations
- Tasks and reusable pipeline configuration
- Reactivation navigation shell
- Scan Studio shell
- API and webhook operations
- MySQL, Redis, Celery, FastAPI, and React/Vite architecture

## Present but incomplete / foundation-only

### Reactivation

The real tenant-scoped case, nine-status Kanban/list, assignment, immutable stage history, notes,
eligibility, reservation/family/conversion/SLA facts, six labels, Follow-up/Release dates, shared
Task reminders, due counters, filters, concurrency, Audit, Timeline, responsive drawer and factual
states are complete. PAR-REP-03 adds event-derived creation/source/stage/terminal outcome and
turnaround analytics plus governed reports. PAR-VIEW-01 adds audited tenant-scoped personal/team
saved filters and board/list definitions. Remaining gaps are campaign conversion attribution and
representative-data visual/WCAG/production-scale performance evidence.

### Contacts

The existing server-evaluated search, tag and enum-attribute filters, cursor paging, mobile filter
sheet, bulk operations and rule-based exports remain complete. PAR-VIEW-02 adds audited
tenant-scoped personal/team definitions through the same governed workspace-view authority as
Reactivation, without storing cursors or duplicating search/audience truth. Remaining work is final
representative-data opt-in/eligibility/assignment/export regression plus target-device/WCAG and
production-scale query commissioning.

### KYC

The dedicated KYC authority, protected document checklist references, Task appointments,
original-holder/Delhi/active-number checks, separated reviewer/manager decisions, structured
rejections, immutable evidence, and Customer 360 projection are complete and preserved.
PAR-VIEW-04 adds governed private/team definitions over URL-backed customer search and lifecycle
status without storing case/checklist/document/appointment/SLA/decision state. Remaining work is
server pagination and target-host protected-media, accessibility, and scale commissioning—not
another KYC authority.

### SIM Orders

The CORE-02 SIM order/event, delivery, ownership, serial, failure, confirmation, SLA, audit and API
foundation exists and remains preserved. The owner-approved daily CRM represents operational need
with the `SIM Required` primary case status and optional `Prepaid Required` label. A separate heavy
fulfilment workspace is intentionally not planned without a later explicit owner instruction.

### Activation

The CORE-02 Activation record, transition, approval/completion/rejection, RBAC, audit and API
foundation exists and remains preserved. The lightweight CRM uses `Activation Pending`, `Completed`
and `Not Required` case dispositions instead of a new standalone Activation Queue. Rich standalone
operations are owner-deferred rather than an active gap.

### Executive reporting

Eleven analytics report families now support asynchronous CSV, Excel, JSON and paginated PDF
delivery through the shared Download Center. Authorized executives can manage personal
daily/weekly/monthly schedules with timezone-aware automatic generation and ready notifications.
PAR-REP-03 supplies domain outcomes; PAR-REP-04 adds conversation/task teammate productivity and a
separate live pending-work table that never sums stock values across dates. Remaining report gaps
are recovered-value/revenue, campaign-to-case attribution, ROI and approved capacity/utilization
inputs plus the other artifact families. PAR-VIEW-05 adds governed personal/team definitions over
the existing period, granularity and comparison URL contract; none of the missing business facts
will be inferred without an approved source of truth.

### Notifications

The durable server-backed Notification Center, unread/read state, team view, deep links, filtering,
polling, mark-read actions and idempotent scheduled-report-ready deliveries are implemented. Remaining gaps are notification settings, final
page-specific visual/responsive acceptance, and only separately approved optional delivery channels;
SSE, browser push, email, and internal WhatsApp are not implied.

### Saved views and favourites

Browser-local favourites/recent destinations and organization-shared Chat History views now join
one audited personal/team workspace-view authority serving Reports, KYC, Campaigns, Contacts and
Reactivation. Reports are complete through PAR-VIEW-05; the approved Segment predicate/saved-filter
slice is the remaining cross-module gap.

### Approval workflows

**CORE-08 — Skipped: Not required by product owner.** A generic
Approval Center, approval framework, queue, escalation system, or new approval authority is not a
product gap and must not be built. Existing KYC-specific approval logic, campaign/automation
authorization concepts, requester/reviewer separation, RBAC, tenant isolation, and completed
authorization safeguards remain preserved and must not be deleted or rewritten.

### Integrations

- Webhook infrastructure exists.
- Google Sheets integration is not implemented.

### Chat History

A dedicated permission-aware Chat History route provides conversation search, status, agent,
channel and tag filtering, cursor pagination, full messages and an audit deep link. PAR-DL-02 adds
`inbox:export`-governed complete/date-bounded PDF/CSV/XLSX/JSON transcripts over the persisted ledger,
with progress/direct download and personal Download Center history. PAR-HIST-01 adds list-level
date/campaign/media/audit-scoped filters and audited organization-shared views. Remaining work is
authenticated representative-data device/browser/WCAG review and production-scale query
commissioning.

### Campaigns

The broadcast engine, guided campaign journey, pacing/scheduling/lifecycle controls, smart retry,
crash-safe batches and PAR-DL-03 governed results artifacts are complete. PAR-CAM-01 makes the
persisted recipient ledger fully operable from Campaign Detail with declared server status filters,
total-aware cursor paging, tenant-safe current identity, safe error/retry/lifecycle evidence and an
explicit failed-recipient retry boundary. PAR-VIEW-03 adds audited tenant-scoped private/team
definitions over URL-backed list search/status/sort, excludes transient page state and leaves send/
lifecycle truth untouched. Remaining gaps are campaign-to-reactivation conversion
attribution and recovered-value/revenue/ROI facts from an approved source of truth, plus target-host
query-plan/scale and authenticated UX commissioning. Delivery counts are not treated as conversion
or revenue.

### Customer 360

CORE-07 completes the factual Contact workspace by composing the existing persisted authorities for
identity and attributes, exact-contact WhatsApp threads/messages, Reactivation status/labels,
reminders, assignment, notes, Documents, Tasks, KYC/SIM/Activation facts, Campaign participation,
Audit, and Customer Timeline. It introduces no snapshot table, duplicate record, synthetic metric,
or parallel workflow. Remaining Customer 360 work is limited to final target-device/WCAG and
production-scale commissioning plus future facts added by separately approved source milestones.

### Lower-severity maintenance findings

- The owner-bootstrap CLI currently accepts reserved `.test` email addresses that the login request
  schema rejects. This does not affect valid production addresses or tenant isolation, but the two
  validation boundaries should be aligned in a later maintenance milestone.

### Download Center

PAR-DL-01 implements the personal, tenant- and permission-scoped Download Center for existing
contact exports and analytics reports, including normalized status/expiry, fresh signed links,
polling, filters and keyset history. PAR-REP-01 adds real analytics PDF artifacts beside CSV, Excel
and JSON; PAR-REP-02 automatically lands scheduled Analytics artifacts with a ready-notification
deep link; PAR-DL-02 adds governed Chat History transcripts; PAR-DL-03 adds tenant/requester/
permission-scoped campaign recipient-result artifacts without a second artifact pipeline. Remaining
scope is source generation and Center integration for compliant Scan results and generated documents.

## Explicitly excluded

The following must not be added:

- Ads Manager
- WhatsApp Payments
- SaaS billing and subscriptions
- Multi-project tenancy
- Public signup
- Reseller tools
- Integration marketplace
- Promotional/trial/upgrade screens

## Correct first engineering milestone

1. Lock navigation and remove unrelated product concepts.
2. Add server-owned domain models:
   - ReactivationCase
   - ReactivationStageEvent
   - EligibilityCheck
   - KycCase and KycDecision
   - SimOrder and SimOrderEvent
   - ActivationRecord
   - SlaPolicy and SlaEvent
3. Add migrations, repositories, services, schemas, RBAC, and APIs. **Complete through `0034`.**
4. Connect Reactivation Kanban to real cases and transitions. **Complete.**
5. Deliver protected KYC operations and Customer 360 projection. **Complete and preserved.**
6. Apply the owner-approved lightweight status/label/Task-reminder CRM correction. **Complete.**
7. Converge remaining factual CRM projections in Customer 360 without adding heavy standalone
   SIM/Activation products. **Complete.**
8. **CORE-08 — Skipped: Not required by product owner.**
9. Build CORE-09, the shared server-backed Notification Center over existing due evidence. **Complete.**
10. Add dedicated Chat History. **Read workspace, governed transcript export, advanced filters and
    shared views complete; authenticated representative-data WCAG/device/browser and target-host
    query commissioning remain.** Continue commissioning without rebuilding the route, query or
    artifact pipeline.
