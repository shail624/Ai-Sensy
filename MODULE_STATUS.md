# Module Status

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

GOV-02 adds a completion gate without changing any percentage: new or materially changed screens
must also pass ADR-0012 and the twenty-point premium screen Definition of Done in Design Document
25. Visual polish alone never increases completion, and a backend-complete workflow with a generic,
inaccessible, placeholder-driven, or inconsistent experience is not final completion.

The owner-corrected CORE-05 extends the existing Reactivation and Task authorities with nine primary
statuses, six labels, governed dates, due views/actions, assignment, Audit and Timeline. CORE-07
converges those facts with identity, WhatsApp history, documents, tasks, KYC/SIM/Activation,
campaigns and evidence inside the existing Customer 360 route. Completed authorities are reused;
separate new heavy SIM fulfilment and Activation operations remain owner-deferred.

Last synchronized: `2026-08-02T17:39:04+05:30`.

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Dashboard | 70% | Phase 1 product experience — release ready | Replace messaging-only projections with revenue, reactivation, KYC, SIM, activation, SLA, queue, and task facts. | Reactivation, KYC, SIM Orders, Activation, SLA analytics |
| Inbox | 91% | Shared Inbox + Live Chat plus CORE-07 exact-contact conversation reuse | Complete intervention-request lifecycle, SLA badges, and final responsive/accessibility regression. | Notifications, SLA |
| Chat History | 40% | Exact-contact persisted conversation/message history is available in Inbox and Customer 360 | Build dedicated route with agent/date/customer/media/campaign/resolution/audit filters and export. | Audit, Download Center |
| Contacts | 95% | FR-CON-04 release-ready baseline | Final scope regression for opt-in, eligibility, assignment/export and server-shared saved views; no rebuild. | Saved Views, Reactivation |
| Customer 360 | 90% | CORE-07 factual workspace composes identity/attributes, WhatsApp threads/messages, Reactivation CRM/reminders/notes/SLA, Tasks, Documents, KYC/SIM/Activation, Campaigns, Audit and Timeline with permission-aware source deep links | Final target-device/WCAG, representative-data query-budget and production-scale commissioning; incorporate future approved source-domain facts without duplicating them. | Source domain milestones, performance lab |
| Campaigns | 85% | Broadcast engine, guided journey and existing authorization safeguards complete | Conversion/ROI to reactivation, failed-message retry UX and complete audience reports; no generic approval engine is required. | Reactivation analytics |
| Templates | 80% | Registry, create/sync/status/media flows complete | Categories/favourites server sync, button/variable preview regression, usage analytics, explicit AI placeholder. | Analytics, settings/Meta sync |
| Segments | 75% | Dynamic/static segment and preset foundation | Complete reactivation/KYC/documents/activation/engagement predicates and shared saved filters. | Domain models, Saved Views |
| Automation | 65% | Definitions, safe test runtime, trigger receipts and existing authorization concepts complete | Governed live receipt consumption, conditions/actions, delays, reminders, module-specific handoff, idempotent effects and operational UI. | Notifications, domain services |
| Analytics | 55% | Messaging rollups and exports complete | Add reactivation funnel/drop-off, lead source, KYC turnaround, SIM delivery, activation success, SLA, agent comparison, date exports. | Domain events and reporting projections |
| Executive Reports | 25% | Analytics-backed report shell | Revenue/ROI/productivity/workload/SLA/activation reports, schedules, CSV/PDF delivery. | Analytics, Download Center, Notifications |
| Reactivation | 91% | CORE-05 real CRM plus CORE-07 factual Customer 360 projection and source deep links | Server-shared saved views/pagination, rich Notification Center delivery, analytics and representative-data visual/WCAG/performance evidence. | Tasks, Notifications, Analytics |
| KYC | 85% | CORE-04 persisted queue/detail workspace, three governed checks, protected Aadhaar/PAN checklist references, Task-backed appointment lifecycle, separated reviewer/manager decisions, structured rejection, immutable audit/Timeline, SLA, Customer 360 and Reactivation handoff complete | Server pagination/saved views, production protected-media commissioning, high-volume performance, and target-browser/device WCAG regression. | Documents, Tasks, Reactivation, Customer 360 |
| Documents | 87% | Phase 4A governed documents plus CORE-04 verified Aadhaar/PAN purpose references without plaintext identity numbers | Download policies, generated-document links and final encryption/retention commissioning; no generic approval authority is required. | Download Center |
| SIM Orders | 35% | CORE-02 order/event lifecycle, address/service area, owner, serial, delivery/failure/customer confirmation, SLA and APIs are preserved; CORE-05 exposes the lightweight `SIM Required` case status | No standalone heavy UI is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, KYC evidence, SLA |
| Activation | 35% | CORE-02 record lifecycle, hand-off, verification/approval/completion/rejection rules, RBAC, audit and APIs are preserved; CORE-05 exposes `Activation Pending`, `Completed` and `Not Required` case outcomes | No standalone Activation Queue or generic approval engine is planned; future exceptional operations require an explicit owner instruction. | Reactivation status, Notifications |
| Notifications | 25% | Preferences plus CORE-05 durable assigned-user Task due evidence and scheduled dispatch adapter | Server-backed center, unread counts, deep links, mark-read, SSE/browser push and optional email/internal WhatsApp adapters. | Task due events, domain event taxonomy, user preferences |
| Settings | 70% | Organization/application/flags/preferences routes complete | Approved business/WhatsApp hours/messages, assignment/auto-resolve/read receipts, campaign/opt-in, pipeline/SLA/notifications/security/audit controls. | Domain configuration APIs, RBAC |
| API | 85% | 189-path OpenAPI 3.1 contract; CORE-05 extends Reactivation status/labels/reminder filters and adds the shared Task Snooze action | Remaining final-domain routes, usage logs/IP restrictions completeness, key regeneration/revocation UX, published documentation. | Each domain milestone, Download Center |
| Webhooks | 80% | Provider webhooks and operations surface complete | Subscription governance, delivery/retry visibility, outbound final-domain events, security/usage documentation. | Domain event taxonomy, API permissions |
| Google Sheets | 0% | Not implemented | Approved credential model, contact import/sync/export jobs, mapping, audit, retries, admin UX. | Jobs, API keys/secrets, Contacts |
| WhatsApp Scan | 15% | Honest non-executing Scan Studio shell | Compliant provider contract, upload/batches/dedup/queue/results/retry/export/segments/analytics; no unofficial Web scanning. | Owner-approved compliant method, Jobs, Segments, Download Center |
| Approval Workflow | 20% | **CORE-08 — Skipped: Not required by product owner.** Existing KYC-specific approval logic and completed campaign/automation authorization safeguards are preserved. | No Approval Center, generic approval framework, approval queue, escalation system or new approval authority will be built. | Existing module-specific RBAC and audit only |
| Download Center | 30% | Backend export jobs exist | Unified user route for CSV/PDF/campaign/contact/scan/generated artifacts, status, expiry, permissions, and history. | Export jobs, Documents |

## Additional scope modules

| Module | Completion | Current milestone / evidence | Pending work | Dependencies |
|---|---:|---|---|---|
| Team Management | 80% | Users, roles, permissions, workload foundations complete | Online presence, assignment rules, login history, permission audit, final role matrix. | Notifications, audit, Settings |
| Tags and Attributes | 90% | CRUD, contact links, custom attributes, filters complete | Required/active controls and final domain-specific fields; preserve existing model. | Settings, domain schemas |
| Global Search / Command Palette | 80% | Search and `Ctrl+K` foundation complete | Index final domain records/documents/notes/agents/tags and add all approved quick actions. | Final domain APIs |
| Saved Views | 35% | Local favourites/recent destinations and inbox views exist | Server synchronization and sharing for contacts, campaigns, reactivation, KYC, SIM, reports, and chat history. | Users/RBAC, module filters |
| Audit Timeline | 90% | CORE-07 exposes distinct Customer Timeline and Audit views over existing immutable evidence, including source references and deep links | Normalize remaining old/new values, device/login, generalized approvals and document-access evidence. | All final domain events |

## Update rule

After each milestone, update only affected rows and their dependencies. Never lower a percentage to
hide a regression; record the regression as `FAIL` in `VALIDATION_RESULTS.md` and pending work here.
Never mark a foundation-only shell complete.
