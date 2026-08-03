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

Last synchronized: `2026-08-04T01:38:00+05:30`.

## UI Taste Modernization — Priority 1 implementation

- **Starting baseline:** `9043fe03a80b682a010304c88c5d29d8ec77d1fa`.
- **Status:** `UI-TASTE-02` is implemented and repository-validated; owner approval and authenticated
  representative-data visual comparison remain pending before Dashboard work.
- **Delivered:** named enterprise radius tiers; shared form, toolbar, filter, pagination, Button,
  Card, PageHeader, and PageContainer improvements; adoption in Contacts, Inbox, and Notification
  Center; focused shared-primitive regressions.
- **Preserved:** sidebar/navigation/routes, backend, migrations, OpenAPI/generated contracts,
  permissions, workflows, keyboard/focus, reduced motion, responsive/mobile behavior, semantic
  themes, and source-domain ownership.
- **Validation:** ESLint, TypeScript, 657 Vitest tests, production build, and high-severity production
  dependency audit pass. Host visual/reference review is pending.
- **Next:** Dashboard redesign only, blocked until owner approval.

Completion percentages below remain domain-capability measures. Shared polish improves consistency
without falsely inflating business-workflow completion.

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Dashboard | 70% | Phase 1 product experience is functional; UI-TASTE audit identifies a messaging-led hierarchy | Reframe the executive/operator surface around real reactivation stage workload, overdue follow-ups, release dates, KYC/document exceptions, activation outcomes, and factual messaging KPIs; validate realistic-data density and responsive behavior. | Reactivation, KYC, Documents, Notifications, Analytics |
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
| Reactivation | 91% | CORE-05 real CRM, CORE-07 factual Customer 360 projection, and CORE-09 actionable notification deep links | UI-TASTE maturity hierarchy, server-shared saved views/pagination, analytics, and representative-data visual/WCAG/performance evidence. | Tasks, Notifications, Analytics, shared design system |
| KYC | 85% | CORE-04 persisted queue/detail workspace, three governed checks, protected Aadhaar/PAN checklist references, Task-backed appointment lifecycle, separated reviewer/manager decisions, structured rejection, immutable audit/Timeline, SLA, Customer 360 and Reactivation handoff complete | Server pagination/saved views, production protected-media commissioning, high-volume performance, and target-browser/device WCAG regression. | Documents, Tasks, Reactivation, Customer 360 |
| Documents | 87% | Phase 4A governed documents plus CORE-04 verified Aadhaar/PAN purpose references without plaintext identity numbers | Download policies, generated-document links and final encryption/retention commissioning; no generic approval authority is required. | Download Center |
| SIM Orders | 35% | CORE-02 order/event lifecycle, address/service area, owner, serial, delivery/failure/customer confirmation, SLA and APIs are preserved; CORE-05 exposes the lightweight `SIM Required` case status | No standalone heavy UI is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, KYC evidence, SLA |
| Activation | 35% | CORE-02 record lifecycle, hand-off, verification/approval/completion/rejection rules, RBAC, audit and APIs are preserved; CORE-05 exposes `Activation Pending`, `Completed` and `Not Required` case outcomes | No standalone Activation Queue or generic approval engine is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, Notifications |
| Notifications | 85% | CORE-09 durable center plus UI-TASTE-02 shared type/status/date/assignee filters and action controls; polling, read-state, team view and deep links are preserved | Page-specific visual hierarchy, authenticated responsive review, notification settings, and separately approved optional channels. SSE/browser push/email/internal WhatsApp are not implied. | Tasks, Reactivation, user preferences, shared design system |
| Settings | 70% | Organization/application/flags/preferences routes complete | Approved business/WhatsApp hours/messages, assignment/auto-resolve/read receipts, campaign/opt-in, pipeline/SLA/notifications/security/audit controls. | Domain configuration APIs, RBAC |
| API | 85% | 193-path OpenAPI 3.1 contract; CORE-09 adds four notification paths while preserving generated TypeScript authority | Remaining final-domain routes, usage logs/IP restrictions completeness, key regeneration/revocation UX, published documentation. | Each domain milestone, Download Center |
| Webhooks | 80% | Provider webhooks and operations surface complete | Subscription governance, delivery/retry visibility, outbound final-domain events, security/usage documentation. | Domain event taxonomy, API permissions |
| Google Sheets | 0% | Not implemented | Approved credential model, contact import/sync/export jobs, mapping, audit, retries, admin UX. | Jobs, API keys/secrets, Contacts |
| WhatsApp Scan | 15% | Honest non-executing Scan Studio shell | Compliant provider contract, upload/batches/dedup/queue/results/retry/export/segments/analytics; no unofficial Web scanning. | Owner-approved compliant method, Jobs, Segments, Download Center |
| Approval Workflow | 20% | **CORE-08 — Skipped: Not required by product owner.** Existing KYC-specific approval logic and completed campaign/automation authorization safeguards are preserved. | No Approval Center, generic approval framework, approval queue, escalation system or new approval authority will be built. | Existing module-specific RBAC and audit only |
| Download Center | 30% | Backend export jobs exist | Unified user route for CSV/PDF/campaign/contact/scan/generated artifacts, status, expiry, permissions, and history. | Export jobs, Documents |

## Additional scope modules

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Shared Enterprise Design System | 90% | UI-TASTE-02 implements governed radius/density, forms, toolbars, filters, pagination, page headers and shared surface refinements with 657-test validation | Authenticated representative-data visual/reference approval, remaining priority-screen adoption, route-level bundle optimization, and final WCAG/browser matrix. | UI-TASTE-03–05 |
| Team Management | 80% | Users, roles, permissions, workload foundations complete | Online presence, assignment rules, login history, permission audit, final role matrix. | Notifications, audit, Settings |
| Tags and Attributes | 90% | CRUD, contact links, custom attributes, filters complete | Required/active controls and final domain-specific fields; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 80% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 35% | Local favourites/recent destinations and inbox views exist | Server synchronization and sharing for contacts, campaigns, reactivation, KYC, reports, and chat history. | Users/RBAC, module filters |
| Audit Timeline | 90% | CORE-07 exposes distinct Customer Timeline and Audit views over existing immutable evidence, including source references and deep links | Normalize remaining old/new values, device/login, generalized approvals and document-access evidence. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
