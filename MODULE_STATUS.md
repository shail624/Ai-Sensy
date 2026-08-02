# Module Status

Completion percentages are evidence-based estimates against
`VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`, not measures of code volume or visual polish. Existing
foundations are preserved; percentages increase only when real backend contracts, permissions,
audit behavior, UI integration, and tests are complete.

GOV-02 adds a completion gate without changing any percentage: new or materially changed screens
must also pass ADR-0012 and the twenty-point premium screen Definition of Done in Design Document
25. Visual polish alone never increases completion, and a backend-complete workflow with a generic,
inaccessible, placeholder-driven, or inconsistent experience is not final completion.

CORE-02 completed the real tenant-scoped Vi domain foundation, permission-scoped lifecycle APIs,
immutable evidence, audit/Timeline projections, migration `0032`, and generated contracts. It did
not build the later Reactivation, KYC, SIM, or Activation operational screens.

Last synchronized: `2026-08-02T11:53:32+05:30`.

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Dashboard | 70% | Phase 1 product experience — release ready | Replace messaging-only projections with revenue, reactivation, KYC, SIM, activation, SLA, queue, and task facts. | Reactivation, KYC, SIM Orders, Activation, SLA analytics |
| Inbox | 90% | Shared Inbox + Live Chat simplicity — release ready | Complete intervention-request lifecycle, document/customer-domain context, SLA badges, and final responsive/accessibility regression. | Notifications, Customer 360, SLA |
| Chat History | 35% | Conversation history exists in Inbox/Customer 360 | Build dedicated route with agent/date/customer/media/campaign/resolution/audit filters and export. | Conversations API extensions, audit, Download Center |
| Contacts | 95% | FR-CON-04 release-ready baseline | Final scope regression for opt-in, eligibility, assignment/export and server-shared saved views; no rebuild. | Saved Views, Reactivation |
| Customer 360 | 65% | 12-tab profile and governed documents foundation | Connect real reactivation, KYC, SIM, activation, reminders/SLA, family numbers, and contact conversation history. | All Phase 1 domain models |
| Campaigns | 85% | Broadcast engine and guided journey complete | General approval linkage, conversion/ROI to reactivation, failed-message retry UX, complete audience reports. | Approval Workflow, Reactivation analytics |
| Templates | 80% | Registry, create/sync/status/media flows complete | Categories/favourites server sync, button/variable preview regression, usage analytics, explicit AI placeholder. | Analytics, settings/Meta sync |
| Segments | 75% | Dynamic/static segment and preset foundation | Complete reactivation/KYC/documents/activation/engagement predicates and shared saved filters. | Domain models, Saved Views |
| Automation | 65% | Definitions, safe test runtime, trigger receipts complete | Governed live receipt consumption, conditions/actions, delays, reminders, approval/handoff, idempotent effects, operational UI. | Notifications, Approval Workflow, domain services |
| Analytics | 55% | Messaging rollups and exports complete | Add reactivation funnel/drop-off, lead source, KYC turnaround, SIM delivery, activation success, SLA, agent comparison, date exports. | Domain events and reporting projections |
| Executive Reports | 25% | Analytics-backed report shell | Revenue/ROI/productivity/workload/SLA/activation reports, schedules, CSV/PDF delivery. | Analytics, Download Center, Notifications |
| Reactivation | 45% | CORE-02 case, stage-event, eligibility, SLA, RBAC, audit, Timeline, and API foundation complete | CORE-03 real Kanban, assignments, reminders, reservations/family/conversion facts, visual workflow, and saved views. | Generated Vi contracts, Customer 360, Notifications |
| KYC | 40% | CORE-02 case/checks, immutable review/manager decisions, approval boundary, tenant/RBAC/audit APIs complete | CORE-04 protected workspace, document checklist/access policies, appointment UX, and full operational review journey. | Reactivation, Approval Workflow, Documents |
| Documents | 85% | Phase 4A governed documents — release ready | Domain-specific document checklists, approval/download policies, generated-document links, final encryption/retention commissioning. | KYC, Approval Workflow, Download Center |
| SIM Orders | 35% | CORE-02 order/event lifecycle, address/service area, owner, serial, delivery/failure/customer confirmation, SLA and APIs complete | CORE-05 fulfilment table/detail/mobile UI, notification publishers, operational retry and exception handling. | KYC approval, SLA, Activation |
| Activation | 35% | CORE-02 record lifecycle, SIM hand-off, verification/approval/completion/rejection rules, RBAC, audit and APIs complete | CORE-06 activation queue/list/detail UI, notification hand-off, and operational completion journey. | SIM Orders, Approval Workflow, Notifications |
| Notifications | 20% | Preferences foundation | Server-backed center, unread counts, deep links, mark-read, SSE/browser push and optional email/internal WhatsApp adapters. | Domain event taxonomy, user preferences |
| Settings | 70% | Organization/application/flags/preferences routes complete | Approved business/WhatsApp hours/messages, assignment/auto-resolve/read receipts, campaign/opt-in, pipeline/SLA/notifications/security/audit controls. | Domain configuration APIs, RBAC |
| API | 82% | 182-path OpenAPI 3.1 contract; CORE-02 adds 29 typed Vi lifecycle paths | Remaining final-domain routes, usage logs/IP restrictions completeness, key regeneration/revocation UX, published documentation. | Each domain milestone, Download Center |
| Webhooks | 80% | Provider webhooks and operations surface complete | Subscription governance, delivery/retry visibility, outbound final-domain events, security/usage documentation. | Domain event taxonomy, API permissions |
| Google Sheets | 0% | Not implemented | Approved credential model, contact import/sync/export jobs, mapping, audit, retries, admin UX. | Jobs, API keys/secrets, Contacts |
| WhatsApp Scan | 15% | Honest non-executing Scan Studio shell | Compliant provider contract, upload/batches/dedup/queue/results/retry/export/segments/analytics; no unofficial Web scanning. | Owner-approved compliant method, Jobs, Segments, Download Center |
| Approval Workflow | 20% | Campaign/automation approval concepts only | General request/decision engine for campaign, KYC, eligibility override, SIM issue, activation, export, and document download. | RBAC, audit, Notifications |
| Download Center | 30% | Backend export jobs exist | Unified user route for CSV/PDF/campaign/contact/scan/generated artifacts, status, expiry, permissions, and history. | Export jobs, Documents, Approval Workflow |

## Additional scope modules

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Team Management | 80% | Users, roles, permissions, workload foundations complete | Online presence, assignment rules, login history, permission audit, final role matrix. | Notifications, audit, Settings |
| Tags and Attributes | 90% | CRUD, contact links, custom attributes, filters complete | Required/active controls and final domain-specific fields; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 80% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 35% | Local favourites/recent destinations and inbox views exist | Server synchronization and sharing for contacts, campaigns, reactivation, KYC, SIM, reports, and chat history. | Users/RBAC, module filters |
| Audit Timeline | 82% | CORE-02 projects Reactivation, eligibility, KYC, SIM, Activation, and SLA evidence through existing audit/Customer Timeline authorities | Normalize remaining old/new values, device/login, generalized approvals, document access and assignment evidence. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
